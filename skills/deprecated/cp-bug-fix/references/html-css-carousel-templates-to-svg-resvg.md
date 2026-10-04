# Port carousel HTML/CSS templates → SVG renderer + resvg-py (no browser)

**When:** you receive carousel HTML/CSS templates (e.g. Freepik/sketch/swoosh from the
`universal-carousel-template-creator` skill, or any package of `slide.html` with
`{{TITLE}} {{BODY}} {{LAYOUT}} {{SLIDE_NUM}}` placeholders) and need to generate 1080×1350 PNG
in production.

**Why not render the HTML directly:** the templates are HTML/CSS. Headless browser
(Chrome/Edge/Puppeteer/Playwright) does NOT exist on the production ECS Linux. The
`universal-carousel-template-creator` skill assumes Playwright/Chrome — following that route
breaks on deploy. The user chose to port to SVG + resvg-py (no browser, runs
on Windows and ECS Linux).

## Portability strategy

1. **Do not try to convert the whole HTML automatically** (invariable/fragile).
   Extract the ESSENCE of each template: palette (CSS `:root` variables) + font
   family + layout types (cover/intro/list/steps/quote/pricing/cta).
2. **Create your own SVG renderer** per template with:
   - solid background (the SVG→DrawingML converter does not materialize gradients; resvg-py
     renders gradients, but keep `* fill` solid + `fill-opacity` to port
     easily and work in both paths),
   - decorative shapes (circles/arcs/stars) approximating the template,
   - hierarchical typography using the real fonts.
3. **Copy the real fonts** from the templates (`_shared_fonts/*.ttf`) to
   `static/carousel_templates/fonts/` in the project.
4. **Render with resvg-py passing `font_files=`** for the template fonts:

```python
import resvg_py
png = resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350, font_files=fonts)
```

Without `font_files`, resvg uses system fonts (Arial) and loses the brand typography.

## Renderer structure (e.g. `chat/skills/carousel_templates.py`)

- `TEMPLATES = {nome: {bg, ink, accent, card, font_heading, font_body, font_files}}`
  — dictionary of palettes/fonts per template.
- `TEMPLATE_NAMES = tuple(TEMPLATES.keys())` — exposed so the LLM can choose the template.
- `render_carousel_svg(template, slides, *, title, brand, handle) -> list[str]` —
  generates one SVG per slide; propagates `handle`/`brand` to slides that do not define them;
  fills `slide_num`/`total` automatically (e.g. `01`/`07`).
- Helpers: `_wrap(text, max_chars)` (breaks by character count), `_esc`
  (html escape), `_wrap_svg(lines, x, y, font, size, fill, lh, weight, max_lines)`.
- Each slide is a dict `{layout, title, body, eyebrow, items, cta, handle, slide_num, total}`.

## Skill that consumes the renderer

The skill (`instagram_carousel_skill.py`) does NOT use the presentations pipeline (generic PPTX/SVG).
It:
1. Calls `llm_client.complete_json(messages, system=...)` (PROVIDER-AGNOSTIC, LiteLLM)
   with a system prompt that asks for `{title, template, slides[]}` + lists the valid TEMPLATES
   and the LAYOUTS (cover/bullets/steps/list/quote/pricing/cta) + Instagram narrative arc
   rules (slide 1 = hook that stops the scroll, last = CTA).
2. Validates the template (`_validate_template` falls back to default if invalid).
3. Renders SVG→PNG and archives via `archive_conversation_file` in the conversation folder.
4. Returns `{"component": "CarouselCard", "props": {title, slides:[{imageUrl, caption}], slideCount, format:"carousel"}}`.

Keep the SAME skill name and the SAME CarouselCard contract → the frontend does not change.

## Pitfalls

- **`_FONTS_DIR` depends on the file depth:** `Path(__file__).resolve().parents[2] / "static" / ...`
  works from `chat/skills/` but NOT from `presentations/services/` (different
  depth). Check when moving the module.
- **resvg accepts `font_files` (list of paths)** and `font_dirs` — use `font_files`
  for template-specific fonts.
- **Validate the LLM template:** the LLM may invent a template name — fall back to
  a safe default (`constellation`).
- **Long-running skill in chat:** the response is "⏳ Estou gerando… recarregue se
  necessário" and the CarouselCard only appears on reload (the frontend re-fetches the history).
  This is expected — it is not a bug.
- **Mock in tests:** mock `llm_client.complete_json` AND `_render` (not resvg);
  test the renderer separately with `font_files` so it does not depend on network/browser.
