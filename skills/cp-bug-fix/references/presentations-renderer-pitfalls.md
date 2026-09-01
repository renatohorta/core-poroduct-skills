# Crewbotics Presentations Renderer — pitfalls & root-cause of "apresentações feias"

Current architecture (`presentations/services/`):
- `agent_service.py::process_presentation_prompt` — LLM generates/edits the `state` JSON
  (`{title, theme, slides}`). Theme = 4 loose colors (`background_color`,
  `text_color`, `accent_color`, `font_family`) + layout per slide.
- `svg_renderer.py::render_slide_svg` — draws the slide as a minimalist SVG
  (rect + text + bullets), positioned by fixed x/y coordinates. This SVG is
  flattened to editable DrawingML in the PPTX.
- `orchestrator.py` — assembles html/pptx/svg.

## Why presentations come out ugly (architectural, not the LLM)
The renderer was designed for PPTX conversion (DrawingML only understands basic
shapes), so it does not support what makes a carousel beautiful:
- **Typography**: everything `Arial`, uppercase, one size per type. No Google font
  pairs (e.g. Playfair Display + DM Sans), no size scale, no
  hierarchy. `_wrap()` breaks by char count, does not measure the font.
- **Color**: 4 loose colors, no system derived from 1 brand color (BRAND_PRIMARY/
  LIGHT/DARK + LIGHT_BG/DARK_BG). No light/dark alternation between slides.
- **Components**: only 5 layouts (title_hero, standard_bullets, two_column_*,
  full_image_background), each = title + bullets + one `accent_bar` rectangle.
  No progress bar, CTA button, feature list, numbered steps, pills, logo lockup.
- **Image**: black 55% scrim overlay over the image → loses the visual.
- **Sequence**: free layout per slide; no narrative arc (hook → problem →
  solution → features → how-to → CTA), no rhythm.

**Fix path (if asked to turbocharge):** introduce a rich
HTML/CSS renderer (like the `instagram-carousel` skill) for `html`/`svg`/`carrossel`,
keeping the simplified SVG only for the PPTX path. Concretely: (1) derive
6 color tokens + a Google font pair from the primary color; (2) rich
components (progress bar, swipe arrow, feature list, numbered steps, CTA, pills, logo);
(3) `agent_service` prompt to structure 7 slides with an arc and alternate backgrounds;
(4) HTML renderer for preview/export.

## Bug 1 — SVGs did not render in chat/carousel (broken image)
`_local_image_path()` converted the MEDIA URL (`/media/...`) into a LOCAL file
path (`C:\...\slide.png`). Necessary for the DrawingML converter to embed
the image in the PPTX, BUT the same SVG served to the browser in the CarouselCard uses that
path → the browser does not resolve → broken image.

**Fix:** `_image_ref(url, *, browser)`. `browser=True` uses `/media/...`;
`browser=False` keeps the local path (for PPTX). Callers that generate SVG/HTML
served to the browser pass `browser=True`:
- `chat/skills/presentation_skill.py` (card SVGs in chat)
- `presentations/services/orchestrator.py` (HTML served to the browser)
- `pptx_builder.py` keeps the default False.
Regenerate old SVGs (already archived in the knowledge base) by overwriting the
file in MEDIA_ROOT at the correct path. **Pitfall:** `doc.file.save(name, ...)`
with the same `name` duplicates the path (`rag/.../rag/...`); use `open(real_path, "w")`
directly and fix `doc.file.name` to `rag/YYYY/MM/<basename>`.

## Bug 2 — Download of the generated file returned 401
The CarouselCard used `<a href={downloadUrl} download>`. The access token lives only in
memory (hybrid auth) → a direct link does not send the Authorization header → 401.

**Fix:** use `api.downloadBlob(path)` (authenticated Bearer fetch + refresh
retry) → blob → `URL.createObjectURL` → `<a>.click()`. Normalize the prefix:
the backend `downloadUrl` already comes with `/api/v1/`; `downloadBlob` expects a path
relative to the base, so remove the prefix before (`startsWith("/api/v1") ? slice(5)`).
The broken already-absolute downloadUrl was `/api/v1/api/v1/...`.

## Bug 3 — Carousel PNG export fails with `NotImplementedError` on Windows

`playwright_export.py::export_carousel_pngs` runs `asyncio.run(_run())` to
launch Chromium and capture the slides. On Windows, if the active event loop is a
**Selector** loop (not Proactor), `asyncio.subprocess_exec` raises
`NotImplementedError` in `_make_subprocess_transport` — Playwright cannot
launch the Chromium subprocess. Symptom in the log:

```
Task exception was never retrieved
... asyncio/base_events.py:528 in _make_subprocess_transport
    raise NotImplementedError
ERROR Falha no export PNG do carrossel:
```

**Root cause:** Playwright async requires a **Proactor** event loop on Windows
(which supports subprocess). If the current loop is Selector (or the `asyncio.run` inherits
a wrong policy), the browser launch breaks.

**Fix:** ensure the Proactor policy before `asyncio.run` in the export:
```python
import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
return asyncio.run(_run())
```
**Additional pitfall:** the export is **non-blocking** by design — `_build_carousel`
in `orchestrator.py` wraps `export_carousel_pngs` in try/except and continues with only the
HTML if the PNG fails. So a Playwright error does not bring down the carousel
generation, but the user is left without the 1080×1350 PNGs. Check the log
(`Falha no export PNG do carrossel`) when reporting "carousel without PNG download".
Also confirm that Chromium is installed (`playwright install chromium`) —
`Executable doesn't exist at ...ms-playwright\chromium_headless_shell-...` is a
separate missing-browser error, not the event loop bug.
