---
name: cp-bug-fix
description: Fixes bugs using the NEXUS-Micro flow with The Agency agents. Creates a CrewAI crew with Developer → QA (with automated test creation) → Evidence Collector, max 3 retries. Use when the user asks to fix a bug, fix an error, or mentions "fix", "bug", "error", "fix", "repair" in any code context.
---

# cp-bug-fix — Bug Fix with NEXUS-Micro

Fixes bugs using the NEXUS-Micro flow with The Agency agents. Creates a CrewAI crew with:

1. **Developer** (Backend Architect or Frontend Developer) — investigates and implements the fix
2. **QA** (API Tester + Test Automation Engineer) — validates the fix AND creates automated tests
3. **Evidence Collector** — final verification with screenshots/evidence

Max 3 attempts in the Dev→QA loop. If it fails 3x, escalates with an escalation report.

## Usage

```
/load skill cp-bug-fix
fix: [bug description]
```

Or directly:

```
fix the bug where the login endpoint returns 500 when the email has an accent
```

## Operation Modes

### 🧪 Simulation (CrewAI — default)

Uses the NEXUS-Micro flow with CrewAI agents: Developer → QA → Evidence Collector.
Max 3 attempts in the Dev→QA loop. If it fails 3x, escalates with an escalation report.

```
[Developer] ──► [QA: API Tester + Test Automation Engineer] ──► [Evidence Collector]
     │                              │                                    │
     │  implements fix             │  validates + creates tests          │  final verification
     │                              │  automated                         │
     │                              │                                    │
     └──────────────────────────────┼────────────────────────────────────┘
                                    │
                              PASS / FAIL
                                    │
                          FAIL (max 3) → ESCALATION
```

### ⚡ Direct (traceback-driven — user's preferred)

Used when the user pastes a traceback. Flow:

1. **Read the traceback** — identify the `ModuleNotFoundError` / `SyntaxError` / `ImportError` and the exact line
2. **Diagnose the root cause** — import of a deleted module, import inside the wrong block, missing function in the migration
3. **Fix the file** — remove the obsolete line, reposition the import, add the missing function
4. **Verify syntax** — `compile(content, path, 'exec')` — ALWAYS compile after editing. Without this, the error only appears at runtime (Django loading URLs), not in the test.
5. **Test** — the user tests via the real system (password-reset, login) and pastes the next error if any
6. **Iterate** — repeat until the error disappears
7. **Commit + push** — after each fix, commit and push to main

**ALWAYS verify syntax with `compile()` after editing** — the syntax error only appears at runtime (Django loading URLs), not in pytest collection. Without this check, you only discover the error when the user tests.

**ALWAYS verify that the `sys.path` is correct** — in environments with multiple venvs (e.g. Hermes + project), the Hermes `lxml` can be loaded before the project's, causing `ImportError: cannot import name 'etree'`. Symptom: `manage.py` hangs or gives an lxml error. Fix: at the top of `manage.py`, remove the Hermes site-packages from `sys.path` and insert the project's at the top.

**ALWAYS remove the `crewai_tools_adapter` if `manage.py` hangs** — the module `chat/skills/crewai_tools_adapter.py` tries to discover 63 CrewAI tools at import time. Several call `input()` in `__init__` or do network I/O, hanging the process **forever** (hours, not seconds). The `lambda: "N"` that neutralizes `input()` is not enough. Definitive solution: delete the module, delete `chat/skills/crewai_custom/`, and remove the import from `chat/skills/__init__.py`. The Copilot does not use these tools — it uses the natively registered skills.

**ALWAYS sweep for stale imports after removing modules** — don't stop at the first error. (Doc-editing secret-masking pitfall: `references/editing-docs-secret-masking.md`) When a `ModuleNotFoundError` appears, the deleted module may have been imported in MULTIPLE files. Use a comprehensive sweep:

```python
# Complete sweep for stale imports
deleted = ["agents.tasks", "chat.tasks", "crews.tasks", "config.celery", ...]
for root, dirs, files in os.walk(back_dir):
    for f in files:
        if f.endswith('.py'):
            with open(fpath) as fh:
                content = fh.read()
            for mod in deleted:
                for line in content.split('\n'):
                    if line.strip().startswith(f'from {mod} import'):
                        print(f"STALE: {rel}: {line}")
```

**ALWAYS verify imports inserted inside wrong blocks** — when you add imports via find-and-replace, they can land inside a multi-line import (inside the parentheses of `from .models import (`). This silently breaks the syntax. Always check the 3 lines above and below the insertion point.

**ALWAYS verify indentation after substitutions** — find-and-replace can break the indentation of `try/except` blocks around the substitution. Check the 5 lines before and after.

**ALWAYS verify whether the server runs WSGI or ASGI** — `manage.py runserver` (WSGI) has no event loop running. The `TaskQueue` and `Scheduler` only start in `LifespanASGI.startup()` of Daphne. Without an event loop, `enqueue_task_sync()` enqueues in the `TaskQueue` but **never executes** — the task stays queued forever. Symptom: background tasks (generate title, index document) never complete.

**How to detect:** Hit any endpoint and check the `Server:` header in the response. If it's `WSGIServer` (Django runserver) or `Cheroot` (waitress), it's WSGI. If it's `daphne` or `uvicorn`, it's ASGI.

**Fix in `config/task_proxy.py`:** When the TaskQueue exists but workers are not running (or there is no event loop), run the task in a **separate thread** with `asyncio.run()`. Three scenarios:

1. **No event loop running** (`except RuntimeError`) — create a thread with `asyncio.run()`.
2. **Loop running but queue without workers** — same approach: separate thread.
3. **Loop running and queue with workers** — enqueue normally via `asyncio.run_coroutine_threadsafe()`.

**Critical pitfall:** Do NOT try `asyncio.run()` inline when there is already a loop running (scenario 2). `asyncio.run()` requires that there be no loop in the current thread. Using `asyncio.ensure_future()` also fails because the coroutine is never executed (nobody awaits it). The correct solution is a **daemon thread** with its own `asyncio.run()`:

```python
def enqueue_task_sync(name, coro_factory, *args, **kwargs):
    import asyncio, threading, uuid
    try:
        loop = asyncio.get_running_loop()
        q = get_queue()
        if q._running:
            # Scenario 3: ASGI with workers — enqueue
            task_obj = Task(name=name, coro=coro_factory(*args, **kwargs), ...)
            asyncio.run_coroutine_threadsafe(q.enqueue(task_obj), loop)
            return task_obj.task_id
        else:
            # Scenario 2: loop running but no workers — separate thread
            _tid = str(uuid.uuid4())
            def _run():
                try:
                    asyncio.run(coro_factory(*args, **kwargs))
                except Exception as exc:
                    logger.error("Task '%s' [%s] falhou: %s", name, _tid, exc)
            t = threading.Thread(target=_run, daemon=True)
            t.start()
            return _tid
    except RuntimeError:
        # Scenario 1: no loop running — separate thread
        _tid = str(uuid.uuid4())
        def _run():
            try:
                asyncio.run(coro_factory(*args, **kwargs))
            except Exception as exc:
                logger.error("Task '%s' [%s] falhou: %s", name, _tid, exc)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return _tid
```

**ALWAYS move `enqueue_task_sync` OUTSIDE of `sync_to_async`** — when `enqueue_task_sync` is called INSIDE a `sync_to_async` block (which runs in a thread pool), `asyncio.get_running_loop()` fails (there is no loop in the thread pool). The inline fallback creates a new event loop with `asyncio.run()`, but the `transaction.atomic()` transaction of the thread pool **has not committed yet**. The inline task tries `Conversation.objects.get(pk=...)` and gets `DoesNotExist` because the record is not visible to the new database connection. Symptom: `generate_session_title` never completes, the title stays "Nova Conversa" forever.

**Fix:** `_build_task` returns `(task, is_new, conversation_id)` instead of just `task`. The async `post()` unpacks the tuple and calls `enqueue_task_sync` **outside** of `sync_to_async`, on the main ASGI event loop, where the transaction has already committed and the TaskQueue is running:

```python
# WRONG — inside sync_to_async (thread pool, uncommitted transaction):
def _build_task(self, user, conv_ref, message):
    with transaction.atomic():
        conversation = Conversation.objects.create(...)
        ChatMessage.objects.create(...)
        enqueue_task_sync("generate_title", generate_session_title, str(conversation.id), message)  # ← FAILS: DoesNotExist
        return AgentTask.objects.create(...)

# CORRECT — returns data, enqueues outside:
def _build_task(self, user, conv_ref, message):
    with transaction.atomic():
        conversation = Conversation.objects.create(...)
        ChatMessage.objects.create(...)
        task = AgentTask.objects.create(...)
        return task, is_new, str(conversation.id)

# In the async post() (ASGI event loop, committed transaction):
task, is_new, conv_id = await sync_to_async(self._build_task)(user, conv_ref, message)
if is_new:
    enqueue_task_sync("generate_title", generate_session_title, conv_id, message)  # ← WORKS
```

**ALWAYS verify that the `runAgent` interceptor uses `activeIdRef.current` (ref) instead of `ctrl.activeId` (state) or `base.threadId` (random constructor UUID)** — when `ChatReady` creates the `HttpAgent` with a `runAgent` interceptor, the closure captures `ctrl.activeId` (React state) with its **initial value** (null). When the user clicks a conversation and types, the interceptor sees `activeId = null` and creates a new conversation. Symptom: the message goes to a new conversation instead of the current one.

**Root cause — TWO traps:**

1. **`ctrl.activeId` is React state, stale in the closure.** The interceptor closure `base.runAgent = async function(...) { ... ctrl.activeId ... }` captures the value of `activeId` at the moment the `HttpAgent` is created (which is created once, via `if (!agentRef.current)`). The React state `activeId` changes later, but the closure still sees the old value.

2. **`base.threadId` is NOT set by the runtime — and it's WORSE than having no interceptor.** The `HttpAgent` constructor generates a random UUID for `this.threadId`. The AG-UI runtime does **not** set `agent.threadId` when switching threads — it only calls the adapter. Using `base.threadId` as a fallback is worse than having no interceptor: the value is always truthy (a fake UUID), so the interceptor passes a nonexistent UUID to the backend, which creates a new conversation **silently** (no error, no 404). The user sees the message disappear and doesn't understand why.

**Fix in 3 parts:**

1. **`onSwitchToThread` in the adapter** sets `agent.threadId = threadId` **before** the REST fetch.
2. **Expose `activeIdRef` in the context** (`ThreadListController` + provider value).
3. **Interceptor uses `ctrl.activeIdRef?.current`** (ref, not state) instead of `ctrl.activeId` or `base.threadId`.

```tsx
// WRONG — ctrl.activeId is React state, stale in the closure:
base.runAgent = async function (params, subscriber) {
  if (!ctrl.activeId) { ... }  // ← always null, closure captured initial value
  ...
};

// WRONG — base.threadId is a random constructor UUID, always truthy:
base.runAgent = async function (params, subscriber) {
  if (base.threadId) { ... }  // ← always truthy, fake UUID, backend creates new conversation
  ...
};

// CORRECT — activeIdRef.current is a ref, always up to date:
const origRunAgent = base.runAgent.bind(base);
base.runAgent = async function (params, subscriber) {
  const ctrl = controller;
  const pendingId = ctrl.pendingThreadIdRef.current;
  if (pendingId) {
    ctrl.pendingThreadIdRef.current = null;
    base.threadId = pendingId;
    params = { ...params, threadId: pendingId };
    return origRunAgent(params, subscriber);
  }
  // Uses activeIdRef.current (ref, not state) to avoid stale closure.
  const activeId = ctrl.activeIdRef?.current;
  if (activeId) {
    base.threadId = activeId;
    params = { ...params, threadId: activeId };
    return origRunAgent(params, subscriber);
  }
  // Fallback: no active threadId, create or get the most recent one
  const conversations = ctrl.conversations;
  const mostRecent = conversations && conversations.length > 0 ? conversations[0] : null;
  if (mostRecent) {
    await ctrl.adapter.onSwitchToThread!(mostRecent.uuid);
    await ctrl.refresh();
    base.threadId = mostRecent.uuid;
  } else {
    const conv = await chatApi.createSession();
    await ctrl.adapter.onSwitchToThread!(conv.uuid);
    await ctrl.refresh();
    base.threadId = conv.uuid;
  }
  params = { ...params, threadId: base.threadId };
  return origRunAgent(params, subscriber);
};
```

**DON'T:**
- Use `ctrl.activeId` inside the `runAgent` interceptor — it's React state, the closure captures the initial value.
- Use `base.threadId` as a fallback — the `HttpAgent` constructor generates a random UUID, always truthy, which the backend interprets as a new conversation.
- Assume the runtime sets `agent.threadId` when switching threads — it does NOT set it, it only calls the adapter.

**After pushing HEAD:main, sync the local main branch** — when you do `git push origin HEAD:main` from a feature branch, the remote `main` is updated but the local `main` becomes outdated. Future commits start from the feature branch and the local `main` falls behind. To fix:
```bash
git checkout main
git merge feature-branch    # fast-forward
git push origin main         # already synced, but confirms
git checkout feature-branch  # back to work
```

**ALWAYS use `git cherry-pick` (not merge) to bring a docs commit from an outdated branch** — when an old branch has a docs/status commit (e.g. marking a feature as Concluída) but is FAR behind main (dozens of divergent files), `git merge` would drag everything in. `cherry-pick <commit>` applies only that commit to main. Before, verify that the files the commit touches are identical between the commit's parent and main (`git show <commit>^:<path>` vs `git show main:<path>`) — if they are, the cherry-pick applies cleanly without conflict. Then `git push origin main`. The old branch can be deleted (the commit has already been ported).

**ALWAYS check for double routing when including urls with a path parameter** — `path("serve/<slug:slug>/", include("pages.urls"))` captures the slug in the prefix, and if `pages/urls.py` also has `<slug:slug>/`, the slug is captured TWICE → 404. Fix: the prefix should not have the path parameter:
```python
# WRONG — slug captured twice:
path("serve/<slug:slug>/", include("pages.urls"))  # + <slug:slug>/ = /serve/<slug>/<slug>/

# CORRECT — prefix without slug:
path("serve/", include("pages.urls"))  # + <slug:slug>/ = /serve/<slug>/
```

**ALWAYS check for catch-all slug in routers included in `/api/v1/`** — a `path("<slug:slug>/", page_serve_by_slug)` in `pages/urls.py` captures ANY single-segment path, including `activity-log/`, `dashboard/`, etc. If `pages.urls` is included in `/api/v1/` BEFORE `activity.urls`, Django tries to serve `activity-log/` as a page slug → 404. Fix: separate the slug-serve routes into a separate file (`serve_urls.py`) that is only included in `/serve/`, and keep only the REST routers in `urls.py` (included in `/api/v1/`).

**ALWAYS add a proxy in vite.config.ts when creating a new public route** — the frontend (Vite dev server on :8080) only redirects to the backend (:8000) the routes listed in `server.proxy`. If you add a route like `/serve/<slug>/` in the backend, you need to add the corresponding proxy in `vite.config.ts`:
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

**ALWAYS verify whether the frontend expects a flat or paginated array when adding pagination in the backend** — when you add `pagination_class` to a DRF ViewSet that previously returned `T[]`, the response changes to `{ count, next, previous, results: T[] }`. The frontend that consumed `data` as an array now receives an object. Fix in 3 layers:

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

**ALWAYS verify whether the element has a fixed width when debugging text overlap** — when the user reports "text overlapping" on pagination or action buttons, the most common root cause is a CSS class with a fixed `width` (e.g. `.mini-btn { width: 34px; height: 34px }`) that doesn't fit the text. Symptom: the text overflows and overlaps adjacent elements in the flex container. Fix: remove the fixed-width class and use explicit `padding` + `whiteSpace: "nowrap"` on the buttons.

**ALWAYS check for a duplicated icon from `data-icon` + React component** — when a button has `data-icon="refresh"` (which renders an icon via CSS `::before` with an SVG mask) AND a React icon component (e.g. `<RefreshCw>`), the result is two overlapping icons. The `data-icon` renders via the `::before` pseudo-element, and the React component renders the real SVG. Fix: remove `data-icon="X"` and keep only the React component. This pattern is common in action buttons (refresh, add, edit) that were migrated from plain HTML to React.

**ALWAYS check gray token contrast in dark mode** — in the Crewbotics dark theme, `gray-200` and `gray-300` are `#404040` — almost invisible on the `#0A0A0A` background. For descriptive text (activity descriptions, labels), use `gray-600` (`#A3A3A3`). For secondary text (usernames, metadata, timestamps), use `gray-400` (`#525252`). Never use `gray-200` or `gray-300` for text in dark mode — they are only for borders and separators.

**ALWAYS verify that the CSS tokens used exist in the dark theme** — tokens like `gray-800` and `gray-700` DO NOT EXIST in the Crewbotics token system. The dark theme only defines `gray-100` to `gray-600` + `gray-900`. Using nonexistent tokens results in a transparent background/border (inherits from the parent). Fix: map to existing tokens:
  - `gray-800` (nonexistent) → `gray-100` (`#262626` in dark mode) for dark background
  - `gray-700` (nonexistent) → `gray-300` (`#404040` in dark mode) for border
  - `gray-200` (`#404040` in dark mode) → `gray-600` (`#A3A3A3`) for text
  - `gray-500` (`#737373`) → `gray-400` (`#525252`) for secondary text

**ALWAYS check imports of libraries with lazy proxies** — packages that use metaclasses for lazy-loading (e.g. `ddgs` with `_ProxyMeta`) can fail with `ImportError: cannot import name 'etree'` even when the module is installed. The proxy tries to load dependencies at the moment of first access, and if `sys.path` has a different venv in front (e.g. the Hermes venv with `lxml` without `etree`), the import fails. Fix: import directly from the submodule (`from ddgs.ddgs import DDGS`) instead of the root package (`from ddgs import DDGS`). See `references/ddgs-api-quirks.md` for details on the ddgs 9.x API.

### ALWAYS check loading dots in assistant messages (AG-UI React)

When the user reports "three dots appear in all the copilot message bubbles", the root cause is that the `<ThreadPrimitive.If running>` with the loading-dots is INSIDE the `AssistantMessage` component, which is rendered for EACH message. When the runtime is processing, `If running` is `true` for ALL messages, not just the last one. Fix: move the loading-dots OUTSIDE of `ThreadPrimitive.Messages`, between the closing of `Messages` and the `Viewport`. Render it as a separate "assistant thinking" bubble at the end of the list.

> **Chat message endpoints** (`branches`, `branch-version`): resolve by `uuid`+`id`, ignore AG-UI optimistic IDs (`__optimistic__`/`msg_`) to avoid 500 loops; **HTML/CSS carousels**: port to SVG + `resvg-py`+`font_files` (no browser, ECS-safe). Code in `references/agui-message-id-resolve-and-carousel-templates.md`.

**NEVER use `s.optional.message?.status?.type === "in_progress"` to detect streaming** — this selector checks the status of the **current** message being rendered by the `AssistantMessage`. When the message appears in the DOM, it has already finished (status is "complete" or similar), so `isStreaming` always returns `false`. The loading-dot never appears. The correct approach is `ThreadPrimitive.If running` **outside** the message loop, which checks whether the AG-UI runtime is processing any request, regardless of which message is being rendered.

```tsx
// WRONG — isStreaming always false, loading-dots never appear:
AssistantMessage: () => {
  const isStreaming = Aui.useAuiState?.(
    (s: any) => s.optional.message?.status?.type === "in_progress",
  );
  return (
    <MessagePrimitive.Root>
      <MessagePrimitive.Parts />
      {isStreaming && <div className="loading-dots">...</div>}  {/* ← never appears */}
    </MessagePrimitive.Root>
  );
}

// CORRECT — ThreadPrimitive.If running outside the loop:
<ThreadPrimitive.Messages components={{...}} />
<ThreadPrimitive.If running>
  <div className="msg msg--ai">
    <div className="msg__bubble">
      <div className="loading-dots">...</div>
    </div>
  </div>
</ThreadPrimitive.If>
```

**ALWAYS check `};` vs `}` in JSX objects** — when editing object literals with multiple inline components (e.g. `components={{ Text: ..., UserMessage: ..., AssistantMessage: ... }}`), the last item must NOT have a `;` after the `}`. A `};` inside a JSX object literal causes `[PARSE_ERROR] Expected ',' or '}' but found ';'`. The Vite/oxc parser is strict. Fix: the last item ends with `}` (no `;`), and the `;` only comes after the object closes: `}};`.

```tsx
{/* WRONG — loading dots inside AssistantMessage, appears in all */}
<ThreadPrimitive.Messages components={{
  AssistantMessage: () => (
    <div>
      <MessagePrimitive.Parts />
      <ThreadPrimitive.If running>   {/* ← appears in ALL messages */}
        <div className="loading-dots">...</div>
      </ThreadPrimitive.If>
    </div>
  ),
}} />

{/* CORRECT — loading dots outside the message loop */}
<ThreadPrimitive.Messages components={{...}} />
<ThreadPrimitive.If running>
  <div className="msg msg--ai">
    <div className="msg__bubble">
      <div className="loading-dots">...</div>
    </div>
  </div>
</ThreadPrimitive.If>
```

**ALWAYS test in the browser after fixing React frontend bugs** — when the bug is in the frontend (duplicate calls, ReferenceError, breaking component), don't rely only on `bun run build`. The build compiles TypeScript, but it doesn't detect runtime errors like `ReferenceError: agent is not defined` or logic that causes duplicate calls. After each fix:

1. `bun run build` — checks that it compiles
2. Reload the page in the browser
3. Open DevTools → Console (check for errors)
4. Open DevTools → Network (check for duplicate calls)
5. Test the action that was broken

**DON'T:** edit → build → commit without testing in the browser. The build passes even with runtime bugs. The user will report the error and you'll need 5 more iterations.

**GOLDEN RULE:** if the user reports a frontend error that you fixed, do NOT make another fix without testing in the browser first. Each iteration without testing generates 3-5 additional fixes. Test in the browser after EACH fix, not after the commit.

**IRON RULE:** if the user says "test in the browser" or "you're editing and not testing", STOP editing immediately. Run `bun run build`, reload the page, test manually, and only then continue editing. The user prefers that you test first and edit later, not the other way around.

**ALWAYS verify that the variable you reference exists in the component's scope** — `ReferenceError: X is not defined` is the most common error when editing React components. Before using a variable in a callback or JSX, verify that it:
- Was declared in the same component (via `useState`, `useRef`, `useMemo`, etc.)
- Was received as a prop
- Was received from a hook (e.g. `useConversationThreadList()`)
- Was NOT declared in a different parent component (e.g. `agent` is in `ChatReady`, not in `ThreadListSidebar`)

**ALWAYS verify that the `agentRef` type is `any`** — the `HttpAgent` from `@ag-ui/client` has a real setter (get/set) on `threadId`. If the type is `{ threadId: string | null }`, the assignment `agent.threadId = uuid` sets a plain property, not the setter — the fetch never fires. Use `React.MutableRefObject<any>` to access the real setter.

**ALWAYS consume the SSE stream in tests that verify persistence** — `StreamingHttpResponse` only persists the `ChatMessage` when the stream is fully consumed. Without `async_to_sync(_collect)(resp)`, `_finish()` never runs and the assistant message is not created in the database. Symptom: tests that create a conversation + send a message find only the user's message, never the assistant's.

```python
# WRONG — stream not consumed, _finish() never runs:
resp = _post(client, {"message": "Oi", "conversationId": str(conv.uuid)}, user=user)
assert resp.status_code == 200
msgs = ChatMessage.objects.filter(conversation=conv)
assert msgs.count() == 2  # ← FAILS: only has 1 (the user's)

# CORRECT — consumes the stream before verifying:
resp = _post(client, {"message": "Oi", "conversationId": str(conv.uuid)}, user=user)
assert resp.status_code == 200
async_to_sync(_collect)(resp)  # ← consumes the stream, _finish() persists the response
msgs = ChatMessage.objects.filter(conversation=conv)
assert msgs.count() == 2  # ← PASS: user + assistant
```

**ALWAYS mock `is_configured` in AG-UI tests** — the `AguiReActEngine._run_loop()` checks `llm_client.is_configured()` first. If it returns `False`, it calls `_stub_run()` which does **not** use `litellm.acompletion`. Mocking only `acompletion` without mocking `is_configured` makes the test pass in isolation but fail in batch (because the stub doesn't persist the assistant message).

```python
# CORRECT — mocks both:
from chat import llm_client
import litellm
monkeypatch.setattr(llm_client, "is_configured", lambda: True)
monkeypatch.setattr(litellm, "acompletion", _fake_acompletion(_text_chunks("OK.")))
```

**ALWAYS check for dead code when finding duplication** — when two files have similar implementations (e.g. `AguiChatPage.tsx` and `AguiRuntimeProvider.tsx` both create an `HttpAgent` with an interceptor), verify whether the second one is imported anywhere. If not, it's dead code and should be removed, not kept.

### GrapesJS RTE — DON'T customize the RTE

The GrapesJS RTE (Rich Text Editor) is fragile. Every customization introduces race conditions that break the double-click to edit text. **Golden rule:** don't add handlers on `rte:enable`, `component:selected`, `canvas:frame:load` or `redelegateTextViews`. Vanilla GrapesJS manages the RTE correctly.

**Patterns that ALWAYS break the RTE:**
- `demoteTextContainers` — changes the parent component type, re-rendering destroys the active RTE in the child
- `redelegateTextViews` — `delegateEvents()` re-binds dblclick handlers, the RTE interprets a second double-click
- `ed.Keymaps.removeAll()` in `rte:enable` — removes the internal protection that prevents the RTE from losing focus
- `requestAnimationFrame(() => requestAnimationFrame(focusEditing))` — double rAF competes with the RTE focus
- A `component:selected` handler that re-selects the component being edited — interrupts the RTE
- `range.selectNodeContents(el)` + `range.collapse(false)` — overwrites the user's text selection

**Protection for `ed.getWrapper()`:** the method throws `TypeError` when called before full initialization. Use `if (!wrapper) return;` or try/catch with retry.

**ALWAYS skip `notify()` (save) while the RTE is active** — the debounced `notify()` (400ms) fires on `component:update`, which is emitted WHEN the RTE activates. `getEditorData()` calls `ed.getHtml()` which serializes the component tree — this causes a canvas re-render that **resets the cursor to the start of the text**. After that, any click on the text returns the cursor to the start because the re-render replaces the DOM. Fix: add `if (ed.getEditing()) return;` at the start of the `setTimeout` callback of `notify()`:

```tsx
const notify = () => {
  if (notifyTimer) clearTimeout(notifyTimer);
  notifyTimer = setTimeout(() => {
    // DON'T save while the RTE is active — ed.getHtml() serializes
    // the component tree and causes a re-render that resets the cursor
    // to the start of the text. The save happens on natural blur (when
    // the user clicks outside the component).
    if (ed.getEditing()) return;
    const data = getEditorData();
    if (data) onChange(data);
  }, 400);
};
```

**Symptom:** user double-clicks text → RTE activates → cursor goes to the start → clicking any position in the text returns the cursor to the start. The save (onChange) is firing during editing and resetting the DOM.

**NEVER use `s.optional.message?.status?.type === "in_progress"` to detect streaming in AG-UI** — this selector checks the status of the **current** message being rendered by the `AssistantMessage`. When the message appears in the DOM, it has already finished (status is "complete" or similar), so `isStreaming` always returns `false`. The loading-dot never appears. The correct approach is `ThreadPrimitive.If running` **outside** the message loop, which checks whether the AG-UI runtime is processing any request, regardless of which message is being rendered.

```tsx
// WRONG — isStreaming always false, loading-dots never appear:
AssistantMessage: () => {
  const isStreaming = Aui.useAuiState?.(
    (s: any) => s.optional.message?.status?.type === "in_progress",
  );
  return (
    <MessagePrimitive.Root>
      <MessagePrimitive.Parts />
      {isStreaming && <div className="loading-dots">...</div>}  {/* ← never appears */}
    </MessagePrimitive.Root>
  );
}

// CORRECT — ThreadPrimitive.If running outside the loop:
<ThreadPrimitive.Messages components={{...}} />
<ThreadPrimitive.If running>
  <div className="msg msg--ai">
    <div className="msg__bubble">
      <div className="loading-dots">...</div>
    </div>
  </div>
</ThreadPrimitive.If>
```

**Empty duplicate conversation takes the top of the sidebar (pendingThreadIdRef never set)** — when the user reports "I start chatting, the chat responds, but on refresh the last conversation disappears", the root cause is that `pendingThreadIdRef` was designed to prevent conversation duplication on the first message but is **never set** in the adapter's `sendPrompt`. The `runAgent` interceptor reads and clears this ref, but since it's always `null`, it falls into the fallback of creating a new conversation (an empty duplicate takes the top of the sidebar; the real conversation seems to disappear on refresh). Fix: set `pendingThreadIdRef.current = conv.uuid` **before** returning in `sendPrompt`. See `references/agui-chat-duplicate-conversation-pending-ref.md`.

**ALWAYS use `runtimeRef` (ref) instead of `runtime` (state) in `useEffect`** — the `useAgUiRuntime` hook returns a NEW object on every render. If you put `runtime` in the dependencies of a `useEffect`, it fires in an infinite loop: effect → switchToThread → setState → re-render → new runtime → effect → ... Use `runtimeRef` (ref) to access the runtime inside the effect:

```tsx
// WRONG — runtime changes every render, infinite loop:
const runtime = useAgUiRuntime({...});
useEffect(() => {
  runtime.threads.switchToThread(id);
}, [runtime]);  // ← infinite loop

// CORRECT — runtimeRef is stable:
const runtimeRef = useRef(runtime);
runtimeRef.current = runtime;
useEffect(() => {
  const r = runtimeRef.current;
  r?.threads?.switchToThread(id);
}, [controller.bootReady]);  // ← no runtime in deps
```

**ALWAYS use `bootReady` state to load the auto-selected conversation on boot** — the `ThreadListProvider` auto-selects the most recent conversation (sets `activeId`) but doesn't call `onSwitchToThread` because the runtime doesn't exist yet. Add `bootReady` (React state) in the provider, set to `true` after the auto-select. In `ChatReady`, add a `useEffect` that observes `bootReady` + `activeIdRef.current` and calls `runtime.threads.switchToThread(id)`:

```tsx
// In the provider (useConversationThreadList.tsx):
const [bootReady, setBootReady] = useState(false);

// In the auto-select useEffect:
useEffect(() => {
  if (autoSelectDone.current) return;
  if (conversations.length === 0) return;
  autoSelectDone.current = true;
  const mostRecent = conversations[0];
  if (!mostRecent) return;
  threadIdRef.current = mostRecent.uuid;
  setActiveId(mostRecent.uuid);
  setBootReady(true);
}, [conversations]);

// In ChatReady (AguiChatPage.tsx):
const bootLoaded = useRef(false);
useEffect(() => {
  if (bootLoaded.current) return;
  if (!controller.bootReady) return;
  const id = controller.activeIdRef?.current;
  if (!id) return;
  bootLoaded.current = true;
  const r = runtimeRef.current;
  if (r?.threads?.switchToThread) {
    r.threads.switchToThread(id);
  }
}, [controller.bootReady, controller.activeIdRef?.current]);
```

### ALWAYS protect `ed.getWrapper()` with a null check or try/catch in GrapesJS

The GrapesJS `Editor.getWrapper()` method throws `TypeError: Cannot read properties of undefined (reading 'getWrapper')` when called before the editor completes its internal initialization. This happens in callbacks registered on `canvas:frame:load` and in double `requestAnimationFrame`. Protect with:

```tsx
// Option 1 — null check (when the wrapper can be undefined):
const wrapper = ed.getWrapper();
if (!wrapper) return;

// Option 2 — try/catch with retry (when the error comes from inside getWrapper):
try {
  const wrapper = ed.getWrapper();
  if (!wrapper) return;
  // ... uses wrapper ...
} catch {
  requestAnimationFrame(() => requestAnimationFrame(redelegateTextViews));
}
```

### ALWAYS remove the `component:selected` handler that re-selects the component being edited

When the RTE is active and the user clicks the text to select/position the cursor, the click propagates to the canvas and GrapesJS selects the component under the cursor. A `component:selected` handler that re-selects the component being edited interrupts the RTE and loses the text selection. **Remove** this handler — GrapesJS already manages internally that the RTE doesn't lose focus when the user clicks the canvas.

### ALWAYS remove `selectNodeContents` + `collapse` from the `rte:enable` handler

The `rte:enable` handler that focuses the element being edited should not call `range.selectNodeContents(el)` + `range.collapse(false)` — this overwrites the text selection the user just made with a double-click. Only focus the element if it isn't already active:

```tsx
ed.on("rte:enable", () => {
  const focusEditing = () => {
    try {
      const editing = ed.getEditing?.();
      const view = editing?.getView?.() as { el?: HTMLElement } | undefined;
      const el = view?.el;
      const doc = ed.Canvas.getDocument();
      if (!el || !doc) return;
      if (doc.activeElement === el) return;
      el.focus();  // ← only focuses, doesn't touch the selection
    } catch { /* best-effort */ }
  };
  requestAnimationFrame(() => requestAnimationFrame(focusEditing));
});
```

### ALWAYS remove specific keymaps (not all) in `rte:enable`

The `rte:enable` handler that removes keymaps should not call `ed.Keymaps.removeAll()` — this removes the GrapesJS internal protection that prevents the RTE from losing focus. Remove only the keymaps that interfere with inline text editing:

```tsx
ed.on("rte:enable", () => {
  const toRemove = [
    "core:copy", "core:paste", "core:cut",
    "core:component-outline", "core:component-delete",
  ];
  for (const id of toRemove) {
    try { ed.Keymaps.remove(id); } catch { /* noop */ }
  }
});
ed.on("rte:disable", () => {
  // Doesn't restore keymaps — GrapesJS recreates them internally
});
```

```typescript
// WRONG — return outside the try, messages out of scope:
try {
  const conv = await chatApi.getSession(threadId);
  const messages = (conv.messages ?? []).map(...);
} finally {
  setIsLoading(false);
}
return { messages };  // ← ReferenceError

// CORRECT — return inside the try:
try {
  const conv = await chatApi.getSession(threadId);
  const messages = (conv.messages ?? []).map(...);
  return { messages };
} finally {
  setIsLoading(false);
}
```

**ALWAYS add `console.debug` in the `runAgent` interceptor** — when the thread switching bug happens, there's no log in the console to diagnose which threadId was used. Add `console.debug("[runAgent]", ...)` in each branch of the interceptor (pending, activeId, fallback, new session):

```tsx
console.debug("[runAgent] using activeId:", activeId);
console.debug("[runAgent] fallback to mostRecent:", mostRecent.uuid);
console.debug("[runAgent] created new session:", conv.uuid);
```

**ALWAYS expose `window.__chatDebug` for remote debugging** — after creating the HttpAgent and the controller, expose the chat state in the browser console:

```tsx
if (typeof window !== "undefined") {
  (window as any).__chatDebug = {
    agent,
    controller,
    get activeId() { return controller.activeId; },
    get agentThreadId() { return agent?.threadId; },
    get conversations() { return controller.conversations; },
  };
}
```

This allows the user to type `__chatDebug` in the DevTools console to inspect the current chat state.

- Import of a module that was deleted (e.g. `agents.tasks` → `agents.tasks_async`)
- Import inserted inside a multi-line import (inside the parentheses of `from .models import (`)
- Function that existed in the old module but was not ported to the new one
- Broken indentation in the block around the substitution
- Duplicate import: old line + new line side by side (the old one breaks, the new one works)
- `manage.py` hanging due to a Hermes `lxml` conflict (fix `sys.path` in manage.py)
- `crewai_tools_adapter.py` hanging the boot forever (solution: delete the whole module)
- Calling an `async def` function in a synchronous test without `asyncio.run()`
- `doc.id` vs `doc.pk` in knowledge tests (use `doc.pk`)
- `run_pipeline` is in `crew_runner_async`, not in `tasks_async`
- Duplicated `asyncio.run(asyncio.run(...))`
- Settings that tests reference were deleted (e.g. `CELERY_TASK_ALWAYS_EAGER`, `CREW_RUN_STALE_AFTER`, `LLM_MODEL`)
- Tests with `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` break when the setting no longer exists
- Lambda mock in tests doesn't accept positional arguments (e.g. `lambda **kw` vs `lambda *a, **kw`)
- `embedding dimension mismatch` in tests (e.g. 3d vector vs 768d expected by pgvector)
- **`operator does not exist: uuid = integer` in all endpoints filtered by org** — a PK UUID→bigint migration that forgot to retype `organization_id` in the domain tables; and **`exclude`/`__in` is case-sensitive in Postgres** (don't `.lower()` the values). Both in `references/organization-fk-retype-uuid-bigint.md`.

**ALWAYS verify that ALL seed functions copy ALL model fields** — when you add a new field to a Django model (e.g. `category` in `CrewTemplate`), you need to update **all** the seed functions that create instances of that model, not just the main one. It's common to have separate seed functions (`crew_seed.py` + `agency_crew_seed.py`) and forget to add the new field in the secondary one. Symptom: the seed runs without error, but the field stays empty in the database. Fix: before creating a seed, list all the model fields with `[f.name for f in Model._meta.get_fields()]` and ensure each seed function sets all of them.

**ALWAYS move fixed bugs [Corrigido] and completed features [Concluído] to `.hermes/inbox/processed/`** — after fixing a bug (or completing a feature), the inbox file has `**Status:** [Corrigido]`/`[Concluído]` but **stays in the active folder** (`inbox/bugs/`, `inbox/features/`). When consolidating the inbox, move these items to `inbox/processed/` with `git mv` (preserves history). Items without an explicit status or with `[Aberto]`/`[Reclassificado]` status stay in the active folder. Leaving the `tasks.md` roadmap outdated is common — when reviewing what's "missing", cross-check the roadmap against the real code (many TSKs marked `[ ]` are already implemented; e.g. ActivityLog lives in the `activity/` app, not `utils/`, and the password-reset backend is already done — only the frontend pages are missing).

**ALWAYS run `manage.py migrate` on the dev DB after merging a feature with a new migration** — when you merge into main a feature that adds a field/model (e.g. `chat.0012_conversation_knowledge_folder`), the code (models/serializers) is up to date but the dev database does NOT have the column until you run `manage.py migrate`. Symptom: an endpoint that queries the model returns 500 with `psycopg.errors.UndefinedColumn: column <table>.<field>_id does not exist`. pytest doesn't catch this (it creates the schema from scratch); it only appears in dev/prod. Fix: `manage.py migrate <app>` (or general `manage.py migrate`) and validate with `manage.py shell -c "from <app>.models import <Model>; <Model>.objects.all()[:1]"`. Check pending migrations with `manage.py showmigrations <app> --plan` (lines with `[ ]` = not applied).

### CrewAI 1.15.5 — crew execution breaks silently

When the Copilot finds the crew, calls `execute_crew`, but the crew "doesn't run" (run stays `QUEUED` or breaks with an error that doesn't propagate to the chat), consult `references/crewai-crew-execution-pitfalls.md`.

**ALWAYS verify whether the crew ran in STUB when restarting the backend via subprocess** — if the run completes DONE but all outputs are `[STUB — crewai ausente]` EVEN with Gemini configured (`is_configured()=True`, log shows `LiteLLM ... provider = gemini`), the cause is that `import crewai` failed inside the restarted process due to missing Windows env vars (`USERPROFILE`, `HOME`, `LOCALAPPDATA`, `APPDATA`) that `chromadb`/`crewai_core` require. `_crewai_available()` returns `False` → falls into the stub. Fix: relaunch Daphne inheriting `os.environ` (only override PYTHONPATH/DJANGO_SETTINGS_MODULE) and validate with `python -c "import crewai"` in the SAME env. Details in `references/crewai-stub-on-subprocess-restart.md`.

**ALWAYS verify whether `import crewai` works in the server process when the crew runs in STUB** — if the card shows `[STUB — crewai ausente]` but Gemini is configured (`is_configured()` True, key in `.env`), the cause is `import crewai` failing inside Daphne, not the key. On Windows, crewai 1.15.5 pulls in `chromadb` (`Path.home()`) and `crewai_core` (`Path(LOCALAPPDATA)`); if the process doesn't have `USERPROFILE`/`HOME`/`LOCALAPPDATA` in its environment (common when relaunching via `subprocess.Popen` with a hand-built env), the import breaks with `RuntimeError: Could not determine home directory` or `TypeError ... not 'NoneType'` → `_crewai_available()` returns False → stub. Fix: relaunch Daphne with the full Windows environment (USERPROFILE, HOMEDRIVE, HOMEPATH, HOME, TEMP, TMP, LOCALAPPDATA, APPDATA). Verify with `python -c "import crewai"` using the SAME env before relaunching. Details in `references/crewai-stub-windows-env.md`. Summary of pitfalls:
- Synchronous `kickoff()` BREAKS with multiple tasks (`cannot schedule new futures after shutdown`) — use `kickoff_async()` via `asyncio.run()` in a daemon thread.
- `build_llm_kwargs`: native providers (gemini) need the model WITHOUT a prefix and WITHOUT an explicit `provider`, otherwise 404 on Gemini.
- The `OutputStatus` enum does NOT have `DONE` (only PENDING/APPROVED/REJECTED) — use `ExecutionStatus.DONE`.
- `sanitize_output(text)` accepts 1 arg.
- `build_tools(crew, allow_ask=True)` and `extract_integration_nodes(graph)` — correct signatures post-asyncio migration.
- `enqueue_task_sync` in the `except RuntimeError`: long tasks (`run_crew`) in a daemon thread, NEVER inline (otherwise Daphne kills the SSE).
- `execute_crew` must validate the required inputs of the `crew.input_schema` before firing (otherwise the agent asks for the data that should have been passed).
- `per_agent_context` in the runner expects a STRING, not a dict — convert `{member: {key: val}}` into readable text before injecting into the backstory.
- Frontend: display `output.executionStatus` (DONE/RUNNING/ERROR), NOT `output.status` (PENDING/APPROVED/REJECTED) — the approval status stays PENDING even when the task ran.

**ALWAYS check the scope when inserting large blocks via find-and-replace** — `content.replace(old, new)` with a non-unique anchor can insert the block INSIDE a function (compiles but corrupts the logic). Prevention: anchors with context lines ABOVE and BELOW; verify with `compile()`; visually check the surrounding indentation. If corrupted, rewrite the whole file.

**ALWAYS verify that `category` is passed when creating CrewTemplates via seed** — the `CrewTemplate` model has a `category` field that the frontend uses to filter templates in the marketplace. If the seed function doesn't set `obj.category`, the template appears without a category in the marketplace. Fix: add `obj.category = crew.get("category", "")` in the seed function, in both `crew_seed.py` and `agency_crew_seed.py`.

**ALWAYS verify that the JSON `input_schema` is used, not the code's** — the `upsert_agency_crews` function in `agency_crew_seed.py` uses `input_schema_for(crew_slug)` which looks up `INPUT_SCHEMAS` in the code. But the JSON `agency_crew_templates.json` also has `input_schema` in each crew. If the two diverge, the code wins. To ensure consistency, either (a) remove the `input_schema` from the JSON and keep it only in the code, or (b) make the seed read from the JSON. Option (a) is preferable to keep the source of truth in the Python code (easier to test and version).

**ALWAYS check the `agency-` prefix in the `member_slug` of the runbook seed** — the `agency_crew_seed.py` (Phase 2) uses `member_slug` with the `agency-` prefix (e.g. `agency-trend-researcher`) in the JSON `agency_crew_templates.json`, but the `BotTemplate` have `metadata["source_slug"]` WITHOUT the prefix (e.g. `trend-researcher`). Symptom: the seed runs without error, the 5 crews are created, but `members.filter(bot_template__isnull=False).count()` is 0 — no member linked to the agent. The runbook stays "empty" of real agents.

**Fix in 2 parts:**
1. **Prefix-tolerant lookup** in `upsert_agency_crews` — index `bots_by_slug` also without the prefix, and resolve with a helper that tries the full slug and then without `agency-`:
```python
def _resolve_bot(bots_by_slug, member_slug):
    if not member_slug:
        return None
    bot = bots_by_slug.get(member_slug)
    if bot:
        return bot
    if member_slug.startswith("agency-"):
        return bots_by_slug.get(member_slug[len("agency-"):])
    return None
```
2. **Create missing BotTemplates** — if some `member_slug` doesn't exist as a `source_slug` (e.g. `multi-platform-publisher`, `pr-communications-manager`), add it to `agents/seed_data/agency_agents.json` and run `manage.py seed_agency_agents` before `seed_agency_runbooks`.

**Verification:** after the seed, check `members.filter(bot_template__isnull=False).count()` == `members.count()` for each runbook. Seed order: `seed_agency_agents` → `seed_agency_runbooks`.

**ALWAYS verify that ALL seed functions copy ALL model fields** — when you add a new field to a Django model (e.g. `category` in `CrewTemplate`), you need to update **all** the seed functions that create instances of that model, not just the main one. It's common to have separate seed functions (`crew_seed.py` + `agency_crew_seed.py`) and forget to add the new field in the secondary one. Symptom: the seed runs without error, but the field stays empty in the database. Fix: before creating a seed, list all the model fields with `[f.name for f in Model._meta.get_fields()]` and ensure each seed function sets all of them.

**ALWAYS check the scope when inserting large blocks via find-and-replace** — `content.replace(old, new)` with a non-unique anchor can insert the block INSIDE a function (compiles but corrupts the logic). Prevention: anchors with context lines ABOVE and BELOW; verify with `compile()`; visually check the surrounding indentation. If corrupted, rewrite the whole file.

### USER PREFERENCE — the Copilot NEVER exposes ids/uuid to the end user

The user requires that the Copilot **never mention id or uuid to the end user**. It must reference crews, pages, documents and knowledge-base folders **ALWAYS by NAME** (e.g. "the Presença Digital crew", "the briefing-produto.txt document", "the sales page"). The ids/uuid are used internally to execute actions, but never shown or asked of the user.

**Bug symptom:** the Copilot responds "The crew with ID '22' was not found" or "I found crew X (ID: 22)". The LLM receives the tool results (which contain `id`, `uuid`, `run_id`, `crew_id`, `folder_id` etc.) and repeats them in the text responses.

**Fix (2 layers):**
1. **System prompt** — add an explicit rule in BOTH prompts:
   - `chat/engine.py` → `_build_system_prompt()` (Copilot's AG-UI engine)
   - `chat/llm.py` → `build_system_prompt()` (normal chat / orchestration)
   ```
   NUNCA exponha IDs, UUIDs ou identificadores técnicos ao usuário final.
   Referencie crews, páginas, documentos e pastas SEMPRE pelo NOME. Os
   resultados das ferramentas podem conter id, uuid, run_id, crew_id,
   folder_id etc. — use-os internamente para executar ações, mas NUNCA
   os mostre ou peça ao usuário. Se precisar que o usuário escolha algo,
   liste pelos nomes.
   ```
2. **Skills** — the returns of `list_crews`, `hire_crew`, `create_crew` should use `str(c.uuid)` (not `str(c.id)`), and `execute_crew` should resolve by uuid with a fallback (see section below). Generative UI components (SiteCard, PlaybookCard) load `pageId`/`run_id` in the props for the frontend to render — this is correct, it's not text to the user.

**Tests:** verify that the system prompt contains the rule; tests that expect `str(crew.id)` (PK) need to be updated to `str(crew.uuid)`.

### ALWAYS use `uuid` (not the numeric `id`) as the external reference for crews

The Crewbotics contract (AGENTS.md §11) defines that **`uuid` is the external reference via API**, not the numeric `id` (PK). The `CoreModel` has `id` (UUID PK) AND `uuid` (secondary UUID). The serializers expose `id = source="uuid"` — so the frontend already receives the uuid as `id`. But the **Copilot skills** and intent helpers often use `str(c.id)` (the numeric PK) by mistake.

**Classic symptom:** the Copilot lists the crew ("Presença Digital para Profissionais, ID: 22"), the user asks to trigger it, and the Copilot responds "The crew with ID '22' was not found". The `list_crews` returned `str(c.id)` = "22" (PK), but `execute_crew` resolves by `uuid`/`pk` and doesn't find it.

**Root cause:** `_uuid.UUID("22")` raises `ValueError`, so the uuid resolution block is skipped, and the name lookup also fails.

**Fix in 2 layers:**
1. **Skills that LIST crews** (`list_crews`, `hire_crew`, `create_crew`) should return `str(c.uuid)`, not `str(c.id)`.
2. **Skills that EXECUTE crews** (`execute_crew`) should resolve by `uuid` first, with a fallback to the numeric `id` (pk) and then the name:
```python
crew = None
import uuid as _uuid
try:
    _uuid.UUID(str(crew_id))
    crew = CrewInstance.objects.filter(uuid=crew_id, organization=self.org).first()
except (ValueError, TypeError):
    pass
if not crew:
    try:
        crew = CrewInstance.objects.filter(pk=int(crew_id), organization=self.org).first()
    except (ValueError, TypeError):
        pass
if not crew:
    qs = CrewInstance.objects.filter(organization=self.org)
    crew = (qs.filter(custom_name__iexact=crew_id).first()
            or qs.filter(custom_name__icontains=crew_id).first())
```

**Complete sweep:** when fixing, look for ALL places that use `str(c.id)`/`crew.id`/`instance.id` in a crew context — `chat/intent.py` (`crew_context_from_queryset`), `chat/views.py` (crew context, orchestration, `CrewIntentView`), `chat/skills/*`. The serializer exposes `id=uuid`, so the frontend is correct; the bug is always in the backend.

**Tests:** tests that expect `str(crew.id)` (PK) need to be updated to `str(crew.uuid)`.

### ALWAYS verify whether crewai imports in the process when seeing the stub "(crewai ausente)"

When the crew runs in stub mode `[STUB — crewai ausente]` but `llm_client.is_configured()` is True (Gemini/OpenAI configured, and even LiteLLM calls appear in the log of OTHER parts of the Copilot), the root cause is `_crewai_available()` returning False because `import crewai` fails INSIDE the running process — it's not a key problem.

On Windows, `import crewai` (1.15.5) pulls in `chromadb` (which calls `Path.home()`) and `crewai_core` (telemetry, which calls `Path(LOCALAPPDATA)`). If the Daphne/process is launched via subprocess with a MINIMAL env (without `USERPROFILE`/`HOME`/`LOCALAPPDATA`/`APPDATA`/`TEMP`), the import breaks with:
- `RuntimeError: Could not determine home directory` (chromadb → `Path.home()`)
- `TypeError: ... not 'NoneType'` (crewai_core → `Path(LOCALAPPDATA)`)

**Diagnosis:** `python -c "import crewai"` with the SAME env as the process. If it fails, this is it.

**Fix:** relaunch the Daphne/process with the full Windows environment (`USERPROFILE`, `HOME`, `HOMEDRIVE`, `HOMEPATH`, `LOCALAPPDATA`, `APPDATA`, `TEMP`, `TMP`). When the backend is started from the user's normal terminal these vars exist — this bug only appears when the agent relaunches the server via `subprocess.Popen` with a partial `env={...}`. Test with `python -c "import crewai"` in the final env before starting.

**ALWAYS diagnose "silent" crew execution via ExecutionLog**

> For the same pattern in **long synchronous skills** (e.g. `create_presentation` generating a carousel with images) that "disappear" from the chat — tool_call without tool_result, task stuck in `running`, artifacts created but response not persisted — see `references/skill-longa-sse-nao-persistida.md`.

When the user reports "I asked to trigger the crew but nothing happened"

```python
from chat.models import ExecutionLog
for l in ExecutionLog.objects.filter(task_id=<id>).order_by('id'):
    print(f'[{l.action_type}] tool={l.tool_name} payload={l.payload}')
```

**Revealing pattern:** an `execute_crew` `tool_call` **without** a corresponding `tool_result` = the async `run_crew` task broke in the background and the error was swallowed. `execute_crew` returns `{status: "dispatched"}` immediately (the dispatch is synchronous), but `run_crew` runs in a **separate thread** via `enqueue_task_sync` — if it throws an exception, the error only goes to the log, NEVER to the chat. The user sees "crew triggered" but nothing runs.

**Most common root cause (post Celery→asyncio migration):** `crews/tasks_async.py` calls functions with **wrong signatures** that weren't updated in the migration. `TypeError` symptoms:
- `build_tools() takes from 1 to 2 positional arguments but 4 were given` → `tasks_async.py` was calling `build_tools(crew, members, tasks, inputs)`, but the signature is `build_tools(crew, allow_ask=True)`. Fix: `build_tools(crew)`.
- `extract_integration_nodes() takes 1 positional argument but 3 were given` → `tasks_async.py` was calling `extract_integration_nodes(crew, tasks, inputs)`, but the signature is `extract_integration_nodes(graph)`. Fix: `extract_integration_nodes(crew.graph or {})`.

**How to confirm the fix:** run `dispatch_run(crew, {...})` in a shell. If it previously failed in seconds with `TypeError` and now takes time (runs the real pipeline), the signature bug is fixed. If the shell times out, that's a sign the crew is really executing (good sign).

**ALWAYS check the signatures of functions called in async tasks after a migration** — the Celery→asyncio migration (`tasks.py` → `tasks_async.py`) can copy calls with positional arguments that don't match the function's current signature. When you see `TypeError: X() takes N positional arguments but M were given` in an async task, check the function's real signature (`def build_tools(crew, allow_ask=True)`) and adjust the call — don't assume the extra arguments are valid.

**ALWAYS run `run_crew` in a separate thread, NEVER inline in the `except RuntimeError` of `enqueue_task_sync`** — when `execute_crew` runs inside the AG-UI engine (via `sync_to_async` in a thread pool), `enqueue_task_sync` falls into the `except RuntimeError` (no event loop in the thread pool). If it executes `asyncio.run(result)` **inline**, the crew completes (7 tasks, with LLM) INSIDE the request, blocking the SSE stream of `POST /chat/agui/` until Daphne kills the connection. Symptom in the log: `Application instance ... took too long to shut down and was killed` for the POST `/api/v1/chat/agui/`.

**Fix in `config/task_proxy.py`** — in the `except RuntimeError`, specialize by task name:
- **`run_crew`** (long task) → runs in a **daemon thread** with its own `asyncio.run()`. NEVER inline.
- **Fast tasks** (`index_document`, `generate_title`, etc.) → stay inline, because the knowledge/chat tests depend on the task persisting BEFORE the request/test returns (in `TransactionTestCase` the database is cleaned before a thread finishes).

```python
except RuntimeError:
    if name == "run_crew":
        import threading
        _tid = str(uuid.uuid4())
        def _run():
            try:
                result = coro_factory(*args, **kwargs)
                if hasattr(result, '__await__'):
                    asyncio.run(result)
            except Exception as exc:
                logger.error("Task '%s' [%s] falhou na thread: %s", name, _tid, exc)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return _tid
    # Fast tasks: inline (persists before returning).
    try:
        result = coro_factory(*args, **kwargs)
        if hasattr(result, '__await__'):
            return asyncio.run(result)
        return result
    except Exception as exc:
        logger.error("Task '%s' falhou inline: %s", name, exc)
        return str(uuid.uuid4())
```

**Test pitfall:** if you switch ALL tasks to a separate thread, the knowledge tests (`test_e2e_ct_005.py`) break with `ProductContext matching query does not exist` — the thread runs after the `TransactionTestCase` cleans the database. That's why `run_crew` is the ONLY task that should go to a thread; the rest stay inline.

**DON'T stop at `run_crew` when listing long tasks — include the approval/rejection callbacks.** When the user clicks "Aprovar entrega"/"Rejeitar", the front does `POST /chat/agui/resume/` and calls `enqueue_task_sync("on_crew_run_approved_callback" | "on_crew_run_rejected_callback", ...)`. If these callbacks run **inline** in the `except RuntimeError` (as `run_crew` originally did), they execute Composio + page creation INSIDE the request — `_apply_decision` hangs, the endpoint never returns headers, and the front's `res.text()` stays "processing" forever (button with spinner). Fix in `config/task_proxy.py`: include `on_crew_run_approved_callback` and `on_crew_run_rejected_callback` in the same separate-thread branch as `run_crew`. Full recipe in `references/agui-chat-crew-run-approval.md`.

**ALWAYS isolate synchronous ORM in an async context when moving callbacks to a thread.** When moving `on_crew_run_approved_callback` to a thread with its own `asyncio.run()`, latent `SynchronousOnlyOperation` bugs appear that were previously masked (the callback didn't even run inline). In `crews/callbacks_async.py`, `_create_page_from_run` did direct synchronous ORM (`_final_task_output(run)`, `run.crew.custom_name`, `run.created_at`) in an async context. Fix: extract a synchronous helper `_read_final_meta(run, _final_task_output)` that returns `(final_link, crew_name, created_at, org_id)` and call it via `sync_to_async`; use `organization_id`/`uuid` (not `run.organization` nor `pk`) in all accesses.

**ALWAYS use the ViewSet's `lookup_field` when calling an action via `asyncio.run_coroutine_threadsafe`/`sync_to_async`.** `_create_page_from_run` called `PageViewSet.publish(request, pk=str(page.id))`, but the `PageViewSet` has `lookup_field = "uuid"` — error `PageViewSet.publish() got an unexpected keyword argument 'pk'`. Fix: `publish(request, uuid=str(page.uuid))`. When invoking a ViewSet action manually, always check the `lookup_field` (default `pk`, but it can be `uuid`).

**ALWAYS generate a `slug` when creating a `Page` in the approval callback.** The `Page` model has `unique_together = [("organization", "slug")]` and `slug = SlugField()` WITHOUT default/auto-generation. If `_create_page_from_run` creates the Page with `title`/`html_content` but without `slug`, the first run passes (empty slug ok) but the SECOND run fails with `duplicate key value violates unique constraint "pages_page_organization_id_slug_30ccfd5f_uniq"` (Key (organization_id, slug)=(1, )). The callback still completes (page=none), but generates an error in the log. Fix: generate the slug from the title via `from django.utils.text import slugify; base_slug = slugify(page_title) or "entrega"` and pass `slug=base_slug` in the `Page.objects.create`. When creating any record with `unique_together`, verify that all non-default fields of the constraint are filled.

### DRF — ALWAYS check the `@action` decorator on ViewSet methods

When a method in a ViewSet doesn't have the `@action(detail=True/False, methods=[...])` decorator, DRF **doesn't expose the route** — the frontend gets a 404. Symptom: the method exists in the code, the logic is correct, but the URL returns "Não encontrado".

**Common root cause:** the method was added without the decorator, or the decorator was lost during a find-and-replace that corrupted the file structure.

**Fix:** add the appropriate decorator:
```python
from rest_framework.decorators import action

@action(detail=True, methods=["get"])  # for operations on a specific object
def download(self, request, **kwargs):
    ...

@action(detail=False, methods=["get"])  # for operations on the collection
def favorites(self, request):
    ...
```

**Verification:** after adding the decorator, test the URL directly via API (curl/requests) before testing in the frontend.

### ALWAYS check the file structure after find-and-replace of large blocks

When you use `content.replace(old, new)` to replace a large block (e.g. a whole function), the anchor text may not be unique enough, and the block can land INSIDE another function or between functions, corrupting the file structure.

**Symptoms:**
- The file compiles (`compile()` passes) but the logic is broken
- A function appears "split" into two parts (header + body separated by another function)
- A function's decorator disappears and the body becomes loose code

**Prevention:**
1. Use anchors with **at least 3 lines of context** above and below the target block
2. After the substitution, visually check the 10 lines before and after the substitution point
3. Verify that adjacent functions weren't affected (decorators, docstrings, indentation)
4. If the file becomes corrupted, **rewrite the whole file** instead of trying more patches

**Corruption example (happened in `knowledge/views.py`):**
```python
# BEFORE the substitution — correct structure:
@action(detail=True, methods=["get"])
def download(self, request, **kwargs):
    """Download de pasta como ZIP."""
    import io, zipfile
    ...  # full body

@action(detail=False, methods=["get"])
def favorites(self, request):
    ...

# AFTER the substitution — corrupted structure:
def download(self, request, **kwargs):  # ← @action lost
    """Download de pasta como ZIP."""
    import io, zipfile
@action(detail=False, methods=["get"])  # ← favorites entered the middle of download
def favorites(self, request):
    ...

        folder = KnowledgeFolder.objects.filter(...)  # ← download body loose
        ...
```

## React Frontend Bug Patterns

> **Collapsible sidebar + `data-icon` icon system** (crewbotics-front): CSS doesn't hide text nodes — wrap nav labels in `<span>`; icons via `[data-icon]::before` with `-webkit-mask: var(--i)`. Full pattern in `references/collapsible-sidebar-data-icon.md`.

### Message goes to a new conversation instead of the current one (AG-UI / @ag-ui/client)

When the user reports "I typed in conversation X but the message went to a new conversation", the root cause is that the `HttpAgent` was created **without** the `runAgent` interceptor that ensures `agent.threadId` is set before sending the message.

**Broken flow:**
1. User clicks a conversation → `switchToThread` is called
2. User types and sends → `HttpAgent.runAgent()` is called
3. The interceptor (if it exists) tries to decide which `threadId` to use
4. If the interceptor uses `ctrl.activeId` (React state) or `base.threadId` (random constructor UUID), the backend receives a wrong UUID and **creates a new conversation**
5. The message goes to the new conversation, the old one stays empty

### Message disappears when sending a new message (sendPrompt + switchToThread)

When the user reports "the assistant's response disappeared after I sent another message", the root cause is that `sendPrompt` calls `runtime.threads.switchToThread(activeId)` **before** doing `append()`. The runtime's `switchToThread` calls `core.applyExternalMessages([])` which **clears all current messages** — including partial assistant responses that are still being streamed. Then it re-fetches the history from the backend, but the partial response **hasn't been saved yet** in the database, so it simply disappears.

**Symptom:** User sends a message while the assistant is responding → partial response disappears. Or: user sends a second message → the first response disappears.

**Fix:** Don't call `switchToThread` when the user is already on the active thread. The `runAgent` interceptor already ensures `agent.threadId` is correct via `activeIdRef.current`:

```tsx
// WRONG — switchToThread clears current messages:
const sendPrompt = useCallback(async (prompt: string) => {
  if (activeId) {
    await runtime.threads.switchToThread(activeId);  // ← clears messages!
    runtime?.thread?.append?.({ role: "user", content: [{ type: "text", text: prompt }] });
  }
}, [...]);

// CORRECT — only appends, no switchToThread:
const sendPrompt = useCallback(async (prompt: string) => {
  if (activeId) {
    runtime?.thread?.append?.({ role: "user", content: [{ type: "text", text: prompt }] });
  } else {
    const conv = await chatApi.createSession();
    await adapter.onSwitchToThread(conv.uuid);
    runtime?.thread?.append?.({ role: "user", content: [{ type: "text", text: prompt }] });
  }
}, [...]);
```

**DON'T:** call `switchToThread` inside `sendPrompt` when `activeId` is already set. The `runAgent` interceptor already injects the correct `threadId` into the params.

### "New conversation" button doesn't clear the message area

When the user clicks "Nova conversa" and the sidebar updates but `chat__msgs` keeps showing the previous conversation, the root cause is that the `onClick` only calls `adapter.onSwitchToNewThread()`, which creates the conversation in the backend and updates the sidebar, but **doesn't clear the current messages** in the runtime.

**Fix:** Use `runtime.threads.switchToNewThread` when available — it calls `core.applyExternalMessages([])` + `core.resetState()` to show the empty state (`ThreadPrimitive.Empty`):

```tsx
// WRONG — only updates the sidebar, doesn't clear messages:
<button onClick={() => adapter.onSwitchToNewThread()}>

// CORRECT — prefers runtime when available:
<button onClick={() => {
  if (runtime?.threads?.switchToNewThread) {
    runtime.threads.switchToNewThread();
  } else {
    adapter.onSwitchToNewThread();
  }
}}>
**DON'T:** call `runtime.threads.switchToThread(uuid)` — it calls the adapter internally AND makes a second fetch. Calling the adapter directly is the correct approach, as long as the adapter sets `agent.threadId` before the fetch.

### Auto-selected conversation on boot doesn't load messages

When the user enters `/chat` and the most recent conversation is marked active in the sidebar but `chat__msgs` shows the empty state, the root cause is that the `ThreadListProvider` auto-selects the conversation (sets `activeId` + `threadIdRef`) but **doesn't call** `onSwitchToThread` because the runtime doesn't exist yet. `ChatReady` creates the runtime later, but there's no mechanism to load the messages of the auto-selected conversation. Fix in 2 parts (provider + ChatReady), using `bootReady` state + `runtimeRef`, without `runtime` in the deps (infinite loop). See the section below "ALWAYS use `runtimeRef`".

The `useAgUiRuntime` hook returns a NEW object on every render. If you put `runtime` in the dependencies of a `useEffect`, it fires in an infinite loop: effect → switchToThread → setState → re-render → new runtime → effect → ... Use `runtimeRef` (ref) to access the runtime inside the effect:

```tsx
// WRONG — runtime changes every render, infinite loop:
const runtime = useAgUiRuntime({...});
useEffect(() => {
  runtime.threads.switchToThread(id);
}, [runtime]);  // ← infinite loop

// CORRECT — runtimeRef is stable:
const runtimeRef = useRef(runtime);
runtimeRef.current = runtime;
useEffect(() => {
  const r = runtimeRef.current;
  r?.threads?.switchToThread(id);
}, [controller.bootReady]);  // ← no runtime in deps
```

### ALWAYS add `console.debug` in the `runAgent` interceptor

When the thread switching bug happens, there's no log in the console to diagnose which threadId was used. Add `console.debug("[runAgent]", ...)` in each branch of the interceptor (pending, activeId, fallback, new session):

```tsx
console.debug("[runAgent] using activeId:", activeId);
console.debug("[runAgent] fallback to mostRecent:", mostRecent.uuid);
console.debug("[runAgent] created new session:", conv.uuid);
```

### ALWAYS expose `window.__chatDebug` for remote debugging

After creating the HttpAgent and the controller, expose the chat state in the browser console:

```tsx
if (typeof window !== "undefined") {
  (window as any).__chatDebug = {
    agent,
    controller,
    get activeId() { return controller.activeId; },
    get agentThreadId() { return agent?.threadId; },
    get conversations() { return controller.conversations; },
  };
}
```

This allows the user to type `__chatDebug` in the DevTools console to inspect the current chat state.

**Root cause — TWO traps:**

1. **`ctrl.activeId` is React state, stale in the closure.** The interceptor `base.runAgent = async function(...) { ... ctrl.activeId ... }` captures the value of `activeId` at the moment the `HttpAgent` is created (which is created once, via `if (!agentRef.current)`). The React state `activeId` changes later, but the closure still sees the initial value (null).

2. **`base.threadId` is NOT set by the runtime.** The `HttpAgent` constructor generates a random UUID for `this.threadId`. The AG-UI runtime does **not** set `agent.threadId` when switching threads — it only calls the adapter. Using `base.threadId` as a fallback is worse than having no interceptor: the value is always truthy (a fake UUID), so the interceptor passes a nonexistent UUID to the backend, which silently creates a new conversation.

**Fix in 3 parts (2 files):**

**1. `useConversationThreadList.tsx` — the `onSwitchToThread` adapter sets `agent.threadId` BEFORE the fetch:**

```tsx
onSwitchToThread: async (threadId: string) => {
  threadIdRef.current = threadId;
  // Sets agent.threadId BEFORE doing the fetch — the HttpAgent uses
  // this.threadId in prepareRunAgentInput. Without this, the runAgent
  // interceptor sees the UUID generated in the constructor (new
  // conversation) instead of the UUID of the conversation the user clicked.
  const agent = agentRef.current;
  if (agent) agent.threadId = threadId;
  setActiveId(threadId);
  const conv = await chatApi.getSession(threadId);
  // ... process messages ...
  return { messages };
},
```

**2. `useConversationThreadList.tsx` — expose `activeIdRef` in the context:**

```tsx
// In the ThreadListController type:
activeIdRef: React.MutableRefObject<string | null>;

// In the provider:
value={{ adapter, conversations, activeId, activeIdRef, refresh, pendingThreadIdRef, agentRef }}
```

**3. `AguiChatPage.tsx` — the `runAgent` interceptor uses `activeIdRef.current` (ref, not state):**

```tsx
const origRunAgent = base.runAgent.bind(base);
base.runAgent = async function (params: any, subscriber: any) {
  const ctrl = controller;
  const pendingId = ctrl.pendingThreadIdRef.current;
  if (pendingId) {
    ctrl.pendingThreadIdRef.current = null;
    base.threadId = pendingId;
    params = { ...params, threadId: pendingId };
    return origRunAgent(params, subscriber);
  }
  // Uses activeIdRef.current (ref, not state) to avoid stale closure.
  // The onSwitchToThread adapter already set agent.threadId before the
  // fetch, but the interceptor can be called with params.threadId=null if
  // the runtime was recreated (useAgUiRuntime returns a new object every render).
  const activeId = ctrl.activeIdRef?.current;
  if (activeId) {
    base.threadId = activeId;
    params = { ...params, threadId: activeId };
    return origRunAgent(params, subscriber);
  }
  // Fallback: no active threadId, create or get the most recent one
  const conversations = ctrl.conversations;
  const mostRecent = conversations && conversations.length > 0 ? conversations[0] : null;
  if (mostRecent) {
    await ctrl.adapter.onSwitchToThread!(mostRecent.uuid);
    await ctrl.refresh();
    base.threadId = mostRecent.uuid;
  } else {
    const conv = await chatApi.createSession();
    await ctrl.adapter.onSwitchToThread!(conv.uuid);
    await ctrl.refresh();
    base.threadId = conv.uuid;
  }
  params = { ...params, threadId: base.threadId };
  return origRunAgent(params, subscriber);
};
```

**ALWAYS verify that the `HttpAgent` has the `runAgent` interceptor** — when `ChatReady` creates the agent directly (without using `AguiRuntimeProvider`), the interceptor that syncs `threadId` is missing. The symptom is messages going to new conversations.

**DON'T:**
- Use `ctrl.activeId` inside the `runAgent` interceptor — it's React state, the closure captures the initial value.
- Use `base.threadId` as a fallback — the `HttpAgent` constructor generates a random UUID, always truthy, which the backend interprets as a new conversation.
- Assume the runtime sets `agent.threadId` when switching threads — it does NOT set it, it only calls the adapter.

### Duplicate API call when clicking a chat conversation (AG-UI / @ag-ui/client)

> **"Chat indisponível" on attachment upload** (ErrorBoundary catching the `throw` of the `send` of attachments without an active conversation; backend OK) → see `references/agui-chat-upload-attachment-errorboundary.md`.

> **Full reference:** `references/agui-chat-thread-switching.md` — contains the complete debugging guide with all variations of the problem, backend and frontend code, and the working configuration.

When the user reports "two calls to the GET /conversations/{uuid}/ endpoint" when clicking a conversation, the root cause is that the `@ag-ui/client` HttpAgent has a **setter** on `agent.threadId` that fires a fetch **every time the value changes**. The problematic flow:

1. `handleClick(uuid)` → `setActiveId(uuid)`
2. `useEffect` detects `activeId` changed → calls `runtime.threads.switchToThread(uuid)`
3. `switchToThread` calls the adapter `onSwitchToThread(uuid)` → **fetch #1**
4. `switchToThread` sets `agent.threadId = uuid` → **fetch #2** (HttpAgent detects the change)

**Definitive fix:** the adapter should set `agent.threadId` **before** doing the fetch. When the runtime later tries to set `agent.threadId`, the HttpAgent sees it's the **same value** and doesn't re-fetch.

```tsx
// In the adapter (useConversationThreadList.tsx):
onSwitchToThread: async (threadId: string) => {
  threadIdRef.current = threadId;
  // Sets agent.threadId BEFORE doing the fetch, so that when
  // the runtime sets agent.threadId later, the HttpAgent sees the
  // same value and does NOT make a second fetch.
  const agent = agentRef.current;
  if (agent) agent.threadId = threadId;
  setActiveId(threadId);
  const conv = await chatApi.getSession(threadId);
  // ... process messages ...
  return { messages };
},
```

**Requirements to work:**
1. The `AguiRuntimeProvider` must expose the `agent` via `controller.agentRef.current = agent` (after the `useMemo` that creates the agent)
2. The `ThreadListController` must have `agentRef: React.MutableRefObject<{ threadId: string | null } | null>`
3. The `handleClick` must call **only** `adapter.onSwitchToThread(uuid)` — without `runtime.threads.switchToThread`
4. The `useEffect` that syncs `activeId` with `agent.threadId` must be **removed** — the adapter already set `agent.threadId` before `setActiveId`

**DON'T:** call `runtime.threads.switchToThread(uuid)` — it calls the adapter internally AND makes a second fetch. Calling the adapter directly is the correct approach, as long as the adapter sets `agent.threadId` before the fetch.

### Generative UI component doesn't render in the chat (CrewToolFallback)

When the user reports "I asked to create a presentation but the card didn't appear in the chat", the root cause is that the `CrewToolFallback` (in `CrewRunCard.tsx`) only detects crew dispatches (`run_id` + `status === "dispatched"`). Skills that return Generative UI components (like `PresentationCard`, `PlaybookCard`, etc.) pass by unnoticed — the fallback returns `null` and the card never appears.

**Symptom in Network:** the REST call to the backend returns 200 with the JSON containing `{ "component": "PresentationCard", "props": {...} }`, but the chat renders nothing.

**Fix in 2 steps:**

1. **`CrewRunCard.tsx`** — `CrewToolFallback` should detect `component` in the result and render the corresponding component from the `UI_REGISTRY`:
```tsx
import { UI_REGISTRY } from "@/components/generative-ui/registry";

export function CrewToolFallback({ result }: { result?: unknown }) {
  const r = result as Record<string, unknown>;
  // Generative UI component (PresentationCard, etc.)
  if (r && typeof r === "object" && "component" in r && typeof r.component === "string") {
    const Component = UI_REGISTRY[r.component];
    if (Component) {
      return <Component {...(r.props as Record<string, unknown>)} />;
    }
  }
  // Crew dispatch (existing logic)
  const isCrewDispatch = !!r && typeof r === "object" && "run_id" in r && r.status === "dispatched";
  if (!isCrewDispatch) return null;
  return <CrewCard result={r as CrewResult} />;
}
```

2. **`registry.tsx`** — `UI_REGISTRY` must be `export const`, not just `const`. Without the export, the import in `CrewRunCard.tsx` fails with `Missing export`.

**DON'T:** assume every tool call result is a crew dispatch. Copilot skills can return any component from the `UI_REGISTRY`.

### Missing ViewSet action in a related model

When a feature works for one model (e.g. favoriting documents) but not for a related model (e.g. favoriting folders), the most common root cause is that the `@action` decorator exists in one ViewSet but not in the other. Symptom: the frontend calls `/knowledge/docs/favorites/` and receives data, but `/knowledge/folders/favorites/` returns 404.

**Fix in 5 steps:**
1. Verify whether the action exists in the ViewSet of the missing model
2. Add the action following the same pattern as the ViewSet that already works
3. Add the corresponding endpoint in the frontend (`endpoints.ts`)
4. Add the React Query hook
5. Update the component that renders the list to include the data from the new endpoint

This pattern is common in Folder/Document pairs, Parent/Child, or any 1:N relationship where one ViewSet was implemented first and the other was left behind.

See `references/padroes-bugs-chat-presentacoes.md` for automatic title (is_new vs existing conv), SVG browser-vs-PPTX, and authenticated download via blob.

See `references/debug-running-process-drf-serializer-pitfalls.md` for: lib traceback that the disk no longer uses = old process in memory (restart the server, don't edit code); DRF `@action` with `url_path` (underscore vs hyphen); adding a field to the serializer breaks the key-set test; a new field requires a migration + `--create-db`.

See `references/playwright-windows-asyncio-loop.md` for PNG export: if it fails with `NotImplementedError` in `_make_subprocess_transport`, the event loop is Selector (doesn't support subprocess) — force `WindowsProactorEventLoopPolicy` before `asyncio.run()`. Don't confuse it with "Executable doesn't exist" (browser not installed → `python -m playwright install chromium`). **For production (ECS Linux/container) don't use Playwright/Chromium — prefer `resvg-py` (SVG→PNG in Rust, no browser/native lib); the reference documents why and how (import `resvg_py`, `svg_to_bytes(svg_string=<str>, width, height)`).**

**Prefer `resvg-py` over Playwright/Chromium for SVG→PNG** — when the PNG export of slides/carousel doesn't need a browser (the SVG already exists via `svg_renderer`), use `resvg-py` (Rust wheel, no native lib, works on Windows and ECS Linux, without downloading Chromium). `channel="chrome"`/`"msedge"` does NOT work in production (Linux container without a browser). See `references/svg-to-png-resvg.md` for the API (`resvg_py.svg_to_bytes`, `svg_string` accepts str not bytes) and pitfalls.

**For PNG export of slides/carousels in production (ECS Linux) or when the Chromium download fails, DON'T use Playwright** — use `resvg-py` (pure Rust SVG→PNG, no browser, no native lib, works on Windows and Linux). The project already generates the 1080×1350 SVG via `svg_renderer.py`; just convert it. `cairosvg` and `svglib`+`reportlab` fail because they require the native libcairo. Details and API quirks in `references/svg-to-png-resvg-alternative.md`.

## Quality Gates, Handoff Templates and Dev→QA Loop (Phase 2 of the Agency Plan)

When the NEXUS pipeline requires quality validation between tasks, implement:

### Model
Add fields to `CrewTemplateTask` (and `CrewInstanceTask`):
```python
quality_gate = models.BooleanField(default=False)       # True = validating task
max_retries = models.PositiveIntegerField(default=3)     # attempts before escalation
handoff_template = models.TextField(blank=True, default="")  # standard output format
```

### Logic in crew_runner.py
In `_build_and_run()`, after the kickoff, iterate the ordered tasks. For each task with `quality_gate=True`, read the output and check whether it starts with `PASS`, `WARN` or `FAIL`:
- **PASS** → log and continue
- **WARN** → log a warning and continue
- **FAIL** → re-execute the previous task (from `context`) up to `max_retries`. If exceeded, generate the `_escalation_<task_key>` key in the output dict.

```python
for t in ordered_tasks:
    if not getattr(t, 'quality_gate', False):
        continue
    gate_output = out.get(t.task_key, "")
    gate_result = gate_output.strip().upper()
    if gate_result.startswith("FAIL"):
        for ctx_key in (t.context or []):
            if ctx_key in out:
                for attempt in range(1, t.max_retries + 1):
                    out[ctx_key] = f"[QUALITY GATE FAIL - tentativa {attempt}/{t.max_retries}]..."
                    if attempt >= t.max_retries:
                        out[f"_escalation_{t.task_key}"] = "ESCALATION: ..."
    elif gate_result.startswith("WARN"):
        logger.info(...)
    elif gate_result.startswith("PASS"):
        logger.info(...)
```

### Handoff template
Inject the `handoff_template` into the task's `description` during creation:
```python
if getattr(t, 'handoff_template', None):
    desc = f"{desc}\n\n=== FORMATO DE SAÍDA (HANDOFF) ===\n{t.handoff_template}"
```

### Seed
Update the seed function to include the new fields:
```python
CrewTemplateTask.objects.create(
    ...,
    quality_gate=t.get("quality_gate", False),
    max_retries=t.get("max_retries", 3),
    handoff_template=t.get("handoff_template", ""),
)
```

### ALWAYS check sync/async divergence when migrating runner features

When a feature (e.g. quality gate) exists in the SYNCHRONOUS runner (`crew_runner.py` → `run_pipeline`) but the REAL execution path is the ASYNC one (`crew_runner_async.py` → `run_pipeline_async`, used by `run_crew` in `tasks_async.py`), the feature may have been **silently lost** in the migration. `run_crew_sync` uses the sync (with the feature), but the async `run_crew` (the one that actually runs) uses the async (without the feature). Symptom: the crew's FAIL is delivered as the final result without retry/escalation.

**Fix:** when fixing a pipeline bug, check BOTH runners (`crew_runner.py` and `crew_runner_async.py`) and port the logic to both. Don't assume the async mirrors the sync.

### ALWAYS verify that ALL functions that COPY tasks copy the quality gate fields

`hire_crew` (in `crews/services.py`) and `CpCrewSkill.execute` (in `chat/skills/cp_base_skill.py`) copy tasks from the template to the instance. If they don't copy `quality_gate`, `max_retries`, `handoff_template`, the copied tasks end up with `quality_gate=False` (default) — and the quality gate **never fires**, even with the runner fixed. Symptom: the crew self-evaluates with FAIL and the retry/escalation doesn't happen. Fix: add the 3 fields to the `CrewInstanceTask.objects.create/bulk_create` in ALL copy functions (not just the main one).

### ALWAYS define `on_task_done` as SYNCHRONOUS but NEVER save synchronous ORM directly

The CrewAI progress callback (`_make_cb` → `on_task_done(task_key, text)`) is called **without await** inside the runner. If you define `on_task_done` as `async def`, it's never executed (the coroutine is created and discarded) — the live progress doesn't record anything. Therefore the function MUST be synchronous (`def`).

**HOWEVER:** this synchronous callback runs INSIDE the event loop of `kickoff_async`. Calling `out.save()` (synchronous ORM) directly there raises `django.core.exceptions.SynchronousOnlyOperation: You cannot call this from an async context`. Symptom: the crew runs but the run becomes `ERROR` with this traceback and the card shows "Erro na execução".

**Fix:** inside the synchronous callback, schedule the save on an executor thread via `asyncio.run_coroutine_threadsafe` + `sync_to_async`:
```python
def _on_task_done(task_key, text):
    link = link_by_key.get(task_key)
    if not link or not text:
        return
    try:
        import asyncio
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop (rare) — saves directly.
        out = link.output
        out.content = sanitize_output(text)
        out.execution_status = ExecutionStatus.DONE
        out.save(update_fields=["content", "execution_status"])
        return

    def _save_sync(link_, text_):
        out_ = link_.output
        out_.content = sanitize_output(text_)
        out_.execution_status = ExecutionStatus.DONE
        out_.save(update_fields=["content", "execution_status"])

    async def _save():
        await sync_to_async(_save_sync)(link, text)

    asyncio.run_coroutine_threadsafe(_save(), loop)
```
Don't do `out.save()` inline inside the callback (which is synchronous but runs on the async loop).

### ALWAYS rebuild crew run cards from `runStatus` in the frontend (AG-UI)

When the user reports "the execution card disappeared after refresh and only the text appeared", the cause is that `toThreadMessage` (in `useConversationThreadList.tsx`) only converted messages with `uiComponent` or text in tool-calls — messages with `runStatus` (created by `post_run_status_message`) were rendered only as text. Fix in 3 parts:
1. **Backend** (`chat/run_status.py`): add `crewName` to the `runStatus` (`sig = {"runId": ..., "status": ..., "crewName": ...}`) so the front renders the card after refresh.
2. **Frontend** (`toThreadMessage`): convert messages with `runStatus` into an `execute_crew` tool-call with `result = { run_id, crew_name, status: "dispatched", finalOutput }` — so the `CrewToolFallback`/`CrewCard` rebuilds the card and the conversation history is preserved.
3. **`CrewCard`**: display `finalOutput.content` when `runStatus === "DONE"` (the result appears in the card, not just as text) and render a progress bar + task list from the `taskOutputs` of the polling in `/crew-runs/<id>/`.

### ALWAYS mock the ENTIRE `crewai` module (incl. the `crewai.tools` submodule) when testing the async runner

`run_pipeline_async` does `from crewai import LLM, Agent, Crew, Process, Task` AND `from crewai.tools import tool` INSIDE the function. To test the quality gate in the async with controlled outputs (FAIL/PASS), install a fake `crewai` module in `sys.modules` **and** the `crewai.tools` submodule (with the `tool` decorator). Also mock `crews.builtin_tools.build_builtin_tools` (imported from `.builtin_tools` inside the function — it's NOT an attribute of `crew_runner_async`, so the patch path is `crews.builtin_tools.build_builtin_tools`, not `crews.crew_runner_async.build_builtin_tools`). The runner creates the Tasks in the order of `ordered_tasks` without passing `task_key` to the constructor — use a global counter to map the creation order to the expected output.

### ALWAYS test the crew run card in the BROWSER via an E2E loop (AG-UI chat)

When the bug is in the crew execution card in the chat, don't rely only on backend tests or `bun run build` — run the real flow in the browser. Full recipe in `references/agui-chat-crew-run-card-e2e.md`. Flow:

1. **Login** at `http://localhost:8080/chat` (the test user; if there are no credentials, create a new user — AGENTS.md §13).
2. **Trigger the crew** — type "acione o time de presenca digital" and send. The Copilot asks for context.
3. **Provide the context** — profession/instagram/services. The crew is fired (`status: "dispatched"`).
4. **Check real progress** — read the bubbles via `Array.from(document.querySelectorAll('.msg__bubble')).map(b=>b.innerText).join('\n---\n')`. The card should show a "X de N etapas" bar + the task list, NOT a generic icon.
5. **Wait for the execution** — 7 tasks with LLM take 1-3 min. Poll the console every ~15-30s (the execution is in a separate thread, without a callback to the browser).
6. **Check the result in the card** — when DONE, the card should display `finalOutput.content` in the card itself + Aprovar/Rejeitar buttons.
7. **Click "Aprovar entrega"** — the button must NOT stay "processing" forever. It should receive the stream from `POST /chat/agui/resume/` (RUN_STARTED → crew.decision → RUN_FINISHED) and return to the normal state. This validates that `on_crew_run_approved_callback` runs in a separate thread (doesn't block the resume). Confirm via console that the button doesn't stay `disabled` with the `animate-spin` spinner.
8. **Refresh (F5)** — reload and verify that the card REMAINS visible with the result (history preserved). This validates `toThreadMessage` rebuilding the card from the `runStatus`.
9. **Single conversation** — via `window.__chatDebug` confirm `convCount` and `activeId` (no duplicates).

**Test the resume endpoint directly (curl/urllib) to isolate button hanging:** if the button stays "processing", the problem is almost always the `POST /api/v1/chat/agui/resume/` endpoint not returning headers (timeout). Test with `urllib.request.urlopen(req, timeout=15)`:
- **Timeout/`TimeoutError`** → the `_apply_decision` (and the inline approval callback) is blocking the request. Root cause = `enqueue_task_sync` running the callback inline.
- **200 in ~2s with SSE stream** → correct. The front's `res.text()` will resolve and the button stops processing.

**Restart Daphne after editing `config/task_proxy.py`/`callbacks_async.py`/`tasks_async.py`:** these modules are imported at ASGI boot — `manage.py runserver`/Daphne does NOT auto-reload these changes. Kill the process listening on port 8000 (`netstat -ano | findstr :8000` → PID → `taskkill /PID <pid> /F`) and relaunch. **Launch pitfall:** when starting via `execute_code`/subprocess, the Hermes sandbox injects its site-packages into `PYTHONPATH`, causing a `cffi`/`lxml`/`_overlapped` conflict (daphne fails at boot). Fix: set `PYTHONPATH` ONLY to `C:\...\.venv\Lib\site-packages` (without the Hermes one) + `PATH` with `.venv\Scripts` in front, and use `python.exe -m daphne` (the `daphne.exe` launcher can pick up the wrong HOME). Test with `python -c "import asyncio, daphne"` before launching.

**Confirm the real crew state:** read `window.__chatDebug.activeId` (the conversation uuid) and check `convCount` — if >1, there's a duplicate (regression of the `runAgent` interceptor).

**Document as a LOOP:** record the test in `.hermes/docs/testes-de-loop/LOOP-<data>-<slug>.md` with approval criteria + a results table per attempt (`cp-goal-loop` pattern). Update the attempt line when done.

**Pitfall:** the browser snapshot (`browser_snapshot`) doesn't show the text of the chat bubbles — use `browser_console` with the `.msg__bubble` selector to read the real content. The send button only enables after typing (the snapshot may show `disabled` — re-snapshot before clicking).

**ALWAYS render the markdown of `finalOutput.content` in the `CrewCard`** — when the user reports "the card shows the result but without formatting (bolding/lists become literal `**texto**`)", the cause is that the `CrewCard` renders `finalContent` in a `<div className="whitespace-pre-wrap">` (plain text). Fix: use `ReactMarkdown` + `remarkGfm` (the same ones already used in `AguiChatPage`), with the `markdown-body` class to inherit the chat's style:
```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
...
<div className="text-sm text-foreground markdown-body break-words">
  <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalContent}</ReactMarkdown>
</div>
```
**Verify in the browser:** `document.querySelectorAll('.msg__bubble .markdown-body')` and count `strong`/`li` in the delivery card (e.g. `strong=26 li=25` for a long PASS) — confirms that bolding and lists became HTML, not literal text. This is an approval criterion of the card's own E2E loop.

## IntegrationLayer (Phase 3 of the Agency Plan)

When you need to unify multiple integration backends (Composio, WhatsApp, Asset Library) under a single interface:

### Structure
```python
def resolve_provider_type(slug: str) -> str:
    # Returns "composio", "whatsapp", "asset" or "unknown"

def execute_action(organization, provider_slug, action, params, user=None) -> dict:
    # Returns {status: "ok"|"error", data: ..., error: ...}
    # NEVER raises an exception — always returns a dict with status

def list_available_actions(organization) -> list[dict]:
    # Lists actions from all connected providers

def check_integration_status(organization, provider_slug=None) -> dict:
    # Status of one or all providers

def validate_required_integrations(organization, required_providers) -> dict:
    # Returns {valid, missing: [{provider, type, message}], connected: [...]}
```

### Rules
- **NEVER raise an exception** — always return `{status: "error", error: "mensagem"}`
- **Local import** inside each `_execute_*` to avoid circular imports
- **Automatic stub** when the real backend isn't available (e.g. baileys not installed)
- **Rate limiting** of at least 3s between WhatsApp messages

## Agentic UI Components (Phase 4 of the Agency Plan)

Copilot skills that return Generative UI components follow this pattern:

### Backend (skill)
```python
@register_skill
class SomeSkill(BaseSkill):
    name = "skill_name"
    category = "Categoria"
    icon = "🎯"
    description = "..."
    parameters = {"type": "object", "properties": {...}}
    
    def execute(self, **kwargs) -> dict:
        # Processes...
        return {
            "component": "ComponentName",  # exact name in UI_REGISTRY
            "props": { ... },              # React component props
        }
```

### Frontend (component)
Create in `src/components/generative-ui/ComponentName.tsx`:
```tsx
import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const ComponentName = ({ prop1, prop2 }: { prop1: string; prop2?: number }) => {
  return (
    <Card className="my-2">
      <CardHeader><CardTitle>{prop1}</CardTitle></CardHeader>
      <CardContent>{/* ... */}</CardContent>
    </Card>
  );
};
```

Register in `registry.tsx`:
```tsx
import { ComponentName } from "./ComponentName";
const UI_REGISTRY = { ..., ComponentName };
```

### Standard Agentic UI components
| Component | Props | Usage |
|-----------|-------|-----|
| `PlaybookCard` | name, description, category, icon, agentCount, taskCount, slug, onSelect | Playbook suggestion |
| `PlaybookList` | playbooks[], total, onSelect | Playbook list |
| `IntegrationStatus` | playbookName, integrations[], allConnected, onConnect | Integration status |
| `WhatsAppQRCode` | qrCode, sessionId, expiresAt, onScanned, onRefresh | WhatsApp QR Code |
| `AssetUploader` | onUpload, maxFiles, accept | Drag-and-drop upload |
| `CrewProgress` | crewName, runId, status, totalTasks, completedTasks | Progress bar |
| `DeliverableGallery` | crewName, deliverables[], total | Deliverables grid |
| `ProposalPreview` | title, pdfUrl, onDownload, onView | PDF preview |
| `MetricsDashboard` | title, metrics[], period | 2x2 metrics grid |

## Script

The `scripts/run.py` script builds and runs the crew automatically with embedded agents (self-contained — doesn't depend on an external directory). It:

1. Creates the CrewAI agents with definitions embedded in the script itself
2. Creates the sequential tasks: Developer → QA → Evidence
3. Runs the crew and reports the result

To run manually:

```bash
python .hermes/skills/cp-bug-fix/scripts/run.py "descrição do bug aqui"
```

## Agents used

| Agent | File | Role |
|--------|---------|--------|
| Backend Architect | `engineering/engineering-backend-architect.md` | Developer (back-end) |
| Frontend Developer | `engineering/engineering-frontend-developer.md` | Developer (front-end) |
| API Tester | `testing/testing-api-tester.md` | QA — functional validation |
| Test Automation Engineer | `testing/testing-test-automation-engineer.md` | QA — automated test creation |
| Evidence Collector | `testing/testing-evidence-collector.md` | Final verification with evidence |
