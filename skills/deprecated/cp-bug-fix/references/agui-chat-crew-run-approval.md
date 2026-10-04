# Approve/Reject on the crew card — button stuck "processing"

## Symptom
User clicks "Aprovar entrega" (or "Rejeitar") on the crew result card in chat. The button stays with a spinner (`animate-spin`), `disabled=true`, and **never** returns to normal. No response/ack appears. The crew message completed (DONE) but the decision is not confirmed.

## Root cause
The frontend (in `CrewRunCard.tsx`, `decide` function) does `POST /api/v1/chat/agui/resume/` and calls `await res.text()`, which waits for the **SSE stream to close**. The backend (`chat/agui/views.py` → `_apply_decision`) calls `enqueue_task_sync("on_crew_run_approved_callback", ...)`.

If that callback runs **inline** (via `asyncio.run` in the `except RuntimeError` of `config/task_proxy.py`), it executes long operations (Composio integrations, page creation) INSIDE the request. The endpoint never returns headers → `res.text()` hangs → "processing" button forever.

## Diagnosis
1. Reproduce in the browser: click approve, verify that the button stays `disabled` + spinner (`document.querySelector(...).disabled`, `innerHTML` with `lucide-loader-circle animate-spin`).
2. Test the endpoint directly:
```python
import urllib.request, json
# login → access token
req = urllib.request.Request(
    f"http://localhost:8000/api/v1/chat/agui/resume/",
    data=json.dumps({"crewRunId": run_id, "decision": "approve"}).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {access}"})
resp = urllib.request.urlopen(req, timeout=15)   # TimeoutError ⇒ inline blocking
```
- `TimeoutError` → callback running inline (bug).
- `200` in ~2s with stream `RUN_STARTED → crew.decision → RUN_FINISHED` → correct.

## Fix (2 parts)

### 1. `config/task_proxy.py` — approval callbacks in a separate thread
In the `except RuntimeError`, the set of long tasks must NOT contain only `run_crew`. Include:
```python
_LONG_TASKS = {
    "run_crew",
    "on_crew_run_approved_callback",
    "on_crew_run_rejected_callback",
}
if name in _LONG_TASKS:
    # runs in a daemon thread with asyncio.run(); returns immediately
```

### 2. `crews/callbacks_async.py` — isolate synchronous ORM (SynchronousOnlyOperation)
When moving the callback to a thread, latent errors masked by the inline appear:
- `_create_page_from_run` called `_final_task_output(run)`, `run.crew.custom_name`, `run.created_at` (synchronous ORM) in an async context → `SynchronousOnlyOperation`.
- Fix: synchronous helper `_read_final_meta(run, _final_task_output)` returning `(final_link, crew_name, created_at, org_id)`, called via `sync_to_async`. Use `organization_id`/`uuid`, never `run.organization`/`pk`.
- `PageViewSet.publish(request, pk=...)` → the `PageViewSet` has `lookup_field="uuid"`. Use `publish(request, uuid=str(page.uuid))`, otherwise `publish() got an unexpected keyword argument 'pk'`.

## Verification
- Regression test `tests/chat/test_resume_nonblocking.py`: calls `enqueue_task_sync("on_crew_run_approved_callback", fake_callback, ...)` in a synchronous test (no event loop) and asserts that (a) it returns < 3s (does not block) and (b) the callback runs in a different thread (`threading.get_ident()`).
- `pytest tests/chat/test_resume_nonblocking.py tests/chat/test_agui_resume_done.py --create-db`.
- E2E loop in the browser: click approve → button returns to normal, ack appears.

## Restart Daphne
Edited modules are imported at ASGI boot (no auto-reload). Kill the PID on port 8000 and relaunch. When starting via subprocess/execute_code, set `PYTHONPATH` ONLY to `.venv\Lib\site-packages` (otherwise cffi/lxml/_overlapped conflict with the Hermes venv) and use `python.exe -m daphne` (not `daphne.exe`). Test `python -c "import asyncio, daphne"` first.
