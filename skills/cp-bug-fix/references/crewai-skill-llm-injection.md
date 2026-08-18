# CrewAI — Injetar LLM configurado em skills novas + pitfall Python

## Problema
Ao criar um pipeline CrewAI dentro de uma skill (ex.: `canvas_design`), um
`Agent(role=..., goal=..., backstory=...)` SEM `llm=` usa o **default OpenAI do
CrewAI** → `OPENAI_API_KEY is required`, mesmo com Gemini/outro provider
configurado globalmente. Sintoma no log: `crewai.flow.runtime ... OPENAI_API_KEY
is required` + a skill devolve erro ao Copilot.

## Correção (provider-agnostic)
Construir o LLM via `crews.crew_runner_async.build_llm_kwargs` e passar
`llm=crew_llm` em CADA agente:

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

`build_llm_kwargs` já cuida de: prefixo do provider, `is_litellm=True` (evita o
`__new__` do CrewAI cair no SDK nativo OpenAI), `api_key`, `api_base`,
`provider_call_extra`. Nunca hardcodar OpenAI — a config global manda.

## Execução: usar kickoff_async em daemon thread
CrewAI 1.15.5 quebra `kickoff()` síncrono com múltiplas tasks. Em skill que cria
a crew e chama `execute`, rodar `kickoff_async()` numa daemon thread com seu
próprio `asyncio.run()` (nunca inline, senão bloqueia o SSE). Padrão:

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

## Pitfall Python: `UnboundLocalError: cannot access local variable 'settings'`
Se o arquivo faz `from django.conf import settings` no topo E um import local
`from django.conf import settings` DENTRO de um método (ex.: para `MEDIA_ROOT`),
o import local torna `settings` uma variável local no escopo inteiro da função
→ a referência no topo do método (`getattr(settings, "LLM_MODEL", ...)`) falha
com `UnboundLocalError`. Correção: renomear o import local
(`from django.conf import settings as dj_settings`).

## Retorno de artefatos (AG-UI / Generative UI)
- `output_format=png` → `component: "ImageCard"` com `props.imageUrl`
- `output_format=pdf` → `component: "FileAttachment"` (já existe no UI_REGISTRY)

Persistir via `knowledge.archiving.archive_conversation_file(conversation, filename, bytes, title=...)`
na pasta `Conversas/<chat>/`; sem conversa, salvar em `MEDIA_ROOT/canvas_outputs/`
(verificar que `/media/` está no .gitignore para não commitar artefatos).
