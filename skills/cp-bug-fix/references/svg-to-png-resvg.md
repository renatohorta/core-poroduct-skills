# SVG → PNG sem browser: `resvg-py` (substitui Playwright/Chromium)

## Quando usar

Precisa converter SVG em PNG (ex: exportar slides de carrossel 1080x1350) e o
Playwright/Chromium não é viável:

- Download do Chromium (~150MB) falha no ambiente (rede lenta, proxy, sandbox).
- Produção roda em **ECS Fargate Linux** — não há Chrome/Edge instalado, e instalar
  browser no container é pesado/frágil.
- `channel="chrome"`/`"msedge"` (usar o Chrome do sistema) NÃO funciona em produção
  (container Linux sem browser).

## Por que `resvg-py`

- **Wheel binário Rust** — sem lib nativa externa (diferente de `cairosvg`/`svglib`
  que exigem libcairo C, que falha no Windows com `OSError: no library called "cairo-2"`).
- **Sem browser** — não precisa baixar Chromium nem instalar Chrome/Edge.
- **Funciona igual no Windows (dev) e ECS Linux (prod)**.
- Reusa o SVG que o projeto já gera (`svg_renderer.render_slide_svg`), então o PNG
  reflete o mesmo design (gradiente, acentos, tipografia).

## Instalação

O venv usa `uv` (não tem pip). Instalar com:

```bash
uv pip install resvg-py
```

Adicionar ao `pyproject.toml`: `"resvg-py>=0.3"`.

## API (import e assinatura)

O módulo importa como **`resvg_py`** (não `resvg`), e a função é **`svg_to_bytes`**
(não `render`):

```python
import resvg_py

# svg_string espera str (NÃO bytes) — passar bytes dá TypeError
png_bytes = resvg_py.svg_to_bytes(
    svg_string=svg,          # str, não bytes
    width=1080,
    height=1350,
)
```

Assinatura completa: `svg_to_bytes(svg_string=None, svg_path=None, background=None,
skip_system_fonts=False, log_information=False, width=None, height=None, zoom=None,
dpi=0.0, style_sheet=None, resources_dir=None, languages=..., font_size=16.0,
font_family=None, serif_family=None, sans_serif_family=None, ...)`.

## Padrão de uso (export de slides)

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

- **`svg_string` aceita `str`, não `bytes`** — `TypeError: 'bytes' object is not an
  instance of 'str'`.
- **Import é `resvg_py`**, não `resvg` (`ModuleNotFoundError: No module named 'resvg'`).
- **Função é `svg_to_bytes`**, não `render` (`AttributeError: module 'resvg_py' has no
  attribute 'render'`).
- **Pillow NÃO renderiza SVG** (`UnidentifiedImageError`) — não tente `Image.open` num
  SVG; use resvg-py.
- **`cairosvg`/`svglib`+`reportlab` exigem libcairo nativa** — falham no Windows
  (`OSError: no library called "cairo-2"` / `RenderPMError: cannot import ... rlPyCairo`).
  `resvg-py` é a opção pura (Rust wheel) que funciona sem lib de sistema.
- **Teste com `TemporaryDirectory`**: feche a imagem Pillow (`with Image.open(p) as img`)
  antes do cleanup, senão `PermissionError: [WinError 32]` no Windows.

## Verificação

```python
import resvg_py
png = resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350)
# PNG header: b"\x89PNG\r\n\x1a\n"
```
