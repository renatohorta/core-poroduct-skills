# Reconstruir um design a partir de um arquivo `.sketch` (Sketch app)

Quando o usuário entrega um template em formato `.sketch` (app Sketch for macOS,
comum em "carousel template" grátis), NÃO é preciso adivinhar o design nem usar visão.
Um `.sketch` é um arquivo ZIP contendo JSON estruturado com todos os dados de design
(textos, fontes, cores, posições, símbolos). Extraia tudo objetivamente.

## 1. O arquivo `.sketch` é um ZIP
```python
import zipfile
zipfile.is_zipfile("Template.sketch")   # -> True
z = zipfile.ZipFile("Template.sketch")
print(z.namelist())
# tipicamente: document.json, pages/*.json, meta.json, previews/preview.png,
#              text-previews/text-previews.pdf, user.json
z.extractall(outdir)
```
Estrutura-chave:
- `pages/*.json` — os artboards (slides) e symbolMasters. É o que importa.
- `document.json` / `meta.json` — metadados e lista de páginas/artboards.
- `previews/preview.png` — renderização (frequentemente uma tira larga com vários
  slides lado a lado, ex.: 2048x424). Útil só como conferência visual, não como fonte.

## 2. Encontrar os artboards (slides) e suas variantes
Cada página JSON tem `layers[]`. Um `artboard` = um slide (ex.: "Step 0".."Step 8").
Carousels costumam ter DUAS fileiras de artboards: variantes Dark e Light.
```python
arts = [l for l in page["layers"] if l.get("_class")=="artboard"]
for a in arts:
    bg = a.get("backgroundColor")
    y  = a.get("frame",{}).get("y")     # fileira: mesmo y = mesma variante
```
O fundo vem de `backgroundColor` do artboard (ex.: Dark #1A1A1A, Light #F0F5F4),
NÃO de um fill no layer tree. Cheque `hasBackgroundColor`/`backgroundColor` quando
`fills=[]`.

## 3. Extrair textos + estilos (fonte, cor, tamanho, alinhamento, posição)
Recursão em `layers[]` coletando nós `_class=="text"`:
```python
def all_texts(obj, acc):
    if isinstance(obj, dict):
        if obj.get("_class")=="text": acc.append(obj)
        for v in obj.get("layers",[]): all_texts(v, acc)
    return acc
```
Por texto, ler:
- `attributedString.string` — o conteúdo.
- `style.textStyle.encodedAttributes`:
  - `MSAttributedStringFontAttribute.attributes` -> name (ex. `InterV_Black`), size.
  - `MSAttributedStringColorAttribute` -> {red,green,blue,alpha} em 0..1 (multiplique por 255 p/ hex).
  - `paragraphStyle.alignment` -> 0=left, 1=right, 2=center.
  - `kerning` (tracking, pode ser negativo).
- `frame` -> {x,y,width,height} (posição no artboard).

## 4. Nomes de fonte `InterV_*` e mapeamento CSS
O sketch usa pesos nomeados do Inter: `InterV_Black`, `InterV_Bold`, `InterV_Semi-Bold`,
`InterV_Medium`. Mapeamento para font-weight:
- Black -> 900, Bold -> 700, Semi-Bold -> 600, Medium -> 500.
- A fonte geralmente acompanha o pacote numa pasta `Fonts/` (ex.: `Inter-V.otf`, uma
  fonte variável que cobre 100-900). Embute via `@font-face { font-weight: 100 900; }`
  no template para fidelidade de peso.

## 5. Símbolos reutilizáveis (Header / Footer)
O header/footer costuma ser `symbolInstance` apontando para `symbolMaster` na página
"Symbols". Para reconstruir, procure os symbolMasters pelos nomes:
- `Header/Dark` e `Header/Light` — kicker ("Step"), nota ("Secondary text"), linha divisória.
- `Footer/Dark`/`Footer/Light` — avatar (retângulo `rectangle` com cor, ex. #1EC670),
  nome + bio (textos), botão `Next →` / `Swipe →` (grupo `Rigth/Dark/Next`).
- `Left/Dark/Avatar+Text` — perfil; `Left/Dark/Like+Comment+Share` — ações.
Examine o symbolMaster igual aos artboards (mesma recursão de textos/shapes).

## 6. Formas decorativas
Elementos decorativos aparecem como `shapeGroup`/`shapePath`/`rectangle` com
`style.fills[].color` e `frame` (posição/tamanho). Ex.: sparks lilás #C3B0FF numa capa.
Para reproduzir como SVG no HTML, use o `frame` do shapeGroup e aproxime a forma
(estrela/raio). Emojis grandes (💬, 👍) vêm como textos com fonte `AppleColorEmoji`.

## 7. Escalar 720x720 artboard -> 1080x1350 (4:5)
Os artboards de carousel costumam ser 720x720 (quadrado). Para o carrossel 4:5
(1080x1350), NÃO estique o quadrado para retângulo — recompusha o layout: multiplique
fontes/medidas por ~1.5 e adote um container 1080x1350 com flex (header topo,
conteúdo central, footer rodapé). Preserve as proporções do texto.

## 8. Verificação
Renderize HTML->PNG 1080x1350 com Chrome headless e compare o histograma de cores
dominantes do render vs. o esperado do sketch (bg, cor de texto, avatar, deco).
OCR no render confirma que todo o conteúdo aparece. Valide pelo menos um layout
"simples" (capa) e um "complexo" (good/bad com emojis) e em AMBAS as variantes
(dark e light).

## Fallback de escrita de arquivo
Se `write_file`/`terminal` falharem no host (erro de relay WSL/bash), escreva via
`execute_code` com Python puro (`os.makedirs` + `open(path,"w")`) — mesma receita da
reconstrução por imagem.
