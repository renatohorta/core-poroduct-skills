# Bug: LLM_MODEL sem prefixo → vertex_ai / ADC (produção)

## Sintoma
Log de produção:
```
LiteLLM completion() model= gemini-2.5-flash; provider = vertex_ai   ← FALHA
LiteLLM completion() model= gemini-2.5-flash; provider = gemini      ← FUNCIONA
google.auth.exceptions.DefaultCredentialsError: Your default credentials were not found.
```
O chat responde mas com ~15s de atraso por chamada (vertex falha → fallback → gemini). O erro é em TODAS as chamadas, inclusive `complete_json` e `astream_with_tools`.

## Causa raiz
O secret `LLM_MODEL` em produção está configurado como **`gemini-2.5-flash` sem o prefixo `gemini/`**. Quando o LiteLLM recebe um modelo sem barra, ele roteia para o provider `vertex_ai`, que exige **Application Default Credentials (ADC/service account)** — que NÃO existem no ECS. O fallback `gemini/gemini-2.5-flash` (com prefixo) usa `provider = gemini` (API key via `GEMINI_API_KEY`) e funciona.

## Fix (hardening no código)
Em `chat/llm_client.py`, adicionar `_normalize_model()` que garante o formato `provider/model` e aplicar em `get_model()`, `_base_kwargs()` e no embedding:

```python
def _normalize_model(model: str) -> str:
    """Garante o formato LiteLLM `provider/model`. Modelo sem barra (ex: gemini-2.5-flash)
    é roteado pelo LiteLLM para vertex_ai (exige ADC), não gemini (API key)."""
    if "/" in model:
        return model
    return f"gemini/{model}"

def get_model() -> str:
    raw = getattr(settings, "LLM_MODEL", "") or "gemini/gemini-2.5-flash"
    return _normalize_model(raw)
```

Também **corrigir o secret `LLM_MODEL` no AWS** para `gemini/gemini-2.5-flash` (o hardening só previne o sintoma; o secret certo é a correção definitiva). Mesmo padrão do bug anterior `gemini-3-flash` inexistente.

## Testes
`tests/chat/test_llm_model_fallback.py` → `ModelNormalizeTests`:
- `_normalize_model("gemini-2.5-flash") == "gemini/gemini-2.5-flash"`
- prefixos explícitos (`ollama_chat/...`, `openai/...`) preservados
- `get_model()` com `LLM_MODEL` sem prefixo normaliza
- `complete()` usa o modelo COM prefixo na chamada ao LiteLLM

---
# Bug: Título automático de conversa nunca é gerado (bug B)

## Sintoma
Conversas criadas via chat ficam com título vazio (mostram "Nova Conversa" na sidebar) mesmo após várias mensagens. O título automático nunca é gerado.

## Causa raiz
O frontend (`AguiChatPage.tsx` → `onSwitchToNewThread` → `createSession()`) cria a conversa **vazia** (sem título) ANTES de enviar a primeira mensagem. Quando a 1ª mensagem chega ao backend (`POST /chat/agui/` → `_build_task`), a conversa **já existe**, então `is_new=False` — e o `generate_session_title` só era disparado quando `is_new=True`. Resultado: a conversa nunca ganha título.

## Fix
Em `chat/agui/views.py`, o `_build_task` retorna `needs_title` (não só `is_new`):

```python
needs_title = is_new or (
    not conversation.title or conversation.title.strip() == "Nova Conversa"
)
return task, is_new, str(conversation.id), needs_title
```
E o `post()` dispara o título quando `needs_title` (não `is_new`). Atualizar o unpacking do caller: `task, is_new, conv_id, needs_title = await sync_to_async(self._build_task)(...)`.

## Teste
`tests/chat/test_agui.py::test_agui_generates_title_for_existing_empty_conversation`:
- cria conversa com `title=""`
- POSTa a 1ª mensagem com `conversationId`
- a task de título roda em daemon thread (TaskQueue sem workers em teste) → **aguardar com loop `for _ in range(20): refresh + sleep(0.2)`** antes de assertar o título
- asserta `conv.title` não vazio e != "Nova Conversa"

## Pitfall: TaskQueue "workers nao rodando" no Daphne
Ao reiniciar o Daphne local e observar o log, tasks de background logam `TaskQueue workers nao rodando — executando task 'generate_session_title' inline`. Isso indica que o lifespan ASGI (que chama `startup()` → `get_queue().start()`) pode não ter disparado. Funciona inline para tasks rápidas (título), mas é GRAVE para tasks longas (`run_crew`) que devem rodar em thread separada — se rodarem inline, travam o SSE. Ao reiniciar o Daphne, confirmar no log `ASGI startup: TaskQueue + Scheduler started`; se não aparecer, o lifespan não rodou e o fluxo de crews pode regredir.
