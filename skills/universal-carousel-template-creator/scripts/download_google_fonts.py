#!/usr/bin/env python3
"""Baixa fontes do Google Fonts como .ttf locais para usar com @font-face.

Cobre dois caminhos:
  1. Repo estatico `google/fonts` (fontes com .ttf fixo: Poppins, Lobster,
     BebasNeue, AbrilFatface, AbhayaLibre, GreatVibes, Gaegu, HerrVonMuellerhoff).
  2. CSS2 API (fontes variaveis que NAO tem .ttf estatico e 404 no repo:
     Montserrat, Raleway, Roboto Condensed, Josefin Sans, Libre Baskerville, Bodoni Moda).

Uso:
    python download_google_fonts.py --out DIR \
        "Montserrat:300;400;500;600;700" "Raleway:600;700;800" \
        "Poppins:400;700" --static "Poppins-Bold.ttf" "Lobster-Regular.ttf"

A API CSS2 devolve .ttf direto quando o User-Agent NAO e de navegador moderno
(com UA de browser ela devolve woff2). Salva como <Family>-<wght>.ttf.
"""
import argparse, re, ssl, urllib.request, os

UA = {"User-Agent": "Mozilla/5.0"}  # UA simples => .ttf, nao woff2
CTX = ssl.create_default_context()
GSTATIC = "https://github.com/google/fonts/raw/main/"


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, context=CTX, timeout=30).read()


def download_css2(family, weights, outdir, tag=None):
    """family: nome Google Fonts (ex 'Roboto+Condensed'); weights: lista de ints."""
    wstr = ";".join(str(w) for w in weights)
    css = _get(f"https://fonts.googleapis.com/css2?family={family}:wght@{wstr}&display=swap").decode()
    blocks = re.findall(r"font-weight:\s*(\d+);[^}]*?url\(([^)]+\.ttf)\)", css, re.S)
    name = tag or family.replace("+", "")
    got = []
    for w, url in blocks:
        data = _get(url)
        fn = os.path.join(outdir, f"{name}-{w}.ttf")
        open(fn, "wb").write(data)
        got.append((w, len(data)))
    return got


def download_static(repo_rel, outdir):
    """repo_rel: ex 'ofl/poppins/Poppins-Bold.ttf'."""
    data = _get(GSTATIC + repo_rel)
    fn = os.path.join(outdir, os.path.basename(repo_rel))
    open(fn, "wb").write(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="pasta destino dos .ttf")
    ap.add_argument("families", nargs="*", help="'Família:wght1;wght2' via CSS2 API")
    ap.add_argument("--static", nargs="*", default=[],
                    help="caminhos do repo google/fonts (ex ofl/poppins/Poppins-Bold.ttf)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for spec in a.families:
        fam, _, w = spec.partition(":")
        weights = [int(x) for x in w.split(";") if x]
        got = download_css2(fam, weights, a.out)
        print(f"{fam}: {got}")
    for rel in a.static:
        n = download_static(rel, a.out)
        print(f"static {rel}: {n} bytes")


if __name__ == "__main__":
    main()
