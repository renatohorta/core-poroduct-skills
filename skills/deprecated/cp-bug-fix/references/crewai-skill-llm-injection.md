# CrewAI — Inject the configured LLM into new skills + Python pitfall

## Problem
When creating a CrewAI pipeline inside a skill (e.g. `canvas_design`), an
`Agent(role=..., goal=..., backstory=...)` WITHOUT `llm=` uses the **CrewAI OpenAI
default** → `OPENAI_API_KEY is required`, even with Gemini/another provider
configured globally. Symptom in the log: `crewai.flow.runtime ... OPENAI_API_KEY
is required` + the skill returns an error to Copilot.

## Fix (provider-agnostic)
Build the LLM via `crews.crew_runner_async.build_llm_kwargs` and pass
`llm=crew_llm` to EACH agent:

```python
from crewai import LLM, Agent
from crews.crew_runner_async import build_llm_kwargs
from chat import llm_client
from django.conf import settings

llm_kwargs = build_llm_kwargs(
    getattr(settings, "LLM_MODEL", "gemini/gemini-2.5-flash") or "gemini/gemini-2.5-flash",
    float(getattr(settings, "LLM_TEMPERATURE", 0.7)),
)
crew_llm = LLM(**llm_kwargs)

art_director = Agent(role=..., goal=..., backstory=...,
                     llm=crew_llm, allow_delegation=False, verbose=False)
```

`build_llm_kwargs` already handles: the provider prefix, `is_litellm=True` (avoids
CrewAI's `__new__` falling into the native OpenAI SDK), `api_key`, `api_base`,
`provider_call_extra`. Never hardcode OpenAI — the global config rules.

## Execution: use kickoff_async in a daemon thread
CrewAI 1.15.5 breaks the synchronous `kickoff()` with multiple tasks. In a skill that creates
the crew and calls `execute`, run `kickoff_async()` in a daemon thread with its
own `asyncio.run()` (never inline, otherwise it blocks the SSE). Pattern:

```python
def _run_crew(crew) -> str:
    import asyncio, threading
    holder = {}
    async def _run():
        r = await crew.kickoff_async()
        return str(getattr(r, "raw", r) or "")
    def _worker():
        try:
            holder["value"] = asyncio.run(_run())
        except Exception as exc:
            holder["error"] = exc
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=180)
    if "error" in holder:
        raise RuntimeError(f"Falha na crew: {holder['error']}")
    return holder.get("value", "")
```

## Python pitfall: `UnboundLocalError: cannot access local variable 'settings'`
If the file does `from django.conf import settings` at the top AND a local import
`from django.conf import settings` INSIDE a method (e.g. for `MEDIA_ROOT`),
the local import makes `settings` a local variable in the whole function scope
→ the reference at the top of the method (`getattr(settings, "LLM_MODEL", ...)`) fails
with `UnboundLocalError`. Fix: rename the local import
(`from django.conf import settings as dj_settings`).

## Artifact return (AG-UI / Generative UI)
- `output_format=png` → `component: "ImageCard"` with `props.imageUrl`
- `output_format=pdf` → `component: "FileAttachment"` (already exists in the UI_REGISTRY)

Persist via `knowledge.archiving.archive_conversation_file(conversation, filename, bytes, title=...)`
in the `Conversas/<chat>/` folder; without a conversation, save in `MEDIA_ROOT/canvas_outputs/`
(verify that `/media/` is in the .gitignore so artifacts are not committed).
