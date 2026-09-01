# Resolving messages by id/uuid in chat endpoints (AG-UI)

Real bug pattern found in the branch picker (BUG-20260810). Applies to ANY
endpoint that receives the `id` of a `ChatMessage` (or of an object the frontend sends).

## The problem (two traps joined)

1. **`ChatMessage.id` is `BigAutoField` (integer)**, but the frontend (AG-UI) sends the
   `uuid` in the query param — `toThreadMessage` builds `{ id: m.uuid, ... }`.
   `filter(pk=uuid_string)` throws `ValueError: Field 'id' expected a number` → **500**.
2. **AG-UI uses optimistic IDs** while the message is still being streamed:
   `__optimistic__Z0fS1y5`, `msg_29abe6...`. These are neither uuid nor integer → same 500.

Without a guard, the frontend (BranchPicker querying on every render) enters a **loop of
500 requests** — each optimistic `msg.id` fires a new call. The build does not catch it;
it only appears in a real browser E2E smoke test.

## Fix (backend + frontend)

Backend — a helper that resolves by uuid OR id, and a "looks valid" id guard:

```python
def _looks_like_valid_message_id(value: str) -> bool:
    """Accepts a UUID string OR an integer (pk). Rejects AG-UI optimistic ids."""
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

Usage in the `@action`: if `not _looks_like_valid_message_id(msg_id)` → return an empty list
/ 404 (never 500). Otherwise `base = _resolve_message(conv, msg_id)`.

Frontend — skip optimistic ids before calling (avoids the whole request):

```ts
useEffect(() => {
  if (!msgId) { setBranches([]); return; }
  if (/^(__optimistic__|msg_)/.test(msgId)) { setBranches([]); return; }
  ...
}, [msgId, activeIdRef]);
```

## General lesson

Whenever the frontend passes the `id` of an entity to a chat endpoint:
- Check the real PK type in the model (`ChatMessage._meta.pk`) — it is usually integer
  while the external contract uses `uuid`.
- Accept BOTH (uuid and integer pk) with a `_resolve_*` helper.
- Reject AG-UI optimistic ids with a guard, returning an empty/404 response, NEVER 500.
- Test the real flow in the browser (E2E smoke), not just build/unit — the 500 loop only
  appears with real optimistic ids.
