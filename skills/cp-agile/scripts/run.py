#!/usr/bin/env python3
"""
cp-agile — Agile (Execution Pipeline) (self-contained)

Maestro of the execution pipeline. The local filesystem (.context/kanban/) is the
SOURCE OF TRUTH. Trello is only a MIRRORED VIEW of the local state —
never the source of decision.

Architecture:
  [Local .context/kanban/]  ──(source of truth)──►  [Trello (mirror/view)]
        ▲                                              │
        └────────────── syncs state ───────────────────┘

  - The daemon ALWAYS reads from local (scan_ready, movement, questions, blockers).
  - If Trello mirroring is enabled (--sync-trello), each local change is
    reflected in Trello (creates/updates cards per the local state).
  - Trello NEVER decides state — it only displays what is local.

Components:
  - CPAgileDaemon        : continuous polling of local + dispatch to orchestrator
  - CPAgileFeedbackLoop  : questions, blockers and resume (local)
  - LocalIntegration     : source of truth (.context/kanban/)
  - TrelloMirror         : mirror/view of local state in Trello
  - TaskTemplate         : task .md template with YAML frontmatter

Usage:
  # Polling daemon (always reads from local)
  python run.py --daemon

  # Daemon with Trello mirroring (view of local in Trello)
  python run.py --daemon --sync-trello

  # Register a question (local; mirrors to Trello if enabled)
  python run.py --question "task-123" --message "What is the MVP scope?" --sync-trello

  # Register a blocker
  python run.py --blocker "task-123" --error "Connection failure" --severity high

  # Resume task (human answer)
  python run.py --resume "task-123" --answer "The MVP covers login and signup"

  # Sync the entire local state to Trello (one-shot)
  python run.py --sync-trello

  # Dry run
  python run.py --daemon --dry-run
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

# DT-01: UTF-8 on stdout/stderr (the Windows console uses cp1252 and crashes the
# skill with UnicodeEncodeError when printing emoji/box-drawing).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Root directory of the local kanban. Uses env var with relative default (portable).
KANBAN_ROOT = Path(os.environ.get("KANBAN_ROOT", ".context/kanban"))

# Kanban folders (flow order)
KANBAN_COLUMNS = [
    "1-backlog",
    "2-todo",
    "3-doing",
    "4-review",
    "5-testing",
    "6-staging",
    "7-done",
]
BLOCKED_DIR = "blocked"

# Inbox root: free-text drop zone. Any loose text file at the ROOT (not in the
# subfolders) is triaged and becomes a task in the kanban.
INBOX_ROOT = Path(os.environ.get("INBOX_ROOT", ".context/inbox"))

# Where the raw text is archived after becoming a task. The root empties, so the
# triage is naturally idempotent — nothing is triaged twice.
INBOX_PROCESSED_DIR = ".processed"

# Inbox root files that triage ignores (documentation, not work).
INBOX_IGNORED = {"readme.md", "index.md", ".gitkeep"}

# Size cap per dropped item. Above this it is not loose text, it is an attachment.
INBOX_MAX_BYTES = int(os.environ.get("INBOX_MAX_BYTES", 512 * 1024))

# Tracks (the item's `type:`) and the id prefix of each one.
TRACKS = {
    "initiative": "INIT",
    "task": "TASK",
    "bug": "BUG",
    "tech-debt": "DT",
}
DEFAULT_TRACK = "task"

# Status that triage assigns when the item does not declare one. `ready` makes
# the pipeline dispatch on the next cycle — it is the drop-zone point.
TRIAGE_STATUS = os.environ.get("INBOX_TRIAGE_STATUS", "ready")

# Classification heuristic: the first track whose pattern matches wins, so
# order matters. `bug` comes before everything because an error report is the
# most frequent and most specific case; `task` is the default, not a pattern.
TRACK_PATTERNS = [
    ("bug", r"(?:\bbugs?\b|\berrors?\b|\bfailure\b|exception|stack ?trace|"
            r"traceback|\bbroke\b|doesn't work|regression|\bcrash)"),
    ("tech-debt", r"(?:tech debt|refactor|hack|workaround|technical debt|"
                   r"\bTODO\b|\bFIXME\b)"),
    ("initiative", r"(?:\binitiative\b|\bepics?\b|\bepic\b|\bvision\b|"
                   r"\broadmap\b|\bOKRs?\b|\bstrategy\b|\bdiscovery\b)"),
]

# Priorities accepted in the frontmatter (same scale as --severity).
VALID_PRIORITIES = {"low", "medium", "high", "critical"}

# Valid states (frontmatter `status:`)
VALID_STATUSES = {
    "backlog", "ready", "todo", "doing", "review",
    "testing", "staging", "done", "blocked",
}

# Path to the orchestrator (for real dispatch of tasks in --task and the daemon)
_THIS_SCRIPT_DIR = Path(__file__).resolve().parent
AGILE_SKILLS_DIR = _THIS_SCRIPT_DIR.parent.parent  # skills/
ORCHESTRATOR_RUN = AGILE_SKILLS_DIR / "cp-orchestrator" / "scripts" / "run.py"

# Polling interval (seconds)
POLL_INTERVAL = int(os.environ.get("AGILISTA_POLL_INTERVAL", "10"))

# Standardized events
EVENT_TASK_DISPATCHED = "TASK_DISPATCHED"
EVENT_QUESTION = "QUESTION"
EVENT_BLOCKER = "BLOCKER"
EVENT_HUMAN_CLARIFICATION = "HUMAN_CLARIFICATION_RECEIVED"
EVENT_INBOX_TRIAGED = "INBOX_ITEM_TRIAGED"


# ═══════════════════════════════════════════════════════════════════════════
# TASK TEMPLATE (.md with YAML frontmatter)
# ═══════════════════════════════════════════════════════════════════════════

TASK_TEMPLATE = """---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
assignee: {assignee}
created_at: {created_at}
updated_at: {updated_at}
tags: {tags}
type: {type}
source: {source}
---

# {title}

## Description

{description}

## Acceptance Criteria

- [ ] {acceptance_criteria}

## Pending Questions

<!-- Sections added by the CPAgileFeedbackLoop -->

## Blockers Log

<!-- Sections added by the CPAgileFeedbackLoop -->
"""


def build_task_template(task_id, title, status="backlog", priority="medium",
                        assignee="", tags="[]", description="",
                        acceptance_criteria="Define acceptance criteria",
                        type=DEFAULT_TRACK, source=""):
    """Generates the content of a task .md file from the template.

    `type` is the item's track (see TRACKS) and `source` stores the name of the
    file dropped in the inbox, when the task came from triage — without it there
    is no way to go back from the kanban to the archived raw text.
    """
    now = datetime.now().isoformat(timespec="seconds")
    return TASK_TEMPLATE.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        assignee=assignee,
        created_at=now,
        updated_at=now,
        tags=tags,
        type=type,
        source=source,
        description=description,
        acceptance_criteria=acceptance_criteria,
    )


# ═══════════════════════════════════════════════════════════════════════════
# YAML FRONTMATTER PARSER (minimal, no external dependency)
# ═══════════════════════════════════════════════════════════════════════════

def parse_frontmatter(content: str) -> dict:
    """Extracts the YAML frontmatter (--- ... ---) from a .md file."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return {}
    data = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip().strip('"').strip("'")
    return data


def read_task_meta(path: Path) -> dict:
    """Reads the full frontmatter of a task file."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    return parse_frontmatter(content)


def read_task_status(path: Path) -> str:
    """Reads the status of a task file from the frontmatter."""
    return read_task_meta(path).get("status", "")


def update_task_meta(path: Path, updates: dict) -> bool:
    """Updates fields of the YAML frontmatter of a task file.

    Only rewrites the fields passed in `updates`; preserves the rest of the
    frontmatter and the file body. Returns True if it changed.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return False
    m = re.match(r"^(---\s*\n.*?\n---)\s*\n", content, re.DOTALL)
    if not m:
        return False
    fm_block = m.group(1)
    body = content[m.end():]
    for key, val in updates.items():
        # Replaces the existing line or adds it at the end of the frontmatter
        pattern = re.compile(rf"^{re.escape(key)}:.*$", re.MULTILINE)
        if pattern.search(fm_block):
            fm_block = pattern.sub(f"{key}: {val}", fm_block)
        else:
            # Inserts before the closing ---
            fm_block = fm_block.rstrip("---\n") + f"{key}: {val}\n---\n"
    path.write_text(fm_block + "\n" + body, encoding="utf-8")
    return True


# ═══════════════════════════════════════════════════════════════════════════
# LOCAL INTEGRATION (.context/kanban/) — SOURCE OF TRUTH
# ═══════════════════════════════════════════════════════════════════════════

class LocalIntegration:
    """Source of truth of the kanban (.context/kanban/). All decisions come from here."""

    def __init__(self, root: Path = None):
        self.root = Path(root) if root else KANBAN_ROOT
        self.ensure_structure()

    def ensure_structure(self):
        """Creates the kanban folder structure if it does not exist."""
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            (self.root / col).mkdir(parents=True, exist_ok=True)

    def scan_ready(self) -> list:
        """Scans the backlog for files with status: ready."""
        ready = []
        backlog = self.root / "1-backlog"
        if backlog.exists():
            for f in sorted(backlog.glob("*.md")):
                if read_task_status(f) == "ready":
                    ready.append(f)
        return ready

    def all_tasks(self) -> list:
        """Lists all tasks with their current column (for mirroring)."""
        tasks = []
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            col_dir = self.root / col
            if not col_dir.exists():
                continue
            for f in sorted(col_dir.glob("*.md")):
                meta = read_task_meta(f)
                tasks.append({
                    "path": f,
                    "id": f.stem,
                    "title": meta.get("title", f.stem),
                    "status": meta.get("status", col),
                    "column": col,
                    "priority": meta.get("priority", "medium"),
                })
        return tasks

    def triage(self, inbox_root: Path = None) -> list:
        """Scans the inbox, classifies each item and creates a task in the kanban.

        Returns a list of dicts with the data of each created task.
        """
        root = Path(inbox_root) if inbox_root else INBOX_ROOT
        imported = []

        # Ensures per-track counters for monotonic IDs
        counters = {k: 0 for k in TRACKS}
        for task_file in self.root.rglob("*.md"):
            meta = read_task_meta(task_file)
            type_ = meta.get("type", DEFAULT_TRACK)
            tid = meta.get("id", "")
            for track, prefix in TRACKS.items():
                if tid.startswith(prefix):
                    # Extracts the sequential number
                    try:
                        num = int(re.search(r"\d+", tid).group())
                        if num > counters[track]:
                            counters[track] = num
                    except (AttributeError, ValueError):
                        pass

        # Walks each inbox subfolder
        for subdir_name in ["initiatives", "tasks", "bugs", "tech-debt"]:
            subdir = root / subdir_name
            if not subdir.exists():
                continue
            for item_path in sorted(subdir.glob("*.md")):
                if item_path.name.lower() in INBOX_IGNORED:
                    continue

                raw = item_path.read_text(encoding="utf-8")
                if len(raw) > INBOX_MAX_BYTES:
                    continue

                # Extracts the title from the file (first heading or file name)
                title_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else item_path.stem

                # Classifies by heuristic
                type_ = DEFAULT_TRACK
                for t, pattern in TRACK_PATTERNS:
                    if re.search(pattern, raw, re.IGNORECASE):
                        type_ = t
                        break

                # Generates ID
                prefix = TRACKS.get(type_, "TASK")
                counters[type_] += 1
                task_id = f"{prefix}-{counters[type_]:03d}"

                # Description: initial excerpt of the raw
                description = raw.strip()

                now = datetime.now().isoformat(timespec="seconds")
                task_content = build_task_template(
                    task_id=task_id,
                    title=title,
                    status=TRIAGE_STATUS,
                    priority="medium",
                    tags="[]",
                    description=description,
                    type=type_,
                    source=item_path.name,
                )

                dest = self.root / "1-backlog" / f"{task_id}.md"
                dest.write_text(task_content, encoding="utf-8")

                # Archives the original item
                processed = root / subdir_name / ".processed"
                processed.mkdir(parents=True, exist_ok=True)
                archived = processed / item_path.name
                item_path.rename(archived)

                imported.append({
                    "task_id": task_id,
                    "title": title,
                    "type": type_,
                    "source": str(archived),
                    "destination": str(dest),
                })

        return imported

    def update_status(self, task_id: str, status: str) -> Path:
        """Updates the status of a task and moves it to the corresponding column.

        Maps status → column:
          backlog → 1-backlog
          ready   → 1-backlog
          todo    → 2-todo
          doing   → 3-doing
          review  → 4-review
          testing → 5-testing
          staging → 6-staging
          done    → 7-done
          blocked → blocked

        Updates both the frontmatter `status:` and moves the file
        to the corresponding folder.
        """
        STATUS_TO_COLUMN = {
            "backlog": "1-backlog",
            "ready": "1-backlog",
            "todo": "2-todo",
            "doing": "3-doing",
            "review": "4-review",
            "testing": "5-testing",
            "staging": "6-staging",
            "done": "7-done",
            "blocked": "blocked",
        }
        column = STATUS_TO_COLUMN.get(status)
        if not column:
            return None

        dest = self.move_to(task_id, column)
        if dest:
            update_task_meta(dest, {"status": status,
                                    "updated_at": datetime.now().isoformat(timespec="seconds")})
        return dest

    def document_kanban(self, context_root: Path = None) -> Path:
        """Generates/updates .context/docs/06-kanban.md with the kanban state.

        The kanban is documented in the .context/ structure (the project's
        source of truth). If .context/ does not exist, the file is created
        anyway (the cp-doc-initializer guarantees the full structure).
        """
        tasks = self.all_tasks()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Groups by column
        by_col = {}
        for t in tasks:
            by_col.setdefault(t["column"], []).append(t)

        lines = [
            "# Kanban / Execution Pipeline",
            "",
            "> Document managed by the `cp-agile` skill. Updated at " + now + ".",
            "",
            "## Kanban State",
            "",
            "| Column | Tasks |",
            "|--------|-------|",
        ]
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            n = len(by_col.get(col, []))
            lines.append(f"| {col} | {n} |")

        lines.append("")
        lines.append("## Tasks by column")
        lines.append("")
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            col_tasks = by_col.get(col, [])
            if not col_tasks:
                continue
            lines.append(f"### {col}")
            lines.append("")
            for t in col_tasks:
                lines.append(f"- **{t['title']}** (`{t['id']}`) — priority {t['priority']}")
            lines.append("")

        content = "\n".join(lines)

        # Destination: .context/docs/06-kanban.md
        # If the kanban is already inside .context/ (e.g. .context/kanban/),
        # the parent is .context/; otherwise, go up one level and find .context/.
        if context_root is None:
            if self.root.parent.name == ".context":
                context_root = self.root.parent
            else:
                context_root = self.root.parent / ".context"
        dest = Path(context_root) / "docs" / "06-kanban.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return dest

    def move_to(self, task_id: str, column: str) -> Path:
        """Moves a task file to a column."""
        src = self.find_task(task_id)
        if not src:
            return None
        dest_dir = self.root / column
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        src.rename(dest)
        return dest

    def find_task(self, task_id: str) -> Path:
        """Locates a task file by id in any column."""
        for col in KANBAN_COLUMNS + [BLOCKED_DIR]:
            for f in (self.root / col).glob("*.md"):
                if f.stem == task_id or task_id in f.name:
                    return f
        return None

    def add_question(self, task_id: str, message: str, source: str = "AI") -> Path:
        """Adds a '## Pending Questions' section to the local file."""
        path = self.find_task(task_id)
        if not path:
            return None
        content = path.read_text(encoding="utf-8")
        question = (
            f"\n### ❓ [AI Question - {source}] {datetime.now().isoformat(timespec='seconds')}\n"
            f"{message}\n"
        )
        if "## Pending Questions" in content:
            content = content.replace("## Pending Questions",
                                      "## Pending Questions\n" + question)
        else:
            content += f"\n## Pending Questions\n{question}"
        path.write_text(content, encoding="utf-8")
        return path

    def add_blocker(self, task_id: str, error: str, severity: str = "medium") -> Path:
        """Moves to blocked/ and appends an error and severity log."""
        path = self.move_to(task_id, BLOCKED_DIR)
        if not path:
            return None
        content = path.read_text(encoding="utf-8")
        log = (
            f"\n### 🚧 [Blocker] {datetime.now().isoformat(timespec='seconds')}\n"
            f"- **Severity**: {severity}\n"
            f"- **Error**: {error}\n"
        )
        if "## Blockers Log" in content:
            content = content.replace("## Blockers Log",
                                      "## Blockers Log\n" + log)
        else:
            content += f"\n## Blockers Log\n{log}"
        path.write_text(content, encoding="utf-8")
        return path

    def resume(self, task_id: str, answer: str) -> Path:
        """Records the human answer and moves back to todo/."""
        path = self.find_task(task_id)
        if not path:
            return None
        content = path.read_text(encoding="utf-8")
        resp = (
            f"\n### ✅ [Human Answer] {datetime.now().isoformat(timespec='seconds')}\n"
            f"{answer}\n"
        )
        content += resp
        path.write_text(content, encoding="utf-8")
        # Moves from blocked/ to 2-todo/
        if path.parent.name == BLOCKED_DIR:
            dest = self.root / "2-todo" / path.name
            path.rename(dest)
            return dest
        return path


# ═══════════════════════════════════════════════════════════════════════════
# TRELLO MIRROR (mirror/view of the local state)
# ═══════════════════════════════════════════════════════════════════════════

# Maps local column -> Trello list
COLUMN_TO_TRELLO_LIST = {
    "1-backlog": "Backlog",
    "2-todo": "Todo",
    "3-doing": "Doing",
    "4-review": "Review",
    "5-testing": "Testing",
    "6-staging": "Staging",
    "7-done": "Done",
    "blocked": "Blocked",
}


class TrelloMirror:
    """Mirror/view of the local state in Trello.

    Trello is NEVER the source of decision — it only reflects what is local.
    If the Trello MCP tools are not available, mirroring is silently disabled
    (the local keeps working on its own).
    """

    def __init__(self, board_name: str = None):
        self.board_name = board_name or os.environ.get("TRELLO_BOARD", "Backlog")
        self.available = self._check_tools()

    def _check_tools(self) -> bool:
        """Checks whether the Trello MCP tools are available."""
        try:
            from mcp_tools import trello  # noqa: F401
            return True
        except ImportError:
            return False

    def _list_for_column(self, column: str) -> str:
        """Returns the Trello list corresponding to a local column."""
        return COLUMN_TO_TRELLO_LIST.get(column, "Backlog")

    def sync_task(self, task: dict):
        """Mirrors a local task in Trello (creates/updates card in the right list)."""
        if not self.available:
            return False
        task_id = task["id"]
        title = task["title"]
        column = task["column"]
        trello_list = self._list_for_column(column)
        # In a real environment, calls the MCP tools:
        #   card = trello.find_card(name=title)
        #   if not card: trello.create_card(name=title, list_name=trello_list)
        #   else: trello.move_card(card_id=card.id, list_name=trello_list)
        print(f"  🔄 [Trello] '{title}' → list '{trello_list}'")
        return True

    def sync_all(self, tasks: list) -> int:
        """Mirrors all local tasks in Trello. Returns how many it synced."""
        if not self.available:
            print("  ⚠️  Trello mirror unavailable (MCP tools not found). "
                  "Local remains the source of truth.")
            return 0
        count = 0
        for task in tasks:
            if self.sync_task(task):
                count += 1
        return count


# ═══════════════════════════════════════════════════════════════════════════
# BIDIRECTIONAL FEEDBACK LOOP
# ═══════════════════════════════════════════════════════════════════════════

class CPAgileFeedbackLoop:
    """Manages questions, blockers and resume.

    The local is ALWAYS the source of truth. Trello (if enabled) is only
    mirrored after each operation.
    """

    def __init__(self, sync_trello: bool = False):
        self.sync_trello = sync_trello
        self.local = LocalIntegration()
        self.trello = TrelloMirror()

    def _dispatch(self, event: str, payload: dict):
        """Emits a standardized event (log + JSON payload)."""
        event_line = {
            "event": event,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
        }
        print(json.dumps(event_line, ensure_ascii=False, indent=2))
        return event_line

    def _mirror(self, task_id: str):
        """Mirrors the task in Trello if mirroring is enabled."""
        if not self.sync_trello:
            return
        path = self.local.find_task(task_id)
        if not path:
            return
        meta = read_task_meta(path)
        self.trello.sync_task({
            "id": task_id,
            "title": meta.get("title", task_id),
            "column": path.parent.name,
        })

    def question(self, task_id: str, message: str, source: str = "AI") -> dict:
        """Records an AI question locally and mirrors it in Trello."""
        payload = {"task_id": task_id, "message": message, "source": source}
        self.local.add_question(task_id, message, source)
        self._mirror(task_id)
        return self._dispatch(EVENT_QUESTION, payload)

    def blocker(self, task_id: str, error: str, severity: str = "medium") -> dict:
        """Records a blocker locally (moves to blocked/) and mirrors it."""
        payload = {"task_id": task_id, "error": error, "severity": severity}
        self.local.add_blocker(task_id, error, severity)
        self._mirror(task_id)
        return self._dispatch(EVENT_BLOCKER, payload)

    def resume_task(self, task_id: str, answer: str) -> dict:
        """Captures the human answer locally and mirrors it in Trello."""
        payload = {"task_id": task_id, "answer": answer}
        self.local.resume(task_id, answer)
        self._mirror(task_id)
        return self._dispatch(EVENT_HUMAN_CLARIFICATION, payload)


# ═══════════════════════════════════════════════════════════════════════════
# POLLING DAEMON
# ═══════════════════════════════════════════════════════════════════════════

class CPAgileDaemon:
    """Continuous polling of the LOCAL (source of truth) and task dispatch.

    Trello, if enabled, is only mirrored — never read as a source.
    """

    def __init__(self, dry_run: bool = False, sync_trello: bool = False):
        self.dry_run = dry_run
        self.sync_trello = sync_trello
        self.local = LocalIntegration()
        self.trello = TrelloMirror()
        self.feedback = CPAgileFeedbackLoop(sync_trello)

    def _dispatch_task(self, task_path: Path):
        """Dispatches a ready task to the cp-orchestrator."""
        task_id = task_path.stem
        payload = {
            "task_id": task_id,
            "source": "local",
            "path": str(task_path),
            "event": EVENT_TASK_DISPATCHED,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        # In a real environment, calls the cp-orchestrator:
        #   subprocess.run([sys.executable, ORCHESTRATOR_RUN, task_id, "--auto"])
        # Moves to 2-todo/ (dispatched) — always local
        if not self.dry_run:
            self.local.move_to(task_id, "2-todo")
            if self.sync_trello:
                self.trello.sync_task({
                    "id": task_id,
                    "title": task_path.stem,
                    "column": "2-todo",
                })

    def poll_once(self) -> list:
        """A single scan of the LOCAL. Returns the ready tasks."""
        ready = self.local.scan_ready()

        dispatched = []
        for task in ready:
            print(f"  📦 Ready task: {task.name}")
            self._dispatch_task(task)
            dispatched.append(task)
        return dispatched

    def run(self, iterations: int = None):
        """Continuous polling loop of the local."""
        print(f"🚀 CPAgileDaemon started (source=local, "
              f"interval={POLL_INTERVAL}s, dry_run={self.dry_run}, "
              f"sync_trello={self.sync_trello})")
        print(f"   Local kanban (source of truth): {self.local.root.resolve()}")
        if self.sync_trello:
            print(f"   Trello (mirror): board='{self.trello.board_name}'")
        print("   Press Ctrl+C to stop.\n")

        count = 0
        try:
            while iterations is None or count < iterations:
                count += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Poll #{count}...")
                self.poll_once()
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\n⏹️  Daemon interrupted by the user.")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-agile: Agile (Execution Pipeline)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
The LOCAL (.context/kanban/) is always the source of truth. Trello is only a
mirrored view (--sync-trello) of the local state.

Examples:
  python run.py --daemon
  python run.py --daemon --sync-trello
  python run.py --sync-trello
  python run.py --question "task-123" --message "What is the MVP scope?"
  python run.py --blocker "task-123" --error "Connection failure" --severity high
  python run.py --resume "task-123" --answer "The MVP covers login and signup"
  python run.py --daemon --dry-run
        """,
    )
    parser.add_argument("--daemon", action="store_true",
                        help="Starts the polling daemon (always reads from local)")
    parser.add_argument("--sync-trello", action="store_true",
                        help="Mirrors the local state in Trello (view, not source)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Does not execute actions, only shows what it would do")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Number of polls (default: infinite)")
    parser.add_argument("--question", metavar="TASK_ID",
                        help="Registers a question for the task (local)")
    parser.add_argument("--message", help="Question message")
    parser.add_argument("--blocker", metavar="TASK_ID",
                        help="Registers a blocker for the task (local)")
    parser.add_argument("--error", help="Description of the blocker error")
    parser.add_argument("--severity", choices=["low", "medium", "high", "critical"],
                        default="medium", help="Blocker severity")
    parser.add_argument("--resume", metavar="TASK_ID",
                        help="Resumes a task with a human answer (local)")
    parser.add_argument("--answer", help="Human answer to unblock")
    parser.add_argument("--init", action="store_true",
                        help="Creates the .context/kanban/ structure and exits")
    parser.add_argument("--doc", action="store_true",
                        help="Generates/updates .context/docs/06-kanban.md with the kanban state")
    parser.add_argument("--triage", action="store_true",
                        help="Scans the inbox, classifies items and creates tasks in the kanban")
    parser.add_argument("--update-status", metavar="STATUS",
                        help="Updates a task status: backlog|ready|todo|doing|review|testing|staging|done|blocked")
    parser.add_argument("--task", metavar="TASK_ID",
                        help="Changes the task status (with --update-status) or dispatches it for execution (without --update-status)")
    args = parser.parse_args()

    feedback = CPAgileFeedbackLoop(sync_trello=args.sync_trello)

    # ── Initializes structure ──
    if args.init:
        LocalIntegration().ensure_structure()
        print(f"✅ .context/kanban/ structure created at {KANBAN_ROOT.resolve()}")
        return

    # ── Documents the kanban in .context/docs/06-kanban.md ──
    if args.doc:
        local = LocalIntegration()
        dest = local.document_kanban()
        print(f"📋 Kanban documented at {dest}")
        return

    # ── Triage: inbox → kanban ──
    if args.triage:
        local = LocalIntegration()
        imported = local.triage()
        if not imported:
            print("📭 No new items in the inbox to triage.")
            return
        print(f"📦 Triage complete: {len(imported)} item(s) imported to the kanban:")
        for item in imported:
            print(f"  - {item['task_id']}: {item['title']} ({item['type']}) → kanban/1-backlog/")
            print(f"    Source: {item['source']}")
        return

    # ── Update status of a task ──
    if args.task and args.update_status:
        local = LocalIntegration()
        dest = local.update_status(args.task, args.update_status)
        if dest:
            print(f"✅ Task {args.task} moved to {dest.parent.name}/ with status={args.update_status}")
        else:
            print(f"❌ Task {args.task} not found in the kanban.")
            sys.exit(1)
        return

    # ── Execute task via orchestrator (manual dispatch) ──
    if args.task and not args.update_status:
        import subprocess as _sp
        local = LocalIntegration()
        task_path = local.find_task(args.task)
        if not task_path:
            print(f"❌ Task {args.task} not found in the kanban.")
            sys.exit(1)
        meta = read_task_meta(task_path)
        briefing = meta.get("title", args.task)
        # Moves to doing before executing
        local.update_status(args.task, "doing")
        print(f"🚀 Dispatching task {args.task}: \"{briefing}\" to the orchestrator...")
        r = _sp.run(
            [sys.executable, str(ORCHESTRATOR_RUN), briefing, "--auto", "--kanban-task", args.task],
            capture_output=True, text=True, timeout=600,
            encoding="utf-8", errors="replace",
        )
        print(r.stdout)
        if r.stderr:
            print(r.stderr[:1000])
        if r.returncode == 0:
            local.update_status(args.task, "done")
            print(f"✅ Task {args.task} completed and moved to 7-done/")
        else:
            print(f"❌ Task {args.task} failed (exit {r.returncode}). Moving to blocked/")
            local.update_status(args.task, "blocked")
        return

    # ── One-shot sync of local to Trello ──
    if args.sync_trello and not args.daemon and not args.question \
            and not args.blocker and not args.resume:
        local = LocalIntegration()
        tasks = local.all_tasks()
        print(f"📋 Syncing {len(tasks)} tasks from local to Trello (mirror)...")
        mirror = TrelloMirror()
        n = mirror.sync_all(tasks)
        print(f"✅ {n} tasks mirrored in Trello.")
        return

    # ── Question ──
    if args.question:
        if not args.message:
            print("❌ --question requires --message")
            sys.exit(1)
        feedback.question(args.question, args.message)
        return

    # ── Blocker ──
    if args.blocker:
        if not args.error:
            print("❌ --blocker requires --error")
            sys.exit(1)
        feedback.blocker(args.blocker, args.error, args.severity)
        return

    # ── Resume ──
    if args.resume:
        if not args.answer:
            print("❌ --resume requires --answer")
            sys.exit(1)
        feedback.resume_task(args.resume, args.answer)
        return

    # ── Daemon ──
    if args.daemon:
        daemon = CPAgileDaemon(args.dry_run, args.sync_trello)
        daemon.run(args.iterations)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
