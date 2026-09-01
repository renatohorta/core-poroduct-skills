# SVG→PNG with real fonts via resvg-py (no browser, ECS-safe)

When you need to render carousel/post templates (HTML/CSS with fonts like
Poppins, Montserrat, AbrilFatface) to PNG **without depending on Chrome/Edge/Playwright** —
essential because production runs on ECS Linux without a browser — use **resvg-py**, which accepts
`font_files`/`font_dirs` to embed the real fonts in the SVG rendering.

## API

```python
import resvg_py
png_bytes = resvg_py.svg_to_bytes(
    svg_string=svg,          # str (NOT bytes)
    width=1080, height=1350,
    font_files=[...abs paths .ttf/.otf...],   # custom template fonts
)
```

- `svg_string` accepts `str` (not bytes).
- `font_files` accepts a list of absolute `.ttf`/`.otf` paths. The text in the SVG
  uses `font-family="Poppins"` etc. and resvg resolves it from the provided files.
- Fonts that are not passed → resvg's built-in fallback (text still renders, but
  without the brand typography). Pass ALL the template fonts.

## Why this works in production
- resvg-py is a Rust binary wheel — **no native lib, no browser**. Runs on Windows and
  ECS Linux without a Dockerfile change.
- Rejected alternatives: cairosvg / svglib+reportlab require the native C libcairo;
  Playwright/Chromium do not exist in a Linux container and `channel="chrome"` only works
  on Windows.

## Pattern for porting an HTML/CSS template → SVG
Instead of automatically converting the HTML (inviable for multi-layout templates),
extract the **palette** (`:root { --bg, --ink, --accent ... }`), the **fonts**
(`font-family`) and the **layouts** (`data-layout="cover|intro|list|quote|cta"`) and
reimplement them as 1080×1350 SVG generators. Typical Freepik/sketch templates:
constellation, coral, fashion, pet, sketch, swoosh, sage, oliva, bebas. Let the LLM
select the template/layout via `llm_client.complete_json` (provider-agnostic).

## Visual validation without vision
After generating the PNG, confirm the design in the browser by opening the file and reading
`distinctColors` via canvas — a real slide has 29-400+ colors (background + text +
decoration); an "empty" PNG would have 1-2. This confirms that text/accents rendered.

## Keep the CarouselCard contract
When reimplementing a carousel skill, the frontend `CarouselCard` is already navigable
when `slides.length > 1` (‹ › arrows + n/N counter + dots). Ensure:
1. **Always 5-10 slides** — force it in the system prompt AND validate in `execute`
   (`if len(slides) < 5: return {"error": ...}`) to never generate a card without navigation.
2. **Working download** — return real `downloadUrl`/`pngsUrl`. For a carousel,
   add an endpoint that generates the ZIP of the archived slides:
   - Filter the `ProductContext` by the **file name** (`os.path.basename(doc.file.name).startswith("slide-")`),
     NOT by the title (the title is the carousel's, e.g. "7 Dicas... 1").
   - Use `zipfile` + `FileResponse(io.BytesIO(...), as_attachment=True)`; in the test read
     `b"".join(resp.streaming_content)` (FileResponse has no `.content`).
   - `Content-Type` can be `application/x-zip-compressed` (not only `application/zip`).

## Find-and-replace pitfall: "stolen" decorator
Inserting a new method before an existing one using `def <nome>` as the anchor can make
the new method inherit the neighbor's decorator and the neighbor lose its `@action`. See
SKILL.md "SEMPRE verificar se o find-and-replace não 'roubou' o decorator".
