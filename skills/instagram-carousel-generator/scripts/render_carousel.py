# -*- coding: utf-8 -*-
"""Deterministic carousel renderer: Modern Minimalist Coral (1080x1350)."""
import json, os, sys, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BG = (242, 237, 228, 255)      # #F2EDE4
INK = (13, 13, 13, 255)        # #0D0D0D
ACC = (255, 82, 43, 255)       # #FF522B coral
W, H = 1080, 1350
SAFE = 90


def _find_font(*names):
    """Resolve a font file portably (Windows/macOS/Linux), no hardcoded paths.

    Tries, in order:
      1. A font bundled next to this script (scripts/fonts/<name>).
      2. Common system font directories per platform.
      3. shutil.which() for the font name (in case it's on PATH).
    Returns an absolute path or None.
    """
    # 1. Bundled fonts next to this script
    here = Path(__file__).resolve().parent
    for name in names:
        for cand in (here / "fonts" / name, here / name):
            if cand.exists():
                return str(cand)

    # 2. System font directories per platform
    sys_dirs = []
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        sys_dirs = [os.path.join(windir, "Fonts")]
    elif sys.platform == "darwin":
        sys_dirs = ["/System/Library/Fonts", "/Library/Fonts",
                    str(Path.home() / "Library" / "Fonts")]
    else:  # linux
        sys_dirs = ["/usr/share/fonts/truetype", "/usr/share/fonts",
                    str(Path.home() / ".fonts")]

    for name in names:
        for d in sys_dirs:
            cand = Path(d) / name
            if cand.exists():
                return str(cand)

    # 3. On PATH
    for name in names:
        found = shutil.which(name)
        if found:
            return found

    return None


# Fontes: tenta nomes comuns por plataforma, com fallback para a primeira
# fonte disponível. A ordem prioriza fontes com suporte a negrito/emoji.
_FONT_CANDIDATES = {
    "bold": ["arialbd.ttf", "Arial-Bold.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"],
    "regular": ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"],
    "serif": ["georgiab.ttf", "Georgia-Bold.ttf", "DejaVuSerif-Bold.ttf", "arial.ttf"],
    "emoji": ["seguiemj.ttf", "NotoColorEmoji.ttf", "arial.ttf"],
}


def _resolve_font(kind):
    """Resolve a font path for a given kind (bold/regular/serif/emoji)."""
    names = _FONT_CANDIDATES.get(kind, _FONT_CANDIDATES["regular"])
    path = _find_font(*names)
    if path is None:
        # Último recurso: qualquer .ttf/.otf no diretório de fontes do sistema
        raise FileNotFoundError(
            f"Nenhuma fonte encontrada para '{kind}'. Instale uma das: {', '.join(names)}"
        )
    return path


FB = _resolve_font("bold")
FR = _resolve_font("regular")
FSERIF = _resolve_font("serif")
FEMOJI = _resolve_font("emoji")

def font(p, s): return ImageFont.truetype(p, s)

def text_w(d, t, f):
    return d.textbbox((0,0), t, font=f)[2]

def draw_frame(d, meta):
    f = font(FB, 24)
    d.text((SAFE, SAFE), meta["author_name"], font=f, fill=INK)
    d.text((SAFE, SAFE+30), meta["category_hashtag"], font=f, fill=ACC)
    d.text((SAFE, H-SAFE-30), meta["handle"], font=f, fill=INK)
    d.text((W-SAFE-text_w(d, meta["year"], f), H-SAFE-30), meta["year"], font=f, fill=INK)

def wrap_title(d, title, f, max_w):
    lines = []
    for raw in title.split("\n"):
        cur = ""
        for ch in raw:
            t = cur + ch
            if text_w(d, t, f) > max_w and cur:
                lines.append(cur); cur = ch
            else:
                cur = t
        if cur: lines.append(cur)
    return lines

def render_cover(d, slide):
    f = font(FB, 92)
    max_w = W - 2*SAFE - 40
    lines = wrap_title(d, slide["title"], f, max_w)
    y = 260
    lh = 96
    last_idx = len(lines)-1
    for i, ln in enumerate(lines):
        # underline accent on last line
        if i == last_idx and slide.get("underline_accent"):
            tw = text_w(d, ln, f)
            d.rectangle([SAFE+20, y+lh-10, SAFE+20+tw+10, y+lh-4], fill=ACC)
        d.text((SAFE+20, y), ln, font=f, fill=INK)
        y += lh

def render_content(d, slide):
    f = font(FB, 66)
    max_w = W - 2*SAFE - 40
    lines = wrap_title(d, slide["title"], f, max_w)
    y = 250
    lh = 70
    for ln in lines:
        d.text((SAFE+20, y), ln, font=f, fill=INK)
        y += lh
    # highlight box (coral)
    body = slide.get("body_text", "")
    bf = font(FR, 36)
    bm = font(FR, 36)
    bw = 30
    tw = text_w(d, body, bm)
    wrapped = []
    cur = ""
    for w in body.split(" "):
        t = (cur+" "+w).strip()
        if text_w(d, t, bm) > (W-2*SAFE-2*bw) and cur:
            wrapped.append(cur); cur = w
        else:
            cur = t
    if cur: wrapped.append(cur)
    box_h = 20 + len(wrapped)*(42+14) + 20
    box_y = 690
    d.rectangle([SAFE, box_y, W-SAFE, box_y+box_h], fill=ACC)
    ty = box_y + 30
    for ln in wrapped:
        d.text((SAFE+bw, ty), ln, font=bf, fill=INK)
        ty += 42+14

def render_cta(d, slide):
    f = font(FB, 78)
    max_w = W - 2*SAFE - 140
    lines = wrap_title(d, slide["title"], f, max_w)
    y = 300
    lh = 84
    for ln in lines:
        d.text((SAFE+20, y), ln, font=f, fill=INK)
        y += lh
    if slide.get("show_bookmark_icon"):
        # bookmark outline in coral, right of title area
        bx, by = W-SAFE-60, 240
        d.rectangle([bx, by, bx+40, by+64], outline=ACC, width=6)
        d.line([(bx+8, by+16),(bx+20, by+32),(bx+32, by+16)], fill=ACC, width=6)

def main(inp, outdir):
    with open(inp, encoding="utf-8") as f:
        data = json.load(f)
    meta = data["meta"]
    os.makedirs(outdir, exist_ok=True)
    for slide in data["slides"]:
        img = Image.new("RGBA", (W, H), BG)
        d = ImageDraw.Draw(img)
        draw_frame(d, meta)
        lt = slide["layout_type"]
        if lt == "cover": render_cover(d, slide)
        elif lt == "cta": render_cta(d, slide)
        else: render_content(d, slide)
        out = os.path.join(outdir, f"slide-{slide['slide_number']:02d}.png")
        img.convert("RGB").save(out)
        print("rendered", out)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
