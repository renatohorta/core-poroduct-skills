# Crews/Skills Componentization — Layers 2/3/4 (Crewbotics)

Architecture pattern used to migrate crews from hardcoded JSON to **layered, reusable
Python code**, with Copilot skills connected to the crews as the
internal engine (public marketplace removed). Discovered 2026-08-08.

## Layer overview

- **Layer 1 — Skill**: what the user invokes (atomic = executes directly; composite = fires a Crew).
- **Layer 2 — Crew**: declarative definition in Python (`crews/crew_templates/*.py`), composition of agents+tasks.
- **Layer 3 — Agent**: reusable, 1x in `crews/components/agents.py` (role/goal/backstory/icon/tools per slug).
- **Layer 4 — Task**: reusable, 1x in `crews/components/tasks.py` (description, quality_gate, is_output, handoff, context).
- **Layer 5 — CrewInstance**: the user's crew, copies the template and customizes.

## File structure

```
crews/components/agents.py          # 20 reusable agents
crews/components/tasks.py           # reusable tasks + QUALITY_GATE_BLOCK
crews/components/registry.py
crews/crew_templates/base.py        # materialize_crew() → builds CrewTemplate
crews/crew_templates/*.py           # 1 file per crew (or cp_fabrica.py with 46)
crews/management/commands/seed_component_crews.py
```

`manage.py seed_component_crews [--slug X]` materializes from Python
(replaces `agency_crew_templates.json` as the source of truth). The JSON stays only for
legacy seed tests.

## materialize_crew() — two task modes

The builder accepts **two types of definition** per task:

1. **Component composition**: `{"key": "...", "task_slug": "research_market"}` —
   looks up `get_task(task_slug)`, maps `context` from global slugs → local keys.
2. **Full inline**: `{"key": "...", "agent": "...", "description": "...", "context": [...]}` —
   without `task_slug`; uses the fields directly.

The `task_slug_to_local_key` and `agent_slug_to_local_key` mappings resolve the crew's local
keys. Inline tasks do not enter the slug map.

## Pitfalls (each cost an iteration)

1. **`json.dumps` does NOT generate Python literals** — it produces `false`/`true` (JSON), which
   become `NameError: name 'false' is not defined` when importing the generated `.py`.
   Use **`pprint.pformat(d, width=100, sort_dicts=False)`** when generating Python files
   programmatically.
2. **A task's `agent` must be the LOCAL member_key, not the component's global slug.**
   If a task uses a generic quality gate (`quality_gate_geral` → `reality-checker`)
   but the crew expects another agent, declare `"agent": "<member_key>"` explicitly
   in the task, otherwise the runner creates a task with a nonexistent agent.
3. **Removing the marketplace breaks `CpCrewSkill`.** It looked up
   `CrewTemplate.objects.filter(metadata__crew_slug=..., is_public=True)` — with the
   internal crews (`is_public=False`) it returned an error. Remove the `is_public` filter
   (look up only by slug). The `test_template_slugs_match_crew_templates` test
   also filtered by `is_public=True`; update it to `all()` + materialize the crews
   in `setUpTestData`.
4. **BotTemplate naming divergence**: crews from the INI-65 catalog use
   `member_slug` with the `agency-` prefix; the `BotTemplate.metadata.source_slug` in the DB
   do NOT have the prefix. Normalize with `resolve_agent_slug()` (strip `agency-`). Many
   specialized agents have no linked BotTemplate — the crew still runs
   (uses the inline role/goal/backstory definition), it just does not inherit extra metadata.
5. **Programmatically generated crews with inline agents** (e.g. 46 `cp_*` crews with
   189 agents) — `materialize_crew` must accept agents with a full inline
   definition OR a component reference via `agent_slug`; use
   `comp = get_agent(agent_slug) or {}` as a fallback.
6. **The component test assumed every task has `task_slug`** — breaks with inline
   crews. Make it tolerant: `if "task_slug" in task_item`.

## End-to-end validated flow

```
skill.execute(briefing) 
  → looks up CrewTemplate by template_slug (without is_public)
  → creates CrewInstance (copies members+tasks, input_schema)
  → dispatch_run → {status: "dispatched", run_id}
```

Test with a mock of `dispatch_run` in a shell (clean PYTHONPATH for the project venv)
and verify that the CrewInstance was created with the members/tasks copied.
