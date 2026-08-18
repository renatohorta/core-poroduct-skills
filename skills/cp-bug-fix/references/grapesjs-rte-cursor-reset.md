# GrapesJS RTE — Cursor Reset ao Editar Texto

## Sintoma

Usuário dá duplo-clique em componente de texto → RTE ativa → cursor vai para o **início** do texto. Clicar em qualquer posição do texto volta o cursor pro início. Editar é impossível.

## Causa Raiz

O `notify()` (debounced a 400ms) dispara em `component:update`, que é emitido **quando o RTE ativa**. O `getEditorData()` chama `ed.getHtml()` que serializa a árvore de componentes — isso causa um re-render do canvas que **substitui o DOM** do elemento em edição, resetando o cursor para o início.

Depois do primeiro re-render, qualquer clique no texto dispara outro `component:update` (porque o GrapesJS detecta mudança de seleção), que chama `notify()` de novo, que serializa e re-renderiza de novo — loop infinito de cursor reset.

## Correção

Adicionar `if (ed.getEditing()) return;` no callback do `setTimeout` do `notify()`:

```tsx
let notifyTimer: ReturnType<typeof setTimeout> | null = null;
const notify = () => {
  if (notifyTimer) clearTimeout(notifyTimer);
  notifyTimer = setTimeout(() => {
    // NÃO salvar enquanto o RTE estiver ativo — ed.getHtml() serializa
    // a árvore de componentes e causa re-render que reseta o cursor
    // para o início do texto. O save acontece no blur natural (quando
    // o usuário clica fora do componente).
    if (ed.getEditing()) return;
    const data = getEditorData();
    if (data) onChange(data);
  }, 400);
};
```

`ed.getEditing()` retorna o componente atualmente em edição (RTE ativo), ou `null`/`undefined` se nenhum. Quando retorna truthy, o save é pulado.

## Por que `ed.getEditing()` funciona

- `ed.getEditing()` retorna o `Component` sendo editado pelo RTE, ou `null` se o RTE não está ativo
- É um método nativo do GrapesJS, não uma customização — não introduz race conditions
- O save (onChange) acontece naturalmente no blur (quando o usuário clica fora do componente), que é quando `ed.getEditing()` volta a ser `null`

## Eventos que disparam `component:update` durante edição

| Evento | Quando dispara | Causa |
|--------|---------------|-------|
| RTE ativa | Duplo-clique | GrapesJS marca componente como `contenteditable` |
| Clique no texto | Durante edição | GrapesJS detecta mudança de seleção |
| Digitação | Durante edição | Cada tecla dispara `component:update` |
| Blur | Fim da edição | Usuário clica fora do componente |

Sem o guard `ed.getEditing()`, todos esses eventos chamam `notify()` → `getEditorData()` → `ed.getHtml()` → re-render → cursor reset.

## Arquivo

`src/components/grapesjs-editor.tsx` — função `notify()` dentro do `useEffect` de inicialização do editor.
