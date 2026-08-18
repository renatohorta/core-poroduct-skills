# AG-UI message `id` ↔ Django `pk`/`uuid` resolution (branch picker 500 loop)

## Sintoma
Endpoints do backend que recebem um `?message=<id>` vindo do frontend AG-UI
retornam **500 em loop**. Traceback típico:
```
ValueError: Field 'id' expected a number but got '3dccd053-f23d-4b71-b8e5-c1604a3174fd'.
```
No Daphne log, centenas de linhas `GET .../branches/?message=... 500` em sequência.

## Causa raiz (DUAS camadas)
1. **`ChatMessage.id` é `BigAutoField` (inteiro), mas o front AG-UI envia o `uuid`.**
   O `toThreadMessage` (em `useConversationThreadList.tsx`) monta o `ThreadMessage`
   com `id: m.uuid` (o UUID), não o `m.id` (inteiro). O backend fazia
   `ChatMessage.objects.filter(pk=msg_id)` — passando um UUID string para um campo
   inteiro → `ValueError` → 500.
2. **IDs otimistas do AG-UI.** Enquanto a mensagem está sendo streamada, o runtime
   AG-UI usa ids locais tipo `__optimistic__Z0fS1y5` ou `msg_29abe6cbe5ab`. Esses
   não são UUID nem inteiro → o mesmo `ValueError`.

## Correção (backend, `chat/views.py`)
Helper que aceita UUID **ou** inteiro, e rejeita IDs otimistas:

```python
def _looks_like_valid_message_id(value) -> bool:
    import uuid as _uuid
    s = str(value).strip()
    if not s: return False
    if s.isdigit(): return True          # pk inteiro
    try:
        _uuid.UUID(s); return True        # uuid string
    except (ValueError, TypeError):
        return False                       # otimista/desconhecido

def _resolve_message(conv, msg_id):
    """Resolve ChatMessage por `uuid` (o que o front envia) OU `id` (pk int)."""
    from .models import ChatMessage as CM
    s = str(msg_id).strip()
    if s.isdigit():
        return CM.objects.filter(conversation=conv, id=int(s)).first()
    return CM.objects.filter(conversation=conv, uuid=s).first()
```

Nos `@action` de ViewSet, SEMPRE:
1. Guard de ID válido primeiro (`if not _looks_like_valid_message_id(msg_id): return ...`),
   retornando resposta vazia/404 — **nunca** deixar chegar ao `filter(pk=...)`.
2. Resolver via `_resolve_message(conv, msg_id)`, não `filter(pk=msg_id)`.

## Correção (frontend, `AguiChatPage.tsx` — BranchPicker)
Pular IDs otimistas antes de chamar o backend:
```tsx
useEffect(() => {
  if (!msgId) { setBranches([]); return; }
  if (/^(__optimistic__|msg_)/.test(msgId)) { setBranches([]); return; }
  ...
}, [msgId, activeIdRef]);
```

## Regra geral
Qualquer endpoint do backend que o AG-UI consome por um id de mensagem deve
resolver por **uuid OU pk inteiro**, e nunca assumir que `pk=<uuid>` funciona
(o `pk` do ChatMessage é inteiro, o front envia o uuid). Adicionar teste que
chama o endpoint com o `uuid` (o que o front realmente manda) — o teste com
`root.pk` passa mas esconde o bug de produção, porque o front nunca envia pk.

## Testes
- `test_branches_accepts_uuid_what_frontend_sends` — chama com `root.uuid`, não pk.
- `test_branches_optimistic_id_returns_empty_not_500` — `__optimistic__...` → 200 vazio.
