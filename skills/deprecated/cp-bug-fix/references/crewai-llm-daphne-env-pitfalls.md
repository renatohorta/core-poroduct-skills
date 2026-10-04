# CrewAI LLM injection + Daphne env pitfalls (Crewbotics)

Pitfalls discovered while implementing CrewAI skills and restarting the backend in
Crewbotics. All validated in a real session.

## 1. CrewAI `Agent()` without `llm=` falls into the OpenAI default

Creating `Agent(...)` without `llm=` makes CrewAI use the OpenAI default and try
`OPENAI_API_KEY` — even with the project configured on Gemini. Symptom in the log:
`OPENAI_API_KEY is required` / `OpenAI API call failed`.

**Fix:** build the LLM from the global config (provider-agnostic) and inject it into
ALL agents:

```python
from crewai import LLM
from crews.crew_runner_async import build_llm_kwargs
from django.conf import settings

llm_kwargs = build_llm_kwargs(
    getattr(settings, "LLM_MODEL", "gemini/gemini-2.5-flash") or "gemini/gemini-2.5-flash",
    float(getattr(settings, "LLM_TEMPERATURE", 0.7)),
)
crew_llm = LLM(**llm_kwargs)
agent = Agent(..., llm=crew_llm)
```

`build_llm_kwargs` already builds `model/temperature/timeout/api_key/provider/is_litellm`
correctly for the active provider. NEVER leave `Agent()` without `llm=`.

## 2. Daphne relaunched via subprocess needs the full Windows env

When the backend is restarted via `subprocess.Popen` (not through the user's
terminal), a minimal env may be missing Windows variables that `import crewai`
requires. crewai 1.15.5 pulls in `chromadb` (calls `Path.home()`) and `crewai_core`
(calls `Path(LOCALAPPDATA)`). Without `USERPROFILE`/`HOME`/`LOCALAPPDATA`, the import
breaks and `_crewai_available()` returns `False` → the crew falls into **stub** mode
(`[STUB — crewai ausente]`) EVEN with Gemini configured and reachable.

**Confusing symptom:** the log shows `LiteLLM completion() model= gemini-2.5-flash`
(from Copilot/chat) but the crew runs in stub. Gemini is OK; the problem is the import.

**Fix:** when relaunching Daphne via subprocess, include the full env:
```python
env = {
    "DJANGO_SETTINGS_MODULE": "config.settings",
    "PYTHONPATH": os.path.join(back, ".venv", "Lib", "site-packages"),
    "PATH": os.path.join(back, ".venv", "Scripts") + os.pathsep + os.environ.get("PATH", ""),
    "VIRTUAL_ENV": os.path.join(back, ".venv"),
    "SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
    "WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
    "USERPROFILE": os.environ.get("USERPROFILE", r"C:\Users\renat"),
    "HOMEDRIVE": os.environ.get("HOMEDRIVE", "C:"),
    "HOMEPATH": os.environ.get("HOMEPATH", r"\Users\renat"),
    "HOME": os.environ.get("HOME", r"C:\Users\renat"),
    "TEMP": os.environ.get("TEMP", r"C:\Users\renat\AppData\Local\Temp"),
    "TMP": os.environ.get("TMP", r"C:\Users\renat\AppData\Local\Temp"),
    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", r"C:\Users\renat\AppData\Local"),
    "APPDATA": os.environ.get("APPDATA", r"C:\Users\renat\AppData\Roaming"),
}
```
**Verify before starting:** `python -c "import crewai; print(crewai.__version__)"`
with this env — if it imports, Daphne will run the crew for real.

## 3. `from django.conf import settings` inside a function → UnboundLocalError

If the module has `from django.conf import settings` at the top AND also a
`from django.conf import settings` INSIDE a function (e.g. in an `if` block),
Python treats `settings` as a LOCAL variable in the whole function — any use
of `settings` before that local import throws `UnboundLocalError: cannot access
local variable 'settings'`. Fix: rename the local import
(`from django.conf import settings as dj_settings`) or use only the top one.

## 4. Postgres `title__in`/`name__in` is case-sensitive

When filtering by `exclude`/`targets` with `__in`, do NOT lowercase the values before the
query — Postgres compares exactly. If you do `str(x).strip().lower()`
to normalize and then use `title__in=[...]`, the match fails silently and
the "kept" item ends up excluded. Keep the original values for the query
(use lowercase only for manual comparison, not for the ORM filter).

## 5. Gemini model WITHOUT the `gemini/` prefix is routed to `vertex_ai` (ADC) in production

**Symptom in the production log (ECS):** LLM calls with `gemini-2.5-flash` (without
the `gemini/` prefix) produce:
```
LiteLLM completion() model= gemini-2.5-flash; provider = vertex_ai   ← FAILS
google.auth.exceptions.DefaultCredentialsError: Your default credentials were not found
...
LiteLLM completion() model= gemini-2.5-flash; provider = gemini      ← WORKS
```
The chat still responds (the `gemini/gemini-2.5-flash` fallback works), but with
~15s delay per call — LiteLLM tries `vertex_ai` first, fails for lack of
ADC, and only then falls into the fallback. On ECS there are no Application Default Credentials
(service account), so `vertex_ai` never works.

**Root cause:** a model **without a slash** (`gemini-2.5-flash`) is routed by LiteLLM
to the `vertex_ai` provider (which requires ADC), instead of `gemini` (which uses an API key via
`GEMINI_API_KEY`). The code default is `gemini/gemini-2.5-flash` (with prefix) —
correct; the bug is the **`LLM_MODEL` secret** that came without a prefix.

**Fix in 2 layers:**
1. **Production secret (AWS):** fix `LLM_MODEL` to `gemini/gemini-2.5-flash`
   (same pattern as the previous nonexistent `gemini-3-flash` bug).
2. **Hardening in code** (`chat/llm_client.py`) so that a prefix-less secret
   does not break in any environment:
```python
def _normalize_model(model: str) -> str:
    """Guarantees the LiteLLM `provider/model` format. A model without a slash (e.g.
    gemini-2.5-flash) is routed by LiteLLM to vertex_ai (requires ADC) instead
    of gemini (API key). Prepend gemini/ to prefix-less models."""
    if "/" in model:
        return model
    return f"gemini/{model}"

def get_model() -> str:
    raw = getattr(settings, "LLM_MODEL", "") or "gemini/gemini-2.5-flash"
    return _normalize_model(raw)
```
   Apply `_normalize_model()` in `get_model()`, `_base_kwargs()` (the central point
   where the model reaches LiteLLM) and in the embedding model (`embed()`) too. The
   crews path is already safe (`_resolve_litellm_model` uses `get_model()`).

**How to diagnose quickly:** in the log, compare the `LiteLLM completion()
model= ...; provider = ...` lines. If `provider = vertex_ai` appears before the fallback
`provider = gemini`, this is the bug — it is not a key problem, it is a prefix/provider one.
