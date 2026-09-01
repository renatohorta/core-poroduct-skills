# Post-Migration Bug Patterns (Celery → Asyncio)

Reproduced in this session (2026-08-04). Use as a checklist when you find `ModuleNotFoundError`, `ImportError` or `SyntaxError` after a migration that deleted/renamed modules.

## 1. Import of a deleted module

**Symptom:** `ModuleNotFoundError: No module named 'agents.tasks'`

**Cause:** The `agents/tasks.py` module was deleted (replaced by `agents/tasks_async.py`), but `agents/views.py` still had `from .tasks import run_agent`.

**Fix:** Remove the obsolete line. The correct import (`from agents.tasks_async import run_agent`) already existed right below.

**Pattern:** Occurred in 4 files:
- `agents/views.py`: `from .tasks import run_agent`
- `knowledge/views.py`: `from .tasks import index_document`
- `integrations/views.py`: `from .tasks import process_webhook_event`
- `crews/services.py`: `from .tasks import run_crew` (2x)

## 2. Import inserted inside a multi-line import

**Symptom:** `SyntaxError: invalid syntax` pointing to the import line.

**Cause:** When inserting `from config.task_proxy import enqueue_task_sync` programmatically, it landed INSIDE the parentheses of:
```python
from .models import (
    CrewInstance,
```
Resulting in:
```python
from .models import (
from config.task_proxy import enqueue_task_sync  # ← SyntaxError
    CrewInstance,
```

**Fix:** Move the imports to before the `from .models import (` block.

**Occurred in:** `crews/services.py`, `integrations/views.py`

## 3. Broken indentation in try/except

**Symptom:** `IndentationError: unindent does not match any outer indentation level`

**Cause:** The replace of `index_document.delay(str(doc.id))` with `enqueue_task_sync(...)` broke the indentation of the surrounding `try` block. The `try:` ended up at one level and `enqueue_task_sync` at another.

**Occurred in:** `knowledge/archiving.py` and `crews/services.py`

## 4. Async function missing in the destination module

**Symptom:** `ImportError: cannot import name 'run_crew' from 'crews.tasks_async'`

**Cause:** The `run_crew` function (full pipeline) existed in the old `crews/tasks.py` but was NEVER ported to `crews/tasks_async.py`. The `crew_runner_async.py` had the low-level engine (`run_pipeline_async`), but the high-level function that `services.py` imported did not exist.

**Fix:** Add the complete `async def run_crew(crew_run_id)` in `crews/tasks_async.py` (141 lines).

## 5. Duplicate side-by-side import

**Symptom:** The old and new imports were inserted side by side:
```python
from .tasks import run_agent       # ← breaks (deleted module)
from agents.tasks_async import run_agent  # ← would work if it got here
```

**Cause:** Python executes the first import — if the module was deleted, it never reaches the second.

## 6. `manage.py` hanging due to Hermes `lxml` conflict

**Symptom:** `ImportError: cannot import name 'etree' from 'lxml'` pointing to Hermes' site-packages, not the project's.

**Cause:** The `sys.path` loads Hermes' site-packages before the project's. Hermes has an incompatible `lxml`.

**Definitive fix in manage.py:**
```python
import sys
project_site = os.path.join(os.path.dirname(__file__), '.venv', 'Lib', 'site-packages')
hermes_site = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'AppData', 'Local', 'hermes', 'hermes-agent', 'venv', 'Lib', 'site-packages',
)
if project_site in sys.path:
    sys.path.remove(project_site)
sys.path.insert(0, project_site)
sys.path = [p for p in sys.path if hermes_site not in p]
```

## 7. `crewai_tools_adapter.py` hanging the boot forever

**Symptom:** `manage.py check` / `migrate` / `runserver` hangs for hours (not seconds). The process stays stuck without an error.

**Cause:** The `chat/skills/crewai_tools_adapter.py` module tries to discover 63 CrewAI tools at `import` time. Several call `input()` in `__init__` asking "Quer instalar a dependência? [y/N]" — even with the `lambda: "N"` that neutralizes `input()`, some tools do network I/O and hang the process **forever**.

**Definitive solution (not just an env var):**
1. Delete `chat/skills/crewai_tools_adapter.py`
2. Delete `chat/skills/crewai_custom/` (entire directory)
3. Remove the import from `chat/skills/__init__.py`
4. Remove the `CrewAIToolsAdapterTests` test class from `tests/chat/test_core.py`

**Copilot does not use these tools.** It uses the native skills registered manually in `chat/skills/`.

## 8. Calling an `async def` in synchronous code without `asyncio.run()`

**Symptom:** `RuntimeWarning: coroutine 'X' was never awaited` + test fails because the function returned a coroutine instead of the result.

**Fix:** Wrap in `asyncio.run()`:
```python
import asyncio
asyncio.run(process_webhook_event(str(evt.id)))
```

## 9. `doc.id` vs `doc.pk` in knowledge tests

**Symptom:** `ProductContext.DoesNotExist` when calling `index_document(str(doc.id))`.

**Cause:** `doc.id` returns the public UUID (`uuid` field of CoreModel), but `index_document` expects the internal PK.

**Fix:** Use `doc.pk` instead of `doc.id`.

## 10. `run_pipeline` is in `crew_runner_async`, not in `tasks_async`

**Symptom:** `AttributeError: module 'crews.tasks_async' has no attribute 'run_pipeline'`

**Fix:** Change the patch path:
```python
# Before:
@patch("crews.tasks_async.run_pipeline")
# After:
@patch("crews.crew_runner_async.run_pipeline_async")
```

## 11. Duplicate `asyncio.run(asyncio.run(...))`

**Symptom:** `ValueError: a coroutine was expected, got 0`

**Fix:** Use only one `asyncio.run()`.

## 12. LLM settings accidentally deleted

**Symptom:** `AttributeError: 'Settings' object has no attribute 'LLM_MODEL'`

**Fix:** Restore the complete LLM settings block. Check the git diff for what was removed.

## 13. Missing compatibility settings

**Symptom:** `AttributeError: 'Settings' object has no attribute 'CELERY_TASK_ALWAYS_EAGER'`

**Fix:** Add as compatibility:
```python
CELERY_TASK_ALWAYS_EAGER = True
CREW_RUN_STALE_AFTER = env_int("CREW_RUN_STALE_AFTER", 300)
```

## 14. `database_sync_to_async` does not exist in the installed asgiref

**Symptom:** `ImportError: cannot import name 'database_sync_to_async'`

**Fix:** Use `sync_to_async` (exists in all versions) combined with `TransactionTestCase`.

## 15. Tests silently disappear due to a syntax error

**Symptom:** The test count drops (e.g. 429 → 369) without a clear warning.

**Fix:** Check the test count BEFORE and AFTER each change. If it dropped, some file did not load.

## 16. `@mock.patch` vs `@patch` — correct import

**Symptom:** `NameError: name 'mock' is not defined`

**Correct:**
```python
from unittest.mock import patch
@patch("path.to.module")
```

## 17. Extra parenthesis from regex replacement

**Symptom:** `SyntaxError: unmatched ')'` pointing to `asyncio.run(...))`.

**Fix:** Always verify the result of block replacements. Use `compile()` to validate syntax.

## 18. Import in the middle of the file (after a decorator)

**Symptom:** `SyntaxError: invalid syntax` on an import line after a decorator.

**Fix:** Imports ALWAYS at the top of the file, before any code.

## 21. Double route when including urls with a path parameter

**Symptom:** 404 when accessing `/serve/<slug>/` even with the route configured.

**Cause:** `path("serve/<slug:slug>/", include("pages.urls"))` captures the slug in the prefix, and `pages/urls.py` also has `<slug:slug>/`. Result: `/serve/<slug>/<slug>/` — slug captured twice.

**Fix:** The prefix must not have the path parameter:
```python
# WRONG:
path("serve/<slug:slug>/", include("pages.urls"))

# RIGHT:
path("serve/", include("pages.urls"))
```

## 22. Missing Vite proxy for a new public route

**Symptom:** 404 when accessing `/serve/<slug>/` through the frontend (:8080), but it works on the backend (:8000).

**Cause:** The Vite dev server only redirects to the backend the routes listed in `server.proxy` in `vite.config.ts`. New routes need to be added.

**Fix:**
```typescript
server: {
  proxy: {
    "/serve": {
      target: process.env.VITE_BACKEND_URL || "http://localhost:8000",
      changeOrigin: true,
    },
  },
}
```

## 23. `enqueue_task_sync` without an event loop — task never runs

**Symptom:** Background tasks (generate conversation title, index document) never complete. The server runs with `manage.py runserver` (WSGI), not Daphne (ASGI).

**Cause:** `manage.py runserver` (WSGI) has no running event loop. The `TaskQueue` and the `Scheduler` only start in `LifespanASGI.startup()` of Daphne. Without an event loop, `enqueue_task_sync()` fell into the `except RuntimeError` and called `asyncio.run(enqueue_task(...))`, which created a temporary loop, queued the task in the `TaskQueue`... but the `TaskQueue` **has no workers running** because they only start in the ASGI lifespan.

**Fix:** In `config/task_proxy.py`, when there is no running event loop, execute the task **inline** instead of queuing:
```python
except RuntimeError:
    # No loop running (WSGI) — executes inline
    try:
        result = coro_factory(*args, **kwargs)
        if hasattr(result, '__await__'):
            return asyncio.run(result)
        return result
    except Exception as exc:
        logger.error("Task '%s' falhou inline: %s", name, exc)
        return str(uuid.uuid4())
```

**How to detect:** Check the `Server:` header in the HTTP response. If it is `WSGIServer` (Django runserver) or `Cheroot` (waitress), it is WSGI. If it is `daphne` or `uvicorn`, it is ASGI.

## 25. DRF pagination breaks a frontend that expected a flat array

**Symptom:** The activities dashboard showed "Nenhuma atividade no período" even with data in the database. The `useQuery` received `{ count, results }` but the component expected an array.

**Cause:** Adding `pagination_class` to a DRF ViewSet that previously returned `T[]` changes the response to `{ count, next, previous, results: T[] }`. The frontend that consumed `data` as an array now receives an object.

**Fix in 3 layers:**

1. **Backend:** Add `pagination_class` to the ViewSet:
```python
from rest_framework.pagination import PageNumberPagination

class MyPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100

class MyViewSet(...):
    pagination_class = MyPagination
```

2. **API endpoint type:** Update the return type in `endpoints.ts`:
```typescript
// Before:
api.get<T[]>("/path/")
// After:
api.get<PaginatedResponse<T>>("/path/")
```

3. **Query hook:** Add `page` and `page_size` to the params, and extract `results`:
```typescript
// In the hook:
useAuthedQuery({
  queryKey: ["key", params],
  queryFn: () => api.list(params),  // returns PaginatedResponse
  select: (data) => data.results,   // extracts the array
})
```

4. **Component:** Add page state + Previous/Next buttons:
```typescript
const [page, setPage] = useState(1);
const { data: pageData } = useQuery(params);
const logs = pageData?.results ?? [];
const totalPages = Math.ceil((pageData?.count ?? 0) / pageSize);
// Render: "{page} de {totalPages}" + Previous/Next
```

**Occurred in:** `dashboard.tsx` (ActivityFeed) + `activity/views.py` (ActivityLogViewSet)

## 26. Frontend/Backend page_size out of sync

**Symptom:** The backend returns 10 items per page but the frontend shows "1 de 2" calculated based on 30 items per page. The pagination shows wrong numbers.

**Cause:** `page_size` was changed in the backend (`ActivityLogPagination.page_size = 10`) but the frontend still had `page_size: 30` hardcoded in 3 places:
1. API call parameter: `page_size: 30`
2. totalPages calculation: `Math.ceil(totalCount / 30)`
3. Redundant slice: `logs?.slice(0, 30)` (unnecessary with pagination)

**Fix:** Whenever you change `page_size` in the backend, search the frontend for ALL occurrences of the old value:
```bash
grep -rn "page_size: 30\|/ 30\|slice(0, 30)" src/
```

**Pattern:** The frontend hardcodes the page_size instead of deriving it from the backend. Consider extracting it to a shared constant or using the backend value via API.

## 27. Pagination layout overlapping content below

**Symptom:** The "Anterior 1 de 2 Próxima" buttons appear overlapping the content below the activities card.

**Cause:** The pagination container has neither `clear: both` nor `position: relative`, allowing floating or absolutely-positioned elements from the content above to interfere.

**Fix:**
```tsx
<div style={{
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 12,
  padding: "16px 0 8px",
  marginTop: 8,
  borderTop: "1px solid var(--rn-gray-800)",
  position: "relative",
  clear: "both",
}}>
  <button disabled={page <= 1} style={{ opacity: page <= 1 ? 0.4 : 1, cursor: page <= 1 ? "default" : "pointer" }}>
    Anterior
  </button>
  <span style={{ whiteSpace: "nowrap" }}>
    {page} de {totalPages}
  </span>
  <button disabled={page >= totalPages} style={{ opacity: page >= totalPages ? 0.4 : 1, cursor: page >= totalPages ? "default" : "pointer" }}>
    Próxima
  </button>
</div>
```

**Critical properties:** `clear: both` (prevents overlap with floats), `whiteSpace: nowrap` (prevents the "X de Y" from wrapping), `position: relative` (creates a stacking context), `marginTop` (spacing from the content above).

**Symptom:** The activities dashboard showed "Nenhuma atividade no período" even with data in the database. The `useQuery` received `{ count, results }` but the component expected an array.

**Cause:** Adding `pagination_class` to a DRF ViewSet that previously returned `T[]` changes the response to `{ count, next, previous, results: T[] }`. The frontend that consumed `data` as an array now receives an object.

**Fix in 3 layers:**

1. **Backend:** Add `pagination_class` to the ViewSet:
```python
from rest_framework.pagination import PageNumberPagination

class MyPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100

class MyViewSet(...):
    pagination_class = MyPagination
```

2. **API endpoint type:** Update the return type in `endpoints.ts`:
```typescript
// Before:
api.get<T[]>("/path/")
// After:
api.get<PaginatedResponse<T>>("/path/")
```

3. **Query hook:** Add `page` and `page_size` to the params, and extract `results`:
```typescript
// In the hook:
useAuthedQuery({
  queryKey: ["key", params],
  queryFn: () => api.list(params),  // returns PaginatedResponse
  select: (data) => data.results,   // extracts the array
})
```

4. **Component:** Add page state + Previous/Next buttons:
```typescript
const [page, setPage] = useState(1);
const { data: pageData } = useQuery(params);
const logs = pageData?.results ?? [];
const totalPages = Math.ceil((pageData?.count ?? 0) / pageSize);
// Render: "{page} de {totalPages}" + Previous/Next
```

**Occurred in:** `dashboard.tsx` (ActivityFeed) + `activity/views.py` (ActivityLogViewSet)

**Symptom:** The remote `main` has commits that the local `main` does not. Future commits start from the feature branch and the local `main` falls behind.

**Cause:** `git push origin HEAD:main` updates the remote but not the local `main` branch.

**Fix:**
```bash
git checkout main
git merge feature-branch    # fast-forward (already on the remote)
git push origin main         # confirms (already synced)
git checkout feature-branch  # back to work
```

**How to detect:** `git log --oneline main..origin/main` shows commits that are on the remote but not local. `git log --oneline origin/main..main` shows the reverse.

## Complete Scan (mandatory after migration)

```python
# 1. Stale imports
deleted_modules = [
    "agents.tasks", "chat.tasks", "crews.tasks", "crews.callbacks",
    "knowledge.tasks", "integrations.tasks", "activity.tasks", "config.celery",
]
for root, dirs, files in os.walk(project_dir):
    for f in files:
        if f.endswith('.py'):
            with open(os.path.join(root, f)) as fh:
                content = fh.read()
            for mod in deleted_modules:
                for line in content.split('\n'):
                    s = line.strip()
                    if s.startswith(f'from {mod} import') or s.startswith(f'import {mod}'):
                        print(f"STALE: {rel}: {s}")

# 2. Essential settings
essential_settings = ["LLM_MODEL", "LLM_API_KEY", "LLM_API_BASE", "LLM_TEMPERATURE", "LLM_TIMEOUT"]
with open("config/settings.py") as f:
    content = f.read()
for s in essential_settings:
    if s not in content:
        print(f"MISSING: {s}")

# 3. Async calls without await
# Look for patterns like: `process_webhook_event(str(...))` without `asyncio.run()`
```
