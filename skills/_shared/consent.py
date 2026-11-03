"""
consent.py — Detect the state of a `.context/` and adopt the RUP standard in it.

`init_context` is what *grants* authorization: it writes the `.rup-standard`
marker. It only ever adds what is missing (folders, skeleton files, the pointer
note in CLAUDE.md / AGENT.md) and never overwrites or deletes anything.

Pure standard library.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from _shared import context

STANDARD_VERSION = "1"
DOC_DIR_CANDIDATES = [".specs", ".spec", ".doc", ".docs", "docs", "doc",
                      "documentation", "specs"]

POINTER_START = "<!-- rup-skills:start -->"
POINTER_END = "<!-- rup-skills:end -->"
POINTER_FILES = ("CLAUDE.md", "AGENT.md")
POINTER_BODY = """## RUP skills — which one to use
- Before building anything new: `rup-discover`
- Plan epics/stories/tasks, roadmap, move cards: `rup-backlog`
- Implement a task (TDD): `rup-build`
- Fix a bug: `rup-debug`
- Review a delivered card: `rup-review`
- RUP documents (governance, disciplines): `rup-orchestrator`
- Project context lives in `.context/` (set up with `rup-context`).
"""

KANBAN_COLUMNS = ["1-backlog", "2-todo", "3-doing", "4-review", "5-testing",
                  "6-staging", "7-done", "blocked"]

_DOC_FILES = [
    "docs/01-inception/vision-and-scope.md",
    "docs/01-inception/requirements.md",
    "docs/02-elaboration/architecture.md",
    "docs/02-elaboration/domain-model.md",
    "docs/03-construction/api-contracts.md",
    "docs/03-construction/ui-spec.md",
    "docs/03-construction/data-dictionary.md",
    "docs/04-transition/test-strategy.md",
    "docs/04-transition/devops-infra.md",
    "tracking/progress.md",
    "tracking/decisions.md",
    "kanban/README.md",
    "README.md",
]
_DIRS = (["inbox/" + d for d in ("initiatives", "tasks", "bugs", "tech-debt", "processed")]
         + ["kanban/" + c for c in KANBAN_COLUMNS] + ["roadmap"])


def _skeleton(rel: str) -> str:
    stem = Path(rel).stem
    if stem == "README":
        stem = "kanban" if rel.startswith("kanban/") else "context"
    title = stem.replace("-", " ").capitalize()
    return f"# {title}\n\n> To be filled.\n"


def standard_tree() -> dict:
    """Relative path -> skeleton text (None = directory). Spec INIT-03 §7.2."""
    tree = {}
    for d in _DIRS:
        tree[d] = None
    for f in _DOC_FILES:
        tree[f] = _skeleton(f)
    return tree


@dataclass
class ContextState:
    context_dir: Path
    exists: bool
    authorized: bool
    missing: list = field(default_factory=list)
    other_doc_dirs: list = field(default_factory=list)


def detect(context_dir) -> ContextState:
    context_dir = Path(context_dir)
    exists = context_dir.is_dir()
    missing = [rel for rel in standard_tree() if not (context_dir / rel).exists()]
    root = context_dir.parent
    others = [n for n in DOC_DIR_CANDIDATES
              if n != context_dir.name and (root / n).is_dir()]
    return ContextState(context_dir, exists, context.has_consent(context_dir),
                        missing, others)


def ensure_pointer_note(project_root) -> list:
    """Create or append the RUP pointer block in CLAUDE.md and AGENT.md.
    Existing text is preserved; the block is added once. Returns touched files."""
    block = f"{POINTER_START}\n{POINTER_BODY}{POINTER_END}\n"
    touched = []
    for name in POINTER_FILES:
        path = Path(project_root) / name
        if not path.exists():
            path.write_text(block, encoding="utf-8")
            touched.append(path)
            continue
        text = path.read_text(encoding="utf-8")
        if POINTER_START in text:
            continue
        sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        path.write_text(text + sep + block, encoding="utf-8")
        touched.append(path)
    return touched


def init_context(context_dir, *, authorized_by: str, now=None) -> list:
    """Adopt the standard: add what is missing, write the marker, add the pointer
    note, log one row. Never overwrites. Returns the created paths.
    Exits 1 when the project root (parent of `.context/`) does not exist."""
    import sys
    context_dir = Path(context_dir)
    now = now or datetime.now()
    if not context_dir.parent.is_dir():
        print(f"[X] The project root {context_dir.parent} does not exist; "
              "refusing to create it. Check --context-dir.")
        sys.exit(1)
    created = []
    if not context_dir.exists():
        context_dir.mkdir()
        created.append(context_dir)
    for rel, text in standard_tree().items():
        path = context_dir / rel
        if path.exists():
            continue
        if text is None:
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        created.append(path)
    marker = context_dir / context.MARKER
    if not context.has_consent(context_dir):
        marker.write_text(
            f"version: {STANDARD_VERSION}\nauthorized_by: {authorized_by}\n"
            f"authorized_at: {now.isoformat(timespec='seconds')}\n", encoding="utf-8")
        created.append(marker)
    created += ensure_pointer_note(context_dir.parent)
    if created:
        context.append_event(
            context_dir, skill="rup-context", now=now,
            what=f"init: {len(created)} entries created, authorized by {authorized_by}")
    return created
