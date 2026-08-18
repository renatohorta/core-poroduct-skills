# Resolvendo mensagens por id/uuid em endpoints de chat (AG-UI)

Padrão de bug real encontrado no branch picker (BUG-20260810). Aplica-se a QUALQUER
endpoint que recebe o `id` de uma `ChatMessage` (ou de objeto que o frontend envia).

## O problema (duas armadilhas emendadas)

1. **`ChatMessage.id` é `BigAutoField` (inteiro)**, mas o frontend (AG-UI) envia o
   `uuid` no query param — `toThreadMessage` constrói `{ id: m.uuid, ... }`.
   `filter(pk=uuid_string)` lança `ValueError: Field 'id' expected a number` → **500**.
2. **O AG-UI usa IDs otimistas** enquanto a mensagem ainda está sendo streamada:
   `__optimistic__Z0fS1y5`, `msg_29abe6...`. Esses não são uuid nem inteiro → mesmo 500.

Sem guard, o frontend (BranchPicker consultando a cada render) entra em **loop de
requisições 500** — cada `msg.id` otimista dispara nova chamada. O build não pega;
só aparece em smoke E2E real no browser.

## Correção (backend + frontend)

Backend — helper que resolve por uuid OU id, e um guard de id "parece válido":

```python
def _looks_like_valid_message_id(value: str) -> bool:
    """Aceita UUID string OU inteiro (pk). Rejeita ids otimistas do AG-UI."""
    import uuid as _uuid
    s = str(value).strip()
    if not s:
        return False
    if s.isdigit():
        return True
    try:
        _uuid.UUID(s)
        return True
    except (ValueError, TypeError):
        return False

def _resolve_message(conv, msg_id):
    from .models import ChatMessage as CM
    s = str(msg_id).strip()
    if s.isdigit():
        return CM.objects.filter(conversation=conv, id=int(s)).first()
    return CM.objects.filter(conversation=conv, uuid=s).first()
```

Uso no `@action`: se `not _looks_like_valid_message_id(msg_id)` → retorna lista vazia
/ 404 (nunca 500). Senão `base = _resolve_message(conv, msg_id)`.

Frontend — pular ids otimistas antes de chamar (evita a requisição inteira):

```ts
useEffect(() => {
  if (!msgId) { setBranches([]); return; }
  if (/^(__optimistic__|msg_)/.test(msgId)) { setBranches([]); return; }
  ...
}, [msgId, activeIdRef]);
```

## Lição geral

Sempre que o frontend passa o `id` de uma entidade a um endpoint de chat:
- Confira o tipo real do PK no modelo (`ChatMessage._meta.pk`) — costuma ser inteiro
  enquanto o contrato externo usa `uuid`.
- Aceite os DOIS (uuid e pk inteiro) com um helper `_resolve_*`.
- Rejeite ids otimistas do AG-UI com guard, retornando resposta vazia/404, NUNCA 500.
- Teste o fluxo real no browser (smoke E2E), não só build/unit — o loop de 500 só
  aparece com ids otimistas reais.
