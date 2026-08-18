# AG-UI — Conversa duplicada vazia toma o topo da sidebar (pendingThreadIdRef nunca setado)

## Sintoma
Usuário reporta: "começo a conversar, o chat responde, mas ao dar refresh a última conversa some" — ou "a conversa real parece sumir e aparece uma vazia no topo da sidebar".

## Causa raiz
O `pendingThreadIdRef` foi **projetado** para evitar duplicação de conversa na primeira mensagem, mas **nunca é setado** no `sendPrompt` do adapter. O interceptor `runAgent` já lê e limpa esse ref — mas como ele fica sempre `null`, o interceptor cai no fallback de criar conversa nova.

**Fluxo quebrado:**
1. `sendPrompt` (AguiChatPage) → `adapter.sendPrompt(prompt)` cria a conversa e seta `activeId`.
2. `runtime.thread.append()` dispara o interceptor `runAgent`.
3. O interceptor lê `pendingThreadIdRef.current` (null) → `activeIdRef.current` (ainda null, pois `setActiveId` só reflete no próximo render).
4. Cai no fallback que cria **OUTRA conversa duplicada** (vazia).

A conversa duplicada vazia toma o topo da sidebar. Ao dar refresh, a conversa real com o histórico parece "sumir" (a duplicata vazia aparece como "última conversa"). Log do backend confirma: `GET /api/v1/chat/conversations/<uuid>/ 404` para a conversa que o interceptor tentou usar.

## Correção
O `sendPrompt` do adapter deve setar `pendingThreadIdRef.current = conv.uuid` **antes** de retornar:

```tsx
// No adapter (useConversationThreadList.tsx):
sendPrompt: async (prompt: string) => {
  const conv = await chatApi.createSession();
  // Seta o ref ANTES de retornar — o interceptor runAgent lê e limpa.
  // Sem isso, o append() dispara o runAgent com activeIdRef ainda null
  // (setActiveId só reflete no próximo render) e cria conversa duplicada.
  pendingThreadIdRef.current = conv.uuid;
  setActiveId(conv.uuid);
  return { threadId: conv.uuid };
},
```

## Validação
- Criar conversa nova + enviar primeira mensagem → `convCount` NÃO deve aumentar (sem duplicata).
- Após refresh, a conversa e o histórico continuam na sidebar.
- Verificar no browser (não só `bun run build`).

## NÃO fazer
- Assumir que `setActiveId` reflete imediatamente no `activeIdRef.current` dentro do mesmo tick — React state só atualiza no próximo render.
- Ignorar o `pendingThreadIdRef` existente: ele existe exatamente para cobrir a janela entre `createSession` e o próximo render. Se nunca é setado, o interceptor cai no fallback de criar conversa nova.

## Diagnóstico rápido
- Backend persiste corretamente (validar via API: conversa nova com web_search persistida com 2 mensagens e aparece na listagem) — o bug é quase sempre no frontend.
- Log do backend: `GET /api/v1/chat/conversations/<uuid>/ 404` = o interceptor usou um UUID de conversa duplicada/inexistente.
