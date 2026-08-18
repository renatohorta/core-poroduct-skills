# "Chat indisponível" no upload de anexo (AG-UI)

## Diagnóstico rápido

A mensagem "Chat indisponível / Não foi possível carregar o chat" NÃO é erro de
servidor — é o `ChatErrorBoundary` (em `src/routes/chat.tsx`) capturando QUALQUER
exceção lançada pelo `AguiChatPage`.

1. **Teste o backend primeiro.** Escreva um teste de reprodução no padrão
   `tests/chat/test_upload_*.py` (APIClient + `force_authenticate` + `SimpleUploadedFile`
   com `content_type="image/png"` e nome com `.png` — se usar `io.BytesIO` sem nome,
   `derive_kind` retorna TXT). Se o endpoint devolve 201 + `FileAttachment`, o bug
   é frontend.
   - Pitfall: o related_name de `ChatMessage.conversation` é `messages`, não
     `chat_messages`.
2. **Se backend OK, o bug é frontend.** O ErrorBoundary captura o `throw` do `send`
   de attachments.

## Causa raiz clássica

No adapter de attachments do `AguiChatPage.tsx` (o `send` em
`useAgUiRuntime({ adapters: { attachments } })`), o código fazia:

```ts
send: async (attachment: any) => {
  const convId = controller.activeIdRef?.current;
  if (!convId) throw new Error("Nenhuma conversa ativa para upload."); // ← dispara ErrorBoundary
  ...
}
```

Quando `activeIdRef.current` é `null` (primeira interação, estado vazio, ou após
refresh sem conversa selecionada), o `throw` propaga para o `ChatErrorBoundary`
→ "Chat indisponível".

O `sendPrompt` do MESMO arquivo já tinha a lógica correta de criar conversa quando
não há thread ativa — o `send` de attachments não replicava.

## Correção

No `send` de attachments, replicar a lógica do `sendPrompt`:

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

`controller` tem `adapter` e `pendingThreadIdRef` expostos no provider
(`useConversationThreadList`). `chatApi.createSession(title?)` aceita título.

## Pitfall de teste no browser

O botão "Anexar arquivo" (`<ComposerPrimitive.AddAttachment>`, `.chat__attach`)
abre o file picker NATIVO do browser, que NÃO é automatizável via DOM — o clique
via `browser_click` não cria um `input[type=file]` acessível para injeção
programática de arquivo. Não perca tempo tentando injetar via `DataTransfer` num
input que não aparece no DOM.

Valide o fix por:
- Teste de backend (endpoint devolve 201 + FileAttachment).
- `bun run build` (compila TS sem erro).
- Pedir ao usuário para testar manualmente o anexo no browser (anexar PNG antes
  de enviar qualquer mensagem — o cenário sem conversa ativa).
