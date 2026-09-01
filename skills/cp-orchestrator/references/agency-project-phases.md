# Agency Project — Multi-Phase Execution Pattern

> How to decompose a large product plan (like `crewbotics-agency-plan.md`) into
> parallelizable phases, each on its own branch, with tests and clean handoffs.

## Branch Strategy

Each phase gets its own branch, created from `main` at the same base commit.
Branches are independent — they do NOT merge into each other sequentially.

```
main ──┬── phase1-agent-catalog     (BotTemplates, seed, endpoint)
       ├── phase2-playbook-templates (5 runbooks, quality gates, handoffs)
       ├── phase3-integrations      (WhatsApp, Asset Library, IntegrationLayer)
       ├── phase4-agentic-ui        (Copilot skills + React components)
       └── phase5-polish-launch     (landing page, onboarding, tests)
```

**Why independent branches instead of sequential merges?**
- Each phase can be reviewed and merged independently
- No merge conflicts between phases (they touch different files)
- If one phase is delayed, others aren't blocked
- The user can test each phase in isolation

## Phase Template

Each phase follows the same structure:

1. **Switch to branch** — `git checkout -b feat/agency-phaseN-name main`
2. **Implement** — backend models/services + frontend components
3. **Migration** — `makemigrations` + `migrate`
4. **Seed** — if adding seed data, create management command + run it
5. **Test** — create `tests/<app>/test_phaseN.py` with:
   - Model tests (creation, fields, constraints)
   - Service tests (business logic, edge cases)
   - Integration tests (end-to-end flows with mocks)
6. **Build** — `bun run build` (frontend) or `pytest` (backend)
7. **Commit** — `git add -A && git commit -m "feat(agency): Fase N - summary"`
8. **Push** — `git push origin feat/agency-phaseN-name`

## What Each Phase Produces

| Phase | Backend | Frontend | Tests |
|-------|---------|----------|-------|
| 1 — Agent Catalog | BotTemplates, seed, endpoint | — | 8 |
| 2 — Playbooks | 5 runbooks, quality gates, handoff, Dev→QA loop | — | 19 |
| 3 — Integrations | WhatsAppSession, AssetLibraryItem, IntegrationLayer | — | 39 |
| 4 — Agentic UI | 6 Copilot skills (list/suggest/deploy/progress/deliverables) | 9 React components (PlaybookCard, IntegrationStatus, WhatsAppQRCode, AssetUploader, CrewProgress, DeliverableGallery, ProposalPreview, MetricsDashboard) | — |
| 5 — Polish | Landing page, onboarding | Landing page | TBD |

## IntegrationLayer Architecture

The IntegrationLayer (`integrations/integration_layer.py`) unifies multiple
backend providers under a single `execute_action()` interface:

```python
def execute_action(organization, provider_slug, action, params) -> dict:
    # Returns {"status": "ok"|"error", "data": ..., "error": ...}
```

Three backends:
- **Composio** — 30+ OAuth providers (gmail, slack, github, twitter, etc.)
- **WhatsApp** — QR Code sessions via baileys (stub mode for dev)
- **Asset** — file upload, listing, tagging

## Agentic UI Pattern

Copilot skills return `{component, props}` dicts instead of plain text.
The frontend `GenerativeUIRenderer` maps component names to React components
via `UI_REGISTRY`:

```typescript
const UI_REGISTRY: Record<string, React.FC<any>> = {
  PlaybookCard,
  PlaybookList,
  IntegrationStatus,
  WhatsAppQRCode,
  AssetUploader,
  CrewProgress,
  DeliverableGallery,
  ProposalPreview,
  MetricsDashboard,
  // ... existing components
};
```

This allows the Copilot to render rich interactive cards (playbook suggestions,
QR codes, progress bars, galleries) without the frontend knowing about every
possible UI state in advance.

## Pitfalls

- **Seed file corruption via find-and-replace**: When inserting a large block
  (e.g. INPUT_SCHEMAS dict) into a Python file using `content.replace()`, the
  anchor string may match inside a function body instead of at module scope.
  The file compiles but the logic is corrupted. Prevention: use unique anchors
  with surrounding context lines, verify with `compile()`, and inspect 10 lines
  above and below the insertion point. If corrupted, rewrite the entire file.
- **Forgetting category in seed**: The `category` field on `CrewTemplate` is
  easy to miss in seed functions. Always check model fields before writing.
- **Multiple seed files**: Adding a field to a model requires updating ALL seed
  functions (`crew_seed.py`, `agency_crew_seed.py`, etc.). Use `grep -rn "def upsert\|def seed"` to find them all.
- **BotTemplate resolution**: Members reference BotTemplates via
  `member_slug` → `BotTemplate.metadata.source_slug`. If the slug doesn't match,
  the member gets `bot_template=None` and loses the agent's full prompt.
