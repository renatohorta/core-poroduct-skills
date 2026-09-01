# Skills Catalog

Detailed catalog of each skill in the repository, with usage triggers, agents and
outputs. For the full content, see each skill's `SKILL.md`.

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

### cp-documentation
**Software Documentation.** Generates technical, API, user documentation and diagrams.

- **Trigger**: "document", "create documentation", "write README", "generate API docs"
- **Agents**: Technical Writer, User, Diagrammer, Reviewer
- **Output**: README.md, API Documentation, User Manual, Diagrams

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

### cp-doc-initializer
**Documentation Initializer.** Centralizes the project context in `.context/`
as a single source of truth, creates `CLAUDE.md`/`AGENT.md` pointers at the root and
generates the per-discipline documentation structure.

- **Trigger**: "initialize documentation", "start project", "docs setup", "create context structure"
- **Structure**: `.context/docs/` (disciplines), `.context/inbox/` (initiatives, tasks, bugs, tech-debt), `.context/tracking/` (progress, decisions)
- **Script**: `scripts/run.py` (`--dir`, `--dry-run`)
