---
name: universal-carousel-template-creator
description: Skill autônoma de ponta a ponta. Realiza crawling de conteúdo da web/arquivos locais, seleciona e aplica templates HTML/CSS de carrossel, injeta o texto gerado, renderiza os slides em PNG (1080x1350px) e gera os entregáveis de publicação.
---

# Universal Branded Carousel Builder

Esta skill transforma qualquer entrada (URL de artigo, perfil do LinkedIn, CV, lista de filmes ou tema de busca) em um carrossel visualmente profissional de alto impacto (1080px x 1350px - proporção 4:5), aplicando injeção em templates HTML e exportação automática para PNG.

---

## 1. Web Crawling & Coleta de Dados
1. **Fontes de Entrada:**
   - Se o usuário fornecer um **link/URL** (Substack, LinkedIn, artigo de notícias, CV online), utilize comandos de terminal (`curl`, `puppeteer`, `playwright` ou scripts em Python com `BeautifulSoup`) para ler o conteúdo na íntegra.
   - Se o usuário fornecer um **arquivo local** ou **texto direto** (ex: currículo, resumo de livro, transcrição), processe o texto nativamente.
   - Se o usuário fornecer apenas um **tema** (ex: "lançamentos de filmes em streaming"), realize buscas na web para extrair informações atualizadas, datas, fontes e dados relevantes.

---

## 2. Leitura de Identidade Visual e Voz
1. **Brand DNA / Sistema de Design (`DESIGN.md`):**
   - Verifique se existe um arquivo `DESIGN.md` na pasta do projeto.
   - Se existir, extraia as cores (código Hex), fontes e estilos de layout.
2. **Tom de Voz (`VOICE.md`):**
   - Verifique se existe um arquivo `VOICE.md`. Caso positivo, adote o estilo de escrita da marca (ex: direto, provocações, linguagem executiva).

---

## 3. Roteirização dos Slides (Slide Framework)
Divida o conteúdo extraído em uma sequência lógica de **5 a 10 slides**:
- **Slide 1 (Capa / Hook):** Título magnético e direto ao ponto + Subtítulo de autoridade ou curiosidade.
- **Slide 2 (A Dor / O Problema / O Contexto):** Apresenta o problema ou a premissa central.
- **Slides 3 a N (Passos / A Lista / O Conteúdo Core):** 1 ideia ou item por slide. **Regra de ouro:** no máximo 25 a 30 palavras por slide para garantir legibilidade mobile.
- **Slide N+1 (A Transformação / Resultado):** Síntese do valor entregue.
- **Slide Final (CTA / Chamada para Ação):** Chamada para ação limpa (ex: salvar o post, conectar no LinkedIn, comentar uma palavra-chave).

---

## 4. Seleção de Template HTML e Injeção de Conteúdo
1. **Localização do Template:**
   - Busque por templates na pasta `./templates/` do projeto (ex: `./templates/minimal-dark/slide.html`).
   - Se o usuário solicitar um template da web (ex: "template dark minimalista do GitHub"), faça o download/clone dos arquivos HTML/CSS públicos.
2. **Substituição de Placeholders:**
   Para cada slide estruturado, substitua os parâmetros no HTML:
   - `{{TITLE}}`: Título principal do slide.
   - `{{BODY}}`: Texto explicativo ou marcadores.
   - `{{SLIDE_NUM}}`: Número atual do slide (ex: `01`).
   - `{{TOTAL_SLIDES}}`: Total de slides (ex: `07`).
   - `{{AUTHOR_NAME}}`: Nome do autor (padrão do `DESIGN.md` ou do usuário).
   - `{{AUTHOR_HANDLE}}`: Usuário das redes (ex: `@renatohorta`).
   - `{{TAGLINE}}`: Categoria ou assunto fixo no rodapé.
   
   A lista de placeholders **não é fixa** — templates podem definir placeholders próprios
   (ex.: `{{KICKER}}`, `{{SUBTITLE}}` num template de capa). Leia o template antes de injetar
   e substitua exatamente os tokens que ele contém.

---

## 5. Renderização Automática para PNG (Playwright/Puppeteer)
1. Execute um script Headless (Python ou Node.js com `playwright`/`puppeteer`) configurado para a viewport exata de **1080px × 1350px**.
2. Abra cada slide HTML preenchido e tire um print (screenshot).
3. Salve as imagens geradas diretamente na pasta `./carrossel_output/`:
   - `slide_01.png`
   - `slide_02.png`
   - ...

> **Fallback:** se o Playwright estiver instalado mas sem navegador baixado, renderize com o
> Chrome/Edge do sistema via `--headless=new --window-size=1080,1350 --force-device-scale-factor=1
> --screenshot=out.png file:///...`. O HTML do slide precisa de `html,body{width:1080px;height:1350px;overflow:hidden}`.
>
> **Criar template a partir de um screenshot de referência sem visão:** ver
> `references/design-reconstruction-from-image.md` — receita de OCR (tesseract) + extração de
> paleta/posição/silhueta + verificação por histograma.
>
> **Criar template a partir de um arquivo `.sketch` (Sketch app):** ver
> `references/design-reconstruction-from-sketch.md` — o .sketch é um ZIP com JSON; extraia
> textos/estilos/símbolos/cores/posições objetivamente (sem visão). Cobre artboards Dark/Light,
> fontes InterV_* e símbolos Header/Footer.
>
> **Criar template a partir de um pacote Freepik/design package (`.ai`/`.eps`/`.jpg`/`.txt`):** ver
> `references/design-reconstruction-from-design-package.md` — o `.ai` é um PDF (não ZIP); o JPG de
> preview é a fonte autoritativa (costuma ser um grid de slides); extraia fontes via regex `FontName`
> no .ai e baixe-as do Google Fonts; ignore as fotos stock listadas no `.txt`.
> Para baixar as fontes de forma reproduzível (incluindo variáveis tipo Montserrat/Raleway/Roboto
> Condensed, que 404 no repo estático), rode `scripts/download_google_fonts.py` — cobre os dois
> caminhos: repo `google/fonts` (estático) e CSS2 API (variáveis, via User-Agent simples).
> ignore as fotos stock listadas no `.txt`.
>
> **Pasta cheia de zips (MUITOS templates de uma vez):** ver
> `references/batch-multi-template-reconstruction.md` — inventário, grid de slides por preview,
> fontes numa pasta `_shared_fonts/` compartilhada, um `slide.html` padronizado por template com
> layouts/placeholders comuns, loop de validação por render, e o pitfall de caminho `../_shared_fonts/`
> e de delegação (subagentes sem `execute_code` não reconstroem imagem).
>
> **Pasta cheia de SVGs de carrossel (cada subpasta = um carrossel de N slides):** ver
> `references/design-reconstruction-from-svg-carousel.md` — o texto vem como PATHS, não `<text>`
> (extraia por OCR do SVG renderizado via Chrome, não lendo o XML); paleta por quantize do render;
> PITFALL crítico: gerar o HTML com f-string consome um nível de chaves e quebra os placeholders
> `{{TITLE}}`/`{{LAYOUT}}` — use string crua + `.replace()`, valide que o `<script>` contém
> literalmente `var t="{{LAYOUT}}"`, e aplique o fundo no `body` (não só em `:root`).
>
> **Criar templates a partir de MUITOS zips de uma vez (pasta com vários pacotes Freepik):** ver
> `references/design-reconstruction-multi-zip-batch.md` — faça inline com `execute_code` (NÃO delegue
> a subagentes, que não recebem `execute_code`); use a API CSS2 do Google Fonts para `.ttf` de fontes
> variáveis (caminhos estáticos 404); uma pasta `templates/_shared_fonts/` compartilhada (pitfall:
> caminho relativo é `../_shared_fonts/`, não `../../`); template multi-layout reutilizável; loop de
> validação por histograma+OCR.

---

## 6. Arquivo de Entrega e Saída
Crie a pasta `./carrossel_output/` e grave o arquivo `CARROSSEL.md` contendo:
1. **Fontes & Links:** Lista de fontes pesquisadas durante o crawling.
2. **Roteiro dos Slides:** Mapeamento do texto exato contido em cada `slide_XX.png`.
3. **Copy de Legenda:** Texto para Instagram e LinkedIn pronto para publicar, com emojis e hashtags.

### Retorno no Terminal:
Ao concluir a execução:
1. Informe que os PNGs e o arquivo `CARROSSEL.md` foram gerados na pasta `./carrossel_output/`.
2. Exiba a lista dos arquivos PNG salvos.
3. Imprima a legenda final no terminal para rápida cópia.
