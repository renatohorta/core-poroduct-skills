---
name: cp-benchmark-to-spec
description: "Benchmark to Technical Specification — transforms a reference product (competitor or benchmark) into complete, replicable technical documentation. Receives inputs (URLs, web research, screenshots), crawls the documentation, extracts the design system from the screens and generates the RUP specification (Inception → Elaboration → Construction → Transition) + project management (epics/stories/tasks) for the development team to rebuild the product. Use when the user says 'replicate product', 'reverse engineering', 'benchmark to spec', 'generate technical documentation of a product', 'crawler + documentation', 'specification to rebuild', 'transform product into spec', or needs to turn a reference product into technical documentation."
---

# cp-benchmark-to-spec — Benchmark to Technical Specification

Transforms a **reference product** (competitor, benchmark, or a product you want to
replicate) into **complete, replicable technical documentation**, ready for the
development team to rebuild the product. The process combines **documentation crawler**,
**design system analysis from screenshots** and **RUP specification generation**.

## Pipeline

```
[Inputs] ──► [Crawler] ──► [Design System] ──► [RUP Spec] ──► [Project Management]
   │             │               │                 │                │
  URLs,        docs in        screenshots      4 RUP phases      epics/stories/
  research,    text/md       → UI tokens       (Inception →     tasks/roadmap
  screenshots  (llms.txt)     (colors, fonts,   Transition)
                              spacing)
```

## Agents

| Agent | Function |
|-------|----------|
| **Documentation Analyst** | Crawls the reference product's documentation and extracts the source content |
| **Design Analyst** | Analyzes screenshots and extracts the design system (colors, typography, components) |
| **Technical Specifier** | Generates the complete RUP specification (4 phases) from the source content |
| **Project Manager** | Generates epics, stories, tasks and roadmap referencing the spec |

## Input

Inputs about the reference product. Can be:
- **Documentation URLs** (e.g. `https://product.com/help/reference`).
- **Web research** (a request to research the product on the internet).
- **Screenshots** (a folder with screen images).
- **Context file** (`--input context.txt`).

## Output

Complete technical documentation in `doc_dev/` (or the indicated folder), organized by RUP phases:

### Phase 1 — Inception (`01-inception/`)
- `00-product-vision.md` — vision, problem, solution, target audience, differentiators
- `01-actors.md` — actors and roles
- `02-general-requirements.md` — functional and non-functional requirements
- `03-glossary.md` — domain terminology

### Phase 2 — Elaboration (`02-elaboration/`)
- `04-system-architecture.md` — architecture (backend/frontend/database)
- `use-cases/` — detailed use cases per domain

### Phase 3 — Construction (`03-construction/`)
- `schema/` — PostgreSQL data model + migrations
- `specification/` — technical detail per module
- `api/` — REST + WebSocket specification
- `frontend/` — React components, pages, types

### Phase 4 — Transition (`04-transition/`)
- `05-test-plan.md` — tests per level
- `06-deploy-and-infra.md` — deploy, CI/CD, infrastructure
- `07-training.md` — training

### Project Management (`05-project-management/`)
- `01-epics.md` — epics per domain
- `02-stories.md` — stories with acceptance criteria
- `03-tasks.md` — tasks with technical references
- `04-roadmap.md` — delivery phases and milestones

### Design System (root)
- `design-system.md` — UI/UX specification (colors, typography, components)

## Quality Gate

The Technical Specifier issues a PASS/FAIL verdict on the spec's completeness. If FAIL,
the spec needs corrections before being considered complete. Criteria:
- All 4 RUP phases present.
- Use cases covering the main domains.
- Design system extracted from the screens.
- Project management (epics/stories/tasks) referencing the spec.

## Usage

```bash
# Direct inputs (URLs + request)
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py "product: Attio; URL: https://attio.com/help/reference; generate the complete spec"

# File context
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py --input context.txt

# Save output to a specific folder
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py "product X" --output ./spec

# Only see the crew structure
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py \
  "I want to replicate the Fibery product. \
   Documentation URL: https://the.fibery.io/@public/User_Guide/Start-6568 \
   Screenshots in: design/ \
   Generate the complete technical specification for my team to rebuild."
```

## Manual path (alternative to the script)

When the target is a specific product and the agent has browser/tools access, the
manual path usually yields better results than the crew — the agent runs the crawler and
the generation directly. Validated flow (used for Attio and Fibery):

1. **Documentation crawler** — access the reference URL. If the product offers an
   `llms.txt`/`llms-full.txt` file (e.g. `https://product.com/llms-full.txt`), download it
   via `curl` — it is much more efficient than scraping page by page. Otherwise, use
   `browser_navigate` + `browser_console` with `document.body.innerText` to extract the text.
2. **Map the structure** — list the main sections of the source content to understand the
   product scope (features, modules, integrations).
3. **Analyze screenshots** — use `vision_analyze` on representative screens to extract the
   design system (hex colors, fonts, spacing, components). **Avoid loops**: analyze
   a few key screens and consolidate, not image by image.
4. **Generate the RUP spec** — create the 4-phase documents in `doc_dev/`, referencing the
   source content. **Do not duplicate** content — each document references the others.
5. **Generate the design system** — `design-system.md` with UI tokens.
6. **Generate the project management** — epics/stories/tasks/roadmap in `05-project-management/`.
7. **Review against the screens** — cross-check the spec with the screenshots to identify gaps
   (features that were left out) and advanced questions.

## Pitfalls

| Pitfall | Solution |
|---------|----------|
| Analyzing screenshot by screenshot enters a loop | Analyze a few key screens and consolidate; use `llms.txt` for the textual content |
| `llms-full.txt` is large (1.6MB+) | Download via `curl` and read key sections, not the whole file |
| Screenshots mix the marketing landing page with the app | Focus on the real app screens (workspace), not the marketing ones |
| Generating docs in the wrong directory | Confirm the output path before writing |
| Duplicating content between docs | Each document references the others, does not rewrite |

## Script

The `scripts/run.py` script is self-contained — all agents are embedded in the Python
code itself. It does not depend on an external directory.

## References

- `cp-skill-craft` — pattern for creating cp-* skills in this repository.
- `cp-competitive-analysis` — complementary skill (competitive analysis, competitor comparison).
