#!/usr/bin/env python3
"""
cp-doc-initializer — Documentation Initializer (self-contained)

Centralizes the project context in .context/ as a single source of truth,
eliminating the pollution of .hermes/ or .claude/. Creates bridge files at the
root (CLAUDE.md and AGENT.md) that instruct any agent to use .context/.

Usage:
  python run.py                          # initializes in the current directory
  python run.py --dir /path/to/project
  python run.py --dry-run                # shows what it would do, without creating
"""

import argparse
import os
import re
import shutil
import sys
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
# .context/ STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════

CONTEXT_DIR = ".context"

# Documentation files per discipline (docs/)
DOC_FILES = {
    "00-vision.md": "Product vision",
    "01-requirements.md": "Requirements (cp-requirements)",
    "02-architecture.md": "Architecture (cp-architecture)",
    "03-security-lgpd.md": "Security/LGPD (cp-security)",
    "04-quality-qa.md": "Quality/QA (cp-quality, cp-testing)",
    "05-devops-operations.md": "DevOps/Operations (cp-devops)",
    "06-kanban.md": "Kanban/pipeline (cp-agile)",
}

# Inbox folders
INBOX_DIRS = ["initiatives", "tasks", "bugs", "tech-debt"]

# Tracking folders
TRACKING_DIRS = ["progress.md", "decisions.md"]

# Kanban columns (kanban/) — mirror KANBAN_COLUMNS/BLOCKED_DIR of
# cp-agile/scripts/run.py. The structure is born here, at initialization: the
# cp-agile assumes it exists and the pipeline needs a queue from day 1.
KANBAN_COLUMNS = [
    "1-backlog",
    "2-todo",
    "3-doing",
    "4-review",
    "5-testing",
    "6-staging",
    "7-done",
]
KANBAN_BLOCKED_DIR = "blocked"

# Template of the .context/ README
CONTEXT_README = """# .context/ — Project Source of Truth

This directory is the **single source of truth** of the project context. All
agents (Claude Code, Hermes Agent, etc.) must read and write context here,
**never** in `.hermes/` or `.claude/`.

## Structure

### docs/ — Engineering disciplines
| File | Discipline |
|---------|-----------|
| `00-vision.md` | Product vision + Initiatives (epics) |
| `01-requirements.md` | Requirements (cp-requirements) |
| `02-architecture.md` | Architecture (cp-architecture) |
| `03-security-lgpd.md` | Security/LGPD (cp-security) |
| `04-quality-qa.md` | Quality/QA (cp-quality, cp-testing) |
| `05-devops-operations.md` | DevOps/Operations (cp-devops) |
| `06-kanban.md` | Kanban/pipeline (cp-agile) |

### inbox/ — Work entry
- `initiatives/` — Product initiatives
- `tasks/` — Tasks
- `bugs/` — Bugs
- `tech-debt/` — Technical debt

### tracking/ — Tracking
- `progress.md` — Overall progress
- `decisions.md` — Decision record (ADRs)

### kanban/ — Execution pipeline (`cp-agile`)
Source of truth of the task flow; Trello, when configured, is only a mirror. A
task is a `.md` with YAML frontmatter, and the column is the folder.
Raw items stay in `inbox/`; after triage, they become tasks in `kanban/1-backlog/`.

`1-backlog/` → `2-todo/` → `3-doing/` → `4-review/` → `5-testing/` →
`6-staging/` → `7-done/`, plus `blocked/` for questions and blockers.

## Rule

Every `cp-*` skill documents its artifacts in `.context/docs/`. The
`cp-doc-initializer` guarantees the structure exists.
"""

# Template of the kanban/ README
KANBAN_README = """# kanban/ — Execution Pipeline

Source of truth of the task flow, managed by the `cp-agile` skill. When Trello
is configured, it is only a **mirrored view** — what matters is what is here.

## Relationship with `../inbox/`

`inbox/` is raw entry: draft of an initiative, task, bug or technical debt.
After triage, the item becomes a task here, in `1-backlog/`, with `status:`
filled in — move with `git mv` to preserve history.

## Columns

| Folder | Meaning |
|-------|-------------|
| `1-backlog/` | Entry. The daemon scans here for tasks with `status: ready` |
| `2-todo/` | Prioritized, awaiting execution |
| `3-doing/` | In execution (dispatched to the `cp-orchestrator`) |
| `4-review/` | Awaiting review |
| `5-testing/` | In testing |
| `6-staging/` | Staging |
| `7-done/` | Completed |
| `blocked/` | Question or blocker awaiting human answer |

## Format of a task

One `.md` file per task, with YAML frontmatter. The `status:` field must
follow the folder the file is in.

```markdown
---
id: TASK-001
title: Task title
status: ready
priority: medium
assignee:
created_at: 2026-01-01T00:00:00
updated_at: 2026-01-01T00:00:00
tags: []
---

# Task title

## Description

## Acceptance Criteria

- [ ] ...
```

Valid `status:` values: `backlog`, `ready`, `todo`, `doing`, `review`, `testing`,
`staging`, `done`, `blocked`. Only `ready` in `1-backlog/` is dispatched.

## Commands

```bash
# Monitor the backlog and dispatch tasks
python <skills>/cp-agile/scripts/run.py --daemon

# Document the current kanban state in ../docs/06-kanban.md
python <skills>/cp-agile/scripts/run.py --doc
```
"""

# Template of the CLAUDE.md (root pointer)
CLAUDE_MD = """# CLAUDE.md — Project Context

**Source of truth: `.context/`**

Read and write all project context in `.context/`. **DO NOT** create or use
`.hermes/` or `.claude/` for context.

- Overview: `.context/README.md`
- Engineering disciplines: `.context/docs/`
- Work entry: `.context/inbox/`
- Tracking: `.context/tracking/`
- Task pipeline: `.context/kanban/`
"""

# Template of the AGENT.md (root pointer)
AGENT_MD = """# AGENT.md — Project Context

**Source of truth: `.context/`**

Read and write all project context in `.context/`. **DO NOT** create or use
`.hermes/` or `.claude/` for context.

- Overview: `.context/README.md`
- Engineering disciplines: `.context/docs/`
- Work entry: `.context/inbox/`
- Tracking: `.context/tracking/`
- Task pipeline: `.context/kanban/`
"""

# Template of a discipline doc
DISCIPLINE_TEMPLATE = """# {title}

> Document managed by the `{skill}` skill. Updated at {date}.

## Status

- [ ] Pending
- [ ] In progress
- [ ] Completed

## Content

<!-- Artifacts of the {skill} skill are written here -->

## Decisions

<!-- Decision record of this discipline -->
"""

# Special template for 00-vision.md — includes the initiatives section
VISION_TEMPLATE = """# 00 — Product Vision

> Document managed by the `cp-doc-initializer` skill. Updated at {date}.

## What it is

<!-- Description of the product/system -->

## Why this repository exists

<!-- Context, motivation, constraints -->

## Initiatives (Epics)

<!-- List of the project's initiatives/epics. Each initiative aggregates multiple kanban cards.
     Suggested format: table with ID, title, status and linked tasks.
     Completed and open initiatives can be in the same section, separated by subtitle.

| ID | Initiative | Status | Progress |
|----|-----------|--------|-----------|
| ... | ... | ... | ... |
-->
"""

# Template of an inbox file
INBOX_TEMPLATE = """# {name}

<!-- {name} items are recorded here. Format: one .md file per item. -->
"""

# Tracking templates
TRACKING_PROGRESS = """# Project Progress

<!-- Updated by the orchestrator at each completed phase -->

| Phase | Status | Date |
|------|--------|------|
| Initialization | {status} | {date} |
"""

TRACKING_DECISIONS = """# Decision Record (ADRs)

<!-- Each important decision is recorded here with context and justification -->

## ADR-0001 — Source of truth in .context/

**Date**: {date}
**Status**: Accepted
**Context**: The project centralizes the context in `.context/` to avoid
pollution of `.hermes/`/`.claude/` and ensure portability between agents.
**Decision**: All context is read/written in `.context/`.
"""


# ═══════════════════════════════════════════════════════════════════════════
# INITIALIZER
# ═══════════════════════════════════════════════════════════════════════════

class DocInitializer:
    """Creates the .context/ structure and the root pointers."""

    def __init__(self, project_dir: Path = None, dry_run: bool = False):
        self.root = Path(project_dir) if project_dir else Path.cwd()
        self.dry_run = dry_run
        self.context = self.root / CONTEXT_DIR
        self.created = []
        self.vision_ingested = False

    def _write(self, path: Path, content: str, overwrite: bool = False):
        """Writes a file (or records it in dry-run).

        By default (overwrite=False), it does not overwrite existing files —
        the initialization is idempotent and preserves already-populated docs.

        With overwrite=True, it overwrites (used for READMEs and infrastructure
        templates that have no custom content).
        """
        if path.exists() and not overwrite:
            return
        if self.dry_run:
            self.created.append(f"[dry-run] {path.relative_to(self.root)}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.created.append(str(path.relative_to(self.root)))

    def _mkdir(self, path: Path):
        """Creates a directory (or records it in dry-run)."""
        if self.dry_run:
            self.created.append(f"[dry-run] {path.relative_to(self.root)}/")
            return
        path.mkdir(parents=True, exist_ok=True)
        self.created.append(str(path.relative_to(self.root)) + "/")

    def ingest_vision(self):
        """Moves vision.md (if it exists at the root) to .context/docs/00-vision.md."""
        vision_src = self.root / "vision.md"
        if not vision_src.exists():
            return False
        vision_dst = self.context / "docs" / "00-vision.md"
        if self.dry_run:
            self.created.append(f"[dry-run] move vision.md → {vision_dst.relative_to(self.root)}")
            return True
        vision_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(vision_src), str(vision_dst))
        self.created.append(f"move vision.md → {vision_dst.relative_to(self.root)}")
        return True

    def migrate_tracking_to_kanban(self):
        """Migrates content of tracking/tasks.md, tracking/bugs.md and
        tracking/tech-debt.md into the respective cards in kanban/. Preserves a
        backup in tracking/_backup_pre_migration/. After the migration, removes
        the 3 tracking files since the content is now in the cards.

        Idempotent: if the card already has '## Tracking content' or the tracking
        file does not exist, it skips.
        """
        if self.dry_run:
            self.created.append("[dry-run] migrate tracking/ → kanban/ (would skip if tracking files exist)")
            return

        tracking_files = {
            "tasks.md": self._parse_tasks,
            "bugs.md": self._parse_bugs,
            "tech-debt.md": self._parse_debt,
        }

        all_sections = {}

        for fname, parser in tracking_files.items():
            src = self.context / "tracking" / fname
            if not src.exists():
                continue
            text = src.read_text(encoding="utf-8")
            sections = parser(text)
            all_sections.update(sections)

        if not all_sections:
            return  # nothing to migrate

        # Backup of the tracking files
        backup_dir = self.context / "tracking" / "_backup_pre_migration"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for fname in tracking_files:
            src = self.context / "tracking" / fname
            if src.exists():
                dst = backup_dir / fname
                if not dst.exists():
                    os.rename(str(src), str(dst))

        # Walks all kanban cards and injects content
        kanban_dir = self.context / "kanban"
        updated = 0
        for root, dirs, files in os.walk(kanban_dir):
            for fname in files:
                if not fname.endswith(".md") or fname == "README.md":
                    continue
                card_id = Path(fname).stem  # BUG-018, TSK-001, TD-022
                card_path = Path(root) / fname

                # Looks for the corresponding section
                section_content = None
                if card_id in all_sections:
                    section_content = all_sections[card_id]
                else:
                    continue  # card without content in tracking

                # Reads current card
                card_text = card_path.read_text(encoding="utf-8")

                # Idempotent: already migrated?
                if "## Tracking content" in card_text:
                    continue

                # Separates frontmatter from body
                if card_text.startswith("---"):
                    parts = card_text.split("---", 2)
                    frontmatter = "---" + parts[1] + "---"
                    body = parts[2] if len(parts) >= 3 else ""
                else:
                    frontmatter = ""
                    body = card_text

                # New body
                title_line = ""
                for line in body.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("# ") and "lives in tracking" not in stripped:
                        title_line = stripped
                        break

                new_body = title_line or f"# {card_id}"
                new_body += "\n\n---\n\n"
                new_body += "## Tracking content\n\n"
                new_body += section_content

                card_path.write_text(frontmatter + "\n" + new_body, encoding="utf-8")
                updated += 1

        self.created.append(f"migrate tracking/ → kanban/: {updated} cards updated, backup in tracking/_backup_pre_migration/")

    # ── Tracking parsers ──────────────────────────────────────────────

    @staticmethod
    def _parse_tasks(text):
        """Parses tasks.md: sections marked by '- [ ] **TSK-NNN: Title**'"""
        sections = {}
        pattern = re.compile(r'^- \[(.)\] \*\*(TSK-\d+):(.+?)\*\*')
        lines = text.split("\n")
        current_id = None
        current_lines = []

        for line in lines:
            m = pattern.match(line)
            if m:
                if current_id:
                    sections[current_id] = "\n".join(current_lines)
                current_id = m.group(2)
                status = m.group(1)
                title = m.group(3).strip()
                current_lines = [
                    f"## {current_id}: {title}",
                    f'**Status in tracking:** {"✅ Completed" if status == "x" else "⬜ Pending"}',
                ]
            elif current_id:
                current_lines.append(line)

        if current_id:
            sections[current_id] = "\n".join(current_lines)
        return sections

    @staticmethod
    def _parse_bugs(text):
        """Parses bugs.md: detailed sections '## BUG-NNN — Title' + table"""
        sections = {}
        # Detailed sections
        section_pattern = re.compile(r"^## (BUG-\d+)\s*[—\-]\s*(.+?)$", re.MULTILINE)
        section_starts = {}
        for m in section_pattern.finditer(text):
            section_starts[m.group(1)] = (m.start(), m.group(2).strip())

        sorted_ids = sorted(section_starts.keys())
        for i, bug_id in enumerate(sorted_ids):
            start, title = section_starts[bug_id]
            end = section_starts[sorted_ids[i + 1]][0] if i + 1 < len(sorted_ids) else len(text)

            # Table
            table_row = ""
            for line in text.split("\n"):
                if f"| {bug_id} " in line or f"|~~{bug_id}~~" in line:
                    table_row = line.strip()
                    break

            content_lines = [f"## {bug_id}: {title}"]
            if table_row:
                content_lines.append(f"**Table entry:** {table_row}")
            content_lines.append("")
            content_lines.append(text[start:end].strip())
            sections[bug_id] = "\n".join(content_lines)

        return sections

    @staticmethod
    def _parse_debt(text):
        """Parses tech-debt.md: detailed sections '## TD-NNN — Title' + table"""
        sections = {}
        section_pattern = re.compile(r"^## (TD-\d+)\s*[—\-]\s*(.+?)$", re.MULTILINE)
        section_starts = {}
        for m in section_pattern.finditer(text):
            section_starts[m.group(1)] = (m.start(), m.group(2).strip())

        sorted_ids = sorted(section_starts.keys())
        for i, td_id in enumerate(sorted_ids):
            start, title = section_starts[td_id]
            end = section_starts[sorted_ids[i + 1]][0] if i + 1 < len(sorted_ids) else len(text)

            table_row = ""
            for line in text.split("\n"):
                if f"| {td_id} " in line or f"|~~{td_id}~~" in line:
                    table_row = line.strip()
                    break

            content_lines = [f"## {td_id}: {title}"]
            if table_row:
                content_lines.append(f"**Table entry:** {table_row}")
            content_lines.append("")
            content_lines.append(text[start:end].strip())
            sections[td_id] = "\n".join(content_lines)

        return sections

    def build(self) -> dict:
        """Runs the full initialization. Returns a summary."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # .context/ README — infrastructure, may overwrite
        self._write(self.context / "README.md", CONTEXT_README, overwrite=True)

        # docs/ — disciplines: NEVER overwrites existing docs to preserve
        # content already populated by skills or manually
        for fname, title in DOC_FILES.items():
            doc_path = self.context / "docs" / fname
            if doc_path.exists():
                continue  # preserves existing content
            if fname == "00-vision.md":
                # 00-vision.md has a special template with the initiatives section
                content = VISION_TEMPLATE.format(date=now)
            else:
                skill = {
                    "01-requirements.md": "cp-requirements",
                    "02-architecture.md": "cp-architecture",
                    "03-security-lgpd.md": "cp-security",
                    "04-quality-qa.md": "cp-quality",
                    "05-devops-operations.md": "cp-devops",
                    "06-kanban.md": "cp-agile",
                }[fname]
                content = DISCIPLINE_TEMPLATE.format(
                    title=title, skill=skill, date=now
                )
            self._write(doc_path, content)

        # inbox/
        for name in INBOX_DIRS:
            self._mkdir(self.context / "inbox" / name)
            self._write(self.context / "inbox" / name / "README.md",
                        INBOX_TEMPLATE.format(name=name),
                        overwrite=True)

        # tracking/ — infrastructure templates, overwrites
        self._write(self.context / "tracking" / "progress.md",
                    TRACKING_PROGRESS.format(status="Pending", date=now),
                    overwrite=True)
        self._write(self.context / "tracking" / "decisions.md",
                    TRACKING_DECISIONS.format(date=now),
                    overwrite=True)

        # kanban/ — the pipeline exists from initialization, not from the
        # first run of cp-agile. Each column carries a .gitkeep because git
        # does not version empty directories.
        self._write(self.context / "kanban" / "README.md", KANBAN_README,
                    overwrite=True)
        for col in KANBAN_COLUMNS + [KANBAN_BLOCKED_DIR]:
            self._mkdir(self.context / "kanban" / col)
            self._write(self.context / "kanban" / col / ".gitkeep", "",
                        overwrite=True)

        # Migration tracking → kanban: if tracking/tasks.md, tracking/bugs.md
        # or tracking/tech-debt.md exist, extracts the content of each section
        # and injects it into the respective kanban cards. The tracking files
        # are moved to _backup_pre_migration/.
        self.migrate_tracking_to_kanban()

        # vision.md ingestion
        vision_ingested = self.ingest_vision()
        self.vision_ingested = vision_ingested

        # Root pointers — infrastructure, overwrites
        self._write(self.root / "CLAUDE.md", CLAUDE_MD, overwrite=True)
        self._write(self.root / "AGENT.md", AGENT_MD, overwrite=True)

        return {
            "root": str(self.root),
            "context": str(self.context),
            "files_created": len(self.created),
            "vision_ingested": vision_ingested,
            "dry_run": self.dry_run,
        }

    def report_gaps(self):
        """Presents an executive summary and clarifying questions per discipline."""
        print("\n" + "=" * 60)
        print("  📋 EXECUTIVE SUMMARY — Documentation Initialization")
        print("=" * 60)
        print(f"  Root: {self.root}")
        print(f"  Source of truth: {self.context}")
        print(f"  Files created: {len(self.created)}")
        print(f"  Kanban: {len(KANBAN_COLUMNS)} columns + blocked/ in "
              f"{CONTEXT_DIR}/kanban/")
        print(f"  vision.md ingested: {'yes' if self.vision_ingested else 'not found'}")
        print()

        print("  ❓ Clarifying questions per discipline:")
        questions = {
            "Requirements (01)": "What is the MVP scope? Who are the stakeholders?",
            "Architecture (02)": "What are the technologies? Are there infrastructure constraints?",
            "Security/LGPD (03)": "Which personal data is processed? Is there a DPO?",
            "Quality/QA (04)": "What is the desired test coverage? Is there CI?",
            "DevOps/Operations (05)": "Where will the deploy be? Is there monitoring?",
            "Kanban/pipeline (06)": "The kanban already exists in .context/kanban/ — is there Trello integration? What are the first tasks?",
        }
        for disc, question in questions.items():
            print(f"    • {disc}: {question}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-doc-initializer: Documentation Initializer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python run.py
  python run.py --dir /path/to/project
  python run.py --dry-run
        """,
    )
    parser.add_argument("--dir", "-d", default=None,
                        help="Project directory (default: current directory)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Shows what it would do, without creating files")
    args = parser.parse_args()

    init = DocInitializer(Path(args.dir) if args.dir else None, args.dry_run)
    summary = init.build()

    print(f"🚀 Initializing documentation in {summary['root']}...")
    if summary["dry_run"]:
        print("🧪 DRY RUN — nothing was created. Remove --dry-run to execute.\n")
    else:
        print(f"✅ .context/ structure created at {summary['context']}\n")

    for item in init.created:
        print(f"  {item}")

    init.report_gaps()


if __name__ == "__main__":
    main()
