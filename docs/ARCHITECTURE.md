# Architecture

The skills under `skills/` implement the **Rational Unified Process** as an
autonomous team of CrewAI agents (Kruchten, 3rd ed.). The user interacts
exclusively with `rup-orchestrator`, which governs the lifecycle and dispatches
the 8 discipline skills. **9 disciplines, 21 agents** (1 orchestrator + 20
specialists).

> The legacy Software Factory family (`cp-*`) was removed (ADR-0010); its
> architecture is recorded in the git history up to commit `6490694`.

```
                    ┌─────────────────────────────┐
                    │   rup-orchestrator          │
                    │   (Project Manager)         │
                    │   - plans phases/iterations │
                    │   - maintains SDP/Risk/Case │
                    │   - sizes the software (UCP)│
                    │   - emits Work Orders       │
                    └─────────────┬───────────────┘
                                  │ Work Orders → subprocess dispatch
   ┌───────────┬───────────┬──────┴────┬───────────┬───────────┬──────────┐
   ▼           ▼           ▼           ▼           ▼           ▼          ▼
rup-env  rup-business  rup-req  rup-analysis  rup-impl   rup-test  rup-ccm  rup-deploy
(1)      -modeling(2)  (2)      -design(5)    (2)        (4)       (2)      (2)
```

## Skill anatomy

Each skill is self-contained: `SKILL.md` + `scripts/run.py` (embedded agents +
argparse) + `references/` (agent → artifact mapping; the orchestrator also has
`lifecycle.md` and `sizing-estimation.md`). Inside a discipline crew, each agent
gets one task and the tasks run in `Process.sequential`.

Shared CLI: `run.py "<briefing>" --phase <P> [--input F] [--output F] [--dry-run]`.
Exit codes: 0 ok · 1 usage · 2 no LLM · 3 no crewai.

## Dispatch

The orchestrator dispatches a discipline by its `scripts/run.py` via
`subprocess` (interpreter: `RUP_SKILLS_PYTHON`, else the current one).

- `--discipline <key>`: one discipline, with the briefing passed positionally.
- `--auto`: the 8 disciplines in order (environment → … → deployment),
  **chained**: before each dispatch the orchestrator writes a context file with
  the briefing plus the artifacts of the previous disciplines (each capped at
  `MAX_PRIOR_ARTIFACT_CHARS`) and passes it with `--input`. Each discipline
  writes its own artifact (`<output-stem>.NN-<key>.md`, or a temporary workdir
  without `--output`). The run stops at the first discipline that fails.

## Software sizing

The orchestrator ships a deterministic **Use Case Points** estimator
(`compute_ucp`, with input validation in `ucp_from_model`):

- CLI: `--estimate [--sizing F] [--json]`, `--sizing-template` — no LLM, no crewai.
- Agent tool: the governance agent gets the `use_case_points_calculator` CrewAI
  tool and is instructed to call it instead of doing the arithmetic itself.

FPA (IFPUG/NESMA) and COCOMO II remain LLM-produced. Details:
`rup-orchestrator/references/sizing-estimation.md`.

## LLM resolution

`skills/_shared/llm.py` resolves the LLM provider-agnostically: agent env vars →
`.env` → per-provider key detection → default `gemini/gemini-2.5-flash`.
Each `run.py` finds `_shared/` next to the skill directory (repository, Claude
Code) or one level up (Hermes, which installs skills under a category).

## Portability

- **Zero hardcoded OS/machine paths** (C:\Windows, C:\Users, etc.)
- **Zero fixed personal values** (handles, machine names)
- Project paths use env vars + relative defaults
