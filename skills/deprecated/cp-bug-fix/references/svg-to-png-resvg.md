# SVG → PNG without a browser: `resvg-py` (replaces Playwright/Chromium)

## When to use

You need to convert SVG to PNG (e.g. export 1080x1350 carousel slides) and
Playwright/Chromium is not viable:

- The Chromium download (~150MB) fails in the environment (slow network, proxy, sandbox).
- Production runs on **ECS Fargate Linux** — there is no Chrome/Edge installed, and installing
  a browser in the container is heavy/fragile.
- `channel="chrome"`/`"msedge"` (use the system Chrome) does NOT work in production
  (Linux container without a browser).

## Why `resvg-py`

- **Rust binary wheel** — no external native lib (unlike `cairosvg`/`svglib`
  which require C libcairo, which fails on Windows with `OSError: no library called "cairo-2"`).
- **No browser** — no need to download Chromium or install Chrome/Edge.
- **Works the same on Windows (dev) and ECS Linux (prod)**.
- Reuses the SVG the project already generates (`svg_renderer.render_slide_svg`), so the PNG
  reflects the same design (gradient, accents, typography).

## Installation

The venv uses `uv` (no pip). Install with:

```bash
uv pip install resvg-py
```

Add to `pyproject.toml`: `"resvg-py>=0.3"`.

## API (import and signature)

The module imports as **`resvg_py`** (not `resvg`), and the function is **`svg_to_bytes`**
(not `render`):

```python
import resvg_py

# svg_string expects str (NOT bytes) — passing bytes gives a TypeError
png_bytes = resvg_py.svg_to_bytes(
    svg_string=svg,          # str, not bytes
    width=1080,
    height=1350,
)
```

Full signature: `svg_to_bytes(svg_string=None, svg_path=None, background=None,
skip_system_fonts=False, log_information=False, width=None, height=None, zoom=None,
dpi=0.0, style_sheet=None, resources_dir=None, languages=..., font_size=16.0,
font_family=None, serif_family=None, sans_serif_family=None, ...)`.

## Usage pattern (slide export)

```python
import resvg_py
from .svg_renderer import render_slide_svg

def export_carousel_pngs(state, output_dir, total_slides):
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    theme = state.get("theme", {}) or {}
    slides = state.get("slides", []) or []
    paths = []
    for i, slide in enumerate(slides[:total_slides], start=1):
        svg = render_slide_svg(slide, theme, "4:5", browser=True)
        png = resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350)
        p = out / f"slide_{i}.png"; p.write_bytes(png); paths.append(str(p))
    return paths
```

## Pitfalls

- **`svg_string` accepts `str`, not `bytes`** — `TypeError: 'bytes' object is not an
  instance of 'str'`.
- **Import is `resvg_py`**, not `resvg` (`ModuleNotFoundError: No module named 'resvg'`).
- **Function is `svg_to_bytes`**, not `render` (`AttributeError: module 'resvg_py' has no
  attribute 'render'`).
- **Pillow does NOT render SVG** (`UnidentifiedImageError`) — do not try `Image.open` on an
  SVG; use resvg-py.
- **`cairosvg`/`svglib`+`reportlab` require native libcairo** — they fail on Windows
  (`OSError: no library called "cairo-2"` / `RenderPMError: cannot import ... rlPyCairo`).
  `resvg-py` is the pure option (Rust wheel) that works without a system lib.
- **Test with `TemporaryDirectory`**: close the Pillow image (`with Image.open(p) as img`)
  before the cleanup, otherwise `PermissionError: [WinError 32]` on Windows.

## Verification

```python
import resvg_py
png = resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350)
# PNG header: b"\x89PNG\r\n\x1a\n"
```
