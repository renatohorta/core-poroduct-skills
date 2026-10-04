# Long synchronous skill that "disappears" from chat (tool_call without tool_result)

Bug pattern discovered on 2026-08-08 (LOOP-20260808-carrossel-ia-instagram):
the user asks for an AI image carousel in chat; Copilot fetches news and
generates the carousel, but the assistant's response with the card **never appears** in the
conversation — the history disappears.

## Symptom in the ExecutionLog

A `tool_call` of `create_presentation` (or another long skill) **without** a corresponding
`tool_result`. The `AgentTask` stays with status `running` forever
(`finished_at=None`). The skill's artifacts (presentation, SVGs, images) are
created in the backend, but the assistant's `ChatMessage` with the card **is never
persisted**.

## Root cause

The skill runs **inline in the SSE request** (`_execute_skill` →
`skill_map[tool_name].execute(**args)` in `chat/agui/engine_async.py`). If it
takes longer than the Daphne timeout, Daphne kills the SSE connection ("took too long
to shut down and was killed") **before** the post-execution code runs — the
`_log("tool_result", ...)` and the `_finish()` (which persists the `ChatMessage` and marks
the task `completed`) never execute.

In the carousel case: `presentations/services/orchestrator.py` →
`execute_presentation_pipeline` generates an **image for each slide** via
`_generate_image_file` (synchronous call to Gemini `gemini-2.5-flash-image`).
12 slides ≈ 13 minutes. The `_finish()` in `chat/engine.py:494` (which creates the
`ChatMessage` and sets `task.status="completed"`) never runs.

## How to confirm

1. `ExecutionLog.objects.filter(task_id=<id>)` — see the `tool_call` of
   `create_presentation` without a `tool_result`.
2. `AgentTask.objects.filter(id=<id>)` — status `running`, `finished_at=None`.
3. Check that the artifacts exist (e.g. `Presentation` created, `ProductContext`
   SVGs archived) — proof that the skill ran, only the response persistence failed.

## Fix (implementation that works)

Long skills must NOT run inline in the SSE. They must be dispatched in a **daemon
thread** (same pattern as `run_crew`), persisting the response via `_finish`
when they finish — even if Daphne kills the SSE before.

In `chat/agui/engine_async.py`:

1. **List of long skills** (module constant):
```python
LONG_SKILLS = {"create_presentation", "canvas_design", "generate_image"}
```

2. **In `_run_loop`, before executing the skill inline**, intercept the long ones —
   emit a user-friendly placeholder, dispatch in the background and end the
   turn (persisting the placeholder via `_finish` so the task does not stay stuck in
   `running`):
```python
if call.name in LONG_SKILLS:
    msg = (f"⏳ Estou gerando o conteúdo de **{call.name}**… "
           "isso pode levar alguns minutos. Assim que ficar pronto, "
           "o resultado aparece aqui na conversa (recarregue se necessário).")
    async for frame in self._emit_text(msg):
        yield frame
    self._dispatch_long_skill(skill_map, call.name, call.args)
    await sync_to_async(self._sync._finish)(msg)  # persists the placeholder
    return  # ends the turn; does NOT emit TOOL_CALL_RESULT with the real result
```

3. **`_dispatch_long_skill`** runs the skill in a daemon thread and persists the result
   when it finishes — the `_finish` here runs OUTSIDE the async event loop (in the thread), so
   the synchronous ORM is safe:
```python
def _dispatch_long_skill(self, skill_map, tool_name, args):
    import threading
    def _run():
        try:
            result = skill_map[tool_name].execute(**args)
            if isinstance(result, dict) and "component" in result:
                summary = self._sync._summarize_ui_component(result)
                self._sync._log("response", payload={"ui_component": result})
                self._sync._finish(summary, ui_component=result)
            elif isinstance(result, dict) and result.get("error"):
                self._sync._finish(f"⚠️ Não consegui concluir: {result['error']}")
            else:
                self._sync._finish(str(result))
        except Exception as exc:
            logger.exception("Skill longa %s falhou: %s", tool_name, exc)
            self._sync._finish(f"⚠️ Ocorreu um erro ao gerar: {exc}")
    threading.Thread(target=_run, daemon=True).start()
```

### Why the inline `_finish` breaks in the test

The `_finish()` uses `transaction.atomic()` (synchronous ORM). Calling it INSIDE the async
event loop (e.g. in a mock of `_dispatch_long_skill` that calls `_finish` directly)
raises `SynchronousOnlyOperation`. In the real flow, `_dispatch_long_skill` runs in a
**daemon thread** (outside the loop), so the ORM is safe. When testing, mock
`_dispatch_long_skill` to only record the call — do NOT try to run `_finish`
inline in the test.

Alternative mitigation (does not replace the dispatch): reduce the synchronous work
(e.g. generate images non-blocking/parallel, or do not generate an image per slide
in the request).

## Test pitfall

- Do not rely only on `bun run build`/pytest — the bug only manifests in the real runtime
  (Daphne killing the SSE). Reproduce via browser with the real prompt and check whether the
  assistant's `ChatMessage` was persisted after the generation.
- When writing AG-UI tests for the dispatch: mock `litellm.acompletion` with a turn
  of `_tool_call_chunks("c1", "create_presentation", '{"prompt": "..."}')` and mock
  `_dispatch_long_skill` to record the call. Validate that the SSE does NOT emit
  `TOOL_CALL_RESULT` (skill went to background), emits a placeholder text and
  ends with `RUN_FINISHED`. Confirm that the `AgentTask` became `completed` (the
  placeholder was persisted). E.g. `tests/chat/test_agui_long_skill.py`.
- For NON-long skills (e.g. web_search), validate that `_dispatch_long_skill` is NOT
  called (they stay inline).
