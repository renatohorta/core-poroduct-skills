# AG-UI: resolve messages by uuid+id (avoid 500) + carousel HTML→SVG templates

Two reusable techniques found while working on the Copilot chat (crewbotics).

---

## 1. Resolve chat messages by `uuid` + integer `id`, ignoring AG-UI optimistic IDs

### Symptom
The endpoint `/api/v1/chat/conversations/<id>/branches/?message=<id>` (and `/branch-version/`)
returns **500 in a loop** when the AG-UI frontend calls it. In the Daphne log:
```
ValueError: Field 'id' expected a number but got '3dccd053-f23d-4b71-b8e5-c1604a3174fd'.
```
Followed by dozens of `500 172522` for the same endpoint (the frontend retries).

### Root cause
The `ChatMessage.id` is `BigAutoField` (integer), but the `message` the frontend sends can be:
- the message **`uuid`** (the `toThreadMessage` of the `useConversationThreadList.tsx` hook
  uses `id: m.uuid`), or
- the **integer `pk`**, or
- an **optimistic ID still streaming**: `__optimistic__Z0fS1y5`, `msg_29abe6cbe5ab`.

`filter(pk=<uuid_string>)` throws `ValueError` (integer field) → 500.

### Fix (backend)
```python
def _looks_like_valid_message_id(value) -> bool:
    s = str(value).strip()
    if not s:
        return False
    if s.isdigit():
        return True            # integer pk
    try:
        uuid.UUID(s)
        return True            # uuid string
    except (ValueError, TypeError):
        return False           # __optimistic__/msg_ → False

def _resolve_message(conv, msg_id):
    s = str(msg_id).strip()
    if s.isdigit():
        return CM.objects.filter(conversation=conv, id=int(s)).first()
    return CM.objects.filter(conversation=conv, uuid=s).first()
```
Use `_resolve_message` instead of `filter(pk=msg_id)` in the message endpoints. Reject optimistic
IDs early (return `{"branches": []}` / 404 instead of 500).

### Fix (frontend)
The BranchPicker skips optimistic IDs before calling the backend:
```tsx
useEffect(() => {
  if (!msgId) { setBranches([]); return; }
  if (/^(__optimistic__|msg_)/.test(msgId)) { setBranches([]); return; }
  // ... calls chatApi.messageBranches(convId, msgId)
}, [msgId, activeIdRef]);
```

### Tests
- `branches/?message=__optimistic__Z0fS1y5` → `200 {"branches":[]}` (not 500).
- `branches/?message=<root.uuid>` → `200` with the list (the frontend sends uuid, not pk).

---

## 2. Carousel HTML/CSS templates → SVG + resvg-py (no browser)

When the user provides carousel HTML/CSS templates (e.g. a `templates/` folder with
`slide.html`, CSS palette, TTF fonts — typical of Freepik zips) and asks to reimplement
a carousel skill, do **NOT** render HTML→PNG with Playwright/Chromium: there is no
browser on ECS Linux (production). The approved strategy was to port the aesthetic to SVG and
render with `resvg-py`, which accepts `font_files=[]` to use the templates' real fonts.

### Steps
1. **Extract palettes**: `:root { --bg:#CDC4FB; --accent:#7070F0; ... }` from each `slide.html`.
2. **Copy TTF fonts** to `static/<modulo>/fonts/` and build a templates dict:
```python
TEMPLATES = {
    "constellation": {
        "bg": "#CDC4FB", "ink": "#7E7AF5", "card": "#FFFFFF", "accent": "#7070F0",
        "font_heading": "Poppins", "font_body": "Poppins",
        "font_files": ["Poppins-ExtraBold.ttf", "Poppins-Bold.ttf", ...],
    },
    # ...
}
TEMPLATE_NAMES = tuple(TEMPLATES.keys())
```
3. **SVG renderer** (1080×1350) with per-slide layouts (cover, bullets, steps, list, quote,
   pricing, cta), using `font-family` + `font-weight` — resvg-py resolves them via `font_files`.
4. **Convert**:
```python
import resvg_py
png = resvg_py.svg_to_bytes(
    svg_string=<str>,   # NOT bytes
    width=1080, height=1350,
    font_files=<list of absolute TTF paths>,
)
```
5. **Route via provider-agnostic LLM**: `llm_client.complete_json(..., system=SYSTEM_PROMPT)`
   returns `{title, template, slides:[{layout, title, body, eyebrow, items}]}` — the LLM chooses
   the template and the layout of each slide. NEVER import a provider SDK.

### resvg-py pitfalls
- `resvg_py.svg_to_bytes(svg_string=...)` expects `str`, not bytes.
- Without `font_files`/`font_dirs`, it falls back to system fonts and loses the typographic
  identity (Poppins/Montserrat/AbrilFatface become generic Arial).
- Font path: resolve with `Path(__file__).resolve().parents[N] / "static" / ...` —
  the N depends on where the module lives.

### Stable contract
Keep the CarouselCard (`slides: {imageUrl, caption}[]`) and the same skill `name` — that way
the frontend does not need to change; Copilot starts using the new implementation automatically.
Archive each PNG in the knowledge base with `archive_conversation_file()` so the
`CarouselCard` displays the inline preview.
