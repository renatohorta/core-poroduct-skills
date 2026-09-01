# Debugging "ErrorBoundary" / "Chat indisponível" errors in React

Classic Crewbotics error: the user reports "Chat indisponível — Não foi possível
carregar o chat. Verifique se o servidor está rodando" (the `ChatErrorBoundary` in
`src/routes/chat.tsx` that wraps the `AguiChatPage`).

## Conceptual root cause — RENDER error, not async

The React ErrorBoundary (via `getDerivedStateFromError`/`componentDidCatch`) **only
catches errors thrown during the `render()` and lifecycle methods** of child components.
Errors thrown inside:
- `async function` / `await`
- `onClick`, `onChange`, `addEventListener`
- `.then()` / callbacks
- attachment `send` handlers

...do NOT reach the boundary — they become unhandled promise rejections and do not
crash the screen.

**Therefore:** if the boundary error screen APPEARED, the error is a rendering error. A
`throw new Error(...)` in an async handler you found is a red herring — fixing
it does NOT resolve the boundary (real experience from this session).

## Diagnostic flow that works

1. **Confirm the backend is OK** with a reproduction test before touching the frontend.
   Example (PNG upload in a conversation):
   ```python
   # tests/chat/test_upload_png_chat.py
   import io
   from PIL import Image
   from django.core.files.uploadedfile import SimpleUploadedFile
   from rest_framework.test import APIClient
   # ...
   resp = client.post(f"/api/v1/chat/conversations/{conv.uuid}/upload/",
       {"file": SimpleUploadedFile("foto.png", _png_bytes(), content_type="image/png")},
       format="multipart")
   assert resp.status_code == 201
   assert resp.json()["uiComponent"]["component"] == "FileAttachment"
   ```
   If it returns 201, the problem is 100% frontend.

   **Test pitfall:** `derive_kind()` (in `knowledge/enums.py`) uses the file name's
   EXTENSION. `io.BytesIO` without a name returns `kind=TXT` (not `IMAGE`). Use
   `SimpleUploadedFile("foto.png", ...)` to test a real image upload.

2. **Confirm in the server log** that the request NEVER arrived (e.g. no upload in the
   `daphne.log`). This proves the error is a client-side render error, before any fetch.

3. **Add temporary logging in the boundary** to expose the real error:
   ```tsx
   class ChatErrorBoundary extends Component<{children: ReactNode}, {error: Error | null}> {
     state = { error: null };
     static getDerivedStateFromError(error: Error) { return { error }; }
     componentDidCatch(error: Error, info: unknown) {
       console.error("[ChatErrorBoundary] erro capturado:", error);
       if (typeof window !== "undefined")
         (window as any).__chatBoundaryError = { message: error.message, stack: error.stack };
     }
     // ...
   }
   ```
   Vite dev does hot-reload, so the logging stays active without a rebuild. The user
   reproduces and you read `window.__chatBoundaryError` in the console to find the exact message.

## Native attachment file picker is NOT automatable via DOM

The AG-UI `<ComposerPrimitive.AddAttachment>` dynamically creates an `<input type=file>`
and calls `.click()`, opening a NATIVE browser dialog. It **does not accept programmatic
injection** via `input.files = dt.files` + `dispatchEvent(change)` — the input disappears
from the DOM as soon as the picker opens (`document.querySelector('input[type=file]')` returns null).

To test the attachment flow in an AG-UI chat:
- Do NOT try to automate the file picker (wastes time).
- Use logging in the ErrorBoundary + have the user test manually in the browser.
- Isolate the backend via authenticated curl/multipart:
  ```bash
  # login → token
  curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"email":"x@y.com","password":"..."}'
  # multipart upload with Bearer token
  curl -X POST http://127.0.0.1:8000/api/v1/chat/conversations/<uuid>/upload/ \
    -H "Authorization: Bearer ***" \
    -F "file=@foto.png;type=image/png"
  ```
  (in the Hermes sandbox, `grep`/`where`/`bun` are not on the PATH; use `execute_code` +
  `urllib.request` for login/upload, and for the frontend use bun's absolute path:
  `C:\Users\<user>\AppData\Roaming\npm\bun.cmd`).

## Detail: adding a conversation when there is no active thread (AG-UI attachments)

The attachments adapter (`AguiChatPage.tsx`, `attachments.send` block) originally
did `throw new Error("Nenhuma conversa ativa para upload.")` when
`activeIdRef.current` was null (empty chat state). Although this is NOT the cause of the
ErrorBoundary (it is async), it is a latent bug: attaching a file without an active
conversation broke. Robust fix — create the conversation when there is no active thread,
replicating `sendPrompt`:
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
  // ...builds the attachment return...
}
```
