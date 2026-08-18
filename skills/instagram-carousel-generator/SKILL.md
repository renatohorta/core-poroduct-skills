---
name: instagram-carousel-generator
description: Skill para geração de conteúdo e especificação visual de carrosséis do Instagram (1080x1350) no estilo "Modern Minimalist Coral" (editorial, textura de papel e destaques em laranja/coral).
version: 1.0.0
---

# Instagram Carousel Generator Skill

Esta especificação define o padrão completo para a criação de carrosséis do Instagram no formato **Modern Minimalist Coral**. O objetivo desta skill é receber um tema, assunto ou texto bruto e transformá-lo em uma estrutura JSON válida e parametrizada para renderização visual em alta resolução (1080x1350px).

---

## 1. Visão Geral do Template: Modern Minimalist Coral

### Estética e Conceito Visual
- **Estilo:** Editorial moderno, minimalista, com ar artesanal e sofisticado.
- **Formato:** Instagram Portrait 4:5 (`1080px` x `1350px`).
- **Fundo:** Textura suave de papel artesanal bege/creme (`#F2EDE4`).
- **Paleta de Cores:**
  - **Texto Principal (Titles & Base):** `#0D0D0D` (Preto/Grafite profundo).
  - **Cor de Destaque (Accent):** `#FF522B` (Laranja/Coral vibrante).
  - **Caixa de Destaque (Highlight Box):** Bloco retangular `#FF522B` com texto interno `#0D0D0D` (ou `#FFFFFF`) garantindo alto contraste.

### Tipografia
- **Títulos (Headings):** Sans-serif / Serif pesada em caixa alta.
  - Exemplo de fontes: `Syne ExtraBold`, `Montserrat Black`, `Arial Black`.
  - Transformação: `UPPERCASE`
  - Entrelinha (Line Height): `0.9` a `1.0` (Efeito denso e impactante).
  - Comprimento máximo da linha: 12-14 caracteres por linha.
- **Corpo do Texto (Body / Highlight Text):** Sans-serif moderna e legível.
  - Exemplo de fontes: `Inter`, `DM Sans`, `SF Pro Display`.
  - Tamanho de fonte: `32px` - `38px`
  - Peso: `500 (Medium)`
  - Estilo: Encapsulado dentro de um bloco preenchido (`padding: 12px 20px`, `border-radius: 2px`).
- **Moldura Fixa (Header & Footer):** Sans-serif discreta.
  - Tamanho: `24px`
  - Peso: `Medium / Regular`
  - Espaçamento entre letras: `0.05em`

### Elementos Decorativos Vetoriais (SVG Assets)
Os vetores decorativos são estáticos e ficam armazenados na biblioteca de assets da skill:
1. `arrow-dashed-curve.svg`: Seta pontilhada em curva para indicar direção.
2. `arrow-loop.svg`: Seta pontilhada em looping.
3. `underline-brush.svg`: Linha pincelada para sublinhar títulos de capa.
4. `bookmark-icon.svg`: Ícone de "Salvar" (Bookmark) em estilo outline de 3px para o slide de CTA.

---

## 2. Moldura Estática Fixa (Static Framework Grid)

Todos os slides compartilham elementos fixos nos quatro cantos da tela, estabelecendo consistência de marca:

- **Margens de Segurança (Safe Area):** Top/Bottom: `90px`, Left/Right: `90px`.
- **Topo Esquerdo (Top: 90px, Left: 90px):** Nome do Autor (`author_name`, ex: `HARPER RUSSO`)
- **Topo Direito (Top: 90px, Right: 90px):** Categoria/Hashtag (`category_hashtag`, ex: `#branding`)
- **Rodapé Esquerdo (Bottom: 90px, Left: 90px):** Handle / Rede Social (`handle`, ex: `@reallygreatsite`)
- **Rodapé Direito (Bottom: 90px, Right: 90px):** Ano / Edição (`year`, ex: `2025`)

---

## 3. Variações de Layout (Slide Layout Types)

O carrossel possui 3 variações de layout que a skill deve atribuir a depender da função do slide na narrativa:

### Layout A: `cover` (Slide 1 - Capa / Hook)
- **Objetivo:** Prender a atenção imediatamente no feed.
- **Elementos:**
  - Título em grande formato (4 a 5 linhas em caixa alta).
  - Pincelada sublinhando a última linha (`underline_accent: true`).
  - Seta em looping no canto inferior direito apontando para a direita (`arrow_type: "loop_bottom_right"`).

### Layout B: `content` (Slides 2 a N-1 - Desenvolvimento)
- **Objetivo:** Explicar o conceito de forma direta e escaneável.
- **Elementos:**
  - Título da Seção (2 a 4 linhas em caixa alta).
  - Parágrafo explicativo em caixa com fundo laranja coral (`body_text`).
  - Seta pontilhada apontando diretamente para o bloco de texto (`arrow_type: "pointing_left"` ou `"pointing_right"`).

### Layout C: `cta` (Último Slide - Chamada para Ação)
- **Objetivo:** Converter visualização em salvamentos e compartilhamentos.
- **Elementos:**
  - Frase de ação direta em caixa alta (ex: `DON'T FORGET TO SAVE THIS POST`).
  - Ícone de Bookmark (Salvar) em linha coral à direita do título (`show_bookmark_icon: true`).
  - Seta apontando para o ícone (`arrow_type: "pointing_left"`).

---

## 4. Estrutura de Arquivos da Skill

```text
instagram-carousel-skill/
├── SKILL.md                  # Especificação e manual da skill (este arquivo)
├── config.json               # Configurações globais (dimensões, exportação)
│
├── templates/                # Especificações de design dos templates
│   ├── modern-minimal-coral.md
│   └── templates-index.json
│
├── assets/                   # Recursos estáticos
│   ├── fonts/                # Arquivos de fonte (.ttf / .woff2)
│   │   ├── Syne-ExtraBold.ttf
│   │   └── Inter-Medium.ttf
│   ├── textures/             # Texturas de fundo
│   │   └── paper-texture.png
│   └── vectors/              # Vetores SVGs reutilizáveis
│       ├── arrow-dashed-curve.svg
│       ├── arrow-loop.svg
│       ├── underline-brush.svg
│       └── bookmark-icon.svg
│
├── src/                      # Código fonte
│   ├── generator/            # Lógica de IA e validação de schema
│   │   ├── prompt-builder.js
│   │   └── schema-validator.js
│   │
│   └── renderer/             # Engine de renderização de imagem
│       ├── html-template.js
│       └── image-exporter.js
│
└── examples/                 # Exemplos de uso e saídas
    ├── input-topic.txt
    ├── generated-content.json
    └── output-slides/
```

---

## 5. Schema JSON de Saída (Output Contract)

Toda geração de conteúdo realizada por esta skill **deve obrigatoriamente** retornar um JSON válido seguindo a estrutura abaixo:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "InstagramCarouselContent",
  "type": "object",
  "properties": {
    "template_id": {
      "type": "string",
      "enum": ["modern-minimal-coral"]
    },
    "meta": {
      "type": "object",
      "properties": {
        "author_name": { "type": "string" },
        "category_hashtag": { "type": "string" },
        "handle": { "type": "string" },
        "year": { "type": "string" }
      },
      "required": ["author_name", "category_hashtag", "handle", "year"]
    },
    "slides": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "slide_number": { "type": "integer" },
          "layout_type": {
            "type": "string",
            "enum": ["cover", "content", "cta"]
          },
          "title": { "type": "string" },
          "body_text": { "type": "string" },
          "underline_accent": { "type": "boolean" },
          "show_bookmark_icon": { "type": "boolean" },
          "arrow_type": {
            "type": "string",
            "enum": ["loop_bottom_right", "pointing_left", "pointing_right", "pointing_up_left", "none"]
          }
        },
        "required": ["slide_number", "layout_type", "title"]
      }
    }
  },
  "required": ["template_id", "meta", "slides"]
}
```

---

## 6. Exemplo Prático de JSON Gerado

```json
{
  "template_id": "modern-minimal-coral",
  "meta": {
    "author_name": "HARPER RUSSO",
    "category_hashtag": "#branding",
    "handle": "@reallygreatsite",
    "year": "2025"
  },
  "slides": [
    {
      "slide_number": 1,
      "layout_type": "cover",
      "title": "BRANDING\nIS MORE\nTHAN JUST\nLOOKS",
      "underline_accent": true,
      "arrow_type": "loop_bottom_right"
    },
    {
      "slide_number": 2,
      "layout_type": "content",
      "title": "WHAT\nBRANDING\nREALLY\nMEANS",
      "body_text": "Branding is how people feel about your business. It's the emotion, trust, and consistency that make them remember you.",
      "arrow_type": "pointing_left"
    },
    {
      "slide_number": 3,
      "layout_type": "content",
      "title": "THE\nINVISIBLE\nELEMENTS",
      "body_text": "Your tone, personality, values, and customer experience all work together to shape your brand identity and how people remember you.",
      "arrow_type": "pointing_left"
    },
    {
      "slide_number": 4,
      "layout_type": "content",
      "title": "BEYOND\nAESTHETICS",
      "body_text": "A beautiful brand can attract attention, but a meaningful one creates connection. That's what keeps people coming back again and again.",
      "arrow_type": "pointing_left"
    },
    {
      "slide_number": 5,
      "layout_type": "content",
      "title": "WHY IT\nMATTERS",
      "body_text": "When your brand communicates clearly and feels authentic, people don't just buy from you, they believe in your mission and story.",
      "arrow_type": "pointing_up_left"
    },
    {
      "slide_number": 6,
      "layout_type": "cta",
      "title": "DON'T\nFORGET\nTO SAVE\nTHIS POST",
      "show_bookmark_icon": true,
      "arrow_type": "pointing_left"
    }
  ]
}
```

---

## 7. Instruções para o LLM (Prompt Instructions)

Ao gerar o conteúdo para este carrossel:
1. **Quebra de linha dos títulos:** Insira sempre `\n` mantendo entre 2 a 4 palavras por linha para preservar o alinhamento visual do template.
2. **Tamanho do corpo do texto:** Limite o campo `body_text` em no máximo 30 palavras para garantir o encaixe perfeito na caixa de destaque laranja.
3. **Coerência da Narrative:**
   - Slide 1 (Capa): Provoca curiosidade e define a tese.
   - Slides intermediários: Desenvolvem o tema em tópicos acionáveis.
   - Slide Final (CTA): Instiga a ação de salvar o post.

---

## 8. Renderização e Fallback de Imagens

### 8.1 Quando não há imagens reais (lançamentos futuros, produtos não lançados)
Se o usuário pedir "foto do jogo/produto" mas não existirem imagens oficiais
disponíveis, **não** buscar na web nem pedir arquivos por padrão. Gere **arte
estilizada** como fallback: gradiente de cor temática + emoji representativo,
meio transparente (alpha ~0.55) à esquerda, com título e data em branco à
direita. Confirme a escolha com o usuário via `clarify` se houver dúvida, mas
a arte estilizada é o fallback aceito.

### 8.2 Pipeline de renderização (Pillow)
Para renderizar cards 1080x1350 em PNG sem depender de Chrome/HTML, use PIL
via `execute_code` (funciona mesmo quando write_file/terminal falham no host).
Detalhes completos (gradiente de fundo, layer de arte transparente, fontes de
emoji, quebra de título, validação por OCR + amostragem de pixels) em:
`references/render-pipeline.md`

### 8.3 Fontes (cross-platform — NUNCA hardcode path de máquina)
Não use `C:\Windows\Fonts\...` fixo no código/produção (quebra no ECS/Linux e em
outros devs — usuário considera isso bug grave). Resolver de forma portátil:
- **Fontes:** prioridade fontes empacotadas no projeto/repo
  (`static/carousel_templates/fonts/*.ttf`) → fontes padrão do SO
  (`/usr/share/fonts/truetype/dejavu/...`) → `ImageFont.load_default()`.
- **Emoji:** procurar em diretórios padrão do SO (Windows/Linux/macOS) com
  fallback, não um arquivo fixo como `seguiemj.ttf`.
- **Tesseract (opcional):** `shutil.which("tesseract")` + env `TESSERACT_CMD`;
  se ausente, PULA o OCR (fallback pixels/arquivos) em vez de quebrar.
- Padrão completo: `deterministic-skill-executors/references/cross-platform-executors.md`.

### 8.4 Validar sempre
Depois de renderizar, rode tesseract (`--psm 3`) no PNG para confirmar texto
legível e amostre pixels para confirmar que a arte transparente está presente
sem sobrepor o texto.

### 8.4.1 Regra dura: TODO carrossel determinístico (decisão de Renato, 11/08/2026)

O usuário decidiu que **qualquer geração de carrossel deve cair no modelo
determinístico** — o LLM nunca desenha o layout. Se o usuário pedir template de
marca explicitamente, **ignorar**: renderizar TUDO no determinístico, sempre.

- O LLM só produz o JSON de conteúdo (slides/cards). Layout fica 100% no código.
- **Imagens POR SLIDE:** para destinos/lugares/produtos, o LLM preenche
  `slides[].image` com a URL/foto de cada item — o executor determinístico desenha
  a foto como fundo (cover + overlay escuro) mantendo o texto legível. Sem foto,
  usa gradiente/paleta. Detalhe em
  `references/crewbotics-deterministic-executor.md` (seção "Imagens POR SLIDE").
- Para o repo `crewbotics-back`, isso significa usar sempre o executor
  `chat/skills/executors/render_carousel.py` (PIL) — ver o detalhe completo
  (diagnóstico do caminho genérico "sage" vazio, sintomas, implementação) em
  `references/crewbotics-deterministic-executor.md`. As 12 specs de design por
  tema do crewbotics ficam em `chat/skills/carousel_specs/` (no repo), mapeando
  1:1 para os `template_id` de `carousel_templates.py` — fonte de estrutura ao
  criar/trabalhar carrossel do crewbotics.
- Em qualquer outro contexto de carrossel, aplicar o mesmo princípio: empacotar
  o renderizador como executor determinístico e dar instrução dura "NÃO escreva
  código; rode scripts/render_*.py", em vez de descrever o layout.

### 8.5 Determinismo entre ambientes (importante)
Se o mesmo conteúdo sair bom num ambiente e ruim em outro (ex.: sistema web),
a causa é o LLM desenhar o layout do zero. Para resultado consistente, empacote
o renderizador como um **executor determinístico** (script pronto que recebe o
JSON e gera os PNGs) e dê no SKILL.md uma **instrução dura** apontando para ele
("NÃO escreva código. Rode `scripts/render_carousel.py --input dados.json`"),
em vez de descrever o layout. O LLM só gera o JSON de dados; o layout fica no
código. Ver o padrão completo em `deterministic-skill-executors`.
