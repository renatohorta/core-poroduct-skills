# Menu lateral colapsável + sistema de ícones `data-icon` (crewbotics-front)

Padrão validado no browser para implementar colapso de sidebar e adicionar ícones
no crewbotics-front. Aplica-se a qualquer nav que use o sistema de máscara SVG.

## Pitfall central: CSS não esconde text nodes

O label `{n.label}` dentro de um `<Link>` renderiza como **texto puro** (não é um
elemento). Um seletor como `.nav-item > :not(.nav-item__ic)` NÃO o esconde — CSS
não consegue mirar um text node solto. Sintoma: ao colapsar, o ícone fica mas o
texto continua visível.

**Correção:** envolver o label em `<span className="nav-item__label">` e esconder
`.cb-rail.is-collapsed .nav-item__label { display: none; }`.

## Padrão completo de colapso

1. **Estado no `AppShell`** (`src/components/app-shell.tsx`):
```tsx
const [collapsed, setCollapsed] = useState<boolean>(() => {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem("cb-rail-collapsed") === "1";
});
const toggleCollapsed = () => {
  setCollapsed((prev) => {
    const next = !prev;
    try { window.localStorage.setItem("cb-rail-collapsed", next ? "1" : "0"); } catch {}
    return next;
  });
};
```
2. **Classe no `<aside>`:** `className={`cb-rail${collapsed ? " is-collapsed" : ""}`}`.
3. **CSS** (`src/styles/crewbotics.css`):
```css
:root { --cb-rail-w: 264px; --cb-rail-w-collapsed: 76px; }
.cb-rail { transition: width 0.2s var(--rn-ease); }
.cb-rail.is-collapsed { width: var(--cb-rail-w-collapsed); padding-left: var(--rn-space-2); padding-right: var(--rn-space-2); }
.cb-rail.is-collapsed .cb-brand__txt,
.cb-rail.is-collapsed .nav-item__label,
.cb-rail.is-collapsed .cb-user__meta,
.cb-rail.is-collapsed .cb-storage { display: none; }
.cb-rail.is-collapsed .nav-item,
.cb-rail.is-collapsed .cb-user { justify-content: center; padding-left: 0; padding-right: 0; }
```
4. **Botão de toggle** com `aria-label` alternando "Colapsar menu"/"Expandir menu".

## Sistema de ícones `data-icon` (máscara SVG via CSS)

O crewbotics-front NÃO usa `<svg>` inline nos nav items. Usa `[data-icon]::before`
com `-webkit-mask: var(--i)` (definido em `src/styles/styles.css`):
```css
[data-icon]::before {
  content: "";
  display: block;
  width: 22px; height: 22px;
  background: currentColor;
  -webkit-mask: var(--i) center/contain no-repeat;
  mask: var(--i) center/contain no-repeat;
}
```
Para adicionar um ícone novo (ex: `chevron-left`/`chevron-right`), adicionar em
`src/styles/styles.css`:
```css
[data-icon="chevron-left"] {
  --i: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="..."/></svg>');
}
```
- `fill="currentColor"` + `background: currentColor` → o ícone herda a cor do texto.
- **SEMPRE** verificar se o ícone já existe antes de criar: `grep 'data-icon="<nome>"' src/styles/styles.css`.
- O `data-icon` renderiza via pseudo-elemento `::before`; se um componente React de
  ícone (lucide) for adicionado junto, aparecem DOIS ícones sobrepostos — usar um ou outro.

## Validação no browser

Após o build, testar via `browser_console`:
```js
(() => { const rail = document.querySelector('.cb-rail'); const label = rail?.querySelector('.nav-item__label');
return { collapsed: rail?.classList.contains('is-collapsed'), railWidth: rail?.getBoundingClientRect().width,
labelDisplay: label ? getComputedStyle(label).display : 'none', stored: localStorage.getItem('cb-rail-collapsed') }; })()
```
- Colapsado: `railWidth` ≈ 76, `labelDisplay` = "none", `stored` = "1".
- Expandido: `railWidth` ≈ 264, `labelDisplay` = "block", `stored` = "0".
- O estado persiste entre sessões (localStorage) — ao recarregar, o menu abre no
  estado salvo.
