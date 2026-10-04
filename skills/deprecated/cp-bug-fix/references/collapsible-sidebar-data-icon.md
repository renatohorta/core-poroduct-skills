# Collapsible sidebar + `data-icon` icon system (crewbotics-front)

Pattern validated in the browser for implementing sidebar collapse and adding icons
in crewbotics-front. Applies to any nav that uses the SVG mask system.

## Central pitfall: CSS does not hide text nodes

The `{n.label}` label inside a `<Link>` renders as **pure text** (it is not an
element). A selector like `.nav-item > :not(.nav-item__ic)` does NOT hide it — CSS
cannot target a loose text node. Symptom: when collapsing, the icon stays but the
text remains visible.

**Fix:** wrap the label in `<span className="nav-item__label">` and hide
`.cb-rail.is-collapsed .nav-item__label { display: none; }`.

## Complete collapse pattern

1. **State in `AppShell`** (`src/components/app-shell.tsx`):
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
2. **Class on the `<aside>`:** `className={`cb-rail${collapsed ? " is-collapsed" : ""}`}`.
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
4. **Toggle button** with `aria-label` alternating "Colapsar menu"/"Expandir menu".

## `data-icon` icon system (SVG mask via CSS)

crewbotics-front does NOT use inline `<svg>` in the nav items. It uses `[data-icon]::before`
with `-webkit-mask: var(--i)` (defined in `src/styles/styles.css`):
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
To add a new icon (e.g. `chevron-left`/`chevron-right`), add in
`src/styles/styles.css`:
```css
[data-icon="chevron-left"] {
  --i: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="..."/></svg>');
}
```
- `fill="currentColor"` + `background: currentColor` → the icon inherits the text color.
- **ALWAYS** check whether the icon already exists before creating it: `grep 'data-icon="<nome>"' src/styles/styles.css`.
- The `data-icon` renders via the `::before` pseudo-element; if a React icon
  component (lucide) is added alongside, TWO overlapping icons appear — use one or the other.

## Browser validation

After the build, test via `browser_console`:
```js
(() => { const rail = document.querySelector('.cb-rail'); const label = rail?.querySelector('.nav-item__label');
return { collapsed: rail?.classList.contains('is-collapsed'), railWidth: rail?.getBoundingClientRect().width,
labelDisplay: label ? getComputedStyle(label).display : 'none', stored: localStorage.getItem('cb-rail-collapsed') }; })()
```
- Collapsed: `railWidth` ≈ 76, `labelDisplay` = "none", `stored` = "1".
- Expanded: `railWidth` ≈ 264, `labelDisplay` = "block", `stored` = "0".
- The state persists between sessions (localStorage) — on reload, the menu opens in the
  saved state.
