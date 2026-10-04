# Instagram carousel with HTML templates → SVG → resvg-py (no browser)

Reusable pattern for porting carousel HTML/CSS templates (e.g. from the
`universal-carousel-template-creator` skill, Freepik/sketch/swoosh templates) to the
Crewbotics Django backend, rendering 1080×1350 PNG **without a browser** (works
on Windows and on ECS Linux).

## Why not use a browser
The reference templates are HTML/CSS and the original skill renders via headless Chrome/Edge.
But production is ECS Linux **without a browser** — Playwright/Chromium does not work.
The solution: port the aesthetic (palettes + typography + layouts) to SVG and render
with `resvg-py` (Rust wheel, no native lib), which accepts `font_files` with the real fonts.

## Architecture of the new skill
```
prompt → llm_client.complete_json (provider-agnostic) → script {title, template, slides[]}
    ↓
chat/skills/carousel_templates.py  (SVG renderer: palettes + layouts)
    ↓
resvg-py.svg_to_bytes(svg_string=..., width=1080, height=1350, font_files=[...])
    ↓
CarouselCard (PNGs archived in the knowledge base)
```

## Key steps
1. **Copy fonts** from the templates to `static/carousel_templates/fonts/` (Poppins,
   Montserrat, AbrilFatface, BebasNeue, etc.). resvg-py uses `font_files` with absolute
   paths — `get_font_paths(template)` resolves from `_FONTS_DIR`.
2. **SVG renderer** (`carousel_templates.py`): a `TEMPLATES` dictionary with the palette
   (bg/ink/card/accent) + `font_heading`/`font_body` + `font_files`. Layouts: cover,
   bullets, steps, list, quote, pricing, cta. Each layout draws the slide in SVG
   1080×1350 (background rectangle + texts with `font-family` + decorative shapes).
3. **Skill** (`instagram_carousel_skill.py`): the LLM generates the JSON script; validates the template;
   renders each slide SVG→PNG; archives via `archive_conversation_file()`; returns
   a `CarouselCard` with `slides: [{imageUrl, caption}]`.

## "Always navigable" — guarantee 5+ slides
The `CarouselCard` only shows arrows/counter/dots when `total > 1`. To guarantee that the
result is ALWAYS a navigable carousel:
- Reinforce in the system prompt: "MANDATORY: between 5 and 10 slides (NEVER less than 5)".
- Validate in `execute`: `if len(slides) < 5: return {"error": ...}` (asks for a rework
  instead of returning a card without navigation).

## Individual slide download (frontend)
The `CarouselCard` must allow downloading each image, not just the ZIP. Add a
"Baixar slide N" button that does an **authenticated fetch** (Bearer token) of the current
slide's `imageUrl` — `/media/` may require auth in production, so a direct `<a href>` is not enough:
```tsx
const headers: Record<string, string> = {};
if (tokenStore.access) headers["Authorization"] = `Bearer ${tokenStore.access}`;
const res = await fetch(slide.imageUrl, { method: "GET", headers, credentials: "include" });
const blob = await res.blob();
// URL.createObjectURL + <a download="slide-N.png"> + click
```

## ZIP download endpoint for the slides
For the card to have working `downloadUrl`/`pngsUrl`, add an `@action` in the
`ConversationViewSet` that generates a ZIP of the archived slides:
- Filter `ProductContext` by `folder=conv.knowledge_folder` and **file name**
  `slide-*` (via `os.path.basename(doc.file.name)`), NOT by the `title` (the title is the
  carousel's, e.g. "7 Dicas... 1").
- `FileResponse` is streaming — in tests use `b"".join(resp.streaming_content)`, not
  `resp.content` (raises AttributeError).
- `Content-Type` can be `application/zip` OR `application/x-zip-compressed` — accept
  both in the test.
- Name the files in the ZIP with `os.path.basename(doc.file.name)` (not `doc.title`).

## Pitfall: `@action` decorator stolen when inserting a new action
When inserting a new `@action` BEFORE an existing one with `url_path` (e.g. `branch_version`
with `url_path="branch-version"`), the existing decorator ends up stacked on the new one
and the existing one loses its `url_path` → the route disappears → 404 in the test. After inserting, check the
decorators of ALL the affected `def`s and restore each one's `url_path`/decorator.
