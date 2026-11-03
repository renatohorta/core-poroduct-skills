"""
context.py — Mandatory persistence of the RUP artifacts into `.context/`.

Every `rup-*` skill records the agent's document into the target project's
`.context/` (ADR-0011, ADR-0012). This module is the single implementation of:

  - where the `.context/` is   (resolve_context_dir)
  - where an artifact goes      (artifact_path)
  - how it is written           (write_artifact, append to tracking/rup-log.md)
  - failing loudly when it cannot write (ensure_writable) — exit code 4

Layout (matches the RUP phases of `.context/docs/`):

  .context/docs/01-inception/rup-<discipline>.md
  .context/docs/02-elaboration/rup-<discipline>.md
  .context/docs/03-construction/rup-<discipline>.md
  .context/docs/04-transition/rup-<discipline>.md
  .context/tracking/rup-log.md        (one line per written artifact)

The `rup-` prefix keeps the generated artifacts apart from the curated docs
(`requirements.md`, `architecture.md`, …), which are never overwritten.
Each run regenerates the artifact of that phase; history lives in git.

Pure standard library.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

EXIT_CONTEXT_NOT_WRITABLE = 4
EXIT_NEEDS_CONSENT = 5

MARKER = ".rup-standard"

CONTEXT_ENV_VAR = "RUP_CONTEXT_DIR"

PHASE_DIRS = {
    "Inception": "01-inception",
    "Elaboration": "02-elaboration",
    "Construction": "03-construction",
    "Transition": "04-transition",
}

PHASE_MILESTONES = {
    "Inception": "Lifecycle Objective (LCO)",
    "Elaboration": "Lifecycle Architecture (LCA)",
    "Construction": "Initial Operational Capability (IOC)",
    "Transition": "Product Release (PR)",
}

LOG_RELATIVE = Path("tracking") / "rup-log.md"
BRIEFING_EXCERPT_CHARS = 1500


def resolve_context_dir(explicit=None, start=None) -> Path:
    """The `.context/` directory the artifacts go to.

    Order: explicit (`--context-dir`) > env `RUP_CONTEXT_DIR` > walk up from
    `start` (default: cwd) to the first dir that has `.context/`, stopping at the
    git root > `<git root or start>/.context` (created on first write).
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get(CONTEXT_ENV_VAR, "").strip()
    if env:
        return Path(env).expanduser().resolve()

    start = Path(start or Path.cwd()).resolve()
    for d in (start, *start.parents):
        if (d / ".context").is_dir():
            return d / ".context"
        if (d / ".git").exists():
            return d / ".context"
    return start / ".context"


def artifact_path(context_dir, phase: str, skill: str, suffix: str = "") -> Path:
    """`<context>/docs/<NN-phase>/<skill><suffix>.md`."""
    if phase not in PHASE_DIRS:
        raise ValueError(f"unknown RUP phase {phase!r} (valid: {', '.join(PHASE_DIRS)})")
    return Path(context_dir) / "docs" / PHASE_DIRS[phase] / f"{skill}{suffix}.md"


def has_consent(context_dir) -> bool:
    """True when the user authorized the RUP standard in this `.context/`."""
    return (Path(context_dir) / MARKER).is_file()


def require_consent(context_dir) -> None:
    """Exit 5 (writing nothing) unless `<context>/.rup-standard` exists."""
    if has_consent(context_dir):
        return
    context_dir = Path(context_dir)
    found = (".context/ without the .rup-standard marker" if context_dir.is_dir()
             else "no .context/")
    print()
    print(f"[!] {context_dir} is not authorized for the RUP standard (found: {found}).")
    print("    Nothing was written. To adopt the RUP standard in .context/: ask the user;")
    print("    on approval run `rup-context --init`.")
    sys.exit(EXIT_NEEDS_CONSENT)


def ensure_writable(context_dir, phase=None, exit_code: int = EXIT_CONTEXT_NOT_WRITABLE) -> Path:
    """Check authorization (exit 5), then create the phase dir and the tracking
    dir, or exit with code 4. `phase=None` checks only the root and `tracking/`.

    Persisting into `.context/` is mandatory: a record that cannot be written
    must fail loudly, never silently drop the agent's work.
    """
    context_dir = Path(context_dir)
    require_consent(context_dir)
    targets = [context_dir / LOG_RELATIVE.parent]
    if phase is not None:
        targets.insert(0, context_dir / "docs" / PHASE_DIRS[phase])
    try:
        for t in targets:
            t.mkdir(parents=True, exist_ok=True)
            probe = t / ".rup-write-probe"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
    except OSError as e:
        print()
        print(f"[X] Cannot write the RUP artifacts to {context_dir}: {e}")
        print("    Persisting into .context/ is mandatory. Fix the permissions, or point")
        print(f"    --context-dir / {CONTEXT_ENV_VAR} to a writable .context directory.")
        sys.exit(exit_code)
    return context_dir


def _excerpt(text: str, limit: int = BRIEFING_EXCERPT_CHARS) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n[… truncated]"


def render_artifact(content, *, skill, title, phase, briefing, now=None) -> str:
    """Markdown document with provenance frontmatter + the crew result."""
    now = now or datetime.now()
    quoted = "\n".join("> " + line if line else ">"
                       for line in _excerpt(briefing).splitlines()) or "> (empty)"
    return (
        "---\n"
        f"skill: {skill}\n"
        f"discipline: {title}\n"
        f"phase: {phase}\n"
        f"milestone: {PHASE_MILESTONES[phase]}\n"
        f"generated_at: {now.isoformat(timespec='seconds')}\n"
        "---\n\n"
        f"# {title} — {phase}\n\n"
        f"> Generated by `{skill}`. Each run regenerates this file for the phase;\n"
        "> previous versions live in git. Curated docs are never overwritten.\n\n"
        "## Briefing\n\n"
        f"{quoted}\n\n"
        "## Artifacts\n\n"
        f"{str(content).strip()}\n"
    )


def append_log(context_dir, *, phase, skill, path, now=None) -> Path:
    """Append one line to `.context/tracking/rup-log.md` (created with a header)."""
    now = now or datetime.now()
    log = Path(context_dir) / LOG_RELATIVE
    log.parent.mkdir(parents=True, exist_ok=True)
    if not log.exists():
        log.write_text(
            "# RUP artifact log\n\n"
            "> Appended by the `rup-*` skills on every artifact written to `.context/`.\n\n"
            "| When | Phase | Skill | Artifact |\n"
            "|------|-------|-------|----------|\n",
            encoding="utf-8",
        )
    try:
        rel = Path(path).resolve().relative_to(Path(context_dir).resolve())
    except ValueError:
        rel = Path(path)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"| {now.isoformat(timespec='seconds')} | {phase} | `{skill}` | "
                 f"`{rel.as_posix()}` |\n")
    return log


def write_artifact(context_dir, content, *, skill, title, phase, briefing,
                   suffix="", now=None) -> Path:
    """Write the artifact into `.context/` and log it. Returns the file path."""
    now = now or datetime.now()
    path = artifact_path(context_dir, phase, skill, suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_artifact(content, skill=skill, title=title, phase=phase,
                                    briefing=briefing, now=now), encoding="utf-8")
    append_log(context_dir, phase=phase, skill=skill, path=path, now=now)
    return path
