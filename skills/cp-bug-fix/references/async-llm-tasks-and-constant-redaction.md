# Async LLM tasks and the constant-redaction trap

## 1. Every new async task that calls the LLM MUST go into the `_LONG_TASKS` set

In `config/task_proxy.py`, the `except RuntimeError` of `enqueue_task_sync` has a
`_LONG_TASKS` set (default: `run_crew`, `on_crew_run_approved_callback`,
`on_crew_run_rejected_callback`). Tasks in this set run in a **daemon thread with
their own event loop** — never inline.

**Symptom of forgetting:** on a WSGI server (`manage.py runserver`, without a running event
loop), the task runs **inline** in the request. The `POST` that queues the task
blocks until the client timeout. Real example (INI-79 Layer 3): the
`POST /api/v1/page-generation/` should return `201 {"status":"pending"}` in
milliseconds, but gave `TimeoutError` in `urllib` because `generate_page` ran
inline (LiteLLM model call).

**Fix:** add the task name to the set:
```python
_LONG_TASKS = {
    "run_crew",
    "on_crew_run_approved_callback",
    "on_crew_run_rejected_callback",
    "generate_page",   # ← new LLM task
}
```

**Golden rule:** a task that makes a model call = `_LONG_TASKS` (thread).
A fast ORM task (`index_document`, `generate_title`) = inline (persists
before the test/request returns; in `TransactionTestCase` the database is cleaned before
a thread finishes).

**Auto-reload:** `manage.py runserver` reloads `task_proxy.py` by itself —
the fix takes effect without restarting the process. (Modules imported at ASGI boot,
like `callbacks_async.py`/`tasks_async.py`, do NOT have auto-reload — those require
restarting.)

## 2. Trap: numeric constants appear as `***` in the tool output

When reading files via `execute_code`/`read_file`, a numeric constant can
appear redacted as `TOKENS_MAX_CHARS=***` (or `=***`). This is a tool
redaction artifact, **NOT a syntax error** — the file is valid.

**How to confirm before "fixing":**
1. `import` the module — if it compiles/imports, there is no bug.
2. Read the raw bytes and decode: `open(p,'rb').read().split(b'\n')[N]` and
   print `list(line)` — the byte ints reveal the real value
   (e.g. `[51,95,53,48,48]` = `3_500`).

Do **NOT** rewrite the line with a guessed value — you would corrupt a file
that was correct. The `***` is just the tool masking the number.

## 3. Asynchronous page generation pattern (INI-79 Layer 3)

When an LLM generation cannot stay in a blocking `POST`:
- `PageGenerationJob` model (status pending/running/done/failed, FK to page).
- `tasks_async.py` with `generate_page_task(job_id)` that reads the job, marks it
  RUNNING, calls the generator, writes the result/error.
- ViewSet with `create` (queues via `enqueue_task_sync`, returns 201 pending)
  + `retrieve` (status for polling) + a catalog action.
- Frontend polls `GET /page-generation/<id>/` every ~2s until done/failed.
- `task_proxy._LONG_TASKS` must include the task name (see section 1).
