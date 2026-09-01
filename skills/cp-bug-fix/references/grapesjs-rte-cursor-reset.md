# GrapesJS RTE — Cursor Reset When Editing Text

## Symptom

User double-clicks a text component → RTE activates → cursor goes to the **start** of the text. Clicking anywhere in the text returns the cursor to the start. Editing is impossible.

## Root Cause

The `notify()` (debounced at 400ms) fires on `component:update`, which is emitted **when the RTE activates**. The `getEditorData()` calls `ed.getHtml()` which serializes the component tree — this causes a canvas re-render that **replaces the DOM** of the element being edited, resetting the cursor to the start.

After the first re-render, any click on the text fires another `component:update` (because GrapesJS detects a selection change), which calls `notify()` again, which serializes and re-renders again — infinite cursor-reset loop.

## Fix

Add `if (ed.getEditing()) return;` in the `setTimeout` callback of `notify()`:

```tsx
let notifyTimer: ReturnType<typeof setTimeout> | null = null;
const notify = () => {
  if (notifyTimer) clearTimeout(notifyTimer);
  notifyTimer = setTimeout(() => {
    // Do NOT save while the RTE is active — ed.getHtml() serializes
    // the component tree and causes a re-render that resets the cursor
    // to the start of the text. The save happens on natural blur (when
    // the user clicks outside the component).
    if (ed.getEditing()) return;
    const data = getEditorData();
    if (data) onChange(data);
  }, 400);
};
```

`ed.getEditing()` returns the component currently being edited (RTE active), or `null`/`undefined` if none. When it returns truthy, the save is skipped.

## Why `ed.getEditing()` works

- `ed.getEditing()` returns the `Component` being edited by the RTE, or `null` if the RTE is not active
- It is a native GrapesJS method, not a customization — it does not introduce race conditions
- The save (onChange) happens naturally on blur (when the user clicks outside the component), which is when `ed.getEditing()` returns to `null`

## Events that fire `component:update` during editing

| Event | When it fires | Cause |
|-------|---------------|-------|
| RTE activates | Double-click | GrapesJS marks the component as `contenteditable` |
| Click on text | During editing | GrapesJS detects a selection change |
| Typing | During editing | Each key fires `component:update` |
| Blur | End of editing | User clicks outside the component |

Without the `ed.getEditing()` guard, all these events call `notify()` → `getEditorData()` → `ed.getHtml()` → re-render → cursor reset.

## File

`src/components/grapesjs-editor.tsx` — the `notify()` function inside the editor initialization `useEffect`.
