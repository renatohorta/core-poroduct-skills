# SVG → PNG without a browser: `resvg-py` (alternative to Playwright/Chromium)

## When to use

When the PNG export of slides/carousels via Playwright is not viable:
- The Chromium download fails (`python -m playwright install chromium` hangs/times out).
- The service is going to **production on ECS Fargate (Linux)** — there is no Chrome/Edge installed
  in the container, and Playwright's Chromium is not even in the `pyproject.toml` (it was installed
  by hand via pip/uv, so it does not exist in the production build).

## Solution: `resvg-py`

Rust SVG renderer, distributed as a **binary wheel** — no browser, no external native
lib, works the same on Windows (dev) and Linux (ECS). Converts the SVG the project
**already generates** (`presentations/services/svg_renderer.py` → 1080×1350 for 4:5)
directly into PNG, without needing to "photograph" an HTML.

```bash
uv pip install resvg-py        # the project venv uses uv, does NOT have pip
```

```python
import resvg_py

png = resvg_py.svg_to_bytes(
    svg_string=svg,            # str, NOT bytes (TypeError if you pass bytes)
    width=1080, height=1350,
)
```

## `resvg-py` API quirks

- The import module is **`resvg_py`** (not `resvg`).
- The function is **`svg_to_bytes`** (not `render`).
- `svg_string` expects **`str`**, not `bytes` — passing bytes raises
  `TypeError: 'bytes' object is not an instance of 'str'`.
- Returns the PNG `bytes` (RGBA). Validate with Pillow: `Image.open(BytesIO(png))`.

## Why the other alternatives fail

| Option | Problem |
|---|---|
| `cairosvg` | Needs the native **libcairo** (C) lib. On Windows: `OSError: no library called "cairo-2" was found`. On ECS it would require `apt install libcairo2`. |
| `svglib` + `reportlab` | `renderPM` needs the **rlPyCairo** backend (also native cairo). `RenderPMError: cannot import desired renderPM backend rlPyCairo`. |
| `resvg-py` ✅ | Pure Rust wheel, no native lib. Works on Windows and Linux. |

## Verification

- `resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350)` returns a PNG with
  content (not white): sample pixels via Pillow, check the 1080×1350 dimensions and
  >1 unique color.

## Note

Playwright's `channel="chrome"` (use the system Chrome/Edge) solves the download
in Windows dev, but **does not serve production ECS** (no Chrome in the container). The
`resvg-py` covers both environments with a single path.

## Pitfall: Playwright traceback when the code already uses resvg-py (server with old code)

When the user pastes a traceback with `NotImplementedError` in `_make_subprocess_transport`
(or any error from an OLD implementation) but the on-disk code ALREADY uses resvg-py,
**do NOT re-fix the code** — it is already correct. The running Daphne/runserver process
still has the old module loaded in memory (the fix was merged but the server was not
restarted). Daphne does not auto-reload implementation modules already imported at boot.

### 3-step diagnosis (before editing anything)

1. **Real import scan** — grep for REAL use of the old lib in the flow
   (`from playwright`, `async_playwright`, `sync_playwright`, `p.chromium`),
   ignoring comments/docstrings. If there are only references in comments, the code
   is correct. Do not confuse the lib name in docstrings with real use.

2. **Run the current function directly against real data** — instead of depending on the
   server, call the function via `python -c`/`manage.py shell -c` with the real database state:
   ```python
   from presentations.services.png_export import export_carousel_pngs
   pres = Presentation.objects.filter(uuid="<uuid>").first()
   pngs = export_carousel_pngs(pres.state, "<dir>", len(pres.state["slides"]))
   print(len(pngs))  # if 7/7 and no error → code OK
   ```
   Generating the correct artifacts (e.g. 7/7 PNGs) proves the on-disk implementation is good.

3. **Restart the server** — `netstat -ano | findstr :8000` → kill the PID →
   relaunch Daphne with the full Windows env (USERPROFILE/HOME/LOCALAPPDATA).
   Only after that should the user re-test the download.

Rule: if the direct function test (step 2) passes, the real fix is the **process restart**,
not a new patch. Do not waste Dev→QA loop retries fixing already-correct code.
