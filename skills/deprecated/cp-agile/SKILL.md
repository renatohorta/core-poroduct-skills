---
name: cp-agile
description: "Agile — task execution pipeline with continuous polling, bidirectional feedback loop (questions and blockers) and Trello/Local integration. The LOCAL (.context/kanban/) is always the source of truth; Trello is only a mirrored view. Monitors the backlog, dispatches tasks to the cp-orchestrator, captures human answers and unblocks the pipeline. Use when the user says 'agile', 'task pipeline', 'kanban', 'monitor backlog', 'dispatch tasks', 'task polling', 'feedback loop', 'question', 'blocker', 'resume task'."
---

# cp-agile — Agile (Execution Pipeline)

Agile is the **maestro of the execution pipeline**. It continuously monitors the
**local** backlog (`.context/kanban/`), dispatches ready tasks to the `cp-orchestrator`,
and manages the **bidirectional feedback loop** — capturing AI questions and blockers,
and resuming tasks when the human answers.

## Architecture: Local is the source of truth

```
[Local .context/kanban/]  ──(source of truth)──►  [Trello (mirror/view)]
      ▲                                              │
      └────────────── syncs state ───────────────────┘
```

- **The LOCAL (`.context/kanban/`) is ALWAYS the source of truth.** All decisions
  (scan, movement, questions, blockers, resume) happen locally.
- **Trello is only a MIRRORED VIEW** of the local state. If mirroring is enabled
  (`--sync-trello`), each local change is reflected in Trello.
- **Trello NEVER decides state** — it only displays what is local.

## Analogy

Imagine an **orchestra conductor** who is also the **doorman**:

```
[Local backlog] ──► [Agile detects ready task] ──► [Dispatch to cp-orchestrator]
                                                          │
                    ┌─────────────────────────────────────┘
                    ▼
              [AI has a question?] ──► [❓ Question to human] ──► [Waits for answer]
                    │                                              │
                    └── [AI blocked?] ──► [🚧 Blocker] ──► [blocked/]
                                                                   │
                    [Human answers] ◄──────────────────────────────┘
                          │
                          ▼
              [HUMAN_CLARIFICATION_RECEIVED] ──► [Unblocks pipeline]
```

## Usage

```
/load skill cp-agile
start pipeline
```

Or:

```
agile, monitor the backlog and dispatch the ready tasks
```

## Components

### 1. `CPAgileDaemon` (Polling & Watcher)

- Creates the automatic local folder structure in `.context/kanban/`:
  `1-backlog/`, `2-todo/`, `3-doing/`, `4-review/`, `5-testing/`, `6-staging/`,
  `7-done/` and `blocked/`.
- Continuous scan of the **local** for files with `status: ready` (YAML frontmatter).
- Standardized dispatch of the `TASK_DISPATCHED` event to the `cp-orchestrator`.
- If `--sync-trello`, mirrors each dispatch in Trello (view).

### 2. `CPAgileFeedbackLoop` (Bidirectionality)

- **Questions (`QUESTION`)**: adds a `## Pending Questions` section to the local file
  (and mirrors in Trello with label `ai:waiting-human` if enabled).
- **Blockers (`BLOCKER`)**: moves the local file to `blocked/` and appends an
  error and severity log.
- **Resume (`resume_task`)**: captures the human answer locally and emits the
  `HUMAN_CLARIFICATION_RECEIVED` event to unblock the pipeline.

### 3. `TrelloMirror` (Mirror/View)

- Reflects the local state in Trello (creates/updates cards per the local column).
- If the Trello MCP tools are not available, mirroring is silently disabled —
  the local keeps working on its own.

### 4. Task `.md` Template and State Matrix

- Schema with full YAML frontmatter for versioning via Git.

## State Matrix

| State | Folder | Description |
|--------|-------|-----------|
| `backlog` | `1-backlog/` | Task awaiting prioritization |
| `ready` | `1-backlog/` | Ready for dispatch (`status: ready` flag) |
| `todo` | `2-todo/` | Dispatched, awaiting execution |
| `doing` | `3-doing/` | Being executed by the cp-orchestrator |
| `review` | `4-review/` | Awaiting review |
| `testing` | `5-testing/` | In testing |
| `staging` | `6-staging/` | In staging |
| `done` | `7-done/` | Completed |
| `blocked` | `blocked/` | Blocked, awaiting human |

## Events

| Event | Source | Destination |
|--------|--------|---------|
| `TASK_DISPATCHED` | Agile (daemon) | cp-orchestrator |
| `QUESTION` | AI (during execution) | Human (local + Trello mirror) |
| `BLOCKER` | AI (during execution) | blocked/ |
| `HUMAN_CLARIFICATION_RECEIVED` | Human (answer) | Pipeline (unblock) |

## Script

```bash
# Start polling daemon (always reads from local)
python .hermes/skills/cp-agile/scripts/run.py --daemon

# Start daemon with Trello mirroring (view of local)
python .hermes/skills/cp-agile/scripts/run.py --daemon --sync-trello

# Sync the entire local state to Trello (one-shot)
python .hermes/skills/cp-agile/scripts/run.py --sync-trello

# Register a question (local; mirrors to Trello if enabled)
python .hermes/skills/cp-agile/scripts/run.py --question "task-123" --message "What is the MVP scope?" --sync-trello

# Register a blocker
python .hermes/skills/cp-agile/scripts/run.py --blocker "task-123" --error "Connection failure" --severity high

# Resume task (human answer)
python .hermes/skills/cp-agile/scripts/run.py --resume "task-123" --answer "The MVP covers login and signup"
```

## Integration with the orchestrator

`cp-agile` is triggered by the `cp-orchestrator` via the `agile` mode:

```bash
python .hermes/skills/cp-orchestrator/scripts/run.py "start pipeline" --mode agile --auto
```

The daemon dispatches `TASK_DISPATCHED` to the orchestrator, which executes the task
via the appropriate pipeline (full, sprint, micro, etc.).
