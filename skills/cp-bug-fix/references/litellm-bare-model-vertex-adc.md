# LiteLLM routes a "bare" model to vertex_ai → DefaultCredentialsError

## Symptom (production ECS)
The chat responds, but with ~15s delay per call. Revealing log — the SAME
model resolves to two different providers:

```
LiteLLM completion() model= gemini-2.5-flash; provider = vertex_ai   ← FAILS (ADC)
LiteLLM completion() model= gemini-2.5-flash; provider = gemini      ← WORKS (API key)
```

`provider = vertex_ai` → `google.auth.exceptions.DefaultCredentialsError: Your
default credentials were not found`. ECS has no ADC/service account.

## Root cause
The `LLM_MODEL` secret in production is configured **without the `provider/` prefix**
(e.g. `gemini-2.5-flash` instead of `gemini/gemini-2.5-flash`). When LiteLLM
receives a model without a slash, it assumes `vertex_ai` (which requires ADC), not `gemini`
(which uses `GEMINI_API_KEY`). The `gemini/gemini-2.5-flash` fallback (with prefix)
uses an API key and works — hence the "works but slow".

## Fix (hardening in code, `chat/llm_client.py`)
Normalize the model to `provider/model` before passing it to LiteLLM:

```python
def _normalize_model(model: str) -> str:
    """Without a slash → prepend 'gemini/'. Without this LiteLLM routes to vertex_ai."""
    if "/" in model:
        return model
    return f"gemini/{model}"
```

Apply in:
- `get_model()` — `_normalize_model(getattr(settings, "LLM_MODEL", ...) or ...)`
- `_base_kwargs()` — `_normalize_model(model or get_model())` (the central point where
  the model reaches `litellm.completion`)
- embedding — `_normalize_model(model or getattr(settings, "EMBEDDING_MODEL", ...))`

The crews path already protects: `crew_runner_async._resolve_litellm_model()` uses
`llm_client.get_model()` (already normalized) for the crew's "bare" models.

## Production action (not just code)
The hardening prevents the symptom, but the **`LLM_MODEL` secret in AWS is still
wrong**. Fix it to `gemini/gemini-2.5-flash`. Same pattern as the previous bug
(`gemini-3-flash` nonexistent) — production config always comes from AWS secrets,
not from code.

## Tests
`tests/chat/test_llm_model_fallback.py` → `ModelNormalizeTests`:
- a bare model gains a prefix (`gemini-2.5-flash` → `gemini/gemini-2.5-flash`)
- an explicit prefix is preserved (`openai/gpt-4o-mini`, `ollama_chat/...`)
- `get_model()` with a prefix-less `LLM_MODEL` returns with a prefix
- `litellm.completion` receives the model WITH prefix (mock `call_args.kwargs["model"]`)
