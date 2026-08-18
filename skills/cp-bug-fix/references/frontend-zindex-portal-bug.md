# Bug de frontend: "nada acontece no back" — conflito de zIndex + Portal

## Sintoma
Usuário clica num botão de ação (ex.: "Excluir definitivamente" num modal de
confirmação) e o request **nunca chega ao backend** — nenhum log, nenhum 4xx/5xx,
"nada acontece". O backend está OK (o endpoint funciona via API/curl).

## Causa raiz típica (React + Radix/Portal)
O modal de confirmação (ex.: Radix `AlertDialog`) usa **Portal** → renderiza no
fim do `<body>`, mas com um `zIndex` baixo (ex.: `z-50`). Se a página tem um
**overlay customizado** com `zIndex` alto (ex.: `9999`), o AlertDialog abre
**atrás** desse overlay. O clique no botão de confirmação cai no overlay
customizado (que tem `onClick` para fechar o modal) → o modal fecha e o request
nunca dispara. Parece "bug no backend", mas é 100% frontend.

## Diagnóstico (ordem)
1. **Confirme que o backend funciona** via API/curl (endpoint + payload). Se
   retorna 2xx/204, o problema é frontend.
2. **Reproduza no browser** e inspecione o DOM: o modal de confirmação está
   visível? O clique chega ao botão certo?
3. **Compare os zIndex**: overlay customizado da página vs. zIndex do
   componente de diálogo (Radix/Portal). Se o diálogo é menor, é o conflito.
4. **Verifique o `onClick` do overlay customizado** — se ele fecha o modal,
   confirma que o clique está caindo ali.

## Fix
Elevar o zIndex do componente de diálogo **acima** do overlay customizado.
Exemplo (Tailwind):
- `AlertDialogContent`: `z-50` → `z-[10000]`
- `AlertDialogOverlay`: `z-50` → `z-[9999]`

## Validação
- Reproduzir no browser: o ConfirmDialog agora aparece por cima; o clique
  dispara o request; o item some.
- Rodar build do frontend (`bun run build`).
- Testes backend do endpoint (se houver) continuam passando.

## Lição geral
Quando o usuário diz "clico e nada acontece no back", **não assuma bug de
backend**. Verifique primeiro se o request realmente sai do frontend (network
tab / logs). Conflitos de zIndex + Portal são causa clássica de clique "engolido"
por um overlay invisível.
