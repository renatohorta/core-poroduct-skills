# Reconstruir um design a partir de uma imagem de referência (sem ferramentas de visão)

Quando o usuário entrega um screenshot/PNG como referência de design e a sessão não tem
visão/`vision_analyze`, use esta receita para extrair dados objetivos da imagem via
`execute_code` (Python) + OCR. Nunca invente cores, fontes ou texto — extraia.

## 1. Dados básicos da imagem
```python
from PIL import Image
im = Image.open(path).convert("RGB")
print(im.size, im.mode)          # ex: (899, 915) RGBA
```

## 2. Paleta de cores dominante
```python
from collections import Counter
small = im.resize((200, int(im.height*200/im.width)))
q = small.quantize(colors=32, method=Image.MEDIANCUT).convert("RGB")
cnt = Counter(q.getdata()); tot = sum(cnt.values())
for c, n in cnt.most_common(32):
    print(f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}  {n/tot*100:5.2f}%")
```
Faça também análise por região (terços / bandas de 50-100px em x e y) para saber ONDE cada cor está:
recorte com `im.crop(box)`, quantize com 4-6 cores, Counter, e cruze com o texto do OCR.

## 3. OCR do texto (instalar tesseract se faltar)
- `pytesseract` pode estar instalado sem o binário. O executável NÃO fica no PATH.
- Instale: `winget install --id UB-Mannheim.TesseractOCR -e --accept-source-agreements --accept-package-agreements --silent`
- O binário fica em `C:\Program Files\Tesseract-OCR\tesseract.exe` (confirme com glob antes).
- Rode com várias modos e cruze os resultados (pym 3/4/6/11/12) — cada um pega uma parte:
```python
import subprocess
subprocess.run([TESS, img, "stdout", "--psm", "3"], capture_output=True, text=True)
```

## 4. Layout / posição dos blocos de texto
Saída TSV dá as bounding boxes por palavra (level 5: `left top width height conf text`):
```python
out = subprocess.run([TESS, img, "stdout", "--psm", "3", "tsv"], capture_output=True, text=True)
# linha por linha: split('\t'); se level=='5' e text: registra L,T,W,H
```
Isso permite reconstruir onde ficam cabeçalho, título, rodapé, e o alinhamento (esquerda/centro).

## 5. Silhueta de formas decorativas (swoosh, ribbon, ícones)
Use um limiar (ex.: `r>235 and g>165 and b>120` para um tom claro sobre fundo laranja) e
renderize uma grade ASCII para "enxergar" o formato:
```python
for y in range(y0, y1, 3):
    row = "".join("#" if is_light(x,y) else " " for x in range(x0, x1, 3))
    if row.strip(): print(f"y{y:3d} {row}")
```
Ajuste o limiar até a forma (faixa diagonal, círculo, estrela) ficar visível. Anote a direção e posição.

## 6. Renderizar HTML → PNG em 1080x1350 (fallback sem Playwright)
Playwright pode estar instalado mas sem o navegador baixado. Fallback rápido com Chrome do sistema
(confirme `os.path.isfile` no `chrome.exe`/`msedge.exe`):
```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1080,1350 --force-device-scale-factor=1 --screenshot=out.png file:///C:/path/slide.html
```
O arquivo HTML deve ter `html,body { width:1080px; height:1350px; overflow:hidden }` para o screenshot
capturar exatamente 1 slide.

## 7. Verificar fidelidade ao original
Compare os histogramas de cores dominantes do referência vs. o render (mesma função de quantize).
Se o laranja de fundo, o tom do título e as cores de destaque baterem, o template está fiel.

## Fallback de escrita de arquivo
Se `write_file`/`terminal` falharem no host (ex.: erro de relay WSL/bash), escreva via
`execute_code` com Python puro:
```python
import os
os.makedirs(os.path.dirname(path), exist_ok=True)
open(path, "w", encoding="utf-8").write(content)
```
Isso contorna o problema sem depender do shell.
