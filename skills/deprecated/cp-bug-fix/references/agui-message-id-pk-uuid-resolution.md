# AG-UI message `id` ↔ Django `pk`/`uuid` resolution (branch picker 500 loop)

## Symptom
Backend endpoints that receive a `?message=<id>` coming from the AG-UI frontend
return **500 in a loop**. Typical traceback:
```
ValueError: Field 'id' expected a number but got '3dccd053-f23d-4b71-b8e5-c1604a3174fd'.
```
In the Daphne log, hundreds of `GET .../branches/?message=... 500` lines in sequence.

## Root cause (TWO layers)
1. **`ChatMessage.id` is `BigAutoField` (integer), but the AG-UI frontend sends the `uuid`.**
   The `toThreadMessage` (in `useConversationThreadList.tsx`) builds the `ThreadMessage`
   with `id: m.uuid` (the UUID), not `m.id` (integer). The backend did
   `ChatMessage.objects.filter(pk=msg_id)` — passing a UUID string to an integer
   field → `ValueError` → 500.
2. **AG-UI optimistic IDs.** While the message is being streamed, the AG-UI
   runtime uses local ids like `__optimistic__Z0fS1y5` or `msg_29abe6cbe5ab`. These
   are neither UUID nor integer → the same `ValueError`.

## Fix (backend, `chat/views.py`)
Helper that accepts UUID **or** integer, and rejects optimistic IDs:

```python
def _looks_like_valid_message_id(value) -> bool:
    import uuid as _uuid
    s = str(value).strip()
    if not s: return False
    if s.isdigit(): return True          # integer pk
    try:
        _uuid.UUID(s); return True        # uuid string
    except (ValueError, TypeError):
        return False                       # optimistic/unknown

def _resolve_message(conv, msg_id):
    """Resolve ChatMessage by `uuid` (what the frontend sends) OR `id` (int pk)."""
    from .models import ChatMessage as CM
    s = str(msg_id).strip()
    if s.isdigit():
        return CM.objects.filter(conversation=conv, id=int(s)).first()
    return CM.objects.filter(conversation=conv, uuid=s).first()
```

In the ViewSet `@action`s, ALWAYS:
1. Guard the valid ID first (`if not _looks_like_valid_message_id(msg_id): return ...`),
   returning an empty/404 response — **never** let it reach `filter(pk=...)`.
2. Resolve via `_resolve_message(conv, msg_id)`, not `filter(pk=msg_id)`.

## Fix (frontend, `AguiChatPage.tsx` — BranchPicker)
Skip optimistic IDs before calling the backend:
```tsx
useEffect(() => {
  if (!msgId) { setBranches([]); return; }
  if (/^(__optimistic__|msg_)/.test(msgId)) { setBranches([]); return; }
  ...
}, [msgId, activeIdRef]);
```

## General rule
Any backend endpoint that AG-UI consumes by a message id must
resolve by **uuid OR integer pk**, and never assume that `pk=<uuid>` works
(the ChatMessage `pk` is integer, the frontend sends the uuid). Add a test that
calls the endpoint with the `uuid` (what the frontend actually sends) — the test with
`root.pk` passes but hides the production bug, because the frontend never sends pk.

## Tests
- `test_branches_accepts_uuid_what_frontend_sends` — calls with `root.uuid`, not pk.
- `test_branches_optimistic_id_returns_empty_not_500` — `__optimistic__...` → 200 empty.
