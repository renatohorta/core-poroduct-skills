---
name: universal-carousel
description: Skill autônoma de ponta a ponta. Analisa a entrada do usuário, escolhe o template de carrossel mais adequado (ou pede informações quando o contexto é insuficiente), edita conforme necessário, injeta o conteúdo, renderiza os slides em PNG (1080x1350px) e gera os entregáveis de publicação.
---

# Universal Branded Carousel Builder

Esta skill transforma qualquer entrada (URL de artigo, perfil do LinkedIn, CV, lista de filmes ou tema de busca) em um carrossel visualmente profissional de alto impacto (1080px x 1350px - proporção 4:5), aplicando injeção em templates HTML e exportação automática para PNG.

**Ponto central desta versão:** a skill escolhe o template mais adequado com base na ENTRADA do usuário, e não o contrário. Se a entrada não der contexto suficiente para decidir bem, a skill PERGUNTA antes de produzir.

---

## 0. Seleção Inteligente de Template (faça ANTES de qualquer coisa)

### 0.1 Ordem de decisão (precedência)
Decida o template nesta ordem:

1. **Pedido explícito de estilo** — se o usuário nomeia um estilo, tema ou referência (ex.: "template fashion", "dark minimalista", "estilo alegre", um screenshot/arquivo `.sketch`/`.ai`), isso TEM precedência sobre tudo. Use a referência fornecida ou o template correspondente.
2. **Identidade de marca (DESIGN.md)** — se existe `DESIGN.md` no projeto, ele define paleta/fontes/dimensões. Adapte o template escolhido à identidade dele (ou crie HTML custom).
3. **Contexto/tema do conteúdo** — cruze o assunto da entrada com o catálogo de templates abaixo e escolha o de melhor encaixe.
4. **Contexto insuficiente** — se não houver nem estilo pedido, nem DESIGN.md, nem tema claro, **PARE e pergunte ao usuário** (veja 0.3).

### 0.2 Catálogo de templates disponíveis
Os templates prontos vivem em:
`C:\Users\renat\AppData\Local\hermes\skills\creative\universal-carousel-template-creator\templates\<pasta>\slide.html`

Cada um tem vários layouts internos (via `{{LAYOUT}}` / `data-layout`). Mapeamento por contexto de uso:

| Template (pasta) | Melhor para | Tema/cores | Layouts | Fontes |
|---|---|---|---|---|
| `swoosh-orange` | Slide único/capa simples de impacto | Laranja #FC6F15 + faixa decorativa | 1 (cover) | Inter |
| `sketch-dark-light` | Carrossel corporativo genérico; 9 tipos de slide (cover, título, lista, quote, links, good/bad, closing) em tema dark OU light | Dark #1A1A1A / Light #F0F5F4 | 0–8 | Inter |
| `freepik-constellation` | Astrologia/constelações, espiritual, "origem/começos", capa lírica | Lavanda #CDC4FB | A B B2 C D | Poppins |
| `freepik-t1-montserrat` | Mockup de post do Instagram (UI real: avatar, likes, comentários); conteúdo que quer parecer "post" | Dark/Light | title list cta | Montserrat |
| `freepik-t2-gilroy` | Marca vibrante/coral; adaptável, energia e movimento | Coral #FF6148 | cover intro list quote cta | Montserrat, Lobster |
| `freepik-t3-fashion` | Moda/loja/e-commerce; vitrine de produtos e preços | Bege #F3EBDE elegante | hero arrivals price feature brand | Raleway, Bodoni, script |
| `freepik-t4-apartment` | Decoração/interiores, estilo de vida, "how to" | Sage #D2DBBE | hero card list quote cta | Abril Fatface, Roboto |
| `freepik-t5-lorem` | Café/chocolate/aconchego, editorial quente | Marrom #844C19 | hero card list quote cta | Abhaya Libre, Poppins |
| `freepik-t6-chairs` | Móveis/produtos físicos, catálogo | Creme #FFEABB | hero products feature cta | Abhaya, Great Vibes, Josefin |
| `freepik-t7-company` | Empresarial/serviços B2B, clean | Rosa #FEEBEF suave | hero card list cta | Libre Baskerville, Montserrat |
| `freepik-t8-newcollection` | Tech moderno, dark + neon, lançamento | Dark oliva + lima #D4F828 | hero card list cta | Poppins, Montserrat |
| `freepik-t9-photos` | Publicidade forte, alto contraste | Navy #021E57 + red #D30045 | hero card list cta | Bebas Neue, Great Vibes |
| `freepik-t10-bebas` | Estilo "app/post", índigo suave | Índigo #C4CEFF | hero card list cta | Bebas Neue, Great Vibes |
| `freepik-t11-pet` | Pet/cachorro, dicas, conteúdo leve e fofo | Bege #E4B97A | hero tips card cta | Gaegu, Poppins |
| `crewbotics-beige-orange` | Microblog/branding, bege + laranja (Harper Russo) | Bege #EEE3D5 + laranja #E8893C | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-bw-productivity` | Produtividade/time block, preto e branco | P&B #090706 | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-bw-marketing-tips` | Dicas de marketing, P&B minimalista | P&B #040405 | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-bw-red` | Personal branding, P&B + vermelho (Daniel Gallego) | P&B #140D0F + vermelho #D32F2F | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-blue-running` | Dicas de corrida, azul dinâmico (Borchelle) | Azul #0F1897 | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-green-business` | Como começar um negócio, verde (Salford & Co.) | Verde #27452A | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-orange-social` | Dicas de mídia social, laranja (Connor Hamilton) | Laranja #FD6F15 | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-orange-black` | Branding, laranja/preto (Harper Russo) | Laranja #B13713 + claro #F2E9EB | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-purple-marketing` | Marketing moderno + IA, roxo/preto/branco | Roxo #B4AEDD + escuro #1A1B1B | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-sage-advertising` | O que saber antes de anunciar, sage | Sage #626048 | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-yellow-black` | Microblog marketing, amarelo/preto (Harper Russo) | Amarelo #E3BF2A + claro #F6F1ED | cover intro steps list cta | Montserrat, Poppins |
| `crewbotics-yellow-green-habits` | Dicas de hábitos, amarelo/verde (Thynk Unlimited) | Verde-oliva #2D2611 | cover intro steps list cta | Montserrat, Poppins |

> **Fonte dos templates `crewbotics-*`:** reconstruídos a partir dos SVGs em
> `C:\Users\renat\Downloads\templates_crewbotics\<diretório>\` (um carrossel por diretório). Cada
> um usa os placeholders padrão `{{TITLE}} {{BODY}} {{EYEBROW}} {{HANDLE}} {{SLIDE_NUM}} {{TOTAL_SLIDES}}
> {{NEXT_LABEL}} {{PROMPT}} {{ITEM_1..3_TITLE}} {{ITEM_1..3_BODY}} {{LAYOUT}}` e as fontes
> Montserrat/Poppins de `_shared_fonts/`.

**Se NENHUM template do catálogo encaixar** (ex.: identidade muito específica, foto de perfil como referência, marca própria), crie um HTML customizado a partir do `DESIGN.md` (veja seções 1, 4 e os blocos "Criar identidade a partir de foto" / "Carrossel pessoal de carreira").

### 0.3 Quando perguntar ao usuário (NÃO adivinhar)
Antes de produzir, se qualquer um destes faltar, **faça uma pergunta objetiva** (use `clarify` ou pergunte direto no chat) em vez de chutar:
- **Tema/assunto** claro do carrossel (o que é, para quem).
- **Estilo visual** desejado (se não houver referência/DESIGN.md): escuro executivo, claro/alegre, minimalista, fashion, etc.
- **Plataforma** (Instagram, LinkedIn, ambos) e **handle/nome de autor** para o rodapé.
- **Quantidade de slides** (5–10 por padrão, mas confirme se for crítico).
- **Elementos específicos** já pedidos anteriormente (ex.: ganchos de comentário, foto de perfil, slide final enxuto).

Exemplo de pergunta: *"Vi que você não indicou o estilo. Prefere uma versão escura executiva, clara/alegre, ou outro tema? E o handle para o rodapé?"*

### 0.4 Edição do template conforme necessário
Após escolher o template:
1. Leia o `slide.html` para mapear os placeholders exatos que ele usa (nem todos são iguais — veja `{{THEME}}`, `{{TITLE_L1}}`, `{{SCRIPT}}`, `{{PRICE}}`, etc.).
2. Edite conforme o necessário: troque cores/fontes para casar com `DESIGN.md` ou com o pedido, adapte layouts, e injete o conteúdo.
3. Só então renderize.

---

## 1. Gestão Automática de Templates de Design e Voz (`DESIGN.md` e `VOICE.md`)

Antes de processar o conteúdo, a skill deve verificar e gerenciar as diretrizes de marca:

1. **Verificação do `DESIGN.md` (Identidade Visual):**
   - Verifique se o arquivo `DESIGN.md` existe na raiz do projeto.
   - **Caso NÃO exista:** Crie o arquivo `DESIGN.md` na raiz com o seguinte template base:
     ```markdown
     # Design System - Carousel

     ## Cores
     - Background: `#09090b` (Dark Zinc)
     - Primary / Text: `#ffffff` (White)
     - Secondary / Text: `#a1a1aa` (Zinc 400)
     - Accent: `#6366f1` (Indigo 500)
     - Border: `#27272a` (Zinc 800)

     ## Tipografia
     - Font Family: `'Inter', sans-serif`
     - Title Size: `64px`
     - Body Size: `32px`

     ## Dimensões do Carrossel
     - Ratio: `4:5` (Instagram/LinkedIn)
     - Resolution: `1080px × 1350px`
     ```

2. **Verificação do `VOICE.md` (Tom de Voz):**
   - Verifique se o arquivo `VOICE.md` existe na raiz do projeto.
   - **Caso NÃO exista:** Crie o arquivo `VOICE.md` na raiz com o seguinte template base:
     ```markdown
     # Brand Voice & Copy Guidelines

     ## Tom de Voz
     - Claro, executivo, direto e sem rodeios.
     - Focado em entregar valor prático nas primeiras linhas.

     ## Regras de Copy para Carrossel
     - **Slide 1 (Hook):** Máximo de 12 palavras. Forte impacto visual e gancho de curiosidade.
     - **Slides Internos:** Máximo de 25 a 30 palavras por slide. Frases curtas e escaneáveis.
     - **CTA Final:** Objetivo, direcionando para salvar, comentar ou conectar.
     ```

3. **Reutilização:** Se os arquivos já existirem, leia as regras personalizadas contidas neles para guiar a criação do texto e os estilos dos templates HTML.

---

## 2. Web Crawling & Coleta de Dados
1. **Fontes de Entrada:**
   - Se o usuário fornecer um **link/URL** (Substack, LinkedIn, artigo de notícias, CV online), utilize comandos de terminal (`curl`, `puppeteer`, `playwright` ou scripts em Python com `BeautifulSoup`) para ler o conteúdo na íntegra.
   - Se o usuário fornecer um **arquivo local** ou **texto direto** (ex: currículo, resumo de livro, transcrição), processe o texto nativamente.
   - Se o usuário fornecer apenas um **tema** (ex: "lançamentos de filmes em streaming"), realize buscas na web para extrair informações atualizadas, datas, fontes e dados relevantes.

---

## 3. Roteirização dos Slides (Slide Framework)
Divida o conteúdo extraído em uma sequência lógica de **5 a 10 slides**, respeitando as diretrizes do `VOICE.md`:
- **Slide 1 (Capa / Hook):** Título magnético e direto ao ponto + Subtítulo de autoridade ou curiosidade.
- **Slide 2 (A Dor / O Problema / O Contexto):** Apresenta o problema ou a premissa central.
- **Slides 3 a N (Passos / A Lista / O Conteúdo Core):** 1 ideia ou item por slide. **Regra de ouro:** no máximo 25 a 30 palavras por slide para garantir legibilidade mobile.
- **Slide N+1 (A Transformação / Resultado):** Síntese do valor entregue.
- **Slide Final (CTA / Chamada para Ação):** Chamada para ação limpa (ex: salvar o post, conectar no LinkedIn, comentar uma palavra-chave).

---

## 4. Seleção de Template HTML e Injeção de Conteúdo
1. **Localização do Template:** use o catálogo da **Seção 0** para escolher a pasta em `universal-carousel-template-creator/templates/`. Se o usuário solicitar um estilo específico ou template da web (ex: "template dark minimalista do GitHub"), faça o download/clone dos arquivos HTML/CSS públicos.
2. **Leia o template antes de injetar:** identifique quais placeholders ele usa de fato (a lista abaixo é genérica; cada template pode ter os próprios — `{{THEME}}`, `{{TITLE_L1}}`, `{{SCRIPT}}`, `{{PRICE}}`, `{{CTA_LABEL}}`, etc.).
3. **Substituição de Placeholders:**
   Para cada slide estruturado, substitua os parâmetros no HTML:
   - `{{TITLE}}`: Título principal do slide.
   - `{{BODY}}`: Texto explicativo ou marcadores.
   - `{{SLIDE_NUM}}`: Número atual do slide (ex: `01`).
   - `{{TOTAL_SLIDES}}`: Total de slides (ex: `07`).
   - `{{AUTHOR_NAME}}`: Nome do autor (padrão do `DESIGN.md` ou do usuário).
   - `{{AUTHOR_HANDLE}}`: Usuário das redes (ex: `@renatohorta`).
   - `{{TAGLINE}}`: Categoria ou assunto fixo no rodapé.
   - `{{LAYOUT}}`: qual layout interno ativar (definido por `data-layout` no HTML).
   - Extras por template (conforme identificados na leitura): `{{EYEBROW}}`, `{{THEME}}`, `{{PRICE}}`, `{{ITEM_N}}`, `{{ITEM_N_TITLE}}`, `{{ITEM_N_BODY}}`, `{{QUOTE_EMOJI}}`, `{{SCRIPT}}`, etc.

---

## 5. Renderização Automática para PNG (Playwright/Puppeteer)
1. Execute um script Headless (Python ou Node.js com `playwright`/`puppeteer`) configurado para a viewport exata de **1080px × 1350px**.
2. Abra cada slide HTML preenchido e tire um print (screenshot).
3. Salve as imagens geradas diretamente na pasta `./carrossel_output/`:
   - `slide_01.png`
   - `slide_02.png`
   - ...

> **Fallback Chrome headless:** se o Playwright estiver instalado mas sem navegador baixado,
> renderize com o Chrome do sistema (confirme `C:\Program Files\Google\Chrome\Application\chrome.exe`):
> ```
> chrome.exe --headless=new --disable-gpu --hide-scrollbars \
>   --window-size=1080,1350 --force-device-scale-factor=1 --screenshot=out.png file:///CAMINHO/slide.html
> ```
> O HTML de cada slide precisa de `html,body{width:1080px;height:1350px;overflow:hidden}` para o
> screenshot capturar exatamente 1 slide.

> **PITFALL — caminhos relativos de assets quebram silenciosamente.** Se os HTMLs dos slides são
> gravados numa subpasta (ex.: `slides_html/`) mas fotos/fontes ficam em `assets/` ou `assets/fonts/`
> na raiz do projeto, os URLs relativos DEVEM usar `../assets/...` (não `assets/...`). Com caminho
> errado, a foto não aparece no PNG mas o Chrome NÃO reporta erro — o slide parece OK por OCR.
> Detecte isso validando o render por histograma (procurar os tons da foto/paleta) além do OCR.
> Alternativa mais simples: grave os HTMLs injetados na raiz (mesmo nível de `assets/`) para usar
> caminhos curtos, ou use caminhos absolutos `file:///`.

> **VALIDAR SEMPRE: OCR + histograma.** Depois de renderizar, rode tesseract (`--psm 3`) no PNG
> para confirmar o texto e compare o histograma de cores (quantize + Counter) com a paleta esperada
> do `DESIGN.md` ou do template escolhido. A foto/imagem do slide confirma-se pela presença dos tons
> correspondentes na paleta do render. Nunca entregue sem esta checagem — pega foto ausente e fonte
> não carregada.

> **Criar identidade visual a partir de uma foto de perfil:** quando o usuário fornece só uma foto
> (ex.: `retrato.jpg`) como referência, extraia a paleta dela (`Image.quantize(colors=N)`) e derive
> o `DESIGN.md` — ex.: fundo graphite escuro do fundo da foto + acento terracota quente dos tons de
> pele. Use essa paleta no template em vez do padrão dark-zinc/indigo.

> **Carrossel pessoal de carreira (líder de tech + IA):** ver `references/tech-leader-ai-carousel.md`
> — framework de 7 slides (hook → dor → números → framework → produto → engenharia → CTA), ganchos
> de comentário por slide, versão escura + versão "alegre", e as regras duras do usuário (handle
> `@renato.academy`, slide final enxuto sem "salve/comente/te marcar", editar só o slide pedido).
> Para este caso, o encaixe é **HTML customizado** (não os templates `freepik-*`), a menos que o
> usuário peça explicitamente um estilo daquele catálogo.

> **Cards de lançamento (lista de itens com data):** ver `references/cards-de-lancamento.md`
> — layout de card 1080x1350 (fundo graphite + arte estilizada meio transparente à esquerda +
> título/data à direita), regra de ouro de oferecer arte estilizada (gradiente + emoji) via
> `clarify` quando não há imagem real, e validação por OCR + amostragem de pixels.

---

## 6. Arquivo de Entrega e Saída
Crie a pasta `./carrossel_output/` e grave o arquivo `CARROSSEL.md` contendo:
1. **Fontes & Links:** Lista de fontes pesquisadas durante o crawling.
2. **Roteiro dos Slides:** Mapeamento do texto exato contido em cada `slide_XX.png`.
3. **Copy de Legenda:** Texto para Instagram e LinkedIn pronto para publicar, alinhado ao `VOICE.md`.

### Retorno no Terminal:
Ao concluir a execução:
1. Confirme se os arquivos `DESIGN.md` e `VOICE.md` foram identificados ou gerados/atualizados.
2. Informe qual template foi escolhido e por quê (ou se foi criado HTML customizado), e o que foi editado.
3. Informe que os PNGs e o arquivo `CARROSSEL.md` foram gerados na pasta `./carrossel_output/`.
4. Exiba a lista dos arquivos PNG salvos.
5. Imprima a legenda final no terminal para rápida cópia.
