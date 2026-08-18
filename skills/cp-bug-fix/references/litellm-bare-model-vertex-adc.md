# LiteLLM roteia modelo "pelado" para vertex_ai → DefaultCredentialsError

## Sintoma (produção ECS)
O chat responde, mas com ~15s de atraso por chamada. Log revelador — o MESMO
modelo resolve para dois providers diferentes:

```
LiteLLM completion() model= gemini-2.5-flash; provider = vertex_ai   ← FALHA (ADC)
LiteLLM completion() model= gemini-2.5-flash; provider = gemini      ← FUNCIONA (API key)
```

`provider = vertex_ai` → `google.auth.exceptions.DefaultCredentialsError: Your
default credentials were not found`. O ECS não tem ADC/service account.

## Causa raiz
O secret `LLM_MODEL` em produção está configurado **sem o prefixo `provider/`**
(ex.: `gemini-2.5-flash` em vez de `gemini/gemini-2.5-flash`). Quando o LiteLLM
recebe um modelo sem barra, ele assume `vertex_ai` (que exige ADC), não `gemini`
(que usa `GEMINI_API_KEY`). O fallback `gemini/gemini-2.5-flash` (com prefixo)
usa API key e funciona — daí o "funciona mas lento".

## Fix (hardening no código, `chat/llm_client.py`)
Normalizar o modelo para `provider/model` antes de passar ao LiteLLM:

```python
def _normalize_model(model: str) -> str:
    """Sem barra → prepend 'gemini/'. Sem isso o LiteLLM roteia p/ vertex_ai."""
    if "/" in model:
        return model
    return f"gemini/{model}"
```

Aplicar em:
- `get_model()` — `_normalize_model(getattr(settings, "LLM_MODEL", ...) or ...)`
- `_base_kwargs()` — `_normalize_model(model or get_model())` (ponto central onde
  o modelo chega ao `litellm.completion`)
- embedding — `_normalize_model(model or getattr(settings, "EMBEDDING_MODEL", ...))`

O caminho das crews já protege: `crew_runner_async._resolve_litellm_model()` usa
`llm_client.get_model()` (já normalizado) para modelos "pelados" da crew.

## Ação em produção (não só código)
O hardening previne o sintoma, mas o **secret `LLM_MODEL` no AWS ainda está
errado**. Corrigir para `gemini/gemini-2.5-flash`. Mesmo padrão do bug anterior
(`gemini-3-flash` inexistente) — config de produção sempre vem de secrets AWS,
não do código.

## Testes
`tests/chat/test_llm_model_fallback.py` → `ModelNormalizeTests`:
- bare model ganha prefixo (`gemini-2.5-flash` → `gemini/gemini-2.5-flash`)
- prefixo explícito preservado (`openai/gpt-4o-mini`, `ollama_chat/...`)
- `get_model()` com `LLM_MODEL` sem prefixo retorna com prefixo
- `litellm.completion` recebe o modelo COM prefixo (mock `call_args.kwargs["model"]`)
