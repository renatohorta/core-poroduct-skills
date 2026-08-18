# Componentização de Crews/Skills — Camadas 2/3/4 (Crewbotics)

Padrão de arquitetura usado para migrar crews de JSON hardcoded para **código
Python em camadas reutilizáveis**, com skills do Copilot conectadas às crews como
motor interno (marketplace público removido). Descoberto 2026-08-08.

## Visão das camadas

- **Camada 1 — Skill**: o que o usuário invoca (atômica = executa direto; composta = dispara uma Crew).
- **Camada 2 — Crew**: definição declarativa em Python (`crews/crew_templates/*.py`), composição de agentes+tasks.
- **Camada 3 — Agente**: reutilizável, 1x em `crews/components/agents.py` (role/goal/backstory/icon/tools por slug).
- **Camada 4 — Task**: reutilizável, 1x em `crews/components/tasks.py` (description, quality_gate, is_output, handoff, context).
- **Camada 5 — CrewInstance**: crew do usuário, copia o template e customiza.

## Estrutura de arquivos

```
crews/components/agents.py          # 20 agentes reutilizáveis
crews/components/tasks.py           # tasks reutilizáveis + QUALITY_GATE_BLOCK
crews/components/registry.py
crews/crew_templates/base.py        # materialize_crew() → monta CrewTemplate
crews/crew_templates/*.py           # 1 arquivo por crew (ou cp_fabrica.py com 46)
crews/management/commands/seed_component_crews.py
```

`manage.py seed_component_crews [--slug X]` materializa a partir do Python
(substitui `agency_crew_templates.json` como fonte da verdade). O JSON fica só para
testes legados de seed.

## materialize_crew() — dois modos de task

O builder aceita **dois tipos de definição** por task:

1. **Composição de componente**: `{"key": "...", "task_slug": "research_market"}` —
   busca em `get_task(task_slug)`, mapeia `context` de slugs globais → keys locais.
2. **Inline completa**: `{"key": "...", "agent": "...", "description": "...", "context": [...]}` —
   sem `task_slug`; usa os campos direto.

O mapeamento `task_slug_to_local_key` e `agent_slug_to_local_key` resolve as keys
locais da crew. Tasks inline não entram no mapa de slugs.

## Pitfalls (cada um custou iteração)

1. **`json.dumps` NÃO gera literais Python** — produz `false`/`true` (JSON), que
   viram `NameError: name 'false' is not defined` ao importar o `.py` gerado.
   Use **`pprint.pformat(d, width=100, sort_dicts=False)`** ao gerar arquivos Python
   programaticamente.
2. **`agent` de task deve ser o member_key LOCAL, não o slug global do componente.**
   Se uma task usa um quality gate genérico (`quality_gate_geral` → `reality-checker`)
   mas a crew espera outro agente, declare `"agent": "<member_key>"` explicitamente
   na task, senão o runner cria task com agent inexistente.
3. **Remoção do marketplace quebra `CpCrewSkill`.** Ele buscava
   `CrewTemplate.objects.filter(metadata__crew_slug=..., is_public=True)` — com as
   crews internas (`is_public=False`) retornava erro. Remover o filtro `is_public`
   (buscar só pelo slug). O teste `test_template_slugs_match_crew_templates`
   também filtrava por `is_public=True`; atualizar para `all()` + materializar crews
   na `setUpTestData`.
4. **Divergência de nomenclatura de BotTemplate**: crews do catálogo INI-65 usam
   `member_slug` com prefixo `agency-`; os `BotTemplate.metadata.source_slug` no DB
   NÃO têm o prefixo. Normalizar com `resolve_agent_slug()` (strip `agency-`). Muitos
   agentes especializados não têm BotTemplate vinculado — a crew roda mesmo assim
   (usa definição inline de role/goal/backstory), só não herda metadados extras.
5. **Crews geradas programaticamente com agentes inline** (ex: 46 crews `cp_*` com
   189 agentes) — o `materialize_crew` precisa aceitar agentes com definição inline
   completa OU referência a componente via `agent_slug`; usar
   `comp = get_agent(agent_slug) or {}` como fallback.
6. **Teste de componentes assumia que toda task tem `task_slug`** — quebrar com crews
   inline. Tornar tolerante: `if "task_slug" in task_item`.

## Fluxo validado de ponta a ponta

```
skill.execute(briefing) 
  → busca CrewTemplate por template_slug (sem is_public)
  → cria CrewInstance (copia membros+tasks, input_schema)
  → dispatch_run → {status: "dispatched", run_id}
```

Testar com mock de `dispatch_run` num shell (PYTHONPATH limpo p/ o venv do projeto)
e verificar que a CrewInstance foi criada com members/tasks copiados.
