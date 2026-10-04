# Skills Catalog

Detailed catalog of the skills in the repository, with usage triggers, agents and
outputs. For the full content, see each skill's `SKILL.md`.

The repository hosts two families:

- **RUP family (`rup-*`) — active**, under `skills/rup/`.
- **Software Factory family (`cp-*`) — deprecated**, under `skills/deprecated/`.

---

## RUP family — active (`skills/rup/`)

Autonomous team of agents implementing the **Rational Unified Process**
(Kruchten, 3rd ed.). The user drives everything through `rup-orchestrator`, which
dispatches the 8 discipline skills. **9 disciplines, 21 agents.**

### rup-orchestrator
**RUP Lifecycle Governance.** Base role: *Project Manager*. Classifies demands
into phases (Inception/Elaboration/Construction/Transition), maintains the SDP,
Business Case and Risk List, produces the **Software Sizing & Effort Estimation**
(Function Points IFPUG/NESMA, Use Case Points UAW/UUCW/UUCP/TCF/EF, COCOMO II /
SLOC-KLOC), emits formal **Work Orders** and dispatches the disciplines. Its
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
not installed. `--help` and `--dry-run` always work without credentials.

Details and provenance: [`skills/rup/README.md`](../skills/rup/README.md).

---

## Software Factory family — deprecated (`skills/deprecated/`)

> ⚠️ **DEPRECATED MODE** — every skill below lives in **`skills/deprecated/`**
> and is no longer installed or orchestrated by default. The catalog is kept for
> historical reference. See `docs/INSTALLATION.md` for the `--deprecated` opt-in.

## Software Factory (CrewAI)

### cp-orchestrator
**Software Factory Manager.** Coordinates all crews in sequence, manages
artifacts between phases and applies quality gates. Includes the native NEXUS pipeline.

- **Trigger**: "run full pipeline", "run software factory", "deliver product"
- **Agents**: Pipeline Orchestrator, Artifact Manager, Decision Maker, Progress Reporter
- **Modes**: full, sprint, micro, security-audit, documentation, bugfix, competitive, full-dev, goal-loop, maintenance
- **Script**: `scripts/run.py`

### cp-requirements
**Requirements Engineering.** Elicits, specifies, validates and prioritizes requirements.

- **Trigger**: "gather requirements", "specify", "create user stories"
- **Agents**: Business Analyst, Specifier, Validator, PO Proxy
- **Output**: Requirements Document, Prioritized Backlog (MoSCoW)

### cp-architecture
**Software Architecture and Design.** Designs architecture, models data, designs APIs.

- **Trigger**: "define architecture", "model data", "design API", "create ADR"
- **Agents**: Software, Data, API, UX Architect, Technical Reviewer
- **Output**: Architecture Document, ADRs, Data Modeling, API Contracts

### cp-implementation
**Software Implementation.** Codes backend/frontend/mobile features with code review.

- **Trigger**: "implement", "code", "develop", "do code review"
- **Agents**: Backend, Frontend, Mobile Dev, Reviewer, Integrator
- **Output**: Source Code, Code Review Report, Integration Report

### cp-testing
**Software Testing.** Runs unit, integration, E2E and performance tests.

- **Trigger**: "test", "create tests", "validate quality", "increase coverage"
- **Agents**: Unit, Integration, E2E, Performance Test Eng., Analyst
- **Output**: Test Report, Evidence, Coverage

### cp-security
**Software Security.** Vulnerability analysis, pentest, compliance.

- **Trigger**: "audit security", "run pentest", "check vulnerabilities", "OWASP"
- **Agents**: Security Analyst, Pentester, Compliance, Fix Engineer
- **Output**: Security Report, Implemented Fixes

### cp-devops
**DevOps and Infrastructure.** CI/CD, infrastructure as code, monitoring, deploy.

- **Trigger**: "deploy", "set up CI/CD", "provision infrastructure"
- **Agents**: CI/CD, Infra, Monitoring, Infra Security Eng.
- **Output**: CI/CD Pipeline, Provisioned Infrastructure, Active Monitoring

### cp-software-spec
**Software Spec & Knowledge Base.** Unifies initialization, reverse engineering
and card refinement (Backlog → ToDo) in a concise RUP model (`.context/`),
generating actionable inputs for code replication by agents.

- **Trigger**: "initialize documentation", "start project", "docs setup",
  "reverse engineer", "inspect codebase", "specify screens", "refine card",
  "backlog to todo", "ready for dev"
- **Modes**: `--init` (scaffold), `--inspect <path>` (reverse engineering),
  `--refine-card <ID>` (Backlog → ToDo executable issue)
- **Structure**: `.context/docs/` (RUP 4 phases), `.context/inbox/`,
  `.context/tracking/`, `.context/kanban/`
- **Script**: `scripts/run.py` (`--init`, `--inspect`, `--refine-card`, `--dir`, `--force`, `--dry-run`)
- **Replaces**: `cp-doc-initializer` and `cp-documentation`

### cp-quality
**Software Quality.** Final audit: metrics, artifacts, continuous improvement.

- **Trigger**: "audit quality", "measure metrics", "ensure quality"
- **Agents**: Auditor, Metrics Analyst, Continuous Improvement, Validator
- **Output**: Quality Report, Quality Certificate

### cp-bug-fix
**Bug Fix (NEXUS-Micro).** Fixes bugs with Developer → QA → Evidence Collector.

- **Trigger**: "fix bug", "fix error", "fix"
- **Agents**: Developer, QA (API Tester), Test Automation Engineer, Evidence Collector
- **Output**: Implemented fix, Automated tests, Evidence
- **Limit**: max. 3 retries

### cp-competitive-analysis
**Competitive Analysis.** Compares products, features, prices, positioning and strategy.

- **Trigger**: "analyze competitors", "competitive analysis", "battle card", "SWOT"
- **Agents**: Market Analyst, Competitors, Pricing/Positioning, Strategist
- **Output**: Competitive Intelligence Report, Battle Cards, SWOT

### cp-goal-loop
**Autonomous Try-and-Correct Loop.** Runs a process until success is reached.

- **Trigger**: "run complete process", "test end to end", "validate flow"
- **Input**: `--goal` (required), `--steps`
- **Output**: Completed process, Attempt log

### cp-maintenance
**Software Maintenance and Evolution.** Diagnoses bugs, refactors code, assesses impact.

- **Trigger**: "fix bug", "refactor", "improve code", "do maintenance"
- **Agents**: Bug Analyst, Fix Developer, Refactoring, Impact Analyst
- **Modes**: bug-fix, refactor, improvement, full

### cp-agile
**Execution Pipeline.** Monitors the backlog (local `.kanban/` or Trello), dispatches
ready tasks to the `cp-orchestrator` and manages the bidirectional feedback loop.

- **Trigger**: "agile", "task pipeline", "kanban", "monitor backlog", "question", "blocker"
- **Components**: CPAgileDaemon (polling), CPAgileFeedbackLoop (questions/blockers/resume), TrelloIntegration, LocalIntegration
- **Events**: TASK_DISPATCHED, QUESTION, BLOCKER, HUMAN_CLARIFICATION_RECEIVED
- **Script**: `scripts/run.py` (`--daemon`, `--question`, `--blocker`, `--resume`, `--init`, `--doc`)
