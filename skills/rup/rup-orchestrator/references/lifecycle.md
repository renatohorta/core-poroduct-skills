# RUP lifecycle — phases, milestones and artifacts

The five RUP information sets grow across the four phases:

| Information set | Contents |
|-----------------|----------|
| Management | SDP, Business Case, Risk List, Iteration Plan, Assessments |
| Requirements | Vision, Stakeholder Requests, Use-Case Model, SRS, Glossary |
| Design | SAD (4+1), Design Model, Data Model, Prototypes |
| Implementation | Code, Implementation Subsystems, Builds, Integration Plan |
| Deployment | Deployment Plan, Installation Material, User Manual, Releases |

## Phases and milestones

| Phase | Objective | Milestone |
|-------|-----------|-----------|
| Inception | Feasibility, scope, stakeholder alignment | Lifecycle Objective (LCO) |
| Elaboration | Stabilize architecture, mitigate risk, detail requirements | Lifecycle Architecture (LCA) |
| Construction | Build/integrate/test remaining components to beta | Initial Operational Capability (IOC) |
| Transition | Put software in users' hands, train, migrate, accept | Product Release (PR) |

## Artifacts by discipline

| Discipline | Agents | Key artifacts |
|------------|--------|---------------|
| Environment | `process-engineer` | Development Case, Project-Specific Guidelines, Templates |
| Business Modeling | `business-process-analyst`, `business-designer` | Business Vision Document, Business Goals, Target-Organization Assessment, Business Use-Case Model, Business Actors, Business Glossary, Business Analysis Model, Business Use-Case Realizations, Business Workers, Business Entities, Business Systems, Business Events, Business Rules, Supplementary Business Specifications, Business Architecture Document |
| Requirements | `system-analyst`, `requirements-specifier` | Stakeholder Requests, Vision Document, Use-Case Model Survey, System Actors, Glossary, Requirements Management Plan, Use Cases, Use-Case Packages, Supplementary Specifications (FURPS), Software Requirements Specification (SRS), Requirements Attributes |
| Analysis & Design | `software-architect`, `designer`, `user-interface-designer`, `database-designer`, `capsule-designer` | Software Architecture Document (SAD) — 4+1 Views, Architectural Prototype / Proof-of-Concept, Design Guidelines, Design Model, Use-Case Realizations, Design Classes, Design Subsystems & Design Packages, Interfaces, Analysis Model, Storyboards, Navigation Map, User-Interface Prototype, Data Model, Object-Relational Mapping, Capsules, Protocols, Events & Signals |
| Implementation | `system-integrator`, `implementer` | Integration Build Plan, Build, Implementation Elements, Implementation Subsystems, Developer Tests, Test Stubs & Testability Elements |
| Test | `test-manager`, `test-analyst`, `test-designer`, `tester` | Test Plan, Test Evaluation Summary, Test Ideas List, Test Cases, Test Data, Workload Analysis Model, Test Strategy, Test Automation Architecture, Test Environment Configuration, Test Interface Specification, Test Scripts, Test Suites, Test Log, Test Results |
| Configuration & Change Management | `configuration-manager`, `change-control-manager` | Configuration Management Plan, Baselines, Change Request (CR) |
| Deployment | `deployment-manager`, `technical-writer` | Deployment Plan, Installation Material, Release Description / Release Notes, User Manual / User Documentation, Training Material |

## User <-> Orchestrator protocol

1. The user dialogues **only** with `rup-orchestrator`.
2. The orchestrator classifies the phase, updates SDP/Business Case/Risk List,
   builds the Iteration Plan and emits formal **Work Orders**.
3. Each Work Order dispatches the responsible discipline skill (subprocess).
4. The orchestrator validates the control milestone (LCO/LCA/IOC/PR), consolidates
   the Iteration/Status Assessment, updates the Measurement Database and closes
   the iteration.

