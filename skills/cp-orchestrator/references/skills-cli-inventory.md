# CLI inventory of the cp-* skills (trigger contract)

When adding a new skill to the orchestrator or debugging why a phase is not
triggered, check the skill's real CLI contract in `scripts/run.py` — do NOT assume
every skill accepts `--output` nor that the briefing enters as a positional
argument. Each skill has its own interface.

## How the orchestrator triggers (the `invoke` metadata in `CREWS`)

Each crew carries `invoke` with two fields:
- `briefing_arg`: `positional` (positional arg), `goal` (`--goal`), `input` (`--input`), or `daemon` (no positional — builds `--daemon --source local`)
- `output`: `True` if the skill accepts `--output`, `False` otherwise

`_build_cli_args` reads this metadata. If a new skill is added without the
metadata, the default is `{"briefing_arg": "input", "output": True}` — which breaks
skills that don't accept `--output` (argparse rejects the unknown flag).

## CLI contract per skill (verified 2026-08)

### Pipeline phases (all accept `--input` and `--output`)
| skill | briefing | output |
|-------|----------|--------|
| cp-requirements | positional / `--input` | YES |
| cp-architecture | positional / `--input` | YES |
| cp-implementation | positional / `--input` | YES (+ `--type`) |
| cp-testing | positional / `--input` | YES (+ `--source`, `--acceptance`, `--mode`) |
| cp-security | positional / `--input` | YES (+ `--mode`) |
| cp-devops | positional / `--input` | YES (+ `--mode`) |
| cp-quality | positional / `--input` | YES (+ `--mode`) |

### Complementary skills (dedicated modes)
| skill | briefing | output | extra flags |
|-------|----------|--------|-------------|
| cp-bug-fix | positional (`bug_description`) | **NO** | `--type backend/frontend` |
| cp-competitive-analysis | positional (`context`) / `--input` | YES | — |
| cp-goal-loop | **`--goal` (required)** | **NO** | `--steps`, `--steps-file`, `--max-attempts`, `--max-time` |
| cp-maintenance | positional (`description`) / `--input` | YES | `--mode bug-fix/refactor/improvement/full` |
| cp-agile | **`--daemon` (no positional)** | **NO** | `--sync-trello`, `--question`, `--blocker`, `--resume`, `--init`, `--doc` |
| cp-software-spec | **`--init` / `--inspect <path>` / `--refine-card <ID>` (no positional)** | **NO** | `--dir`, `--force`, `--dry-run` |

> **`cp-full-dev` was merged into the orchestrator (removed).** The NEXUS pipeline (7 phases,
> 39 agents) now runs natively via `NexusExecutor` in the orchestrator's `run.py`.
> The `full-dev` mode runs NEXUS in memory (automatic full/sprint/micro detection,
> per-phase quality gates) — there is no longer an external `scripts/run.py` to call.

## Pitfalls
- `cp-goal-loop` has NO positional argument — the briefing enters only via `--goal`.
  Passing the briefing as positional makes argparse fail.
- `cp-bug-fix`, `cp-goal-loop` and `cp-agile` do NOT accept `--output`. Passing
  that flag makes argparse reject it (unknown argument).
- `cp-agile` has NO positional argument — only `--daemon`/`--question`/`--blocker`/
  `--resume`/`--init`. The orchestrator uses `briefing_arg: "daemon"` to build
  `--daemon --source local`.
- NEXUS (`full-dev`) is native: do not use `SKILL_PATHS`/`CREWS` for it — `main()`
  diverts to `NexusExecutor` when `mode == "full-dev"`.

## How to verify a new skill's contract
```python
import re
from pathlib import Path
content = Path(".../cp-X/scripts/run.py").read_text(encoding="utf-8")
print("output:", "--output" in content)
print("input:", "--input" in content)
m = re.search(r'add_argument\(\s*"([a-z_]+)"', content)  # positional arg
print("positional:", m.group(1) if m else None)
```
