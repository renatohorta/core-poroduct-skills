# Decision Log (ADRs) — Core Product Skills

> Every important decision is recorded here with context and rationale.

---

## ADR-0001 — Source of truth in `.context/`

**Date**: 2026-08-18 · **Status**: Accepted

**Context**: The project context was spread across `.hermes/` and `.claude/`,
polluting the repository and tying the documentation to a specific agent.

**Decision**: All context is read and written in `.context/`. `CLAUDE.md` and
`AGENT.md` at the root are only pointers. Creating `.hermes/`/`.claude/` for
context is forbidden.

**Consequences**: Documentation portable across agents; a single place to
consult. `docs/` still exists for human-facing documentation — in case of
divergence, `.context/` prevails.

---

## ADR-0002 — `cp-full-dev` merged into `cp-orchestrator`

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: The NEXUS pipeline (7 phases, 39 agents) lived in a separate skill,
triggered by the orchestrator via subprocess — an extra hop and two surfaces to
keep in sync.

**Decision**: NEXUS runs natively in the orchestrator via `NexusExecutor`; the
`cp-full-dev` skill was eliminated. Access is through the `full-dev` mode.

**Consequences**: Less indirection and automatic mode detection
(full/sprint/micro). In exchange, the orchestrator's `run.py` grew larger and
concentrates more responsibility.

---

## ADR-0003 — Provider-agnostic LLM resolution

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: Without an explicit `llm=`, CrewAI falls into the OpenAI default and
fails with `OPENAI_API_KEY is required` even with another provider configured.

**Decision**: `skills/_shared/llm.py` resolves the LLM in this order: agent env
vars → project `.env` → per-provider key detection → default
`gemini/gemini-2.5-flash`. Every skill uses `build_crew_llm()`.

**Consequences**: The skills work with the host agent's LLM (Hermes or Claude)
without code changes. `_shared` must be propagated to the **root** of each
agent's skills, not to the category.

---

## ADR-0004 — Communication between skills via subprocess + files

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: The orchestrator needs to trigger 14 other skills.

**Decision**: Triggering via `subprocess.run` with an argument list (no
`shell=True`), passing context by file (`_ctx_<phase>.txt`) and receiving
artifacts in `outputs/pipeline_<timestamp>/`.

**Consequences**: Each skill remains self-contained and independently
installable, and a skill that hangs does not bring down the orchestrator (600s
timeout per phase). In exchange, the CLI contract becomes implicit coupling —
hence the `invoke` metadata (and DT-03, which proposes validating it
automatically).

---

## ADR-0005 — Installation by destructive copy

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: Installed copies diverged from the repository when edited at the
destination.

**Decision**: `install.sh` does `rm -rf "$dst"` before copying; `__pycache__/`
and `outputs/` are removed from the destination after the copy.

**Consequences**: The install is always a faithful mirror of the repository and
local edits are discarded by design. Risk: pointing `HERMES_SKILLS_DIR`/
`CLAUDE_SKILLS_DIR` at a directory with its own content erases that content.

---

## ADR-0006 — Mode auto-detection instead of an optional flag

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: Alternative skill modes controlled by an optional flag with
`default=False` were never triggered — the LLM calls the skill via function
calling and decides the parameters itself, without "remembering" the flag.

**Decision**: The correct mode is **detected** from the input content, not
declared by a flag.

**Consequences**: Skills work without extra instruction to the LLM. Requires
explicit, tested detection heuristics — and a clear fallback, to avoid falling
into a generic template without a signal that detection failed.
