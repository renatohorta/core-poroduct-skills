# AG-UI Chat Thread Switching — Debugging Guide

## The Problem

When clicking a conversation in the sidebar, the REST endpoint `GET /conversations/{uuid}/` is called but the `chat__main` area doesn't render the messages. Or: the endpoint is called **twice** (duplicate requests).

## Architecture

The chat uses `@ag-ui/client` (HttpAgent) + `@assistant-ui/react` (runtime). The flow is:

```
handleClick(uuid)
  → runtime.threads.switchToThread(uuid)
    → adapter.onSwitchToThread(uuid)     [REST fetch of history]
    → agent.threadId = uuid              [HttpAgent setter → POST /chat/agui/ SSE]
```

## Root Causes

### 1. Duplicate REST calls (2x GET /conversations/{uuid}/)

The HttpAgent has a **setter** on `agent.threadId` that fires a fetch when the value changes. If the adapter also does a REST fetch, you get 2 calls.

**Fix:** The adapter sets `agent.threadId` **before** doing its REST fetch. When the runtime later sets `agent.threadId`, the HttpAgent sees the same value and doesn't re-fetch.

```tsx
// In adapter (useConversationThreadList.tsx):
onSwitchToThread: async (threadId: string) => {
  threadIdRef.current = threadId;
  const agent = agentRef.current;
  if (agent) agent.threadId = threadId;  // ← set BEFORE fetch
  setActiveId(threadId);
  const conv = await chatApi.getSession(threadId);
  // ... process messages ...
  return { messages };
},
```

**Requirements:**
- `agentRef` type must be `React.MutableRefObject<any>` (not `{ threadId: string | null }`) — the HttpAgent has a real get/set setter, not a plain property
- `ChatReady` must set `controller.agentRef.current = agent` after creating the agent
- `handleClick` must call **only** `adapter.onSwitchToThread(uuid)` — no `runtime.threads.switchToThread`
- No `useEffect` that syncs `activeId` to `agent.threadId` — the adapter already did it

### 3. Message goes to new conversation instead of current one

The user clicks a conversation, types a message, and the message appears in a **new** conversation instead of the one they selected.

**Root cause — TWO traps:**

1. **`ctrl.activeId` is React state, stale in the closure.** The `runAgent` interceptor in `ChatReady` captures `ctrl.activeId` (React state) in its closure. Since the `HttpAgent` is created **once** via `if (!agentRef.current)`, the closure sees the **initial** value of `activeId` (null). When the user types and sends, the interceptor checks `ctrl.activeId`, sees null, and creates a new conversation.

2. **`base.threadId` is NOT set by the runtime.** The `HttpAgent` constructor generates a random UUID for `this.threadId`. The AG-UI runtime does **not** set `agent.threadId` when switching threads — it only calls the adapter. Using `base.threadId` as a fallback is worse than having no interceptor: the value is always truthy (a fake UUID), so the interceptor passes a non-existent UUID to the backend, which silently creates a new conversation.

```tsx
// ERRADO — ctrl.activeId é React state, stale no closure:
if (!agentRef.current) {
  const base = new HttpAgent({...});
  base.runAgent = async function (params, subscriber) {
    const ctrl = controller;
    if (!ctrl.activeId) {  // ← sempre null! closure capturou valor inicial
      const conv = await chatApi.createSession();
      base.threadId = conv.uuid;
    }
    return origRunAgent(params, subscriber);
  };
}

// ERRADO — base.threadId é UUID aleatório do construtor, sempre truthy:
if (base.threadId) {  // ← sempre truthy! UUID fake, backend cria conversa nova
  params = { ...params, threadId: base.threadId };
  return origRunAgent(params, subscriber);
}
```

**Fix in 3 parts (2 files):**

**1. `useConversationThreadList.tsx` — adapter `onSwitchToThread` sets `agent.threadId` BEFORE the fetch:**

```tsx
onSwitchToThread: async (threadId: string) => {
  threadIdRef.current = threadId;
  // Set agent.threadId BEFORE the fetch — the HttpAgent uses
  // this.threadId in prepareRunAgentInput. Without this, the
  // interceptor sees the constructor-generated UUID (new conversation).
  const agent = agentRef.current;
  if (agent) agent.threadId = threadId;
  setActiveId(threadId);
  const conv = await chatApi.getSession(threadId);
  // ... process messages ...
  return { messages };
},
```

**2. `useConversationThreadList.tsx` — expose `activeIdRef` in the context:**

```tsx
// In ThreadListController type:
activeIdRef: React.MutableRefObject<string | null>;

// In provider:
value={{ adapter, conversations, activeId, activeIdRef, refresh, pendingThreadIdRef, agentRef }}
```

**3. `AguiChatPage.tsx` — interceptor uses `activeIdRef.current` (ref, not state):**

```tsx
const origRunAgent = base.runAgent.bind(base);
base.runAgent = async function (params: any, subscriber: any) {
  const ctrl = controller;
  const pendingId = ctrl.pendingThreadIdRef.current;
  if (pendingId) {
    ctrl.pendingThreadIdRef.current = null;
    base.threadId = pendingId;
    params = { ...params, threadId: pendingId };
    return origRunAgent(params, subscriber);
  }
  // Use activeIdRef.current (ref, not state) to avoid stale closure.
  // The adapter onSwitchToThread already set agent.threadId before the fetch,
  // but the interceptor may be called with params.threadId=null if the
  // runtime was recreated (useAgUiRuntime returns a new object on every render).
  const activeId = ctrl.activeIdRef?.current;
  if (activeId) {
    base.threadId = activeId;
    params = { ...params, threadId: activeId };
    return origRunAgent(params, subscriber);
  }
  // Fallback: no active thread, create or pick the most recent
  const conversations = ctrl.conversations;
  const mostRecent = conversations?.length > 0 ? conversations[0] : null;
  if (mostRecent) {
    await ctrl.adapter.onSwitchToThread!(mostRecent.uuid);
    await ctrl.refresh();
    base.threadId = mostRecent.uuid;
  } else {
    const conv = await chatApi.createSession();
    await ctrl.adapter.onSwitchToThread!(conv.uuid);
    await ctrl.refresh();
    base.threadId = conv.uuid;
  }
  params = { ...params, threadId: base.threadId };
  return origRunAgent(params, subscriber);
};
```

**Never do:**
- Use `ctrl.activeId` inside the `runAgent` interceptor — it's React state, the closure captures the initial value.
- Use `base.threadId` as a fallback — the `HttpAgent` constructor generates a random UUID, always truthy, which the backend interprets as a new conversation.
- Assume the runtime sets `agent.threadId` when switching threads — it does NOT, it only calls the adapter.

The REST fetch returns data but the runtime doesn't display it. This happens when:

**a) `handleClick` calls `adapter.onSwitchToThread` directly** — the adapter returns messages but the runtime doesn't know about them. The runtime needs `runtime.threads.switchToThread` to process the adapter's returned messages.

**Fix:** Use `runtime.threads.switchToThread(uuid)` when available, fall back to `adapter.onSwitchToThread(uuid)`.

**b) `handleClick` sets `agent.threadId` directly** — this triggers `POST /chat/agui/` (SSE) without a message. The backend returns 400 "Nenhuma mensagem do usuário encontrada." The runtime gets an error, not messages.

**Fix:** The backend must handle the case where `POST /chat/agui/` has a `threadId` but no `message`. Return the thread's messages as standard AG-UI events (`TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`).

```python
# In chat/agui/views.py:
if not message and conv_ref:
    conv = await sync_to_async(
        lambda: Conversation.objects.filter(uuid=conv_ref).first()
    )()
    if conv:
        msgs = await sync_to_async(
            lambda: list(ChatMessage.objects.filter(conversation=conv).order_by("created_at"))
        )()
        serializer = ChatMessageSerializer(msgs, many=True)
        frames = []
        for m in serializer.data:
            mid = m["id"]
            frames.append(f"data: {json.dumps({'type': 'TEXT_MESSAGE_START', 'messageId': mid})}\n\n")
            if m.get("content"):
                frames.append(f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': mid, 'delta': m['content']})}\n\n")
            if m.get("uiComponent"):
                frames.append(f"data: {json.dumps({'type': 'TOOL_CALL_START', 'toolCallId': mid, 'toolCallName': m['uiComponent']['component']})}\n\n")
                frames.append(f"data: {json.dumps({'type': 'TOOL_CALL_RESULT', 'toolCallId': mid, 'result': m['uiComponent']})}\n\n")
            frames.append(f"data: {json.dumps({'type': 'TEXT_MESSAGE_END', 'messageId': mid})}\n\n")
        async def stream_switch():
            for f in frames:
                yield f.encode("utf-8")
        return StreamingHttpResponse(stream_switch(), content_type="text/event-stream")
```

## The Working Configuration

After extensive iteration, the configuration that works (1 REST call, messages displayed):

1. **`handleClick`** calls `runtime.threads.switchToThread(uuid)` (or `adapter.onSwitchToThread(uuid)` as fallback)
2. **Adapter** does the REST fetch AND sets `agent.threadId` via `agentRef` BEFORE the fetch
3. **Backend** returns messages via standard AG-UI events when `POST /chat/agui/` has no message
4. **No `useEffect`** syncs `activeId` to `agent.threadId` — `switchToThread` handles it
5. **`agentRef` type** is `React.MutableRefObject<any>` to access the real HttpAgent setter
