# GrapesJS RTE Debugging — RTE Ativa e Desativa Imediatamente

## Sintoma

Duplo-clique em componente de texto não selecionado → RTE aparece e desaparece imediatamente. Se o componente já está selecionado (1 clique), o duplo-clique funciona.

## Causas Raiz (múltiplas, qualquer uma pode causar)

### 1. `demoteTextContainers` — muda tipo de componente pai

Quando o parser do `grapesjs-preset-webpage` marca containers (section, div, header) como `type: "text"`, o código que rebaixa esses containers para `type: "default"` força uma re-renderização da view do pai. Se o RTE está ativo no filho, a re-renderização do pai destrói o RTE.

**Correção:** Remover `demoteTextContainers` completamente. O benefício (editar texto em containers) é menor que o dano (RTE quebrado).

### 2. `redelegateTextViews` — re-liga handlers de dblclick

`delegateEvents()` re-liga o handler `dblclick` nas views de texto. Se registrado em `canvas:frame:load`, o RTE ativa recarregando o frame, o que dispara `canvas:frame:load`, que re-delega eventos, que faz o RTE interpretar um segundo duplo-clique e se desativar.

**Correção:** Remover `redelegateTextViews` completamente. O GrapesJS gerencia a delegação de eventos internamente após re-renderização.

### 3. Keymap removal em `rte:enable` — `ed.Keymaps.removeAll()`

Remover TODOS os keymaps remove a proteção interna do GrapesJS que impede o RTE de perder foco. O RTE ativa, perde a proteção, e o próximo evento de canvas desativa o RTE.

**Correção:** Remover APENAS keymaps específicos que interferem com edição de texto:
```tsx
const toRemove = [
  "core:copy", "core:paste", "core:cut",
  "core:component-outline", "core:component-delete",
];
for (const id of toRemove) {
  try { ed.Keymaps.remove(id); } catch { /* noop */ }
}
```
Ou, melhor ainda, **remover todo o handler** — o GrapesJS vanilla já funciona.

### 4. Focus handler em `rte:enable` — `double rAF focusEditing`

O handler que foca o elemento em edição com `requestAnimationFrame(() => requestAnimationFrame(focusEditing))` compete com o próprio gerenciamento de foco do RTE. O double rAF atrasa o foco o suficiente para o RTE já ter se estabelecido, e o foco extra causa desativação.

**Correção:** Remover o focus handler. O GrapesJS já foca o elemento quando o RTE ativa.

### 5. Handler `component:selected` — re-seleciona componente em edição

Quando o RTE está ativo e o usuário clica no texto para selecionar/posicionar o cursor, o clique propaga para o canvas e o GrapesJS seleciona o componente sob o cursor. Um handler que re-seleciona o componente em edição interrompe o RTE.

**Correção:** Remover o handler `component:selected`. O GrapesJS já gerencia internamente que o RTE não perde foco.

### 6. `selectNodeContents` + `collapse` no `rte:enable`

O handler que foca o elemento não deve chamar `range.selectNodeContents(el)` + `range.collapse(false)` — isso sobrescreve a seleção de texto que o usuário acabou de fazer com duplo-clique.

**Correção:** Apenas focar o elemento se ele não está ativo, sem mexer na seleção:
```tsx
if (doc.activeElement === el) return;
el.focus();
```

## Regra de Ouro

**NÃO adicionar customizações ao RTE do GrapesJS.** O RTE vanilla do GrapesJS funciona. Toda customização (demoteTextContainers, redelegateTextViews, keymap removal, focus handler, component:selected handler) introduz race conditions que quebram o RTE. Se o problema é que containers estão marcados como `type: "text"`, aceite — o usuário pode editar o container como texto, o que é melhor que o RTE não funcionar.

## Proteção para `ed.getWrapper()`

O método `Editor.getWrapper()` do GrapesJS lança `TypeError: Cannot read properties of undefined (reading 'getWrapper')` quando chamado antes do editor completar a inicialização interna. Proteja com:

```tsx
// Opção 1 — null check:
const wrapper = ed.getWrapper();
if (!wrapper) return;

// Opção 2 — try/catch com retry:
try {
  const wrapper = ed.getWrapper();
  if (!wrapper) return;
  // ... usa wrapper ...
} catch {
  requestAnimationFrame(() => requestAnimationFrame(fn));
}
```
