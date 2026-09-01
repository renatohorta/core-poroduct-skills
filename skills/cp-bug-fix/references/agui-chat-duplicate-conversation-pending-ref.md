# AG-UI — Empty duplicate conversation takes over the sidebar top (pendingThreadIdRef never set)

## Symptom
User reports: "I start chatting, the chat replies, but on refresh the last conversation disappears" — or "the real conversation seems to disappear and an empty one appears at the top of the sidebar".

## Root cause
The `pendingThreadIdRef` was **designed** to prevent conversation duplication on the first message, but it is **never set** in the adapter's `sendPrompt`. The `runAgent` interceptor already reads and clears this ref — but since it is always `null`, the interceptor falls into the fallback of creating a new conversation.

**Broken flow:**
1. `sendPrompt` (AguiChatPage) → `adapter.sendPrompt(prompt)` creates the conversation and sets `activeId`.
2. `runtime.thread.append()` fires the `runAgent` interceptor.
3. The interceptor reads `pendingThreadIdRef.current` (null) → `activeIdRef.current` (still null, since `setActiveId` only reflects on the next render).
4. Falls into the fallback that creates **ANOTHER duplicate (empty) conversation**.

The empty duplicate conversation takes over the sidebar top. On refresh, the real conversation with history seems to "disappear" (the empty duplicate appears as the "last conversation"). Backend log confirms: `GET /api/v1/chat/conversations/<uuid>/ 404` for the conversation the interceptor tried to use.

## Fix
The adapter's `sendPrompt` must set `pendingThreadIdRef.current = conv.uuid` **before** returning:

```tsx
// In the adapter (useConversationThreadList.tsx):
sendPrompt: async (prompt: string) => {
  const conv = await chatApi.createSession();
  // Sets the ref BEFORE returning — the runAgent interceptor reads and clears it.
  // Without this, append() fires runAgent with activeIdRef still null
  // (setActiveId only reflects on the next render) and creates a duplicate conversation.
  pendingThreadIdRef.current = conv.uuid;
  setActiveId(conv.uuid);
  return { threadId: conv.uuid };
},
```

## Validation
- Create a new conversation + send the first message → `convCount` must NOT increase (no duplicate).
- After refresh, the conversation and history remain in the sidebar.
- Verify in the browser (not just `bun run build`).

## Do NOT
- Assume `setActiveId` reflects immediately in `activeIdRef.current` within the same tick — React state only updates on the next render.
- Ignore the existing `pendingThreadIdRef`: it exists precisely to cover the window between `createSession` and the next render. If it is never set, the interceptor falls into the fallback of creating a new conversation.

## Quick diagnosis
- Backend persists correctly (validate via API: new conversation with web_search persisted with 2 messages and appears in the listing) — the bug is almost always in the frontend.
- Backend log: `GET /api/v1/chat/conversations/<uuid>/ 404` = the interceptor used a duplicate/nonexistent conversation UUID.
