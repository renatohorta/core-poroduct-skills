# Crewbotics — Skills x Crews: Real Architecture (2026-08-08)

Architecture view discovered while investigating "can I delete the crew templates
from the marketplace if the skills do the same thing?". Answer: **they are not the same
thing, and deleting breaks Copilot**. Keep this in mind before any skills/crews
refactor in the project.

## Two distinct mechanisms

1. **Skills** — conversation capabilities that the LLM calls via function calling.
   - Registered 100% in CODE via `@register_skill` (decorator). **There is no model
     in the database for a skill** — it is not editable via admin (by design).
   - Atomic (execute directly): `web_search`, `analyze_image`, `create_presentation`,
     `canvas_design`, `generate_image`, `execute_crew`, `list_crews`, etc.
   - Composite (`CpCrewSkill`): fire a crew. They look up `CrewTemplate` by
     `template_slug`, create a `CrewInstance` (copies members/tasks) and call
     `dispatch_run`.

2. **Crews / CrewTemplate** — the multi-agent engine.
   - `CrewTemplate` is the catalog (marketplace), with `CrewTemplateMember` (agents,
     tools per agent) + `CrewTemplateTask` (tasks, quality_gate, handoff,
     is_output, tools per task). It has admin (`crews/admin.py`) with inlines.
   - `CrewInstance` = crew hired/customized by the user, copies members/tasks
     from the template. Fireable via `dispatch_run` and via the `execute_crew` skill.

## Critical point: the composite skill DEPENDS on the CrewTemplate

`CpCrewSkill.execute()` does:
```python
template = CrewTemplate.objects.filter(
    metadata__crew_slug=self.template_slug, is_public=True).first()
if not template:
    return {"error": f"Template '{self.template_slug}' não encontrado no marketplace."}
```
Each of the 46 `cp_*` skills (Software Factory) has `template_slug = "cp_*"`.
**On 2026-08-08 there were 0 `cp_*` templates in the database** (only the 6 `agency-*`) → all
46 `cp_*` skills returned "Template não encontrado" (broken).

Implication: **hiding/deleting the marketplace does NOT make the skills "take over"** — the
`cp_*` skills look for `cp_*` slugs, not `agency-*`. For the Copilot skills
to work you must POPULATE the `cp_*` templates (internal, `is_public=False`).

## Data state (08/08)

- Agency templates in the database (6, all is_public=True): agency-campanha-marketing-
  multicanal, agency-carousel-creator-instagram (created in the session), agency-feature-
  enterprise, agency-lancamento-produto-digital, agency-presenca-digital-profissional,
  agency-resposta-crise.
- `crews/seed_data/crew_templates.json` is EMPTY (`{"crews": []}`). The `cp_*` were NEVER
  seeded.
- `crews/seed_data/agency_crew_templates.json` has the 6 agency ones.

## Current seed is DESTRUCTIVE

`upsert_agency_crews` and `upsert_crews` do `obj.members.all().delete()` +
`obj.tasks.all().delete()` and recreate. **Any admin edit is lost on the next
seed.** If the user asks to "edit a template via admin", the seed must be made
non-destructive (only populate the 1st time or via a flag) — not yet done (the session ended
before that).

## Target componentization (user's direction)

The user wants "maximum componentization, keeping it in code, without editing everything via
the database". Layer view:
- SKILL (self-contained process) → atomic skill | composite skill (→ crew)
- CREW (engine) → reusable agents (Python, not JSON) + reusable tasks
- Replace `agency_crew_templates.json` with Python definitions of agents/tasks/
  composite crews (each agent defined 1x and referenced by N crews).
- There is already partial reuse: `agency-reality-checker` appears in 5 crews, `agency-content-
  creator` in 4, etc. (20 distinct agents used in 35 instances).

## Useful tools/execution in this area

- Run Django queries with the project venv and a **clean PYTHONPATH** (only
  `.venv\Lib\site-packages`), otherwise the Hermes sandbox injects its PIL/venv and gives
  `ImportError: cannot import name '_imaging'`. Use:
  `env = dict(os.environ); env["PYTHONPATH"] = <project site-packages>`
- Inspect the skill catalog without instantiating with a user: `from chat.skills.registry import _registry` and iterate `sorted(_registry.keys())`.
