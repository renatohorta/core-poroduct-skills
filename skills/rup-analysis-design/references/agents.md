# rup-analysis-design — agents and artifacts

> RUP discipline: **Analysis & Design** (discipline 4/9).
> Phase focus: Elaboration → Construction.

| Agent | Base RUP role | Artifacts |
|-------|---------------|-----------|
| `software-architect` | Software Architect | Software Architecture Document (SAD) — 4+1 Views, Architectural Prototype / Proof-of-Concept, Design Guidelines |
| `designer` | Designer | Design Model, Use-Case Realizations, Design Classes, Design Subsystems & Design Packages, Interfaces, Analysis Model |
| `user-interface-designer` | User-Interface Designer | Storyboards, Navigation Map, User-Interface Prototype |
| `database-designer` | Database Designer | Data Model, Object-Relational Mapping |
| `capsule-designer` | Capsule Designer | Capsules, Protocols, Events & Signals |

## Missions

### `software-architect`

- **Mission**: Define and maintain the conceptual integrity, robustness and structural feasibility of the system in the large (breadth), synthesizing the architecture.
- **Produces**: Software Architecture Document (SAD) — 4+1 Views, Architectural Prototype / Proof-of-Concept, Design Guidelines

### `designer`

- **Mission**: Transform the behavioral requirements of use cases into detailed class, interface and collaboration structures ready for construction.
- **Produces**: Design Model, Use-Case Realizations, Design Classes, Design Subsystems & Design Packages, Interfaces, Analysis Model

### `user-interface-designer`

- **Mission**: Model the graphical interfaces with exclusive focus on ergonomics, navigation flow and user goals.
- **Produces**: Storyboards, Navigation Map, User-Interface Prototype

### `database-designer`

- **Mission**: Design and optimize the storage schemas, keys, indexes and integrity of the system's persistent data.
- **Produces**: Data Model, Object-Relational Mapping

### `capsule-designer`

- **Mission**: Model the reactive behavior and event-driven concurrent flows for components with rigid timing requirements (real-time / reactive systems).
- **Produces**: Capsules, Protocols, Events & Signals

