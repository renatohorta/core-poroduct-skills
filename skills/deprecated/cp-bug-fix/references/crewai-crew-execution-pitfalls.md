# CrewAI 1.15.5 — Crew Execution Pitfalls (crewbotics-back)

Classic symptom: Copilot finds the crew, calls `execute_crew`, but the crew "does not run" —
the run stays `QUEUED` forever or breaks with a silent error (the task runs in a separate
thread and the error does not propagate to the chat).

## 1. Synchronous `kickoff()` BREAKS with multiple tasks

**Error:** `cannot schedule new futures after shutdown` (from `crewai.flow.runtime`).

**Cause:** CrewAI 1.15.5's synchronous `kickoff()` calls `asyncio.run()` internally
in the `agent_executor`. With 1 task it works; with multiple chained tasks (context),
the flow runtime tries `asyncio.to_thread` after the loop has already been closed → breaks.

**Fix:** ALWAYS use `kickoff_async()` (via `run_pipeline_async`), running in a
daemon thread with `asyncio.run()`:

```python
# task_proxy.py, except RuntimeError, name == "run_crew":
def _run():
    from crews.tasks_async import run_crew
    asyncio.run(run_crew(*args, **kwargs))   # run_crew uses run_pipeline_async (kickoff_async)
t = threading.Thread(target=_run, daemon=True)
t.start()
```

Do NOT create `run_crew_sync` that uses `run_pipeline` (synchronous kickoff) — it breaks with
multiple tasks.

## 2. `build_llm_kwargs` — native providers need a model WITHOUT prefix

**Error:** `Google Gemini API error: 404 - Not Found`.

**Cause:** for CrewAI native providers (gemini, openai, anthropic...), passing
`model='gemini/gemini-2.5-flash'` + explicit `provider='gemini'` makes CrewAI use
`model_string = model` (with prefix) → the native SDK expects `gemini-2.5-flash` → 404.

**Fix:** for native providers, pass `model` WITHOUT the prefix and do NOT pass
an explicit `provider` (CrewAI infers it from the model string and uses `model_part`). Only use
`is_litellm=True` + explicit `provider` for NON-native providers (e.g. `ollama_chat`).

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
    kwargs = dict(model=_model_part, ..., is_litellm=False)  # no explicit provider
```

## 3. `OutputStatus` enum does NOT have `DONE`

**Error:** `type object 'OutputStatus' has no attribute 'DONE'`.

**Cause:** `agents.enums.OutputStatus` only has `PENDING/APPROVED/REJECTED` (it is the
`AgentOutput.status` field). The `DONE` lives in `ExecutionStatus`.

**Fix:** when recording a completed output, set `link.output.execution_status =
ExecutionStatus.DONE` and do NOT touch `link.output.status` (leave it PENDING).

## 4. `sanitize_output(text)` accepts 1 argument

**Error:** `sanitize_output() takes 1 positional argument but 2 were given`.

**Fix:** `sanitize_output(task_result)` — do not pass `crew.output_format`.

## 5. Correct helper signatures (Celery→asyncio migration)

- `build_tools(crew, allow_ask=True)` — NOT `(crew, members, tasks, inputs)`.
- `extract_integration_nodes(graph)` — NOT `(crew, tasks, inputs)`; pass `crew.graph or {}`.

## 6. `enqueue_task_sync` in the `except RuntimeError` — long tasks in a thread

When there is no ASGI event loop (thread pool of `sync_to_async`, WSGI), NEVER run
`run_crew` inline — the full crew runs inside the request and Daphne kills the SSE
(`took too long to shut down and was killed`). Run in a daemon thread. Fast tasks
(`index_document`) can stay inline (knowledge tests depend on persisting before
the return).

## 7. `execute_crew` does NOT validate the schema's required inputs

**Symptom:** the crew runs and ends `DONE`, but the first task returns something like
"Olá! Sou Auditar... preciso das seguintes informações: nome de usuário do Instagram,
concorrentes..." — the agent asks for the data that should have been passed. The following
tasks reproduce the error because they chain the empty output.

**Cause:** `execute_crew` fired `dispatch_run(crew, {"objective": context})`
without collecting or validating the `crew.input_schema` fields. The schema has fields
`required: true` (e.g. `profissao`, `instagram`, `servicos`) that were never filled.

**Fix in `chat/skills/crew_skill.py`:**
1. Add `inputs` (dict) to the skill's `parameters`, with a description asking for the schema keys.
2. Before firing, iterate the `crew.input_schema` and collect the missing `required` ones:
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
3. Build `run_inputs = {"objective": context}` + each filled schema field.

## 8. `per_agent_context` — the runner expects STRING, not dict

**Symptom:** even with filled and validated inputs, the agent still does not receive the
data (asks for everything again). The `run.inputs` has the values, but the agent does not use them.

**Cause:** `tasks_async.py` built `per_agent_context` as a **dict of dicts**
(`{member_key: {input_key: value}}`), but the runner (`crew_runner_async.py`) injects
`per_agent_context.get(m.member_key, "")` as a **text block** in the agent's
backstory. A dict becomes a literal `"{'profissao': 'X'}"` or is ignored — the agent does not see
the data.

**Fix in `crews/tasks_async.py`** (both blocks, async and sync): after building the
per-agent dict, convert it to readable text:
```python
for mk, vals in per_agent_context.items():
    per_agent_context[mk] = "\n".join(f"{k}: {v}" for k, v in vals.items())
```

## 9. Frontend shows `output.status` (PENDING) instead of `executionStatus` (DONE)

**Symptom:** the crew ends `DONE`, but in the UI each task appears "PENDING" — the user
thinks nothing ran.

**Cause:** `RunOutputDetailCard` (in `crews.$id.index.tsx`) displayed `output.status`
(the APPROVAL status: PENDING/APPROVED/REJECTED) instead of `output.executionStatus`
(the EXECUTION status: QUEUED/RUNNING/DONE/ERROR). The `status` stays PENDING until it is
approved; the `executionStatus` reflects whether the task actually ran.

**Fix:** derive the badge/label from `output.executionStatus`:
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

## Verification

Test the isolated pipeline before touching the chat flow:
```python
# 1 task works, 2 tasks works, 7 tasks (real crew) ~35-90s
result = await run_pipeline_async(crew=crew, members=..., tasks=..., inputs=...,
    crew_name=..., llm_model=..., temperature=0.7, knowledge_context="", tools=[],
    on_task_done=None, per_agent_context={}, register_pending_action=None,
    integration_sources=[], integration_sinks=[])
```
If 1 task works but 7 breaks → it is the synchronous `kickoff()` (pitfall #1).
