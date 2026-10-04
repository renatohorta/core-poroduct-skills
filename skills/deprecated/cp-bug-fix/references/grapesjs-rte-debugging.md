# GrapesJS RTE Debugging — RTE Activates and Immediately Deactivates

## Symptom

Double-click on an unselected text component → RTE appears and disappears immediately. If the component is already selected (1 click), the double-click works.

## Root Causes (multiple, any one can cause it)

### 1. `demoteTextContainers` — changes the parent component type

When the `grapesjs-preset-webpage` parser marks containers (section, div, header) as `type: "text"`, the code that demotes these containers to `type: "default"` forces a re-render of the parent's view. If the RTE is active in the child, the parent re-render destroys the RTE.

**Fix:** Remove `demoteTextContainers` completely. The benefit (editing text in containers) is less than the damage (broken RTE).

### 2. `redelegateTextViews` — re-binds dblclick handlers

`delegateEvents()` re-binds the `dblclick` handler on text views. If registered on `canvas:frame:load`, the RTE activates by reloading the frame, which fires `canvas:frame:load`, which re-delegates events, which makes the RTE interpret a second double-click and deactivate itself.

**Fix:** Remove `redelegateTextViews` completely. GrapesJS manages event delegation internally after re-render.

### 3. Keymap removal in `rte:enable` — `ed.Keymaps.removeAll()`

Removing ALL keymaps removes GrapesJS's internal protection that prevents the RTE from losing focus. The RTE activates, loses the protection, and the next canvas event deactivates the RTE.

**Fix:** Remove ONLY the specific keymaps that interfere with text editing:
```tsx
const toRemove = [
  "core:copy", "core:paste", "core:cut",
  "core:component-outline", "core:component-delete",
];
for (const id of toRemove) {
  try { ed.Keymaps.remove(id); } catch { /* noop */ }
}
```
Or, even better, **remove the whole handler** — vanilla GrapesJS already works.

### 4. Focus handler in `rte:enable` — `double rAF focusEditing`

The handler that focuses the element being edited with `requestAnimationFrame(() => requestAnimationFrame(focusEditing))` competes with the RTE's own focus management. The double rAF delays the focus long enough for the RTE to have already established itself, and the extra focus causes deactivation.

**Fix:** Remove the focus handler. GrapesJS already focuses the element when the RTE activates.

### 5. `component:selected` handler — re-selects the component being edited

When the RTE is active and the user clicks the text to select/position the cursor, the click propagates to the canvas and GrapesJS selects the component under the cursor. A handler that re-selects the component being edited interrupts the RTE.

**Fix:** Remove the `component:selected` handler. GrapesJS already manages internally that the RTE does not lose focus.

### 6. `selectNodeContents` + `collapse` in `rte:enable`

The handler that focuses the element must not call `range.selectNodeContents(el)` + `range.collapse(false)` — this overwrites the text selection the user just made with the double-click.

**Fix:** Only focus the element if it is not already active, without touching the selection:
```tsx
if (doc.activeElement === el) return;
el.focus();
```

## Golden Rule

**Do NOT add customizations to the GrapesJS RTE.** The vanilla GrapesJS RTE works. Every customization (demoteTextContainers, redelegateTextViews, keymap removal, focus handler, component:selected handler) introduces race conditions that break the RTE. If the problem is that containers are marked as `type: "text"`, accept it — the user can edit the container as text, which is better than the RTE not working.

## Protection for `ed.getWrapper()`

GrapesJS's `Editor.getWrapper()` method throws `TypeError: Cannot read properties of undefined (reading 'getWrapper')` when called before the editor completes internal initialization. Protect with:

```tsx
// Option 1 — null check:
const wrapper = ed.getWrapper();
if (!wrapper) return;

// Option 2 — try/catch with retry:
try {
  const wrapper = ed.getWrapper();
  if (!wrapper) return;
  // ... uses wrapper ...
} catch {
  requestAnimationFrame(() => requestAnimationFrame(fn));
}
```
