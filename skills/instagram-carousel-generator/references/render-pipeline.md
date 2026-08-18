# Render Pipeline (PIL) & Stylized-Art Fallback

Técnica validada para renderizar cards de carrossel (1080x1350) quando não há
imagens reais disponíveis (ex.: lançamentos futuros) e/ou quando o host não
permite write_file/terminal (usar execute_code com Python puro).

## Quando usar
- O usuário pede "foto do jogo" mas não existem imagens oficiais (lançamentos
  futuros, produtos não lançados). NÃO buscar na web nem pedir arquivos por
  padrão — oferecer/gerar arte estilizada (gradiente de cor + emoji
  representativo) meio transparente. Confirmar com o usuário via clarify se
  houver dúvida, mas a arte estilizada é o fallback aceito.
- Renderização direta em PNG sem depender de Chrome/HTML.

## Pipeline (Pillow)
```python
from PIL import Image, ImageDraw, ImageFont
W, H = 1080, 1350
img = Image.new("RGBA", (W, H), BG)
draw = ImageDraw.Draw(img)
```

### Fundo com gradiente
```python
for i in range(H):
    t = i / H
    draw.line([(0,i),(W,i)], fill=(r,g,b,255))  # interpolar BG->BG2 por linha
```

### Arte "meio transparente" (gradiente + emoji)
Criar layer RGBA separado, desenhar, aplicar alpha, compor:
```python
layer = Image.new("RGBA", (W, H), (0,0,0,0))
ld = ImageDraw.Draw(layer)
# gradiente vertical do bloco
for i in range(h):
    ld.line([(x,y+i),(x+w,y+i)], fill=(r,g,b,255))
# emoji centralizado
f_em = ImageFont.truetype(EMOJI_FONT, emoji_size)
eb = ld.textbbox((0,0), emoji, font=f_em)
ld.text((ex,ey), emoji, font=f_em, fill=(255,255,255,255))
# aplicar transparencia
layer = layer.point(lambda p: int(p*alpha) if p>0 else 0)  # alpha ~0.55
img = Image.alpha_composite(img, layer)
draw = ImageDraw.Draw(img)  # redesenhar apos composicao
```

### Fontes (cross-platform — NUNCA hardcode path de máquina)
Não use `C:\Windows\Fonts\...` fixo no código/produção (quebra no ECS/Linux e
em outros devs). Resolver de forma portátil:

```python
from pathlib import Path
import os
_FONTS_PROJECT = Path(__file__).resolve().parents[N] / "static" / "carousel_templates" / "fonts"

def _load_font(name: str, size: int):
    cands = [str(_FONTS_PROJECT / name),
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]  # fallback Linux
    for path in cands:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()
```
- Prioridade: fontes empacotadas no projeto → fontes padrão do SO → PIL default.
- **Emoji:** procurar em diretórios padrão do SO (Windows/Linux/macOS) com
  fallback, não um arquivo fixo como `seguiemj.ttf`.
- **Tesseract (opcional):** `shutil.which("tesseract")` + env `TESSERACT_CMD`;
  se ausente, PULA o OCR (fallback pixels/arquivos) em vez de quebrar.
- Padrão completo: `deterministic-skill-executors/references/cross-platform-executors.md`.

### Quebra de título
Usar `font.getbbox(text)[2] <= max_w` para quebrar em linhas que cabem na
largura disponível (evita estouro do texto sobre a arte).

## Validação (sempre)
1. **OCR** com tesseract (`--psm 3`) no PNG para confirmar título, data e
   moldura legíveis.
2. **Amostragem de pixels** para confirmar que a arte transparente está
   presente à esquerda e o texto branco à direita, sem sobreposição.

## Extrair texto de SVGs vetorizados
SVGs de templates (ex.: `templates_crewbotics`) costumam ter o texto convertido
em paths e imagens base64 embutidas — não há `<text>` nem fontes legíveis.
Para reconstruir a estrutura: renderizar cada SVG em PNG via Chrome headless
(`--headless=new --window-size=1080,1350 --screenshot=out.png file:///...`) e
rodar OCR. Limpar os PNGs temporários depois.
