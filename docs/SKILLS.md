# Skills Catalog

Detailed catalog of the skills in the repository, with usage triggers, agents and
outputs. For the full content, see each skill's `SKILL.md`.

The skills live under `skills/rup-*`. The legacy Software Factory family
(`cp-*`) was removed (ADR-0010) and is only in the git history.

---

## RUP family (`skills/rup-*`)

Autonomous team of agents implementing the **Rational Unified Process**
(Kruchten, 3rd ed.). The user drives everything through `rup-orchestrator`, which
dispatches the 8 discipline skills. **9 disciplines, 21 agents.** The 6
execution skills are described at the end.

### rup-orchestrator
**RUP Lifecycle Governance.** Base role: *Project Manager*. Classifies demands
into phases (Inception/Elaboration/Construction/Transition), maintains the SDP,
Business Case and Risk List, produces the **Software Sizing & Effort Estimation**
(Function Points IFPUG/NESMA, Use Case Points UAW/UUCW/UUCP/TCF/EF, COCOMO II /
SLOC-KLOC), emits formal **Work Orders** and drives the disciplines (`--auto`
prints the iteration protocol; each discipline's packet embeds the artifacts the
earlier ones recorded). Use Case Points are computed by code (`--estimate`),
never by the model. Its
artifacts: SDP, Risk List, Problem Resolution Plan, Product Acceptance Plan,
Measurement Plan & Database, Sizing & Effort Estimation, Business Case,
Iteration Plan, Iteration/Status Assessment, Work Order.

- **Trigger**: "run RUP", "rational unified process", "plan the iteration", "manage the project", "work orders", "estimate effort", "use case points"
- **CLI**: `--phase`, `--input`, `--context-dir`, `--record`, `--discipline`, `--auto`, `--status`, `--list`, `--estimate`, `--sizing`, `--sizing-template`, `--json`

### Disciplines

| Skill | Discipline | Agents | Key artifacts |
|-------|------------|--------|---------------|
| `rup-environment` | Environment | `process-engineer` | Development Case, Guidelines, Templates |
| `rup-business-modeling` | Business Modeling | `business-process-analyst`, `business-designer` | Business Vision, Business Use-Case Model, Business Analysis Model, Business Architecture |
| `rup-requirements` | Requirements | `system-analyst`, `requirements-specifier` | Vision Document, Use-Case Model, SRS (FURPS), Glossary |
| `rup-analysis-design` | Analysis & Design | `software-architect`, `designer`, `user-interface-designer`, `database-designer`, `capsule-designer` | SAD (4+1), Design Model, Data Model, Storyboards/Nav Map, Capsules |
| `rup-implementation` | Implementation | `system-integrator`, `implementer` | Integration Build Plan, Builds, Implementation Elements, Developer Tests |
| `rup-test` | Test | `test-manager`, `test-analyst`, `test-designer`, `tester` | Test Plan, Test Cases, Test Strategy, Test Log/Results, Test Evaluation Summary |
| `rup-ccm` | Configuration & Change Mgmt | `configuration-manager`, `change-control-manager` | Configuration Management Plan, Baselines, Change Requests |
| `rup-deployment` | Deployment | `deployment-manager`, `technical-writer` | Deployment Plan, Installation Material, Release Notes, User Manual, Training Material |

**The agent running the skill is the LLM** (ADR-0012). Each discipline skill
shares the same CLI:

- `run.py "<briefing>" [--input F] [--phase P] [--context-dir D]` → work packet
  (roles, missions, required artifacts, earlier `.context/` artifacts);
- `run.py --record doc.md [--phase P] ["<briefing>"]` → validates every required
  `## <Artifact>` and writes `.context/docs/<NN-phase>/rup-<skill>.md` (mandatory)
  + a row in `.context/tracking/rup-log.md`.

Exit codes: `0` success · `1` usage error / missing artifacts · `4` `.context/`
not writable · `5` `.context/` not authorized (no `.rup-standard` marker; see
`rup-context`). Standard library only.

## Execution skills (`skills/rup-*`, ADR-0013)

Six skills that conduct the work and replace the superpowers plugin. They keep
state in `.context/` (cards, roadmap, generated views) and never run git or the
project's tests. All writing commands need the `.context/.rup-standard` marker
(exit 5 otherwise).

| Skill | Trigger | Main commands |
|-------|---------|---------------|
| `rup-context` | A skill exits 5; project without `.context/` or marker; "set up RUP" | `--status`, `--init --authorized-by "<who>"`, `--import`, `--record-import FILE\|-` |
| `rup-discover` | Before building anything new, idea still fuzzy | `"<idea>"` (packet, phase Inception), `--record FILE\|-` -> `docs/01-inception/rup-discover.md` |
| `rup-backlog` | Add/derive/list cards, move them, plan releases and iterations | `--new {epic,story,task}`, `--show`, `--list`, `--move ID COL --reason`, `--derive`, `--release-new`, `--iteration-new`, `--plan`, `--roadmap` |
| `rup-build` | Implement a `TK-NNN` (or fix a `BUG-NNN`) test-first | `--start ID`, `--finish ID --delivery FILE\|- [--project-root]` |
| `rup-debug` | A bug, regression or unexpected behavior | `--open`, `--diagnose BUG-NNN --doc FILE\|-` |
| `rup-review` | A card sits in `4-review` | `<ID>` (checklist packet), `--record <ID> --doc FILE\|-` |

Cards: `EP`/`ST`/`TK`/`BUG-NNN`, acceptance criteria `ST-NNN/AC-n`. Exit codes:
`0` ok · `1` usage / invalid document / rejected delivery · `4` not writable ·
`5` needs authorization.

Details and provenance: [`skills/README.md`](../skills/README.md).
