"""
discipline.py — Host-LLM engine shared by every rup-* skill (ADR-0012).

The skills do not call any LLM. The agent that invokes the skill (Claude Code,
Hermes, …) IS the LLM. A skill run has two deterministic steps:

  1. Work packet   `run.py "<briefing>" [--input F] --phase P`
     Prints, as markdown, everything the host needs to produce the artifacts:
     the RUP roles of the discipline (goal, perspective, mission), the exact
     artifact headings it must write, the briefing, and the artifacts already in
     `.context/` that this one builds on. Read-only.

  2. Record        `run.py --record FILE|- --phase P ["<briefing>" | --input F]`
     Validates that the document has one `## <Artifact>` section for every
     required artifact and writes it to `.context/docs/<NN-phase>/<skill>.md`
     (+ a row in `.context/tracking/rup-log.md`) — mandatory persistence (ADR-0011).

Chaining: a discipline's packet embeds the governance artifact and the artifacts
of the disciplines before it (same phase) that exist in `.context/`, so running
the disciplines in order gives each one the output of the previous ones.

Pure standard library.
"""
import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from _shared import context as ctx
from _shared.rup import (DISCIPLINES, EXIT_USAGE, MAX_PRIOR_ARTIFACT_CHARS,
                         ORCHESTRATOR_SKILL, PHASES)

GENERAL_RULES = [
    "Follow the RUP conventions (Kruchten, *The Rational Unified Process: An "
    "Introduction*, 3rd ed.) for each artifact type.",
    "Be specific and traceable: reuse the names, IDs and decisions of the earlier "
    "artifacts below and reference them explicitly.",
    "Where information is missing, state the assumption explicitly instead of "
    "inventing facts, and list open questions at the end of the artifact.",
]


# ─── small helpers ───────────────────────────────────────────────────────

def cmdline(args):
    """A shell command line for the host to copy, quoted for the current OS."""
    args = [str(a) for a in args]
    if os.name == "nt":
        return subprocess.list2cmdline(args)
    return " ".join(shlex.quote(a) for a in args)


def fail(message, code=EXIT_USAGE):
    print(f"❌ Error: {message}")
    sys.exit(code)


def artifact_body(text):
    """The content of a `.context/` artifact, without the provenance header/briefing."""
    marker = "\n## Artifacts\n"
    return text.split(marker, 1)[1] if marker in text else text


def required_artifacts(spec):
    return [a for agent in spec["agents"] for a in agent["artifacts"]]


def _norm(text):
    text = re.sub(r"\(.*?\)", " ", text.lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def missing_artifacts(content, required):
    """Required artifacts with no `## ` heading containing their name.

    Matching ignores case, punctuation and parenthesised qualifiers, so
    `## Supplementary Specifications` satisfies "Supplementary Specifications (FURPS)".
    """
    headings = [_norm(line[3:]) for line in content.splitlines()
                if line.startswith("## ")]
    return [a for a in required if not any(_norm(a) in h for h in headings)]


# ─── context of earlier work ─────────────────────────────────────────────

def prior_artifacts(context_dir, phase, skill, discipline_key=None):
    """Artifacts in `.context/` this run builds on, in RUP order.

    A discipline sees the governance artifact plus the disciplines before it;
    the orchestrator (governance) sees every discipline artifact of the phase.
    Returns [(label, path, body)].
    """
    items = []
    if skill != ORCHESTRATOR_SKILL:
        items.append(("Project Management (rup-orchestrator)", ORCHESTRATOR_SKILL))
    for key, d in DISCIPLINES.items():
        if key == discipline_key:
            break
        items.append((f"{d['title']} ({d['skill']})", d["skill"]))

    found = []
    for label, s in items:
        path = ctx.artifact_path(context_dir, phase, s)
        if path.is_file():
            body = artifact_body(path.read_text(encoding="utf-8", errors="replace")).strip()
            if len(body) > MAX_PRIOR_ARTIFACT_CHARS:
                body = (body[:MAX_PRIOR_ARTIFACT_CHARS]
                        + f"\n[… truncated — full artifact in {path}]")
            found.append((label, path, body))
    return found


# ─── work packet ─────────────────────────────────────────────────────────

# A positional briefing up to this size is repeated in the suggested --record
# command (for the provenance header); longer ones should go through --input.
MAX_INLINE_BRIEFING = 400


def record_command(script, phase, context_dir, briefing_file=None, briefing=None):
    cmd = [sys.executable, script, "--record", "<your-document.md>", "--phase", phase,
           "--context-dir", context_dir]
    if briefing_file:
        cmd += ["--input", briefing_file]
    elif briefing and len(briefing) <= MAX_INLINE_BRIEFING:
        cmd.append(briefing.strip())
    return cmdline(cmd)


def render_packet(spec, *, skill, script, briefing, phase, context_dir, briefing_file=None):
    target = ctx.artifact_path(context_dir, phase, skill)
    lines = []
    if not ctx.has_consent(context_dir):
        lines += ["⚠️ .context/ not authorized yet — recording will ask for authorization "
                  "(rup-context --init).", ""]
    lines += [
        f"# RUP work packet — {spec['title']} (`{skill}`)",
        "",
        f"- **Phase**: {phase} — milestone {ctx.PHASE_MILESTONES[phase]}",
        f"- **Artifact goes to**: `{target}`",
        "",
        "## How to execute — you, the agent running this skill, are the LLM",
        "",
        "1. Play each role below **in order**, writing ONE markdown document.",
        "2. Start each role with `# <Role>` and write every artifact it owns under a "
        "level-2 heading with its exact name: `## <Artifact>`.",
    ]
    for i, rule in enumerate(GENERAL_RULES + spec.get("instructions", []), start=3):
        lines.append(f"{i}. {rule}")
    n = 3 + len(GENERAL_RULES) + len(spec.get("instructions", []))
    lines += [
        f"{n}. Save the document to a file and record it (mandatory — it validates "
        "every required heading and writes `.context/`):",
        "",
        "   ```bash",
        f"   {record_command(script, phase, context_dir, briefing_file, briefing)}",
        "   ```",
        "",
        "   Use `--record -` to pass the document on stdin. If the recorder lists "
        "missing artifacts, add those sections and record again.",
        "",
        "## Briefing",
        "",
        briefing.strip(),
        "",
    ]

    prior = prior_artifacts(context_dir, phase, skill, spec.get("key"))
    if prior:
        lines += ["## Earlier artifacts in `.context/` (build on them)", ""]
        for label, path, body in prior:
            lines += [f"### {label} — `{path}`", "", body, ""]

    lines += ["## Roles", ""]
    for i, agent in enumerate(spec["agents"], start=1):
        lines += [
            f"### {i}. {agent['role']}",
            "",
            f"- **Goal**: {agent['goal']}",
            f"- **Perspective**: {agent['backstory']}",
            f"- **Mission**: {agent['mission']}",
            "- **Artifacts** (one `## ` section each):",
        ]
        lines += [f"  - {a}" for a in agent["artifacts"]]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ─── record ──────────────────────────────────────────────────────────────

def read_document(source):
    try:
        text = sys.stdin.read() if source == "-" else Path(source).read_text(
            encoding="utf-8", errors="replace")
    except OSError as e:
        fail(f"cannot read --record source: {e}")
    if not text.strip():
        fail("the recorded document is empty")
    return text


def record(spec, *, skill, content, briefing, phase, context_dir):
    """Validate the host's document and persist it into `.context/`."""
    missing = missing_artifacts(content, required_artifacts(spec))
    if missing:
        print("❌ Error: the document is missing required artifacts — add a "
              "`## <Artifact>` section for each and record again:")
        for a in missing:
            print(f"  - {a}")
        print("Nothing was written to .context/.")
        sys.exit(EXIT_USAGE)
    ctx.ensure_writable(context_dir, phase)
    path = ctx.write_artifact(context_dir, content, skill=skill, title=spec["title"],
                              phase=phase, briefing=briefing)
    print(f"🗂️  Artifact written to {path}")
    print(f"📝 Logged in {Path(context_dir) / ctx.LOG_RELATIVE}")
    return path


# ─── CLI ─────────────────────────────────────────────────────────────────

def add_common_args(parser):
    parser.add_argument("briefing", nargs="?",
                        help="Briefing / business demand (or use --input)")
    parser.add_argument("--input", dest="input_file",
                        help="File with the briefing (alternative to the positional)")
    parser.add_argument("--phase", choices=PHASES, default="Elaboration",
                        help="RUP phase (default: Elaboration)")
    parser.add_argument("--context-dir",
                        help="The .context/ directory (default: $RUP_CONTEXT_DIR, else the "
                             "nearest .context/ up to the git root)")
    parser.add_argument("--record", metavar="FILE",
                        help="Validate the document you wrote (FILE, or - for stdin) and "
                             "write it to .context/ (mandatory step)")


def read_briefing(args, required=True):
    briefing = args.briefing
    if args.input_file:
        try:
            briefing = Path(args.input_file).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            fail(f"cannot read --input file: {e}")
    if required and not (briefing or "").strip():
        fail("provide the briefing (positional or --input)")
    return briefing or ""


def run(spec, args, *, script):
    """Packet (default) or record, for a parsed `args`."""
    skill = Path(script).resolve().parent.parent.name
    context_dir = ctx.resolve_context_dir(args.context_dir)

    if args.record:
        content = read_document(args.record)
        briefing = read_briefing(args, required=False) or "(briefing not provided at record time)"
        record(spec, skill=skill, content=content, briefing=briefing,
               phase=args.phase, context_dir=context_dir)
        return

    briefing = read_briefing(args)
    print(render_packet(spec, skill=skill, script=str(Path(script).resolve()),
                        briefing=briefing, phase=args.phase, context_dir=context_dir,
                        briefing_file=(str(Path(args.input_file).resolve())
                                       if args.input_file else None)))


def main(spec, *, script):
    parser = argparse.ArgumentParser(
        description=f"RUP {spec['title']} — prints the work packet for the host agent "
                    f"(the LLM) and records its result into .context/",
    )
    add_common_args(parser)
    run(spec, parser.parse_args(), script=script)
