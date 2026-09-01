# Bug patterns from this session (auto title, SVG browser vs PPTX, authenticated download)

## 1. `is_new` vs "already-existing conversation without a title" when generating the auto title

**Symptom:** conversations created via chat stay with an empty title ("Nova Conversa" forever),
even after several messages. The automatic title generation never runs.

**Root cause:** the frontend creates the empty conversation via `createSession()` (without a title) BEFORE the
user sends the 1st message. When the message reaches the backend, the conversation ALREADY EXISTS →
`is_new=False`. If `generate_session_title` is only fired when `is_new=True`, it
NEVER runs.

**Fix** (`chat/agui/views.py`): `_build_task` returns `needs_title`
(= `is_new` or empty/placeholder `"Nova Conversa"` title); the `post()` calls
`enqueue_task_sync("generate_session_title", ...)` when `needs_title`.

```python
needs_title = is_new or (not conversation.title or conversation.title.strip() == "Nova Conversa")
return task, is_new, str(conversation.id), needs_title
```

See `BUG-20260809-titulo-conversa-nao-gerado`.

## 2. Image path in the SVG: browser vs converter (PPTX)

**Symptom:** carousel/HTML displayed in chat have a broken image (SVG renders only the background),
but the same deck in PPTX is correct.

**Root cause:** `render_slide_svg` converted the media URL (`/media/...`) into a LOCAL disk
file path (`C:\...\media\slide.png`). This is necessary for the DrawingML
converter to embed the binary file in the PPTX. But the SAME SVG is served to the browser in the
CarouselCard / HTML page — and the browser does not resolve a local path → broken image.

**Fix** (`presentations/services/svg_renderer.py`): separate by context with a kwarg.

```python
def _image_ref(url, *, browser):
    if url.startswith(media_url):
        if browser:
            return url                      # /media/... resolves via HTTP
        return str(Path(MEDIA_ROOT) / url[len(media_url):])  # local path for the converter
```

- `browser=True` → SVGs/HTML served to the browser (chat, HTML page).
- `browser=False` (default) → intermediate SVGs that the DrawingML converter reads for PPTX.

## 3. Authenticated download (fetch + blob) instead of `<a href download>` with in-memory token

**Symptom:** the "Download" button does not work (401) on endpoints that require auth.

**Root cause:** hybrid auth — the access token lives only in memory. An `<a href={downloadUrl} download>`
does not send the `Authorization` header → the endpoint responds 401.

**Fix** (frontend): replace the `<a>` with a `<button onClick>` that uses the authenticated helper.

```tsx
const { blob, filename } = await api.downloadBlob(path);  // fetch with Bearer + refresh retry
const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url; a.download = filename || `arquivo.ext`; a.click();
URL.revokeObjectURL(url);
```

**Pitfall:** if the backend `downloadUrl` already includes `/api/v1/`, remove the prefix before
calling `downloadBlob` (it expects a path relative to the `/api/v1` base).

```tsx
const path = downloadUrl.startsWith("/api/v1") ? downloadUrl.slice("/api/v1".length) : downloadUrl;
```

## Test

- Auto title: `tests/chat/test_agui.py::test_agui_generates_title_for_existing_empty_conversation`
  (the task runs in a daemon thread when the TaskQueue has no workers — use a `time.sleep` loop
  waiting for the title to appear before asserting).
