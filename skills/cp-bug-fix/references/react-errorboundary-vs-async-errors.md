# Debugando erro de "ErrorBoundary" / "Chat indisponível" em React

Erro clássico do Crewbotics: o usuário reporta "Chat indisponível — Não foi possível
carregar o chat. Verifique se o servidor está rodando" (o `ChatErrorBoundary` em
`src/routes/chat.tsx` que envolve o `AguiChatPage`).

## Causa raiz conceitual — erro de RENDER, não async

O React ErrorBoundary (via `getDerivedStateFromError`/`componentDidCatch`) **só captura
erros lançados durante o `render()` e métodos de ciclo de vida** de componentes filhos.
Erros lançados dentro de:
- `async function` / `await`
- `onClick`, `onChange`, `addEventListener`
- `.then()` / callbacks
- handlers de `send` de attachments

...NÃO chegam ao boundary — viram unhandled promise rejection e não derrubam a tela.

**Portanto:** se a tela de erro do boundary APARECEU, o erro é de renderização. Um
`throw new Error(...)` num handler async que você encontrou é uma pista falsa — corrigir
ele NÃO resolve o boundary (experiência real desta sessão).

## Fluxo de diagnóstico que funciona

1. **Confirme que o backend está OK** com um teste de reprodução antes de mexer no frontend.
   Exemplo (upload de PNG numa conversa):
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
   Se devolve 201, o problema é 100% frontend.

   **Pitfall do teste:** `derive_kind()` (em `knowledge/enums.py`) usa a EXTENSÃO do nome
   do arquivo. `io.BytesIO` sem nome retorna `kind=TXT` (não `IMAGE`). Use
   `SimpleUploadedFile("foto.png", ...)` para testar upload de imagem de verdade.

2. **Confirme no log do servidor** que a requisição NUNCA chegou (ex.: nenhum upload no
   `daphne.log`). Isso prova que o erro é de render no cliente, antes de qualquer fetch.

3. **Adicione logging temporário no boundary** para expor o erro real:
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
   O Vite dev faz hot-reload, então o logging fica ativo sem rebuild. O usuário reproduz
   e você lê `window.__chatBoundaryError` no console para achar a mensagem exata.

## File picker nativo de anexo NÃO é automatizável via DOM

O `<ComposerPrimitive.AddAttachment>` do AG-UI cria dinamicamente um `<input type=file>`
e chama `.click()`, abrindo um dialog NATIVO do browser. Ele **não aceita injeção
programática** via `input.files = dt.files` + `dispatchEvent(change)` — o input some do
DOM assim que o picker abre (`document.querySelector('input[type=file]')` retorna null).

Para testar o fluxo de anexo num chat AG-UI:
- NÃO tente automatizar o file picker (perde tempo).
- Use logging no ErrorBoundary + faça o usuário testar manualmente no browser.
- Isole o backend via curl/multipart autenticado:
  ```bash
  # login → token
  curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"email":"x@y.com","password":"..."}'
  # upload multipart com Bearer token
  curl -X POST http://127.0.0.1:8000/api/v1/chat/conversations/<uuid>/upload/ \
    -H "Authorization: Bearer <token>" \
    -F "file=@foto.png;type=image/png"
  ```
  (no sandbox do Hermes, `grep`/`where`/`bun` não existem no PATH; use `execute_code` +
  `urllib.request` para login/upload, e para o frontend use o caminho absoluto do bun:
  `C:\Users\<user>\AppData\Roaming\npm\bun.cmd`).

## Detalhe: adicionar conversa quando não há thread ativa (AG-UI attachments)

O adapter de attachments (`AguiChatPage.tsx`, bloco `attachments.send`) originalmente
fazia `throw new Error("Nenhuma conversa ativa para upload.")` quando
`activeIdRef.current` era null (estado vazio do chat). Embora isso NÃO seja a causa do
ErrorBoundary (é async), é um bug latente: anexar arquivo sem conversa ativa quebrava.
Correção robusta — criar a conversa quando não há thread ativa, replicando `sendPrompt`:
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
  // ...monta o retorno do attachment...
}
```
