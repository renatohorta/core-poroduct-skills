# Presentations: SVG dual-use (media URL vs local path) + authenticated download

Recurring bug patterns in the presentations/carousel flow (Crewbotics).

## 1. The SAME SVG serves two audiences with different image references

`presentations/services/svg_renderer.py` generates the canonical SVG of a slide. The SVG is used
in TWO places that need DIFFERENT image references:

- **DrawingML to PPTX converter** (`pptx_builder.py`): needs the **local disk path**
  (`C:\...\media\slide.png`) to EMBED the binary image in the deck.
- **Browser** (CarouselCard in chat / HTML page): needs the **MEDIA URL**
  (`/media/...`) that the browser resolves via HTTP. A local path (`C:\...`) does NOT resolve →
  broken image (naturalWidth=0).

### Bug
The original `_local_image_path(url)` function ALWAYS converted the media URL into a local
path. The SVG generated with the local path was archived in the knowledge base and served
as `imageUrl` in the CarouselCard → the `<img>` displayed a broken image.

### Fix — `browser` parameter
```python
def _image_ref(url: str | None, *, browser: bool) -> str | None:
    if not url:
        return None
    media_url = settings.MEDIA_URL
    if url.startswith(media_url):
        if browser:
            return url                     # /media/...  → browser resolves
        return str(Path(settings.MEDIA_ROOT) / url[len(media_url):])  # local path → PPTX embeds
    return url.lstrip("/")

def render_slide_svg(slide, theme, aspect_ratio="16:9", *, browser=False) -> str:
    ...
    img_path = _image_ref(image.get("url"), browser=browser)
```

Callers that serve the browser pass `browser=True`:
- `chat/skills/presentation_skill.py` (archives SVGs for the CarouselCard in chat)
- `presentations/services/orchestrator.py` (generates HTML served to the browser)

`pptx_builder.py` keeps the default (`browser=False`, local path to embed).

### Regenerate already-archived SVGs (old conversations)
SVGs generated BEFORE the fix still have the local path in storage. To fix an
existing conversation, regenerate from the presentation's `state`:
```python
p = Presentation.objects.get(uuid="...")
svg = render_slide_svg(slide, p.state["theme"], "1:1", browser=True)
path = os.path.join(settings.MEDIA_ROOT, doc.file.name)
open(path, "w", encoding="utf-8").write(svg)
```

## 2. FileField pitfall: `doc.file.save(nome, ...)` DUPLICATES the path

When `ProductContext.file.name` already contains the subpath (`rag/2026/08/slide.svg`) and
you call `doc.file.save(doc.file.name, content, save=True)`, Django prepends the
`upload_to` again → `rag/2026/08/rag/2026/08/slide.svg`. The file the browser serves
(`/media/rag/2026/08/slide.svg`) keeps the old content.

**Fix:** write directly to the file via `open(doc.file.path, "w")` OR fix the
`file.name` before saving. Always check `doc.file.name` after saving.

## 3. Authenticated download — `<a href>` does NOT send the JWT (in-memory hybrid auth)

When the access token lives only in memory (hybrid auth with httpOnly cookie only for
refresh), an `<a href={downloadUrl} download>` link opens a browser request WITHOUT the
`Authorization` header → the download endpoint responds **401**.

### Symptom
"The card generated the SVGs but the download button failed" — the download opens and returns an error.

### Fix — `api.downloadBlob()` (authenticated fetch → blob → createObjectURL)
`src/lib/api/client.ts` exposes `api.downloadBlob(path)` which:
1. injects `Authorization: Bearer ***
2. on 401 tries refresh once and retries
3. extracts the filename from `Content-Disposition`
4. returns `{ blob, filename }`

In the component (e.g. `CarouselCard.tsx`):
```tsx
const handleDownload = async () => {
  // downloadUrl from the backend already includes /api/v1/; downloadBlob expects a path relative to the base.
  const path = downloadUrl.startsWith("/api/v1") ? downloadUrl.slice("/api/v1".length) : downloadUrl;
  const { blob, filename } = await api.downloadBlob(path);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename || "arquivo.ext";
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
};
// button: <button onClick={handleDownload}> instead of <a href={downloadUrl} download>
```
Normalize the `/api/v1` prefix: `downloadBlob` concatenates `BASE_URL (/api/v1) + path`;
if `downloadUrl` already comes with `/api/v1/`, pass the relative path (strip the prefix).

**Browser verification:** the button must be a `<button>` with `onClick` (not `<a href>`);
clean console (no 401); the button returns from "Baixando..." to its normal state.

## 4. Automatic conversation title NEVER fires when the conversation is created before the 1st prompt

### Bug
The frontend creates the empty conversation via `createSession()` ("New conversation" flow) BEFORE
sending the first message. On the backend, `_build_task` sees the ALREADY EXISTING conversation →
`is_new=False` → `generate_session_title` only ran when `is_new=True` → the conversation
stays with an empty title forever.

### Fix — return `needs_title` (not just `is_new`)
```python
needs_title = is_new or (not conversation.title or conversation.title.strip() == "Nova Conversa")
return task, is_new, str(conversation.id), needs_title
```
And in `post()`: fire the title when `needs_title` (not when `is_new`). Covers the case
of the pre-created empty conversation. Update ALL the tuple unpackers.

### Test pitfall
The title task runs in a **daemon thread** (TaskQueue without workers in tests) that persists
AFTER `refresh_from_db()`. In the test, poll with sleep until the title appears:
```python
for _ in range(20):
    conv.refresh_from_db()
    if conv.title and conv.title != "Nova Conversa": break
    time.sleep(0.2)
```
