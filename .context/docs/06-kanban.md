# Kanban / Pipeline — Core Product Skills

> ⚠️ **DEPRECATED MODE** — all `cp-*` skills live in **`skills/deprecated/`** and
> are no longer installed or orchestrated by default (ADR-0007). The kanban flow
> below is historical.

> Discipline: Execution pipeline (`cp-agile`). Updated 2026-10-04.

## Status

- [x] Initial backlog recorded
- Kanban source of truth: **local** (`.context/kanban/`). Trello, if connected,
  is only a mirrored view.

## Flow

```
.context/inbox/{initiatives,tasks,bugs,tech-debt}/  ← raw intake (drafts)
        │  manual triage (human or agent)
        ▼
.context/kanban/{1-backlog,2-todo,...}/                  ← triaged work in flow
        │  cp-agile (polling)
        ▼
   cp-orchestrator  ──► skill of the appropriate mode ──► .context/docs/<discipline>.md
        │
        └─► question/blocker ──► .context/kanban/blocked/ ──► waits for human answer
```

## Board

### 🔵 Backlog

_(empty — all backlog raised at initialization was completed on 2026-08-18)_

New work enters as a draft in `.context/inbox/`. After triage, it moves to `.context/kanban/1-backlog/`.

### 🟡 In progress

_(empty)_

### 🟢 Done

| ID | Item | Date |
|----|------|------|
| DT-02 | Smoke test suite (`--help`, `--dry-run`, exit codes) | 2026-08-18 |
| DT-03 | Validation of the `invoke` x `argparse` contract | 2026-08-18 |
| DT-04 | Optional authentication in `claude_proxy.py` (`CLAUDE_PROXY_TOKEN`) | 2026-08-18 |
| DT-05 | `requirements.txt` + `requirements-dev.txt` | 2026-08-18 |
| DT-06 | CI (GitHub Actions: Linux 3.12/3.13 + Windows informative) | 2026-08-18 |
| DOC-01 | Proxy port aligned at 8090 | 2026-08-18 |
| BUG-03 | Quality gate fails on exit code != 0 | 2026-08-18 |
| BUG-04 | Quality gate matches keywords by whole word | 2026-08-18 |
| BUG-05 | `cp-goal-loop` derives a single step from `--goal` | 2026-08-18 |
| DT-07 | `crewai` with guarded import — `--help` in 15/15 | 2026-08-18 |
| DT-08 | `require_llm()` fails early with actionable message | 2026-08-18 |
| DT-01 | `setup_console()` forces UTF-8 on stdout/stderr | 2026-08-18 |
| INIT-01 | Documentation initialization in `.context/` | 2026-08-18 |

## Conventions

- One `.md` file per item, inside the corresponding kanban folder.
- Raw (untriaged) item stays in `.context/inbox/`; after triage, move it with `git mv` to `.context/kanban/`.
- Completed item: mark `[Done]` (feature) or `[Fixed]` (bug) in the title and
  move it with `git mv` to the processed folder, preserving history.
- Priority follows MoSCoW, aligned with `.context/docs/01-requirements.md`.
