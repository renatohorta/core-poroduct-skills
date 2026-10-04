# AG-UI Chat Architecture — Reference

## File Map

### Backend (`crewbotics-back/chat/`)

| File | Role |
|------|------|
| `agui/views.py` | SSE endpoint `POST /chat/agui/` + `POST /chat/agui/resume/` |
| `agui/engine_async.py` | `AguiReActEngine` — async wrapper around `WebHermesEngine` |
| `agui/events.py` | SSE event builders (`RUN_STARTED`, `TEXT_MESSAGE_*`, `TOOL_CALL_*`, etc.) |
| `engine.py` | `WebHermesEngine` — sync ReAct loop (system prompt, sliding window, skills) |
| `llm_client.py` | LiteLLM abstraction — `complete`, `stream`, `complete_with_tools`, `astream_with_tools` |
| `models.py` | `Conversation`, `ChatMessage`, `AgentTask`, `ExecutionLog` |
| `tasks_async.py` | `generate_session_title`, `summarize_conversation` |
| `views.py` | `ConversationViewSet` (CRUD), `MessageFeedbackView`, `ConversationUploadView` |
| `skills/` | ~60 skills registered via `@register_skill` decorator |

### Frontend (`crewbotics-front/src/components/copilot/`)

| File | Role |
|------|------|
| `AguiChatPage.tsx` | Main page — `ChatReady` (creates `HttpAgent` + interceptor), `Thread` (messages), `ThreadListSidebar` |
| `useConversationThreadList.tsx` | Adapter + context provider — manages conversations, activeId, thread switching, bootReady |
| `AguiToolUIs.tsx` | `makeAssistantToolUI` registrations for Generative UI components |
| `CrewRunCard.tsx` | `CrewToolFallback` — renders crew cards and Generative UI fallback |

**Removed:** `AguiRuntimeProvider.tsx` (dead code, never imported).

## Known Bug Patterns

### 1. Message goes to new conversation

**Root cause:** Interceptor uses `ctrl.activeId` (React state, stale closure) or `base.threadId` (constructor UUID, always truthy).

**Fix:** Use `ctrl.activeIdRef.current` (ref, always current). Adapter sets `agent.threadId` before fetch.

### 2. Message disappears on send

**Root cause:** `sendPrompt` calls `switchToThread(activeId)` which clears all messages via `core.applyExternalMessages([])`.

**Fix:** Don't call `switchToThread` when already on the active thread. Just do `append()`.

### 3. Title never generated

**Root cause:** `enqueue_task_sync` inside `sync_to_async` (thread pool) — transaction not committed, `DoesNotExist`.

**Fix:** Return `(task, is_new, conv_id)` from `_build_task`, call `enqueue_task_sync` outside `sync_to_async`.

### 4. Duplicate REST calls

**Root cause:** HttpAgent setter on `agent.threadId` fires a fetch when value changes. Adapter + runtime both fetch.

**Fix:** Adapter sets `agent.threadId` BEFORE its own fetch. Runtime sees same value, doesn't re-fetch.

### 5. "Nova conversa" button doesn't clear messages area

**Root cause:** `adapter.onSwitchToNewThread()` creates conversation + updates sidebar but doesn't clear runtime messages.

**Fix:** Prefer `runtime.threads.switchToNewThread()` which calls `core.applyExternalMessages([])` + `core.resetState()`.

### 6. Auto-selected conversation at boot doesn't load messages

**Root cause:** `ThreadListProvider` sets `activeId` but doesn't call `onSwitchToThread` (runtime doesn't exist yet). `ChatReady` creates runtime later but has no trigger to load.

**Fix:** Add `bootReady` state in provider, `useEffect` in `ChatReady` that calls `switchToThread` when both `bootReady` and runtime are ready.

### 7. Test: stream not consumed → assistant message missing

**Root cause:** `StreamingHttpResponse` only persists `ChatMessage` when the stream is fully consumed. Without `async_to_sync(_collect)(resp)`, `_finish()` never runs.

**Fix:** Always consume the stream in tests that check for assistant messages.

### 8. Test: `is_configured` not mocked → stub run instead of LLM

**Root cause:** `AguiReActEngine._run_loop()` checks `llm_client.is_configured()` first. If `False`, calls `_stub_run()` which doesn't use `litellm.acompletion`.

**Fix:** Always mock both `is_configured` and `acompletion` in AG-UI tests.

### 9. Dead code: duplicate HttpAgent implementations

**Root cause:** `AguiChatPage.tsx` and `AguiRuntimeProvider.tsx` both create `HttpAgent` with interceptors. The latter is never imported.

**Fix:** Remove the dead file. Verify by searching for imports before deleting.

### 10. File upload in chat does nothing (attachments adapter empty)

**Symptom:** user clicks "Anexar arquivo" (`ComposerPrimitive.AddAttachment`), picks a file, sends — nothing happens. No error, no upload, no message card. Backend endpoint works fine when hit directly via API (returns 201 with `FileAttachment`).

**Root cause:** `useAgUiRuntime` in `AguiChatPage.tsx` configured `adapters.attachments: {} as any` — an EMPTY adapter. The composer's `AddAttachment` adds the file to the pending list, but on send the attachments adapter has no `send` implementation, so nothing is uploaded. The backend (`ConversationUploadView` + `archive_conversation_file`) is fine — the bug is purely the missing frontend adapter.

**Fix:** implement the `AttachmentAdapter` in `useAgUiRuntime`:
```tsx
attachments: {
  accept: "image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.md,.pptx",
  add: async ({ file }: { file: File }) => ({
    id: `${Date.now()}-${file.name}`,
    type: "file",
    name: file.name,
    contentType: file.type,
    file,
    status: { type: "requires-action", reason: "composer-send" },
  }),
  remove: async () => {},
  send: async (attachment: any) => {
    const convId = controller.activeIdRef?.current;   // ref, not state
    if (!convId) throw new Error("Nenhuma conversa ativa para upload.");
    const resp = await chatUploadApi.uploadFile(convId, attachment.file);
    const ui = resp?.uiComponent;
    return {
      id: attachment.id,
      type: "file",
      name: attachment.file.name,
      contentType: attachment.file.type,
      status: { type: "complete" },
      content: [{ type: "file", data: "", mimeType: attachment.file.type || "application/octet-stream", filename: attachment.file.name }],
      ...(ui ? { uiComponent: ui } : {}),
    };
  },
},
```
Import `chatUploadApi` from `@/lib/api/endpoints` (it wraps the auth token; a raw `fetch` to the upload URL returns 401 because it doesn't inject the token).

**Pitfalls:**
- The `AttachmentAdapter` contract (from `@assistant-ui/core`): `accept: string`, `add({file}) → PendingAttachment`, `remove(attachment)`, `send(attachment) → CompleteAttachment`. `PendingAttachment` has `status: {type:"requires-action", reason:"composer-send"}`; `CompleteAttachment` has `status:{type:"complete"}` and `content: ThreadUserMessagePart[]` (a `file` part with `data`/`mimeType`/`filename`).
- Use `controller.activeIdRef?.current` (ref) for the conversation id — same stale-closure rule as the `runAgent` interceptor.
- The `AssetUploader` Generative UI component is display-only: `GenerativeUIRenderer` renders it with `{...uiPayload.props}` and does NOT pass `onUpload`, so its "Enviar" button is a no-op. The real upload path is the composer's attachments adapter, not `AssetUploader`.
- Verify the backend independently first (multipart POST to `/chat/conversations/<uuid>/upload/` returns 201 + `uiComponent`), so you know the bug is frontend-only.

## Key Architectural Decisions

- **Transport:** SSE AG-UI only (no REST blocking, no polling)
- **Engine:** `AguiReActEngine` (async) wraps `WebHermesEngine` (sync) via `sync_to_async`
- **LLM:** Provider-agnostic via LiteLLM (`chat/llm_client.py`)
- **Background tasks:** In-process `TaskQueue` (asyncio), not Celery
- **ThreadId sync:** Adapter sets `agent.threadId` before fetch; interceptor reads `activeIdRef.current`
- **Boot flow:** `bootReady` state signals runtime to load auto-selected conversation messages
