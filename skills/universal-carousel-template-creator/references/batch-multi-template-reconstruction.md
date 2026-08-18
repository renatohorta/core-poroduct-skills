# Batch: reconstruir MUITOS templates de uma vez (pasta cheia de zips)

Quando o usuário entrega uma PASTA com N zips de template (ex.: 13 zips Freepik) e pede
"um template por zip", o fluxo é em lote, não um-por-um. Receita testada com 12 templates.

## 1. Inventariar sem abrir
```python
import zipfile, os
for z in sorted(os.listdir(pasta)):
    zf = zipfile.ZipFile(os.path.join(pasta,z))
    exts = {}
    for n in zf.namelist(): exts[os.path.splitext(n)[1].lower()] = exts.get(os.path.splitext(n)[1].lower(),0)+1
    # exts ~ {'.ai':1,'.eps':1,'.jpg':1,'.txt':4} -> é um pacote Freepik
```
Padrão Freepik: cada zip tem exatamente 1 `.ai` + 1 `.eps` + 1 `.jpg` (preview) + `.txt`.
Um zip pode ser `.psd` + `.jpg` (mockup) — pule ou trate à parte; não é template de carrossel.

## 2. Extrair TODOS os previews e .ai de uma vez
Extraia o `.jpg` (fonte autoritativa de design) e o `.ai` (para ler as fontes via regex `BaseFont`)
de cada zip para pastas temporárias. Não analise um a um dentro do zip.

## 3. Grid de slides por preview
Cada preview é um grid de mockups de posts. Detecte o layout por bandas de "gutter" (linhas/colunas
onde quase não há pixels longe da cor de fundo):
```python
# para cada eixo (x e y): para cada posição i, conte pixels != cor de fundo numa faixa;
# posições com contagem ~0 são gutters; agrupe em bandas (gap <30px = mesma banda).
# As bandas maiores delimitam os "cards/slides".
```
Atenção à indexação `px[x,y]` (x primeiro) — trocar inverte e dá IndexError em imagens não-quadradas.

## 4. OCR de cada preview (uma vez por imagem, cruzar --psm 3/6/11/12)
```python
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
out = subprocess.run([TESS, jpg, "stdout", "--psm", "3", "tsv"], ...)  # bounding boxes por palavra
```
Para previews grandes (3000x2000), recorte por região e upscale 2x antes do OCR para legibilidade;
escala as coordenadas de volta (`*0.625`).

## 5. Fontes: colete os pesos de TODOS os .ai e baixe em uma pasta SHARED
```python
fonts = set(re.findall(r'/BaseFont\s*/([A-Za-z0-9+\-]+)', open(ai,'r',encoding='latin-1',errors='replace').read()))
# sufixo após '+' = peso real. Coletar a união de todos os zips evita baixar 2x a mesma fonte.
```
Baixe uma vez para `templates/_shared_fonts/` e cada `slide.html` referencia com `@font-face` apontando
para `../_shared_fonts/...`. Assim 12 templates compartilham as fontes sem duplicar.
- Fontes comerciais (ex.: **Gilroy**) não estão no Google Fonts — use substituto fiel de peso equivalente
  (Gilroy ExtraBold → Montserrat-800, Gilroy Light → Montserrat-300) e nomeie o `@font-face` com o nome
  original (ex.: `font-family:'Gilroy'`) para o CSS ficar idêntico ao design.

## 6. Um slide.html por template, com layouts padronizados
Padronize: cada template tem 1 arquivo `slide.html` com 3-5 layouts (`data-layout` + `<script>` que
alterna via `classList.toggle('active', ...)`) e placeholders COMUNS:
`{{TITLE}} {{BODY}} {{EYEBROW}} {{SLIDE_NUM}} {{TOTAL_SLIDES}} {{HANDLE}} {{BRAND}} {{NEXT_LABEL}}`
`{{ITEM_1..3}} {{ITEM_1..3_TITLE}} {{ITEM_1..3_BODY}} {{ITEM_1..3_NUM}} {{PRICE}} {{CTA_LABEL}}`.
Layouts típicos por template: hero/cover, card, list, quote, cta. A consistência entre templates
facilita o usuário injetar conteúdo e trocar de tema.

## 7. Validar todos com um loop de render
Loop que, para cada template: preenche placeholders com valores dummy, renderiza Chrome headless,
checa histograma (cor de fundo esperada) + OCR (conteúdo presente). Confirma também os layouts
alternativos (list/cta), não só o hero.

## Pitfall: caminho relativo das fontes
Se o `slide.html` está em `templates/xxx/slide.html`, o caminho para `_shared_fonts` (que fica em
`templates/_shared_fonts`) é `../_shared_fonts/` — NÃO `../../_shared_fonts/`. Usar o caminho errado
faz a fonte cair em fallback silencioso e o render "funciona" mas com fonte errada. Confirme com
`os.path.isdir(os.path.abspath(os.path.join(template_dir, ref)))`.

## Pitfall: delegação paralela para reconstrução de imagem
Subagentes (`delegate_task`) com toolsets `file/terminal/web` NÃO têm `execute_code` nem
visão — a reconstrução de imagem exige Python/PIL/tesseract. Numa sessão onde o host tem o relay
bash quebrado e só `execute_code` grava arquivos, subagentes ficam bloqueados. Para este tipo de
trabalho pesado em imagem, faça no agente principal via `execute_code`, não delegue.
