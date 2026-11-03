# Skills Catalog

Detailed catalog of the skills in the repository, with usage triggers, agents and
outputs. For the full content, see each skill's `SKILL.md`.

The skills live under `skills/rup-*`. The legacy Software Factory family
(`cp-*`) was removed (ADR-0010) and is only in the git history.

---

## RUP family (`skills/rup-*`)

Autonomous team of agents implementing the **Rational Unified Process**
(Kruchten, 3rd ed.). The user drives everything through `rup-orchestrator`, which
dispatches the 8 discipline skills. **9 disciplines, 21 agents.**

### rup-orchestrator
**RUP Lifecycle Governance.** Base role: *Project Manager*. Classifies demands
into phases (Inception/Elaboration/Construction/Transition), maintains the SDP,
Business Case and Risk List, produces the **Software Sizing & Effort Estimation**
(Function Points IFPUG/NESMA, Use Case Points UAW/UUCW/UUCP/TCF/EF, COCOMO II /
SLOC-KLOC), emits formal **Work Orders** and dispatches the disciplines (`--auto` chains
them: each discipline receives the artifacts of the previous ones). The Use Case
Points are computed by a deterministic tool the agent calls, never by the LLM. Its
artifacts: SDP, Risk List, Problem Resolution Plan, Product Acceptance Plan,
Measurement Plan & Database, Sizing & Effort Estimation, Business Case,
Iteration Plan, Iteration/Status Assessment, Work Order.

- **Trigger**: "run RUP", "rational unified process", "plan the iteration", "manage the project", "work orders", "estimate effort", "use case points"
- **CLI**: `--phase`, `--discipline`, `--auto`, `--list`, `--estimate`, `--sizing`, `--sizing-template`, `--json`, `--input`, `--output`, `--dry-run`

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

Each discipline skill shares the same CLI:
`run.py "<briefing>" [--phase P] [--input F] [--output F] [--dry-run]`.

Exit codes: `0` success · `1` usage error · `2` no LLM configured · `3` `crewai`
not installed. `--help` and `--dry-run` always work without credentials (and
`--dry-run` also without crewai).

Details and provenance: [`skills/README.md`](../skills/README.md).
