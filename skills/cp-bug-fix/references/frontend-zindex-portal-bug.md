# Frontend bug: "nothing happens in the back" — zIndex + Portal conflict

## Symptom
The user clicks an action button (e.g. "Excluir definitivamente" in a confirmation
modal) and the request **never reaches the backend** — no log, no 4xx/5xx,
"nothing happens". The backend is OK (the endpoint works via API/curl).

## Typical root cause (React + Radix/Portal)
The confirmation modal (e.g. Radix `AlertDialog`) uses **Portal** → it renders at the
end of the `<body>`, but with a low `zIndex` (e.g. `z-50`). If the page has a
**custom overlay** with a high `zIndex` (e.g. `9999`), the AlertDialog opens
**behind** that overlay. The click on the confirmation button lands on the custom
overlay (which has an `onClick` to close the modal) → the modal closes and the request
never fires. It looks like a "backend bug", but it is 100% frontend.

## Diagnosis (in order)
1. **Confirm the backend works** via API/curl (endpoint + payload). If it
   returns 2xx/204, the problem is frontend.
2. **Reproduce in the browser** and inspect the DOM: is the confirmation modal
   visible? Does the click reach the right button?
3. **Compare the zIndex**: the page's custom overlay vs. the zIndex of the
   dialog component (Radix/Portal). If the dialog is lower, it is the conflict.
4. **Check the custom overlay's `onClick`** — if it closes the modal,
   it confirms that the click is landing there.

## Fix
Raise the dialog component's zIndex **above** the custom overlay.
Example (Tailwind):
- `AlertDialogContent`: `z-50` → `z-[10000]`
- `AlertDialogOverlay`: `z-50` → `z-[9999]`

## Validation
- Reproduce in the browser: the ConfirmDialog now appears on top; the click
  fires the request; the item disappears.
- Run the frontend build (`bun run build`).
- Backend tests of the endpoint (if any) still pass.

## General lesson
When the user says "I click and nothing happens in the back", **do not assume a
backend bug**. First verify whether the request actually leaves the frontend (network
tab / logs). zIndex + Portal conflicts are a classic cause of a click "swallowed"
by an invisible overlay.
