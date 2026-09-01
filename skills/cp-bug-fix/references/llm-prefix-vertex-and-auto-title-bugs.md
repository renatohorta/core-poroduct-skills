# Bug: LLM_MODEL without prefix → vertex_ai / ADC (production)

## Symptom
Production log:
```
LiteLLM completion() model= gemini-2.5-flash; provider = vertex_ai   ← FAILS
LiteLLM completion() model= gemini-2.5-flash; provider = gemini      ← WORKS
google.auth.exceptions.DefaultCredentialsError: Your default credentials were not found.
```
The chat responds but with ~15s delay per call (vertex fails → fallback → gemini). The error is in ALL calls, including `complete_json` and `astream_with_tools`.

## Root cause
The `LLM_MODEL` secret in production is configured as **`gemini-2.5-flash` without the `gemini/` prefix**. When LiteLLM receives a model without a slash, it routes to the `vertex_ai` provider, which requires **Application Default Credentials (ADC/service account)** — which do NOT exist on ECS. The `gemini/gemini-2.5-flash` fallback (with prefix) uses `provider = gemini` (API key via `GEMINI_API_KEY`) and works.

## Fix (hardening in code)
In `chat/llm_client.py`, add `_normalize_model()` that guarantees the `provider/model` format and apply it in `get_model()`, `_base_kwargs()` and the embedding:

```python
def _normalize_model(model: str) -> str:
    """Guarantees the LiteLLM `provider/model` format. A model without a slash (e.g. gemini-2.5-flash)
    is routed by LiteLLM to vertex_ai (requires ADC), not gemini (API key)."""
    if "/" in model:
        return model
    return f"gemini/{model}"

def get_model() -> str:
    raw = getattr(settings, "LLM_MODEL", "") or "gemini/gemini-2.5-flash"
    return _normalize_model(raw)
```

Also **fix the `LLM_MODEL` secret in AWS** to `gemini/gemini-2.5-flash` (the hardening only prevents the symptom; the correct secret is the definitive fix). Same pattern as the previous nonexistent `gemini-3-flash` bug.

## Tests
`tests/chat/test_llm_model_fallback.py` → `ModelNormalizeTests`:
- `_normalize_model("gemini-2.5-flash") == "gemini/gemini-2.5-flash"`
- explicit prefixes (`ollama_chat/...`, `openai/...`) preserved
- `get_model()` with a prefix-less `LLM_MODEL` normalizes
- `complete()` uses the model WITH prefix in the LiteLLM call

---
# Bug: Automatic conversation title is never generated (bug B)

## Symptom
Conversations created via chat stay with an empty title (show "Nova Conversa" in the sidebar) even after several messages. The automatic title is never generated.

## Root cause
The frontend (`AguiChatPage.tsx` → `onSwitchToNewThread` → `createSession()`) creates the **empty** conversation (without a title) BEFORE sending the first message. When the 1st message reaches the backend (`POST /chat/agui/` → `_build_task`), the conversation **already exists**, so `is_new=False` — and `generate_session_title` was only fired when `is_new=True`. Result: the conversation never gets a title.

## Fix
In `chat/agui/views.py`, `_build_task` returns `needs_title` (not just `is_new`):

```python
needs_title = is_new or (
    not conversation.title or conversation.title.strip() == "Nova Conversa"
)
return task, is_new, str(conversation.id), needs_title
```
And the `post()` fires the title when `needs_title` (not `is_new`). Update the caller unpacking: `task, is_new, conv_id, needs_title = await sync_to_async(self._build_task)(...)`.

## Test
`tests/chat/test_agui.py::test_agui_generates_title_for_existing_empty_conversation`:
- creates a conversation with `title=""`
- POSTs the 1st message with `conversationId`
- the title task runs in a daemon thread (TaskQueue without workers in tests) → **wait with a `for _ in range(20): refresh + sleep(0.2)` loop** before asserting the title
- asserts `conv.title` is not empty and != "Nova Conversa"

## Pitfall: TaskQueue "workers nao rodando" in Daphne
When restarting the local Daphne and observing the log, background tasks log `TaskQueue workers nao rodando — executando task 'generate_session_title' inline`. This indicates that the ASGI lifespan (which calls `startup()` → `get_queue().start()`) may not have fired. It works inline for fast tasks (title), but is SERIOUS for long tasks (`run_crew`) that must run in a separate thread — if they run inline, they block the SSE. When restarting Daphne, confirm in the log `ASGI startup: TaskQueue + Scheduler started`; if it does not appear, the lifespan did not run and the crews flow may regress.
