#!/usr/bin/env python3
"""
cp-software-spec — Software Spec & Knowledge Base (self-contained)

Unifies documentation initialization, reverse engineering and software
specification in a concise RUP model (.context/), generating actionable inputs
for code replication by agents and refining kanban cards into executable issues.

Modes:
  --init                 Scaffold the canonical .context/ structure (new project)
  --inspect <path>       Reverse-engineer an existing codebase into RUP docs
  --refine-card <ID>     Refine a backlog card into an executable issue (2-todo/)

Usage:
  python run.py --init
  python run.py --init --dir /path/to/project
  python run.py --inspect /path/to/project
  python run.py --refine-card TASK-001
  python run.py --dry-run            # shows what it would do, without creating
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
# .context/ CANONICAL STRUCTURE (RUP Operational — 4 phases)
# ═══════════════════════════════════════════════════════════════════════════

CONTEXT_DIR = ".context"

# RUP phases (docs/) — the single source of truth. No flat root files, no
# 05-project-management: task management lives exclusively in kanban/.
RUP_PHASES = {
    "01-inception": {
        "vision-and-scope.md": "Product vision, actors and business goals",
        "requirements.md": "Functional (FR) and Non-Functional (NFR) requirements",
    },
    "02-elaboration": {
        "architecture.md": "Stack, C4/Mermaid diagrams and structural decisions",
        "domain-model.md": "Domain entities, aggregates and core use cases",
    },
    "03-construction": {
        "api-contracts.md": "OpenAPI contracts, endpoints, payloads and schemas",
        "ui-spec.md": "Routes, Design System tokens, AppShell and Generative UI",
        "data-dictionary.md": "DB models, migrations, tables and persistence rules",
    },
    "04-transition": {
        "test-strategy.md": "Test pyramid, coverage and execution commands",
        "devops-infra.md": "Docker, CI/CD pipelines, variables and runbooks",
    },
}

# Inbox folders (raw intake)
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

### docs/ — RUP Operational (4 phases)
| Phase | File | Content |
|-------|------|---------|
| `01-inception/` | `vision-and-scope.md` | Product vision, actors and business goals |
| `01-inception/` | `requirements.md` | Functional (FR) and Non-Functional (NFR) requirements |
| `02-elaboration/` | `architecture.md` | Stack, C4/Mermaid diagrams and structural decisions |
| `02-elaboration/` | `domain-model.md` | Domain entities, aggregates and core use cases |
| `03-construction/` | `api-contracts.md` | OpenAPI contracts, endpoints, payloads and schemas |
| `03-construction/` | `ui-spec.md` | Routes, Design System tokens, AppShell and Generative UI |
| `03-construction/` | `data-dictionary.md` | DB models, migrations, tables and persistence rules |
| `04-transition/` | `test-strategy.md` | Test pyramid, coverage and execution commands |
| `04-transition/` | `devops-infra.md` | Docker, CI/CD pipelines, variables and runbooks |

### inbox/ — Work intake
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

When a card is promoted to `2-todo/` it is refined into an **executable issue**
(Ready for Dev) with Definition of Ready (DoR), API contracts, schemas and
target files — see `kanban/2-todo/{ID}.md`.

## Rule

Every `cp-*` skill documents its artifacts in `.context/docs/`. The
`cp-software-spec` skill guarantees the structure exists.
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
|--------|---------|
| `1-backlog/` | Entry. The daemon scans here for tasks with `status: ready` |
| `2-todo/` | Prioritized, awaiting execution. **Cards here are executable issues (Ready for Dev)** |
| `3-doing/` | In execution (dispatched to the `cp-orchestrator`) |
| `4-review/` | Awaiting review |
| `5-testing/` | In testing |
| `6-staging/` | Staging |
| `7-done/` | Completed |
| `blocked/` | Question or blocker awaiting human answer |

## Backlog → ToDo promotion (executable issue)

When a card is promoted from `1-backlog/` to `2-todo/`, it is transformed and
validated as an **Issue Executável (Ready for Dev)** with Definition of Ready
(DoR), API contracts, schemas and target files. Use the `cp-software-spec`
skill:

```bash
python <skills>/cp-software-spec/scripts/run.py --refine-card TASK-001
```

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
- RUP specification: `.context/docs/`
- Work intake: `.context/inbox/`
- Tracking and ADRs: `.context/tracking/`
- Task pipeline: `.context/kanban/`
"""

# Template of the AGENT.md (root pointer)
AGENT_MD = """# AGENT.md — Project Context

**Source of truth: `.context/`**

Read and write all project context in `.context/`. **DO NOT** create or use
`.hermes/` or `.claude/` for context.

- Overview: `.context/README.md`
- RUP specification: `.context/docs/`
- Work intake: `.context/inbox/`
- Tracking and ADRs: `.context/tracking/`
- Task pipeline: `.context/kanban/`
"""

# Template of a RUP phase doc
RUP_DOC_TEMPLATE = """# {title}

> Document managed by the `cp-software-spec` skill. Updated at {date}.

## Status

- [ ] Pending
- [ ] In progress
- [ ] Completed

## Content

<!-- Artifacts of the {phase} phase are written here -->

## Decisions

<!-- Decision record of this phase -->
"""

# Template of the vision-and-scope.md — includes the initiatives section
VISION_TEMPLATE = """# 01 — Product Vision & Scope

> Document managed by the `cp-software-spec` skill. Updated at {date}.

## What it is

<!-- Description of the product/system -->

## Why this repository exists

<!-- Context, motivation, constraints -->

## Actors

<!-- Who interacts with the system -->

## Business goals

<!-- What the product must achieve -->

## Initiatives (Epics)

<!-- List of the project's initiatives/epics. Each initiative aggregates multiple kanban cards.
     Suggested format: table with ID, title, status and linked tasks.

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

# Executable issue template (Backlog -> ToDo promotion)
EXECUTABLE_ISSUE_TEMPLATE = """---
id: {task_id}
title: "{title}"
type: {type}
status: ready
assigned_to: agent-coder
context_refs:
  - .context/docs/02-elaboration/architecture.md
  - .context/docs/03-construction/api-contracts.md
---

### 1. Contexto & Objetivo

{description}

### 2. Arquivos Alvo

- **Modificar**: `{target_modify}`
- **Criar**: `{target_create}`
- **Testes**: `{target_tests}`

### 3. Critérios de Aceite (DoR / DoD)

- [ ] {acceptance_criteria}

### 4. Insumos Técnicos e Contratos de Dados

```json
{data_contract}
```

### 5. Passos de Validação e Execução

1. `{test_command}`
2. `{lint_command}`
"""


# ═══════════════════════════════════════════════════════════════════════════
# SOFTWARE SPEC — scaffold, reverse engineering and card refinement
# ═══════════════════════════════════════════════════════════════════════════

class SoftwareSpec:
    """Creates/maintains the .context/ structure, reverse-engineers codebases
    and refines kanban cards into executable issues."""

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
            self.created.append(f"[dry-run] {self._rel(path)}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.created.append(str(self._rel(path)))

    def _rel(self, path: Path) -> Path:
        """Returns the path relative to the project root, or the absolute path
        if it is outside the root (e.g. --inspect writing into a target's
        .context/)."""
        try:
            return path.relative_to(self.root)
        except ValueError:
            return path

    def _mkdir(self, path: Path):
        """Creates a directory (or records it in dry-run)."""
        if self.dry_run:
            self.created.append(f"[dry-run] {path.relative_to(self.root)}/")
            return
        path.mkdir(parents=True, exist_ok=True)
        self.created.append(str(path.relative_to(self.root)) + "/")

    def ingest_vision(self):
        """Moves vision.md (if it exists at the root) to .context/docs/01-inception/vision-and-scope.md."""
        vision_src = self.root / "vision.md"
        if not vision_src.exists():
            return False
        vision_dst = self.context / "docs" / "01-inception" / "vision-and-scope.md"
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
        section_pattern = re.compile(r"^## (BUG-\d+)\s*[—\-]\s*(.+?)$", re.MULTILINE)
        section_starts = {}
        for m in section_pattern.finditer(text):
            section_starts[m.group(1)] = (m.start(), m.group(2).strip())

        sorted_ids = sorted(section_starts.keys())
        for i, bug_id in enumerate(sorted_ids):
            start, title = section_starts[bug_id]
            end = section_starts[sorted_ids[i + 1]][0] if i + 1 < len(sorted_ids) else len(text)

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

        # docs/ — RUP phases: NEVER overwrites existing docs to preserve
        # content already populated by skills or manually
        for phase, files in RUP_PHASES.items():
            for fname, title in files.items():
                doc_path = self.context / "docs" / phase / fname
                if doc_path.exists():
                    continue  # preserves existing content
                if fname == "vision-and-scope.md":
                    content = VISION_TEMPLATE.format(date=now)
                else:
                    content = RUP_DOC_TEMPLATE.format(
                        title=title, phase=phase, date=now
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
        """Presents an executive summary and clarifying questions per phase."""
        print("\n" + "=" * 60)
        print("  📋 EXECUTIVE SUMMARY — Software Spec Initialization")
        print("=" * 60)
        print(f"  Root: {self.root}")
        print(f"  Source of truth: {self.context}")
        print(f"  Files created: {len(self.created)}")
        print(f"  Kanban: {len(KANBAN_COLUMNS)} columns + blocked/ in "
              f"{CONTEXT_DIR}/kanban/")
        print(f"  vision.md ingested: {'yes' if self.vision_ingested else 'not found'}")
        print()

        print("  ❓ Clarifying questions per RUP phase:")
        questions = {
            "Inception (01)": "What is the MVP scope? Who are the stakeholders?",
            "Elaboration (02)": "What are the technologies? Are there infrastructure constraints?",
            "Construction (03)": "Which endpoints/schemas? Which screens? Which DB models?",
            "Transition (04)": "What is the desired test coverage? Is there CI? Where will the deploy be?",
        }
        for phase, question in questions.items():
            print(f"    • {phase}: {question}")

    # ═══════════════════════════════════════════════════════════════════
    # REVERSE ENGINEERING (--inspect)
    # ═══════════════════════════════════════════════════════════════════

    def inspect(self, target: Path) -> dict:
        """Reverse-engineers an existing codebase into concise RUP docs.

        Generates replication-oriented documents: schema tables, type-contract
        snippets, reproducible commands and Mermaid diagrams. Idempotent: does
        not overwrite docs that already contain deep manual customizations
        (unless --force). The docs are written into the TARGET project's own
        `.context/docs/` (not the current working directory's).
        """
        target = Path(target)
        if not target.exists():
            print(f"❌ Target path does not exist: {target}")
            sys.exit(1)

        findings = self._scan_ecosystem(target)
        self._write_inspection_docs(target, findings)

        return {
            "target": str(target),
            "manifests": findings["manifests"],
            "routes": findings["routes"],
            "api_files": findings["api_files"],
            "db_files": findings["db_files"],
            "infra_files": findings["infra_files"],
            "dry_run": self.dry_run,
        }

    def _scan_ecosystem(self, target: Path) -> dict:
        """Scans the technical ecosystem of a codebase."""
        findings = {
            "manifests": [],
            "routes": [],
            "api_files": [],
            "db_files": [],
            "infra_files": [],
        }

        # Manifest files
        for name in ["package.json", "pyproject.toml", "Cargo.toml", "go.mod",
                     "requirements.txt", "Pipfile", "composer.json"]:
            p = target / name
            if p.exists():
                findings["manifests"].append(str(p.relative_to(target)))

        # Routes & screens
        for pattern in ["src/routes/**/*.tsx", "src/routes/**/*.jsx",
                        "src/pages/**/*.tsx", "src/pages/**/*.jsx",
                        "app/**/page.tsx", "app/**/page.jsx"]:
            for p in target.glob(pattern):
                findings["routes"].append(str(p.relative_to(target)))

        # API & schemas
        for pattern in ["**/controllers/**/*.py", "**/routes/**/*.py",
                        "**/api/**/*.py", "**/schemas/**/*.py",
                        "**/serializers.py", "**/views.py"]:
            for p in target.glob(pattern):
                if "node_modules" in str(p) or ".venv" in str(p):
                    continue
                findings["api_files"].append(str(p.relative_to(target)))

        # Database
        for pattern in ["**/models.py", "**/models/**/*.py",
                        "prisma/schema.prisma", "**/migrations/**/*.sql",
                        "**/migrations/**/*.py"]:
            for p in target.glob(pattern):
                if "node_modules" in str(p) or ".venv" in str(p):
                    continue
                findings["db_files"].append(str(p.relative_to(target)))

        # Infrastructure
        for name in ["Dockerfile", "docker-compose.yml", "docker-compose.yaml",
                     ".github/workflows/*.yml", ".github/workflows/*.yaml"]:
            for p in target.glob(name):
                findings["infra_files"].append(str(p.relative_to(target)))

        return findings

    def _write_inspection_docs(self, target: Path, findings: dict):
        """Writes the reverse-engineered docs into the TARGET's RUP structure.

        The docs go to `target/.context/docs/` — the target project's own source
        of truth — not the current working directory's.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        target_context = target / CONTEXT_DIR
        docs_root = target_context / "docs"

        # 02-elaboration/architecture.md
        arch_path = docs_root / "02-elaboration" / "architecture.md"
        if not arch_path.exists() or self._force:
            arch = [
                "# Architecture — Reverse Engineered",
                "",
                f"> Generated by `cp-software-spec --inspect` at {now}.",
                "",
                "## Stack (manifests)",
                "",
            ]
            if findings["manifests"]:
                for m in findings["manifests"]:
                    arch.append(f"- `{m}`")
            else:
                arch.append("- _(no manifest found)_")
            arch += [
                "",
                "## Routes & Screens",
                "",
            ]
            if findings["routes"]:
                for r in findings["routes"]:
                    arch.append(f"- `{r}`")
            else:
                arch.append("- _(none found)_")
            arch += [
                "",
                "## API & Schemas",
                "",
            ]
            if findings["api_files"]:
                for a in findings["api_files"]:
                    arch.append(f"- `{a}`")
            else:
                arch.append("- _(none found)_")
            arch += [
                "",
                "## Database",
                "",
            ]
            if findings["db_files"]:
                for d in findings["db_files"]:
                    arch.append(f"- `{d}`")
            else:
                arch.append("- _(none found)_")
            arch += [
                "",
                "## Infrastructure",
                "",
            ]
            if findings["infra_files"]:
                for i in findings["infra_files"]:
                    arch.append(f"- `{i}`")
            else:
                arch.append("- _(none found)_")
            arch += [
                "",
                "## Decisions",
                "",
                "<!-- Record structural decisions here as ADRs -->",
                "",
            ]
            self._write(arch_path, "\n".join(arch))

        # 03-construction/api-contracts.md
        api_path = docs_root / "03-construction" / "api-contracts.md"
        if not api_path.exists() or self._force:
            api = [
                "# API Contracts — Reverse Engineered",
                "",
                f"> Generated by `cp-software-spec --inspect` at {now}.",
                "",
                "## Endpoints & Schemas",
                "",
            ]
            if findings["api_files"]:
                for a in findings["api_files"]:
                    api.append(f"- `{a}`")
            else:
                api.append("- _(none found — document the OpenAPI contracts here)_")
            api += [
                "",
                "## Data Contracts",
                "",
                "```json",
                "{}",
                "```",
                "",
            ]
            self._write(api_path, "\n".join(api))

        # 03-construction/data-dictionary.md
        dd_path = docs_root / "03-construction" / "data-dictionary.md"
        if not dd_path.exists() or self._force:
            dd = [
                "# Data Dictionary — Reverse Engineered",
                "",
                f"> Generated by `cp-software-spec --inspect` at {now}.",
                "",
                "## Models & Tables",
                "",
            ]
            if findings["db_files"]:
                for d in findings["db_files"]:
                    dd.append(f"- `{d}`")
            else:
                dd.append("- _(none found — document the DB models here)_")
            dd += [
                "",
                "## Persistence Rules",
                "",
                "<!-- migrations, constraints, indexes -->",
                "",
            ]
            self._write(dd_path, "\n".join(dd))

        # 04-transition/devops-infra.md
        devops_path = docs_root / "04-transition" / "devops-infra.md"
        if not devops_path.exists() or self._force:
            devops = [
                "# DevOps & Infra — Reverse Engineered",
                "",
                f"> Generated by `cp-software-spec --inspect` at {now}.",
                "",
                "## Docker / CI-CD",
                "",
            ]
            if findings["infra_files"]:
                for i in findings["infra_files"]:
                    devops.append(f"- `{i}`")
            else:
                devops.append("- _(none found — document the infra here)_")
            devops += [
                "",
                "## Runbook",
                "",
                "<!-- reproducible commands, env vars, deploy steps -->",
                "",
            ]
            self._write(devops_path, "\n".join(devops))

    # ═══════════════════════════════════════════════════════════════════
    # CARD REFINEMENT (--refine-card) — Backlog -> ToDo
    # ═══════════════════════════════════════════════════════════════════

    def refine_card(self, task_id: str) -> Path:
        """Transforms a backlog card into an executable issue (Ready for Dev).

        Reads the card from kanban/1-backlog/, enriches it with the executable
        issue schema (DoR, target files, acceptance criteria, data contracts,
        validation steps) and moves it to kanban/2-todo/.
        """
        kanban = self.context / "kanban"
        backlog = kanban / "1-backlog"
        todo = kanban / "2-todo"

        # Locates the card in the backlog
        card_path = None
        if backlog.exists():
            for f in backlog.glob("*.md"):
                if f.stem == task_id or task_id in f.name:
                    card_path = f
                    break
        if not card_path:
            print(f"❌ Card {task_id} not found in {backlog}")
            sys.exit(1)

        content = card_path.read_text(encoding="utf-8")
        meta = self._parse_frontmatter(content)

        title = meta.get("title", task_id)
        type_ = meta.get("type", "feature")
        description = self._extract_description(content)

        # Builds the executable issue
        issue = EXECUTABLE_ISSUE_TEMPLATE.format(
            task_id=task_id,
            title=title,
            type=type_,
            description=description or "<!-- objective of the change and the value it adds -->",
            target_modify="src/",
            target_create="src/",
            target_tests="tests/",
            acceptance_criteria="Define the Definition of Ready (DoR) acceptance criteria",
            data_contract='{\n  "request": {},\n  "response": {}\n}',
            test_command="pytest tests/ -v",
            lint_command="ruff check .",
        )

        if self.dry_run:
            self.created.append(f"[dry-run] refine {task_id} → {todo / f'{task_id}.md'}")
            return todo / f"{task_id}.md"

        # Writes the executable issue in 2-todo/
        todo.mkdir(parents=True, exist_ok=True)
        dest = todo / f"{task_id}.md"
        dest.write_text(issue, encoding="utf-8")

        # Removes the original backlog card
        card_path.unlink()

        self.created.append(f"refine {task_id} → {dest.relative_to(self.root)}")
        return dest

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        """Extracts YAML frontmatter (--- ... ---) from a .md file."""
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not m:
            return {}
        data = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                data[key.strip()] = val.strip().strip('"').strip("'")
        return data

    @staticmethod
    def _extract_description(content: str) -> str:
        """Extracts the description section from a card body."""
        m = re.search(r"## Description\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if m:
            return m.group(1).strip()
        # Fallback: first paragraph after the title
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                return stripped
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-software-spec: Software Spec & Knowledge Base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Modes:
  --init                 Scaffold the canonical .context/ structure (new project)
  --inspect <path>       Reverse-engineer an existing codebase into RUP docs
  --refine-card <ID>     Refine a backlog card into an executable issue (2-todo/)

Examples:
  python run.py --init
  python run.py --init --dir /path/to/project
  python run.py --inspect /path/to/project
  python run.py --refine-card TASK-001
  python run.py --init --dry-run
        """,
    )
    parser.add_argument("--init", action="store_true",
                        help="Scaffold the canonical .context/ structure")
    parser.add_argument("--inspect", metavar="PATH", default=None,
                        help="Reverse-engineer an existing codebase into RUP docs")
    parser.add_argument("--refine-card", metavar="TASK_ID", default=None,
                        help="Refine a backlog card into an executable issue (2-todo/)")
    parser.add_argument("--dir", "-d", default=None,
                        help="Project directory (default: current directory)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite docs even if they contain manual customizations")
    parser.add_argument("--dry-run", action="store_true",
                        help="Shows what it would do, without creating files")
    args = parser.parse_args()

    spec = SoftwareSpec(Path(args.dir) if args.dir else None, args.dry_run)
    spec._force = args.force

    # ── Mode 1: Initialization / Scaffold ──
    if args.init:
        summary = spec.build()
        print(f"🚀 Initializing software spec in {summary['root']}...")
        if summary["dry_run"]:
            print("🧪 DRY RUN — nothing was created. Remove --dry-run to execute.\n")
        else:
            print(f"✅ .context/ structure created at {summary['context']}\n")
        for item in spec.created:
            print(f"  {item}")
        spec.report_gaps()
        return

    # ── Mode 2: Reverse Engineering / Deep inspection ──
    if args.inspect:
        print(f"🔍 Reverse-engineering {args.inspect}...")
        result = spec.inspect(Path(args.inspect))
        print(f"\n✅ Inspection complete. Findings:")
        print(f"  Manifests: {len(result['manifests'])}")
        print(f"  Routes: {len(result['routes'])}")
        print(f"  API files: {len(result['api_files'])}")
        print(f"  DB files: {len(result['db_files'])}")
        print(f"  Infra files: {len(result['infra_files'])}")
        print(f"\n  Docs written under {Path(args.inspect) / '.context' / 'docs'}:")
        for item in spec.created:
            print(f"    {item}")
        return

    # ── Mode 3: Card refinement (Backlog -> ToDo) ──
    if args.refine_card:
        print(f"🎯 Refining card {args.refine_card} into an executable issue...")
        dest = spec.refine_card(args.refine_card)
        if spec.dry_run:
            print(f"🧪 DRY RUN — would write {dest}")
        else:
            print(f"✅ Card {args.refine_card} refined and moved to 2-todo/")
            print(f"   → {dest}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
