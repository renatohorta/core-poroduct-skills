# AG-UI Chat — Test Patterns for Thread Switching

## The Problem

Tests for the AG-UI chat endpoint (`POST /api/v1/chat/agui/`) have several traps that cause false failures. This guide covers the patterns that work.

## Trap 1: SSE Stream Must Be Consumed

`StreamingHttpResponse` only persists the `ChatMessage` (via `_finish()`) when the stream is **fully consumed**. Without consuming the stream, the assistant's response never gets written to the database.

```python
# WRONG — stream not consumed, _finish() never runs:
resp = _post(client, {"message": "Oi", "conversationId": str(conv.uuid)}, user=user)
assert resp.status_code == 200
msgs = ChatMessage.objects.filter(conversation=conv)
assert msgs.count() == 2  # ← FAILS: only 1 (the user's)

# RIGHT — consumes the stream before checking:
resp = _post(client, {"message": "Oi", "conversationId": str(conv.uuid)}, user=user)
assert resp.status_code == 200
async_to_sync(_collect)(resp)  # ← consumes the stream, _finish() persists the response
msgs = ChatMessage.objects.filter(conversation=conv)
assert msgs.count() == 2  # ← PASS: user + assistant
```

**Helper function:**
```python
async def _collect(response) -> bytes:
    chunks = []
    async for chunk in response:
        chunks.append(chunk)
    return b"".join(chunks)
```

## Trap 2: Mock `is_configured` AND `acompletion`

The `AguiReActEngine._run_loop()` checks `llm_client.is_configured()` first. If it returns `False`, it calls `_stub_run()` which does **not** use `litellm.acompletion`. Mocking only `acompletion` without `is_configured` makes the test pass in isolation but fail in batch (because the stub doesn't persist an assistant message).

```python
# RIGHT — mocks both:
from chat import llm_client
import litellm
monkeypatch.setattr(llm_client, "is_configured", lambda: True)
monkeypatch.setattr(litellm, "acompletion", _fake_acompletion(_text_chunks("OK.")))
```

## Trap 3: `try/finally` Indentation

When adding `setIsLoading(true/false)` to `onSwitchToThread`, the `return { messages }` must be **inside** the `try` block. If it's after the `finally`, the variable `messages` is out of scope (declared with `const` inside `try`).

```typescript
// WRONG — return outside try, messages out of scope:
try {
  const conv = await chatApi.getSession(threadId);
  const messages: ThreadMessage[] = (conv.messages ?? []).map(...);
} finally {
  setIsLoading(false);
}
return { messages };  // ← ReferenceError: messages is not defined

// RIGHT — return inside try:
try {
  const conv = await chatApi.getSession(threadId);
  const messages: ThreadMessage[] = (conv.messages ?? []).map(...);
  return { messages };
} finally {
  setIsLoading(false);
}
```

## Trap 4: `sendPrompt` Must Not Call `switchToThread`

When the user is already on the active thread, `sendPrompt` must **not** call `runtime.threads.switchToThread(activeId)`. The `switchToThread` method calls `core.applyExternalMessages([])` which **clears all current messages** — including partial assistant responses still being streamed.

```typescript
// WRONG — switchToThread clears current messages:
const sendPrompt = useCallback(async (prompt: string) => {
  if (activeId) {
    await runtime.threads.switchToThread(activeId);  // ← clears messages!
    runtime?.thread?.append?.({ role: "user", content: [{ type: "text", text: prompt }] });
  }
}, [...]);

// RIGHT — only appends, no switchToThread:
const sendPrompt = useCallback(async (prompt: string) => {
  if (activeId) {
    runtime?.thread?.append?.({ role: "user", content: [{ type: "text", text: prompt }] });
  } else {
    const conv = await chatApi.createSession();
    await adapter.onSwitchToThread(conv.uuid);
    runtime?.thread?.append?.({ role: "user", content: [{ type: "text", text: prompt }] });
  }
}, [...]);
```

## Trap 5: Check for Dead Code When Finding Duplication

When two files have similar implementations (e.g., `AguiChatPage.tsx` and `AguiRuntimeProvider.tsx` both create `HttpAgent` with an interceptor), check if the second is imported anywhere. If not, it's dead code and should be removed, not maintained.

```bash
grep -r "AguiRuntimeProvider" src/  # if only the file itself matches, it's dead
```

## Trap 6: "Nova conversa" Button Must Use Runtime, Not Just Adapter

When the user clicks "Nova conversa", calling only `adapter.onSwitchToNewThread()` creates the conversation in the backend and updates the sidebar, but **does not clear the current messages** in the runtime. The `chat__msgs` area continues showing the previous conversation's messages.

```typescript
// WRONG — only updates sidebar, does not clear messages:
<button onClick={() => adapter.onSwitchToNewThread()}>

// RIGHT — prefers runtime when available:
<button onClick={() => {
  if (runtime?.threads?.switchToNewThread) {
    runtime.threads.switchToNewThread();  // ← calls core.applyExternalMessages([]) + core.resetState()
  } else {
    adapter.onSwitchToNewThread();
  }
}}>
```

## Trap 7: Auto-Selected Conversation at Boot Doesn't Load Messages

When entering `/chat`, the `ThreadListProvider` auto-selects the most recent conversation (sets `activeId` + `threadIdRef`) but **does not call** `onSwitchToThread` because the runtime doesn't exist yet. `ChatReady` creates the runtime later, but without a trigger, the messages never load.

**Fix in `useConversationThreadList.tsx`:**
```typescript
const [bootReady, setBootReady] = useState(false);

// In the auto-select useEffect:
useEffect(() => {
  if (autoSelectDone.current) return;
  if (conversations.length === 0) return;
  autoSelectDone.current = true;
  const mostRecent = conversations[0];
  if (!mostRecent) return;
  threadIdRef.current = mostRecent.uuid;
  setActiveId(mostRecent.uuid);
  setBootReady(true);  // ← signals that boot is ready
}, [conversations]);
```

**Fix in `AguiChatPage.tsx` (ChatReady):**
```typescript
const bootLoaded = useRef(false);
useEffect(() => {
  if (bootLoaded.current) return;
  if (!controller.bootReady) return;
  const id = controller.activeIdRef?.current;
  if (!id) return;
  bootLoaded.current = true;
  const r = runtimeRef.current;
  if (r?.threads?.switchToThread) {
    r.threads.switchToThread(id);
  }
}, [controller.bootReady, controller.activeIdRef?.current]);
```

**Do NOT:** use `runtime` (state) as the effect dependency — `useAgUiRuntime` returns a NEW object on every render, causing an infinite loop. Use `runtimeRef` (ref).

## Complete Test Template

```python
"""Test: thread switching does not create duplicate conversations."""

import json
import pytest
from asgiref.sync import async_to_sync
from django.test import AsyncClient, override_settings
from accounts.enums import Role, SubStatus
from accounts.models import Organization, User
from accounts.serializers import issue_tokens
from chat.models import ChatMessage, Conversation


class _Delta:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _Choice:
    def __init__(self, delta):
        self.choices = [type("C", (), {"delta": delta})()]


def _text_chunks(*pieces):
    return [_Choice(_Delta(content=p)) for p in pieces]


async def _aiter(chunks):
    for c in chunks:
        yield c


def _fake_acompletion(chunks):
    async def _call(*args, **kwargs):
        return _aiter(chunks)
    return _call


async def _collect(response) -> bytes:
    chunks = []
    async for chunk in response:
        chunks.append(chunk)
    return b"".join(chunks)


@pytest.fixture
def org_user(db):
    org = Organization.objects.create(name="TestOrg", subscription_status=SubStatus.ACTIVE)
    user = User.objects.create_user(
        email="t@t.com", password="x", name="Test", role=Role.PRODUCER, organization=org
    )
    return org, user


def _token(user):
    return issue_tokens(user)["access"]


def _post(client, payload, user=None):
    kwargs = {}
    if user is not None:
        kwargs["headers"] = {"authorization": f"Bearer {_token(user)}"}
    return async_to_sync(client.post)(
        "/api/v1/chat/agui/",
        data=json.dumps(payload),
        content_type="application/json",
        **kwargs,
    )


@pytest.mark.django_db(transaction=True)
@override_settings(LLM_MODEL="gemini/gemini-2.5-flash", LLM_API_KEY="***")
def test_thread_switch_does_not_create_duplicate_conversation(org_user, monkeypatch):
    from chat import llm_client
    import litellm
    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    monkeypatch.setattr(litellm, "acompletion", _fake_acompletion(_text_chunks("OK.")))

    org, user = org_user
    client = AsyncClient()
    conv = Conversation.objects.create(organization=org, user=user, title="A")

    # Send message to conversation A
    resp = _post(client, {"message": "Oi", "conversationId": str(conv.uuid)}, user=user)
    assert resp.status_code == 200
    async_to_sync(_collect)(resp)

    # Verify only 1 conversation exists
    assert Conversation.objects.count() == 1

    # Send another message to conversation A
    resp = _post(client, {"message": "Tudo bem?", "conversationId": str(conv.uuid)}, user=user)
    assert resp.status_code == 200
    async_to_sync(_collect)(resp)

    # Verify still only 1 conversation
    assert Conversation.objects.count() == 1
    # Verify 4 messages (2 user + 2 assistant)
    assert ChatMessage.objects.filter(conversation=conv).count() == 4
```
