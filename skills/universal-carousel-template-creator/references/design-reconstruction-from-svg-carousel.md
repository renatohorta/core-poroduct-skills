# Reconstruir templates a partir de uma pasta de SVGs de carrossel

Quando o usuário entrega uma pasta com vários `N.svg` (ex.: `templates_crewbotics/` com
subpastas, cada uma sendo UM carrossel completo: `1.svg`..`7.svg`, um slide por arquivo),
reconstrua um `slide.html` por subpasta. Fonte: design-package/sketch são casos especiais;
SVG é uma família própria porque o TEXTO costuma vir como paths (curvas), não `<text>`.

## 1. Inventário
```
por subpasta: quantos .svg (nº de slides do carrossel)
ex.: 12 subpastas → 12 templates; 6 svgs → carrossel de 6 slides
```

## 2. Texto NÃO vem em `<text>` — está em paths
- `re.findall(r'<text[^>]*>(.*?)</text>', c)` costuma retornar VAZIO (texto virou curvas).
- Então extraia o texto por **OCR do SVG renderizado**, não lendo o XML:
  1. Renderize com Chrome headless: `--window-size=1080,1080 --screenshot=tmp.png file:///<svg>`
     (SVGs destes pacotes são quadrados 1080×1080; ajuste se `viewBox` indicar outro).
  2. `tesseract tmp.png --psm 3` para o texto. Rode `--psm 11` se 3 sair com ruído.
- Paleta: `Image.quantize(colors=N)` no render (não os `fill=` do XML, que podem ter 824
  ocorrências de branco e esconder as cores de fundo reais).
- Estrutura por slide (OCR do slide 2..n-1): conteúdo; último slide costuma ser CTA
  ("LOVE THIS POST?", "Swipe —", @handle).

## 3. Gerar um `slide.html` multi-layout por subpasta
- 5 layouts padronizados: `cover`, `intro`, `steps`, `list`, `cta` (via `data-layout`).
- Placeholders: `{{TITLE}} {{BODY}} {{EYEBROW}} {{HANDLE}} {{SLIDE_NUM}} {{TOTAL_SLIDES}}`
  `{{NEXT_LABEL}} {{PROMPT}} {{ITEM_1..3_TITLE}} {{ITEM_1..3_BODY}} {{LAYOUT}}`.
- Fontes: use a pasta compartilhada `_shared_fonts/` (Montserrat/Poppins); caminho relativo
  do template é `../_shared_fonts/<Font>.ttf` (NÃO `../../`).
- Nome da pasta de saída: `crewbotics-<slug>` (ex.: `crewbotics-blue-running`).

## 4. PITFALLS de GERAÇÃO de HTML com f-strings Python (crítico)
Gerar o template com `f"""..."""` CONSUME um nível de chaves — placeholders viram
`{TITLE}` (1 chave) e o JS fica `var t="{LAYOUT}"` (perde o placeholder). Sintomas:
- Nenhum texto renderiza no PNG (as sections ficam `display:none`).
- O `{{LAYOUT}}` no `<script>` vira `{LAYOUT}` ou `{{{LAYOUT}}}` dependendo de quantas vezes
  você rodou o replace — o script compara com o `data-layout` e NUNCA ativa a section.

Correção confiável:
- Não escreva os placeholders dentro da f-string de geração. Melhor: escreva o template como
  string CRUA (r'''...''' ou '''...''' SEM prefixo f), e injete as cores via `.replace()` de
  tokens dedicados, OU use placeholders `{{{{TITLE}}}}` (4 chaves) na f-string.
- Após gerar, VALIDE o script: deve conter literalmente `var t="{{LAYOUT}}"`.
- Para corrigir em massa templates já quebrados: `re.sub(r'<script>.*?</script>', SCRIPT_CORRETO, c, flags=re.S)`.

## 5. PITFALLS de CSS/render
- O fundo (var(--bg)) precisa estar no **`body`** (`background:var(--bg)`), NÃO só em `:root`.
  `:root` define a variável, mas se o body não aplica, o render sai com a cor padrão (branco).
- Valide por histograma (a cor de fundo esperada no topo) + OCR (texto presente).

## 6. Loop de validação por template
Para cada subpasta: preencher placeholders → render 1080×1350 → checar `bg_ok`
(top-N histograma contém a cor esperada) e `text_ok` (OCR acha "Sample"/"Title").
Correção em lote com regex quando todos quebram igual.

## 7. Inspeção rápida quando o render sai em branco
Se o PNG tiver só a cor de fundo e zero texto: abrir no browser (file:///) e ler no console:
- `getComputedStyle(section).display` → deve ser `flex` (se `none`, o script de layout quebrou).
- `document.querySelector('script').textContent` → conferir se `{{LAYOUT}}` sobreviveu.
- `getComputedStyle(document.body).backgroundColor` → conferir se o fundo aplicou.
