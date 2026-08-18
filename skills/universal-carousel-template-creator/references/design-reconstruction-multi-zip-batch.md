# Reconstruir MUITOS pacotes Freepik de uma vez (batch multi-zip)

Quando o usuário entrega uma PASTA com vários zips de templates (ex.: `templates/` com
`instagram-carousel-templates (1..7).zip`, `*-new-collection.zip`, `*-with-photos.zip`, etc.)
e pede "um template por zip", o fluxo single-package do
`design-reconstruction-from-design-package.md` se repete N vezes. Esta receita otimiza o batch.

## 0. NÃO delegue — faça inline com `execute_code`
Regra dura: reconstrução de design (PIL para paleta/geometria + tesseract para OCR + Chrome headless
para validar) é um trabalho de `execute_code`. Subagentes via `delegate_task` NÃO recebem
`execute_code` no toolset (os toolsets disponíveis são terminal/file/web/browser/etc.) e, neste
host, o relay de shell falha — então subagentes com `file/terminal/web` ficam paralisados: não
conseguem rodar Python/PIL/OCR/Chrome nem gravar arquivo. Resultado: entregam HTML não-gravado e
você tem que refazer tudo. **Quando a tarefa depende de `execute_code`, faça inline no agente pai**
ou dê ao subagente apenas pedaços que ele consiga fazer por outros meios.

## 1. Inventário em massa
Liste todos os zips e extraia de cada um: o `.jpg` de preview (autoritativo) + `.ai` (fontes) + `.txt`.
Extraia para uma pasta temporária única, renomeando por zip para não colidir:
`<zipname>__<basename>`. Um zip pode ser um mockup PSD (`.psd`+`.jpg`) — não é template, pule.

## 2. Fontes de TODOS os .ai numa passada só
Varra todos os `.ai` e agrupe as fontes únicas. `BaseFont` dá `PREFIXO+NomePeso` (ex. `NJOCQD+Poppins-Bold`);
o sufixo após `+` é o peso. Mapa de fontes comerciais → substituto gratuito:
- **Gilroy** (ExtraBold/Light) → **Montserrat** (800/300) — Gilroy não está no Google Fonts.
- Bodoni-16 → Bodoni Moda (ou Georgia fallback).
- Demais (Montserrat, Raleway, Poppins, Roboto Condensed, Josefin Sans, Libre Baskerville, Abril
  Fatface, Abhaya Libre, Great Vibes, Bebas Neue, Gaegu, Lobster, HerrVonMuellerhoff) estão no Google Fonts.

## 3. Baixar fontes: use a API CSS2 (não o caminho estático do github)
Fontes variáveis (Montserrat, Raleway, Roboto Condensed, etc.) **404** nos caminhos estáticos do repo
`google/fonts` (ex. `ofl/montserrat/static/Montserrat-Regular.ttf` não existe). Em vez disso use o
endpoint CSS2 com User-Agent normal — ele devolve URLs `.ttf` por peso:
```python
import urllib.request, re
def get_css(family_wght):  # ex. "Montserrat:wght@300;400;500;600;700"
    url = f"https://fonts.googleapis.com/css2?family={family_wght}&display=swap"
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})  # UA normal => .ttf
    return urllib.request.urlopen(req, timeout=30).read().decode()
css = get_css("Montserrat:wght@300;400;500;600;700")
for w,url in re.findall(r"font-weight:\s*(\d+);[^}]*?url\(([^)]+\.ttf)\)", css, re.S):
    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=30).read()
    open(f"{name}-{w}.ttf","wb").write(data)
```
(Fontes estáticas — Poppins, BebasNeue, AbhayaLibre, etc. — ainda baixam pelo caminho github `raw/main/ofl/<fonte>/<Fonte>.ttf`.)

## 4. Padrão `_shared_fonts/` (um diretório para todos os templates)
Todos os templates ficam como subpastas de `templates/<nome>/slide.html`. Para não duplicar 29 fontes
por template, crie uma pasta única `templates/_shared_fonts/` e cada slide declara:
```css
@font-face{font-family:'Montserrat';src:url('../_shared_fonts/Montserrat-400.ttf') format('truetype');font-weight:400;}
```
**Pitfall de caminho relativo:** o template está em `templates/<nome>/slide.html`, ou seja UMA pasta
abaixo de `templates/`. O caminho correto é `../_shared_fonts/` — **NÃO** `../../_shared_fonts/`
(esse sobe além de `templates/` e não acha). Verifique sempre contando níveis de pasta.

## 5. Template padrão multi-layout (reutilizável)
Estruture cada `slide.html` como um arquivo único com vários `<section data-layout="...">` e um
`<script>` que mostra só o ativo:
```js
(function(){var t="{{LAYOUT}}";document.querySelectorAll('[data-layout]').forEach(function(el){
  el.classList.toggle('active', el.getAttribute('data-layout')===t);});})();
```
Layouts comuns que cobrem a maioria dos carrosséis Freepik: `hero`/`cover`, `card` (título+parágrafo),
`list` (itens numerados), `quote`, `cta`. Placeholders padronizados:
`{{TITLE}} {{BODY}} {{EYEBROW}} {{SLIDE_NUM}} {{TOTAL_SLIDES}} {{HANDLE}} {{BRAND}} {{NEXT_LABEL}}
{{ITEM_1..3}} {{ITEM_1..3_TITLE}} {{ITEM_1..3_BODY}} {{ITEM_1..3_NUM}} {{PRICE}} {{CTA_LABEL}}
{{QUOTE_EMOJI}}`. Específicos por tema: `{{THEME}}`(dark/light), `{{TITLE_L1}} {{TITLE_L2}}`,
`{{SCRIPT}}`(fonte script), `{{LOCATION}} {{IMG_LABEL}} {{LIKES}} {{CAPTION}} {{COMMENTS}} {{TIME_AGO}}`
(mockup de post Instagram).

## 6. Validar TODOS em loop
Escreva uma função de validação que, para cada template: preenche um demo, renderiza com Chrome
headless 1080x1350, e checa (a) cor de fundo dominante via histograma `quantize` contra a esperada
e (b) presença de texto via OCR. Rode os 12 e liste OK/falha. Fundos com gradiente terão a cor de
topo ligeiramente deslocada — aceite se aparecer nas 2-3 primeiras cores.

## 7. Documentar no README
Ao final, escreva `templates/README.md` com a tabela: pasta → zip fonte → tema → paleta → fontes →
layouts. Facilita a próxima sessão escolher o template certo.

## Pitfall: OCR de emojis/ícones
Emojis (💬 👍 👎 🪑) renderizam no Chrome headless mas o tesseract não lê — o OCR pode sair truncado
nessas áreas sem ser bug do template. Não use a ausência do emoji no OCR como falha.
