---
name: cp-implementation
description: "Software Implementation — creates a CrewAI crew with Backend, Frontend, Mobile Dev, Reviewer and Integrator to code features, review code and integrate components. Use when the user says 'implement', 'code', 'develop', 'do code review', 'integrate front and back'."
---

# cp-implementation — Software Implementation

Creates a self-contained CrewAI crew with 5 specialized agents to implement, review and integrate software code.

## Agents

| Agent | Role |
|--------|--------|
| **Backend Developer** | Implements APIs, business logic, models, migrations, REST/GraphQL endpoints |
| **Frontend Developer** | Implements UI, React/Vue/Angular components, states, API integration, accessibility |
| **Mobile Developer** | Implements mobile version (React Native / Flutter), screens, navigation, API integration |
| **Code Reviewer** | Code review: checks patterns, best practices, security, performance, cohesion |
| **Integrator** | Ensures front+back+mobile work together, integration tests, contract validation |

## Pipeline

```
[Backend Dev] ──► [Frontend Dev] ──► [Mobile Dev*] ──► [Reviewer] ──► [Integrator]
      │                │                    │               │               │
      │  APIs,         │  UI,               │  screens,     │  code         │  integration
      │  models,       │  components,       │  navigation   │  review       │  + validation
      │  migrations    │  states            │               │               │
      └────────────────┴────────────────────┴───────────────┴───────────────┴──► PASS/FAIL
```

*Mobile Dev is optional — run only when `--type mobile` or `--type full`.

## Input

- **Technical specification** — description of what to implement (features, endpoints, components)
- **API contracts** (optional) — definition of the interfaces between frontend and backend
- Can be direct text or a file via `--input`

## Output

- Implemented code (backend, frontend and/or mobile)
- Code review report with problems found and suggestions
- Integration report with PASS/FAIL verdict

## Quality Gate

The Integrator issues the final PASS/FAIL verdict. If FAIL, it lists the integration problems that need to be resolved.

## Usage

```bash
# Complete implementation (backend + frontend)
python .hermes/skills/cp-implementation/scripts/run.py "implement user CRUD with JWT authentication"

# Backend only
python .hermes/skills/cp-implementation/scripts/run.py "create reports endpoint" --type backend

# Frontend only
python .hermes/skills/cp-implementation/scripts/run.py "login screen with validation" --type frontend

# Full stack + mobile
python .hermes/skills/cp-implementation/scripts/run.py "scheduling system" --type full

# With file specification
python .hermes/skills/cp-implementation/scripts/run.py --input specification.md

# Save output to a specific directory
python .hermes/skills/cp-implementation/scripts/run.py "products CRUD" --output ./implementation

# Just view the crew structure
python .hermes/skills/cp-implementation/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-implementation/scripts/run.py \
  "implement authentication module: registration (email+password), JWT login, \
   password recovery, authentication middleware. Frontend: login screen, \
   registration, protected dashboard. Contract: /api/auth/register POST, \
   /api/auth/login POST, /api/auth/forgot-password POST" \
  --type full --output ./auth-module
```

## Script

The `scripts/run.py` script is self-contained — all 5 agents are embedded in the Python code itself. It does not depend on an external agent directory.

## Reference Files

- `references/django-windows-hermes-pitfalls.md` — Hermes venv contamination fix, git SSH on Windows, force-push to overwrite bot commits, TanStack Router routeTree.gen.ts exclusion
- `references/aws-ses-smtp-setup.md` — AWS SES SMTP setup for Django transactional email (password reset, invites), domain verification, IAM user creation, HTML email templates
