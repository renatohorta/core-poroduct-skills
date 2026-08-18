# Reconstruir um design a partir de um pacote Freepik / design package (.ai/.eps/.jpg/.txt)

Quando o usuário entrega uma pasta de template tipo Freepik (`.ai` + `.eps` + `.jpg` + `.txt`)
em vez de um screenshot puro ou `.sketch`, o fluxo é diferente. Aqui está a receita testada.

## 1. Reconhecer o pacote
Liste a pasta. Assinaturas de um pacote Freepik/Adobe:
- `NNNNNNNN.eps` (grande, ~5MB) + `NNNNNNNN.ai` + `NNNNNNNN.jpg` (o PREVIEW) + `NNNNNNNN.txt` + `Fonts.txt`.
- `Fonts.txt` lista as fontes de terceiros (ex.: "Poppins" + URL do Google Fonts).
- `NNNNNNNN.txt` contém URLs de fotos de banco de imagem usadas como recursos (não são o design principal — são fotos stock para substituir).

IMPORTANTE: o `.ai` NÃO é um ZIP (diferente do `.sketch`). Começa com `%PDF-1.x`. Não tente `zipfile`.

## 2. A fonte autoritativa de design é o JPG de preview
O `.jpg` é uma montagem dos slides. Geralmente é um GRID (ex.: 2000x2000 = grid 2x2 de 4 slides de ~1000x1000).
- Divida em quadrantes e analise cada um separadamente (OCR + paleta + geometria).
- Se o preview for quadrado mas os slides do carrossel devem ser 4:5, o grid mostra o layout 1:1; você re-escala para 1080x1350 ao montar o HTML.

## 3. Extrair textos e posições por quadrante
Cada quadrante é um slide. Recorte e faça OCR com `--psm 6` e TSV (`--psm 3 tsv`) para bounding boxes por palavra.
Escale as coordenadas de volta se tiver upscaled o recorte (`*0.625` para 1600→1000).
Cruze os textos dos 4 quadrantes para montar a sequência lógica do carrossel (capa → contexto → lista/timeline → CTA).

## 4. Extrair fontes do .ai (PDF)
O `.ai` é um PDF. Regex no texto latin-1:
```python
import re
content = open(ai, 'r', encoding='latin-1', errors='replace').read()
fonts = set(re.findall(r'/FontName\s*/([A-Za-z0-9+\-]+)', content))  # ex: NJOCQD+Poppins-Bold
base  = set(re.findall(r'/BaseFont\s*/([A-Za-z0-9+\-]+)', content))
```
Os nomes vêm com prefixo de subset (ex.: `NJOCQD+Poppins-Bold`) — o sufixo após `+` é o peso real.
O texto BT/TJ geralmente está comprimido — não vale a pena tentar extrair conteúdo textual do .ai; use o OCR do preview.

## 5. Baixar as fontes do Google Fonts
Se a fonte não estiver no sistema, baixe do repo `google/fonts` (url com User-Agent + SSL context):
```python
import urllib.request, ssl
ctx = ssl.create_default_context()
url = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf"
req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
data = urllib.request.urlopen(req, context=ctx, timeout=30).read()
open("fonts/Poppins-Bold.ttf","wb").write(data)
```
Salve os pesos usados (Regular/Medium/SemiBold/Bold/ExtraBold) e declare cada um com `@font-face` separado no HTML.

### Fallback: CSS2 API quando o caminho estático 404 (fontes variáveis)
Várias fontes NÃO têm `.ttf` estático no repo `google/fonts` (ex.: Montserrat, Raleway, Roboto Condensed, Josefin Sans, Libre Baskerville, Bodoni Moda — são variáveis). O caminho estático `ofl/.../Montserrat-Bold.ttf` retorna 404. Use a CSS2 API do Google Fonts com User-Agent normal (sem o UA de woff2) para obter URLs `.ttf` diretas:
```python
import re, urllib.request, ssl
ctx = ssl.create_default_context()
def get_css(family_wght):
    url = f"https://fonts.googleapis.com/css2?family={family_wght}&display=swap"
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})  # UA normal => .ttf, n?o woff2
    return urllib.request.urlopen(req, context=ctx, timeout=30).read().decode()

css = get_css("Montserrat:wght@300;400;500;600;700")  # pesos separados por ;
blocks = re.findall(r"font-weight:\s*(\d+);[^}]*?url\(([^)]+\.ttf)\)", css, re.S)
# blocks == [(300, url), (400, url), ...] -> baixe cada url e salve como Montserrat-<peso>.ttf
```
Com o User-Agent de um navegador moderno a API devolve woff2; com UA simples devolve `.ttf` — é o que queremos para `@font-face` local. `Lobster`, `BebasNeue`, `AbrilFatface`, `AbhayaLibre`, `GreatVibes`, `Gaegu`, `HerrVonMuellerhoff`, `Poppins` têm estáticos no repo (baixam direto).

## 6. Cores e decorações do preview
- Paleta dominante: `quantize(colors=...)` no preview e por quadrante.
- Texto: amostre pixels escuros dentro da bbox de texto (exclua branco e fundo) — o "tint" dominante é a cor do texto.
- Exclua a cor de fundo (família da cor base) e o branco antes de contar cores de destaque, senão o fundo domina tudo.
- Silhueta ASCII (limiar por cor) para mapear formas decorativas (estrelas, linhas de constelação, círculos).

## 7. Renderizar + validar (fallback Chrome headless)
Mesmo fluxo dos outros refs: `chrome.exe --headless=new --window-size=1080,1350 --force-device-scale-factor=1 --screenshot=out.png file:///...`, depois confirmar histograma de cores + OCR do render.

## Pitfall: fotos stock no pacote
As URLs/fotos de pessoas/objetos do `NNNNNNNN.txt` são recursos de banco de imagem, NÃO parte do design de carrossel. Foque no layout/cores/tipografia. Não tente incluir as fotos stock por padrão.
