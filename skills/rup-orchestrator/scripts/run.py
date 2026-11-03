#!/usr/bin/env python3
"""
rup-orchestrator — RUP lifecycle governance (host-LLM, ADR-0012).

The agent running this skill is the LLM. This script never calls a model: it
prints work packets and protocols for the agent, records the agent's documents
into .context/ (mandatory, ADR-0011) and computes Use Case Points exactly.

Usage:
  python run.py "demand" --phase Inception                 # governance work packet
  python run.py --record doc.md --phase Inception "demand" # validate + write .context/
  python run.py "demand" --discipline requirements         # a discipline's work packet
  python run.py "demand" --auto                            # iteration protocol (all steps)
  python run.py --status --phase Elaboration               # what is recorded in .context/
  python run.py --sizing-template > sizing.json
  python run.py --estimate --sizing sizing.json [--json]   # UCP (also written to .context/)
  python run.py --list
"""
import argparse
import subprocess
import sys
from pathlib import Path

# _shared/ sits in the skills root: next to this skill (repo, Claude Code) or one
# level up when the agent nests skills in a category (Hermes: skills/<category>/).
_SKILL_DIR = Path(__file__).resolve().parent.parent
for _root in (_SKILL_DIR.parent, _SKILL_DIR.parent.parent):
    if (_root / "_shared" / "discipline.py").is_file():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break

from _shared import context as rup_context  # noqa: E402
from _shared import discipline  # noqa: E402
from _shared.rup import (DISCIPLINES, EXIT_USAGE, PHASES,  # noqa: E402
                         setup_console)

SKILL = _SKILL_DIR.name
PHASE_MILESTONES = rup_context.PHASE_MILESTONES
TITLE = "Project Management"
SIZING_TITLE = "Software Sizing & Effort Estimation"
SIZING_SUFFIX = "-sizing"
# Root holding the discipline skills (siblings of this one): skills/ in the repo,
# ~/.claude/skills/ or <hermes>/skills/<category>/ once installed.
RUP_ROOT = _SKILL_DIR.parent

PM = {
    "slug": "rup-orchestrator",
    "role": "RUP Orchestrator",
    "goal": "Govern the RUP lifecycle: produce and maintain the Software Development Plan, Business Case, Risk List, Software Sizing & Effort Estimation (FPA, Use Case Points, COCOMO II), Iteration Plan, Iteration/Status Assessments, Work Orders and the Measurement Plan/Database.",
    "backstory": "Project Manager who runs the RUP lifecycle: you are the only interface to the user, you translate business goals into Work Orders, size the software and estimate effort with Function Points, Use Case Points and COCOMO II, balance scope, schedule, risk and cost, and judge each iteration against formal acceptance criteria.",
    "mission": "Classify the demand into the RUP phase and the disciplines it touches; update the Software Development Plan, Business Case and Risk List; size the software and estimate the effort per iteration; plan the iteration with one Work Order per discipline involved; state the acceptance criteria and the measurement plan.",
    "artifacts": [
        "Phase Classification",
        "Software Development Plan (SDP)",
        "Business Case",
        "Risk List",
        "Software Sizing & Effort Estimation",
        "Iteration Plan",
        "Work Orders",
        "Acceptance Criteria & Measurement Plan",
    ],
}


def discipline_run_py(discipline_key: str) -> Path:
    return RUP_ROOT / DISCIPLINES[discipline_key]["skill"] / "scripts" / "run.py"


def this_script() -> str:
    return str(Path(__file__).resolve())


def governance_spec(phase, context_dir):
    """The governance work packet spec (instructions carry the exact sizing commands)."""
    py, me = sys.executable, this_script()
    template = discipline.cmdline([py, me, "--sizing-template"])
    estimate = discipline.cmdline([py, me, "--estimate", "--sizing", "<sizing.json>",
                                   "--phase", phase, "--context-dir", context_dir])
    disciplines = ", ".join(f"`{d['skill']}` ({d['title']})" for d in DISCIPLINES.values())
    return {
        "key": None,
        "title": TITLE,
        "agents": [PM],
        "instructions": [
            "Use Case Points are computed by code, never by you: write the sizing "
            f"model (empty template: `{template}`), run `{estimate}` — it prints UAW, "
            "UUCW, UUCP, TCF, EF, UCP and the effort, and records "
            "`rup-orchestrator-sizing.md` in .context/ — and copy those numbers into "
            "the Software Sizing & Effort Estimation section. FPA (IFPUG/NESMA) and "
            "COCOMO II/SLOC are your estimates: show the inputs and the arithmetic.",
            f"Write one Work Order per discipline involved, addressed to its skill: {disciplines}.",
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════
# Software Sizing & Effort Estimation — Use Case Points (UCP)
#
# Pure-Python, deterministic estimator following the UCP method (Karner /
# Schneider & Winters). The host agent builds the sizing model and runs
# `--estimate`; it never computes UCP itself. FPA (IFPUG/NESMA) and COCOMO II
# are estimated by the host from the use-case and data models.
# ═══════════════════════════════════════════════════════════════════════════

# Unadjusted Actor Weight (UAW): simple=1, average=2, complex=3
ACTOR_WEIGHTS = {"simple": 1, "average": 2, "complex": 3}

# Unadjusted Use Case Weight (UUCW): simple=5, average=10, complex=15
# (complexity by number of transactions: <=3, 4..7, >7)
USECASE_WEIGHTS = {"simple": 5, "average": 10, "complex": 15}

# Technical Complexity Factors (TCF): 13 factors, weight 0..5 (2 = neutral)
TECHNICAL_FACTORS = [
    ("T1", "Distributed system"),
    ("T2", "Performance / response-time objectives"),
    ("T3", "End-user efficiency"),
    ("T4", "Complex internal processing"),
    ("T5", "Reusable code"),
    ("T6", "Easy to install"),
    ("T7", "Easy to use"),
    ("T8", "Portable"),
    ("T9", "Easy to change"),
    ("T10", "Concurrent"),
    ("T11", "Special security features"),
    ("T12", "Provides direct access for third parties"),
    ("T13", "Special user training facilities required"),
]

# Environmental Factors (EF): 8 factors, weight 0..5 (3 = neutral)
ENVIRONMENTAL_FACTORS = [
    ("F1", "Familiar with the project model", "negative"),
    ("F2", "Application experience", "negative"),
    ("F3", "Object-oriented experience", "negative"),
    ("F4", "Lead analyst capability", "negative"),
    ("F5", "Motivation", "negative"),
    ("F6", "Stable requirements", "negative"),
    ("F7", "Part-time workers", "positive"),
    ("F8", "Difficult programming language", "positive"),
]

DEFAULT_ACTORS = [{"type": "simple", "count": 0},
                  {"type": "average", "count": 0},
                  {"type": "complex", "count": 0}]
DEFAULT_USECASES = [{"type": "simple", "count": 0},
                    {"type": "average", "count": 0},
                    {"type": "complex", "count": 0}]


def compute_ucp(actors=None, usecases=None, technical_factors=None,
                environmental_factors=None, productivity_hours=20.0,
                default_tcf=1.0, default_ef=1.0):
    """Compute Unadjusted/Ajusted Use Case Points and the effort in hours.

    actors: list of {"type": "simple|average|complex", "count": n}
    usecases: list of {"type": "simple|average|complex", "count": n}
    technical_factors: {T1..T13: 0..5}   (missing -> 2 = neutral)
    environmental_factors: {F1..F8: 0..5} (missing -> 3 = neutral)
    productivity_hours: hours per Use Case Point (default 20).
    Returns a dict with every intermediate value.
    """
    actors = actors or []
    usecases = usecases or []
    tf = technical_factors or {}
    ef = environmental_factors or {}

    uaw = sum(ACTOR_WEIGHTS[a["type"]] * a["count"] for a in actors)
    uucw = sum(USECASE_WEIGHTS[u["type"]] * u["count"] for u in usecases)
    uucp = uaw + uucw

    # TCF = 0.65 + 0.01 * sum(T1..T13). An EMPTY factor map is neutral: TCF = 1.0.
    # When factors are provided, each is rated 0..5 (missing ones default to 2).
    if tf:
        tf_sum = sum(int(tf.get(k, 2)) for k, _ in TECHNICAL_FACTORS)
        tcf = round(0.65 + 0.01 * tf_sum, 4)
    else:
        tf_sum = None
        tcf = 1.0

    # EF = 1.4 - 0.03 * sum(F1..F8). An EMPTY factor map is neutral: EF = 1.0.
    # F1..F6 (negative) are inverted (5 - value); F7..F8 (positive) use the value.
    if ef:
        ef_sum = 0
        for key, _, sense in ENVIRONMENTAL_FACTORS:
            v = int(ef.get(key, 3))
            ef_sum += (5 - v) if sense == "negative" else v
        ef_val = round(1.4 - 0.03 * ef_sum, 4)
    else:
        ef_sum = None
        ef_val = 1.0

    ucp = round(uucp * tcf * ef_val, 2)
    effort_hours = round(ucp * productivity_hours, 1)

    return {
        "method": "Use Case Points (UCP)",
        "actors": actors,
        "usecases": usecases,
        "uaw": uaw,
        "uucw": uucw,
        "uucp": uucp,
        "technical_factor_sum": tf_sum,
        "tcf": tcf,
        "environmental_factor_sum": ef_sum,
        "ef": ef_val,
        "ucp": ucp,
        "productivity_hours_per_ucp": productivity_hours,
        "effort_hours": effort_hours,
    }


class SizingError(ValueError):
    """Invalid sizing model (bad JSON shape, unknown type, out-of-range factor)."""


def _validate_counts(items, weights, label):
    if not isinstance(items, list):
        raise SizingError(f"{label} must be a list of {{type, count}}")
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise SizingError(f"{label}[{i}] must be an object {{type, count}}")
        if item.get("type") not in weights:
            raise SizingError(f"{label}[{i}].type must be one of {sorted(weights)}, "
                              f"got {item.get('type')!r}")
        count = item.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise SizingError(f"{label}[{i}].count must be a non-negative integer, "
                              f"got {count!r}")


def _validate_factors(factors, valid_keys, label):
    if not isinstance(factors, dict):
        raise SizingError(f"{label} must be an object {{key: 0..5}}")
    for key, value in factors.items():
        if key not in valid_keys:
            raise SizingError(f"{label}: unknown factor {key!r} (valid: {', '.join(valid_keys)})")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 5:
            raise SizingError(f"{label}.{key} must be a number 0..5, got {value!r}")


def ucp_from_model(data):
    """Validate a sizing model (dict) and compute the UCP. Raises SizingError."""
    if not isinstance(data, dict):
        raise SizingError("the sizing model must be a JSON object")
    actors = data.get("actors", DEFAULT_ACTORS)
    usecases = data.get("usecases", DEFAULT_USECASES)
    tf = data.get("technical_factors", {}) or {}
    ef = data.get("environmental_factors", {}) or {}
    _validate_counts(actors, ACTOR_WEIGHTS, "actors")
    _validate_counts(usecases, USECASE_WEIGHTS, "usecases")
    _validate_factors(tf, [k for k, _ in TECHNICAL_FACTORS], "technical_factors")
    _validate_factors(ef, [k for k, _, _ in ENVIRONMENTAL_FACTORS], "environmental_factors")
    try:
        hours = float(data.get("productivity_hours", 20.0))
    except (TypeError, ValueError):
        raise SizingError("productivity_hours must be a number")
    if hours <= 0:
        raise SizingError("productivity_hours must be > 0")
    return compute_ucp(actors=actors, usecases=usecases, technical_factors=tf,
                       environmental_factors=ef, productivity_hours=hours)


def estimate_from_json(path):
    """Compute UCP from a JSON sizing file. Raises SizingError / OSError."""
    import json
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SizingError(f"invalid JSON in {path}: {e}")
    return ucp_from_model(data)


def template_sizing():
    """Return an empty sizing model (JSON) to fill in and pass to --estimate.

    Factors start empty = neutral (TCF = EF = 1.0). Fill each 0..5 to adjust.
    """
    import json
    return json.dumps({
        "note": "Fill the actor/use-case counts. Factor maps are optional: empty = "
                "neutral (TCF=EF=1.0); fill each 0..5 to adjust. "
                "T1..T13 = " + ", ".join(k for k, _ in TECHNICAL_FACTORS) + "; "
                "F1..F8 = " + ", ".join(k for k, _, _ in ENVIRONMENTAL_FACTORS) + ".",
        "actors": DEFAULT_ACTORS,
        "usecases": DEFAULT_USECASES,
        "technical_factors": {},
        "environmental_factors": {},
        "productivity_hours": 20,
    }, indent=2)


def render_estimate_md(result, source):
    """Markdown body of the sizing artifact written to .context/."""
    import json
    rows = [
        ("UAW (Unadjusted Actor Weight)", result["uaw"]),
        ("UUCW (Unadjusted Use Case Weight)", result["uucw"]),
        ("UUCP (Unadjusted Use Case Points)", result["uucp"]),
        ("TCF (Technical Complexity Factor)", result["tcf"]),
        ("EF (Environmental Factor)", result["ef"]),
        ("UCP (Use Case Points)", result["ucp"]),
        (f"Effort @ {result['productivity_hours_per_ucp']} h/UCP", f"{result['effort_hours']} h"),
    ]
    table = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return (f"Method: {result['method']} — computed deterministically (`compute_ucp`).\n"
            f"Source model: {source}\n\n"
            "| Metric | Value |\n|--------|-------|\n" + table + "\n\n"
            "```json\n" + json.dumps(result, indent=2) + "\n```")


def print_estimate(result):
    """Human-readable UCP report."""
    print("\n🧮 Software Sizing & Effort Estimation — Use Case Points (UCP)")
    print("─" * 62)
    print("  Actors:")
    for a in result["actors"]:
        print(f"    - {a['type']:8s} x{a['count']:<3d} "
              f"(weight {ACTOR_WEIGHTS[a['type']]})")
    print("  Use cases:")
    for u in result["usecases"]:
        print(f"    - {u['type']:8s} x{u['count']:<3d} "
              f"(weight {USECASE_WEIGHTS[u['type']]})")
    print("─" * 62)
    print(f"  UAW (Unadjusted Actor Weight)       : {result['uaw']}")
    print(f"  UUCW (Unadjusted Use Case Weight)   : {result['uucw']}")
    print(f"  UUCP (Unadjusted Use Case Points)   : {result['uucp']}")
    tf_sum = result["technical_factor_sum"]
    ef_sum = result["environmental_factor_sum"]
    print(f"  TCF (Technical Complexity Factor)   : {result['tcf']}"
          + (f"  (sum {tf_sum})" if tf_sum is not None else "  (neutral)"))
    print(f"  EF  (Environmental Factor)          : {result['ef']}"
          + (f"  (sum {ef_sum})" if ef_sum is not None else "  (neutral)"))
    print(f"  UCP (Use Case Points)               : {result['ucp']}")
    print(f"  Effort @ {result['productivity_hours_per_ucp']} h/UCP : "
          f"{result['effort_hours']} h")


# ═══════════════════════════════════════════════════════════════════════════
# Disciplines: work packets, iteration protocol, status
# ═══════════════════════════════════════════════════════════════════════════

def briefing_args(args):
    """How to pass the caller's briefing on to another command."""
    if args.input_file:
        return ["--input", str(Path(args.input_file).resolve())]
    return [args.briefing] if args.briefing else []


def discipline_packet(key, args, context_dir):
    """Print a discipline's work packet by running its skill (subprocess, ADR-0004)."""
    run_py = discipline_run_py(key)
    if not run_py.exists():
        discipline.fail(f"discipline skill not found: {run_py}")
    cmd = [sys.executable, str(run_py), *briefing_args(args),
           "--phase", args.phase, "--context-dir", str(context_dir)]
    return subprocess.run(cmd, cwd=str(RUP_ROOT)).returncode


def steps():
    """Iteration steps in order: governance, then the 8 disciplines."""
    yield 0, "Governance", SKILL, Path(this_script()), None
    for i, (key, d) in enumerate(DISCIPLINES.items(), start=1):
        yield i, d["title"], d["skill"], discipline_run_py(key), key


def _generated_at(path):
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:8]:
        if line.startswith("generated_at:"):
            return line.split(":", 1)[1].strip()
    return "?"


def status_rows(context_dir, phase):
    rows = []
    for n, title, skill, _, _ in steps():
        path = rup_context.artifact_path(context_dir, phase, skill)
        rows.append((n, title, skill, path, _generated_at(path) if path.is_file() else None))
    return rows


def print_status(context_dir, phase):
    print(f"## Status — {phase} ({PHASE_MILESTONES[phase]}) — `{context_dir}`\n")
    print("| # | Step | Skill | Recorded |")
    print("|---|------|-------|----------|")
    pending = None
    for n, title, skill, _, when in status_rows(context_dir, phase):
        print(f"| {n} | {title} | `{skill}` | {('✅ ' + when) if when else '⏳ not yet'} |")
        if when is None and pending is None:
            pending = (n, title)
    print()
    print(f"Next pending step: {pending[0]} — {pending[1]}" if pending
          else "Every step has an artifact recorded for this phase.")


def print_protocol(args, context_dir):
    phase, py = args.phase, sys.executable
    print(f"# RUP iteration protocol — {phase} ({PHASE_MILESTONES[phase]})\n")
    print("You, the agent running this skill, are the LLM. Run the steps **in order**; "
          "for each one:\n")
    print("1. run the packet command — it prints the roles, the required artifacts and "
          "the artifacts already recorded by the earlier steps;")
    print("2. write the document the packet asks for;")
    print("3. record it with the `--record` command the packet shows (mandatory: it "
          "validates the artifacts and writes `.context/`).\n")
    print("Do not skip ahead: each packet is built from what the earlier steps recorded.")
    if not args.input_file:
        print("Tip: for a long briefing, save it to a file and pass `--input <file>`.")
    print("\n## Packet commands\n")
    for n, title, skill, run_py, _ in steps():
        cmd = discipline.cmdline([py, str(run_py), *briefing_args(args), "--phase", phase,
                                  "--context-dir", str(context_dir)])
        print(f"{n}. **{title}** (`{skill}`)\n   ```bash\n   {cmd}\n   ```")
    print()
    print_status(context_dir, phase)


def list_disciplines():
    print("RUP disciplines (in --auto order):")
    for k, v in DISCIPLINES.items():
        print(f"  - {k:20s} {v['title']}  (`{v['skill']}`)")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="RUP-Orchestrator — governance work packets for the host agent (the "
                    "LLM), iteration protocol, .context/ recording and UCP sizing",
    )
    discipline.add_common_args(parser)
    parser.add_argument("--discipline", choices=list(DISCIPLINES.keys()),
                        help="Print that discipline's work packet (instead of governance)")
    parser.add_argument("--auto", action="store_true",
                        help="Print the iteration protocol: governance + the 8 disciplines, in order")
    parser.add_argument("--status", action="store_true",
                        help="Show which steps have an artifact recorded in .context/ for the phase")
    parser.add_argument("--list", action="store_true", help="List the disciplines and exit")
    parser.add_argument("--estimate", action="store_true",
                        help="Compute Use Case Points (deterministic) and record them in .context/")
    parser.add_argument("--sizing", dest="sizing_file",
                        help="JSON sizing model for --estimate (actors, use cases, TCF/EF factors)")
    parser.add_argument("--sizing-template", action="store_true",
                        help="Print an empty JSON sizing model to fill in and exit")
    parser.add_argument("--json", action="store_true",
                        help="With --estimate: emit the UCP result as JSON")
    args = parser.parse_args()

    if args.sizing_template:
        print(template_sizing())
        return
    if args.list:
        list_disciplines()
        return

    context_dir = rup_context.resolve_context_dir(args.context_dir)

    if args.status:
        print_status(context_dir, args.phase)
        return

    if args.estimate:
        try:
            result = (estimate_from_json(args.sizing_file) if args.sizing_file
                      else compute_ucp())
        except (OSError, SizingError) as e:
            print(f"❌ Error: invalid sizing model: {e}")
            sys.exit(EXIT_USAGE)
        if args.json:
            import json
            print(json.dumps(result, indent=2))
        else:
            print_estimate(result)
        rup_context.ensure_writable(context_dir, args.phase)
        written = rup_context.write_artifact(
            context_dir, render_estimate_md(result, args.sizing_file or "empty (neutral)"),
            skill=SKILL, title=SIZING_TITLE, phase=args.phase,
            briefing=f"Use Case Points from {args.sizing_file or 'an empty model'}",
            suffix=SIZING_SUFFIX)
        # stderr: with --json, stdout must stay pure JSON
        print(f"🗂️  Artifact written to {written}", file=sys.stderr)
        return

    if args.discipline:
        if args.record:
            discipline.fail(f"record a discipline with its own skill: "
                            f"{discipline_run_py(args.discipline)} --record …")
        discipline.read_briefing(args)  # validate before delegating
        sys.exit(discipline_packet(args.discipline, args, context_dir))

    if args.auto:
        discipline.read_briefing(args)
        print_protocol(args, context_dir)
        return

    # Governance: work packet (default) or --record.
    discipline.run(governance_spec(args.phase, str(context_dir)), args, script=__file__)


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    main()
