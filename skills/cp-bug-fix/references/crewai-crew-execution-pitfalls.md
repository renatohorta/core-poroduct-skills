# CrewAI 1.15.5 — Pitfalls de Execução de Crews (crewbotics-back)

Sintoma clássico: o Copilot acha a crew, chama `execute_crew`, mas a crew "não roda" —
o run fica `QUEUED` para sempre ou quebra com erro silencioso (a task roda numa thread
separada e o erro não propaga para o chat).

## 1. `kickoff()` síncrono QUEBRA com múltiplas tasks

**Erro:** `cannot schedule new futures after shutdown` (do `crewai.flow.runtime`).

**Causa:** o `kickoff()` síncrono do CrewAI 1.15.5 chama `asyncio.run()` internamente
no `agent_executor`. Com 1 task funciona; com múltiplas tasks encadeadas (context),
o flow runtime tenta `asyncio.to_thread` depois que o loop já foi fechado → quebra.

**Correção:** usar SEMPRE `kickoff_async()` (via `run_pipeline_async`), rodando numa
daemon thread com `asyncio.run()`:

```python
# task_proxy.py, except RuntimeError, name == "run_crew":
def _run():
    from crews.tasks_async import run_crew
    asyncio.run(run_crew(*args, **kwargs))   # run_crew usa run_pipeline_async (kickoff_async)
t = threading.Thread(target=_run, daemon=True)
t.start()
```

NÃO criar `run_crew_sync` que usa `run_pipeline` (kickoff síncrono) — quebra com
múltiplas tasks.

## 2. `build_llm_kwargs` — providers nativos precisam model SEM prefixo

**Erro:** `Google Gemini API error: 404 - Not Found`.

**Causa:** para providers nativos do CrewAI (gemini, openai, anthropic...), passar
`model='gemini/gemini-2.5-flash'` + `provider='gemini'` explícito faz o CrewAI usar
`model_string = model` (com prefixo) → o SDK nativo espera `gemini-2.5-flash` → 404.

**Correção:** para providers nativos, passar `model` SEM o prefixo e NÃO passar
`provider` explícito (o CrewAI infere do model string e usa `model_part`). Só usar
`is_litellm=True` + `provider` explícito para providers NÃO-nativos (ex: `ollama_chat`).

```python
_NATIVE_PROVIDERS = {"openai","anthropic","claude","azure","azure_openai",
    "google","gemini","bedrock","aws","openrouter","deepseek","ollama",
    "hosted_vllm","cerebras","dashscope","snowflake"}
use_litellm = crewai_provider not in _NATIVE_PROVIDERS
if use_litellm:
    kwargs = dict(model=effective_model, ..., is_litellm=True)
    if crewai_provider: kwargs["provider"] = crewai_provider
else:
    _model_part = effective_model.split("/",1)[1] if "/" in effective_model else effective_model
    kwargs = dict(model=_model_part, ..., is_litellm=False)  # sem provider explícito
```

## 3. `OutputStatus` enum NÃO tem `DONE`

**Erro:** `type object 'OutputStatus' has no attribute 'DONE'`.

**Causa:** `agents.enums.OutputStatus` só tem `PENDING/APPROVED/REJECTED` (é o campo
`AgentOutput.status`). O `DONE` vive em `ExecutionStatus`.

**Correção:** ao gravar output concluído, setar `link.output.execution_status =
ExecutionStatus.DONE` e NÃO tocar em `link.output.status` (deixa PENDING).

## 4. `sanitize_output(text)` aceita 1 argumento

**Erro:** `sanitize_output() takes 1 positional argument but 2 were given`.

**Correção:** `sanitize_output(task_result)` — não passar `crew.output_format`.

## 5. Assinaturas corretas de helpers (migração Celery→asyncio)

- `build_tools(crew, allow_ask=True)` — NÃO `(crew, members, tasks, inputs)`.
- `extract_integration_nodes(graph)` — NÃO `(crew, tasks, inputs)`; passar `crew.graph or {}`.

## 6. `enqueue_task_sync` no `except RuntimeError` — tasks longas em thread

Quando não há event loop ASGI (thread pool do `sync_to_async`, WSGI), NUNCA rodar
`run_crew` inline — a crew completa roda dentro do request e o Daphne mata o SSE
(`took too long to shut down and was killed`). Rodar em daemon thread. Tasks rápidas
(`index_document`) podem ficar inline (testes de knowledge dependem de persistir antes
do retorno).

## 7. `execute_crew` NÃO valida inputs obrigatórios do schema

**Sintoma:** a crew roda e termina `DONE`, mas a primeira task devolve algo como
"Olá! Sou Auditar... preciso das seguintes informações: nome de usuário do Instagram,
concorrentes..." — o agente pede os dados que deveriam ter sido passados. As tasks
seguintes reproduzem o erro porque encadeiam o output vazio.

**Causa:** o `execute_crew` disparava `dispatch_run(crew, {"objective": context})`
sem coletar nem validar os campos do `crew.input_schema`. O schema tem campos
`required: true` (ex: `profissao`, `instagram`, `servicos`) que nunca eram preenchidos.

**Correção em `chat/skills/crew_skill.py`:**
1. Adicionar `inputs` (dict) ao `parameters` da skill, com descrição pedindo as chaves do schema.
2. Antes de disparar, iterar o `crew.input_schema` e coletar os `required` faltantes:
```python
schema = crew.input_schema or []
inputs = dict(inputs or {})
missing = [f for f in schema
           if f.get("required") and not str(inputs.get(f.get("key"), "")).strip()]
if missing:
    questions = "\n".join(f"- {f.get('label') or f.get('key')}: {f.get('question','')}" for f in missing)
    return {"error": f"A crew '{crew.custom_name}' precisa de mais informações antes de rodar. Por favor, responda:\n{questions}",
            "missing_inputs": [f.get("key") for f in missing], "crew_name": crew.custom_name}
```
3. Montar `run_inputs = {"objective": context}` + cada campo do schema preenchido.

## 8. `per_agent_context` — o runner espera STRING, não dict

**Sintoma:** mesmo com inputs preenchidos e validados, o agente ainda não recebe os
dados (pede tudo de novo). O `run.inputs` tem os valores, mas o agente não os usa.

**Causa:** o `tasks_async.py` montava `per_agent_context` como **dict de dicts**
(`{member_key: {input_key: value}}`), mas o runner (`crew_runner_async.py`) injeta
`per_agent_context.get(m.member_key, "")` como um **bloco de texto** no backstory do
agente. Um dict vira `"{'profissao': 'X'}"` literal ou é ignorado — o agente não vê
os dados.

**Correção em `crews/tasks_async.py`** (ambos os blocos, async e sync): após montar o
dict por agente, converter para texto legível:
```python
for mk, vals in per_agent_context.items():
    per_agent_context[mk] = "\n".join(f"{k}: {v}" for k, v in vals.items())
```

## 9. Frontend mostra `output.status` (PENDING) em vez de `executionStatus` (DONE)

**Sintoma:** a crew termina `DONE`, mas na UI cada task aparece "PENDING" — o usuário
acha que nada rodou.

**Causa:** `RunOutputDetailCard` (em `crews.$id.index.tsx`) exibia `output.status`
(o status de APROVAÇÃO: PENDING/APPROVED/REJECTED) em vez de `output.executionStatus`
(o status de EXECUÇÃO: QUEUED/RUNNING/DONE/ERROR). O `status` fica PENDING até ser
aprovado; o `executionStatus` reflete se a task rodou de verdade.

**Correção:** derivar o badge/label do `output.executionStatus`:
```tsx
const execStatus = output.executionStatus ?? "QUEUED";
const badge = execStatus === "DONE" ? "tag--paid"
  : execStatus === "ERROR" ? "tag--overdue"
  : execStatus === "RUNNING" ? "tag--active" : "tag--pending";
const statusLabel = execStatus === "DONE" ? "Concluída"
  : execStatus === "ERROR" ? "Erro"
  : execStatus === "RUNNING" ? "Rodando"
  : execStatus === "WAITING_APPROVAL" ? "Aguardando" : "Na fila";
```

## Verificação

Testar o pipeline isolado antes de mexer no fluxo do chat:
```python
# 1 task funciona, 2 tasks funciona, 7 tasks (crew real) ~35-90s
result = await run_pipeline_async(crew=crew, members=..., tasks=..., inputs=...,
    crew_name=..., llm_model=..., temperature=0.7, knowledge_context="", tools=[],
    on_task_done=None, per_agent_context={}, register_pending_action=None,
    integration_sources=[], integration_sinks=[])
```
Se 1 task funciona mas 7 quebra → é o `kickoff()` síncrono (pitfall #1).
