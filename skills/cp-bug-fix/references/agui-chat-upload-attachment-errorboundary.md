# "Chat indisponível" on attachment upload (AG-UI)

## Quick diagnosis

The "Chat indisponível / Não foi possível carregar o chat" message is NOT a
server error — it is the `ChatErrorBoundary` (in `src/routes/chat.tsx`) catching ANY
exception thrown by the `AguiChatPage`.

1. **Test the backend first.** Write a reproduction test in the
   `tests/chat/test_upload_*.py` pattern (APIClient + `force_authenticate` + `SimpleUploadedFile`
   with `content_type="image/png"` and a name with `.png` — if you use `io.BytesIO` without a name,
   `derive_kind` returns TXT). If the endpoint returns 201 + `FileAttachment`, the bug
   is frontend.
   - Pitfall: the related_name of `ChatMessage.conversation` is `messages`, not
     `chat_messages`.
2. **If the backend is OK, the bug is frontend.** The ErrorBoundary catches the `throw` from the `send`
   of attachments.

## Classic root cause

In the attachments adapter of `AguiChatPage.tsx` (the `send` in
`useAgUiRuntime({ adapters: { attachments } })`), the code did:

```ts
send: async (attachment: any) => {
  const convId = controller.activeIdRef?.current;
  if (!convId) throw new Error("Nenhuma conversa ativa para upload."); // ← fires ErrorBoundary
  ...
}
```

When `activeIdRef.current` is `null` (first interaction, empty state, or after
refresh without a selected conversation), the `throw` propagates to the `ChatErrorBoundary`
→ "Chat indisponível".

The `sendPrompt` of the SAME file already had the correct logic to create a conversation when
there is no active thread — the attachment `send` did not replicate it.

## Fix

In the attachment `send`, replicate the `sendPrompt` logic:

```ts
send: async (attachment: any) => {
  let convId = controller.activeIdRef?.current;
  if (!convId) {
    const conv = await chatApi.createSession(attachment.file.name);
    controller.pendingThreadIdRef.current = conv.uuid;
    await controller.adapter.onSwitchToThread(conv.uuid);
    await controller.refresh();
    convId = conv.uuid;
  }
  const resp = await chatUploadApi.uploadFile(convId, attachment.file);
  ...
}
```

`controller` has `adapter` and `pendingThreadIdRef` exposed in the provider
(`useConversationThreadList`). `chatApi.createSession(title?)` accepts a title.

## Browser test pitfall

The "Anexar arquivo" button (`<ComposerPrimitive.AddAttachment>`, `.chat__attach`)
opens the browser's NATIVE file picker, which is NOT automatable via DOM — the click
via `browser_click` does not create an accessible `input[type=file]` for programmatic
file injection. Do not waste time trying to inject via `DataTransfer` into an
input that does not appear in the DOM.

Validate the fix by:
- Backend test (endpoint returns 201 + FileAttachment).
- `bun run build` (compiles TS without error).
- Ask the user to manually test the attachment in the browser (attach a PNG before
  sending any message — the no-active-conversation scenario).
