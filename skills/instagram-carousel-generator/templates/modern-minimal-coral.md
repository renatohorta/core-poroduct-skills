---
template_id: modern-minimal-coral
name: Minimalist Editorial Coral
description: Template moderno estilo editorial com fundo de textura de papel, tipografia bold em caixa alta e destaques em bloco laranja.
version: 1.0.0
aspect_ratio: 4:5 (1080x1350)
---

# Template Specification: Modern Minimalist Coral

## 1. Visual Identity & Tokens

### Colors
- **Background:** `#F2EDE4` (Textura de papel bege claro)
- **Primary Text:** `#0D0D0D` (Preto profundo / quase preto)
- **Accent Color:** `#FF522B` (Laranja/Coral vibrante)
- **Accent Text Color:** `#0D0D0D` ou `#FFFFFF` (Dependendo do contraste do bloco)

### Typography
- **Header Top & Footer:** `Inter`, `Montserrat` ou `Helvetica Neue`
  - Size: `24px`
  - Weight: `Medium / Regular`
  - Letter Spacing: `0.05em`
- **Slide Headings (Titles):** `Syne`, `Montserrat ExtraBold` ou `Arial Black`
  - Transform: `UPPERCASE`
  - Line Height: `0.9` a `1.0` (Entrelinha ajustada)
  - Weight: `900 (Black)`
  - Max line length: 12-14 caracteres por linha
- **Body / Highlight Text:** `Inter`, `DM Sans` ou `SF Pro Display`
  - Size: `32px` - `38px`
  - Weight: `500 (Medium)`
  - Style: Bloco com background `#FF522B` (Padding: `12px 20px`, Border-radius: `2px`)

### Decorative Vector Assets (SVG)
1. `arrow-dashed-curve.svg`: Seta pontilhada em arco.
2. `arrow-loop.svg`: Seta em curva fluida/looping.
3. `underline-brush.svg`: Linha de destaque sublinhando a última linha do título de capa.
4. `bookmark-icon.svg`: Ícone de "Salvar" no estilo outline para o slide de CTA.

---

## 2. Canvas & Layout Grid

- **Canvas Size:** `1080px` x `1350px` (Instagram Portrait 4:5)
- **Safe Area Margins:**
  - Top Margin: `90px`
  - Bottom Margin: `90px`
  - Left / Right Margin: `90px`

### Static Framework Layout
- **Header Left (Top: 90px, Left: 90px):** `{{meta.author_name}}` (ex: `HARPER RUSSO`)
- **Header Right (Top: 90px, Right: 90px):** `{{meta.category_hashtag}}` (ex: `#branding`)
- **Footer Left (Bottom: 90px, Left: 90px):** `{{meta.handle}}` (ex: `@reallygreatsite`)
- **Footer Right (Bottom: 90px, Right: 90px):** `{{meta.year}}` (ex: `2025`)

---

## 3. Slide Layout Variants

### Layout A: `cover` (Slide 1)
- **Main Title:** Caixas grandes em caixa alta (4 a 5 linhas).
- **Accent Element:** Pincelada sublinhando a última linha (`underline_accent: true`).
- **Decorative SVG:** Seta em looping no canto inferior direito (`arrow_type: "loop_bottom_right"`).

### Layout B: `content` (Slides 2 a N-1)
- **Section Title:** Título principal em caixa alta (2 a 4 linhas).
- **Highlight Box Body:** Texto explicativo (máx. 30 palavras) dentro de bloco preenchido em Laranja Coral.
- **Decorative SVG:** Seta pontilhada direcionada ao bloco (`arrow_type: "pointing_left"`).

### Layout C: `cta` (Slide Final)
- **Main Title:** Frase direta em caixa alta (ex: `DON'T FORGET TO SAVE THIS POST`).
- **CTA Icon:** Ícone de Bookmark (Salvar) em outline laranja à direita do título (`show_bookmark_icon: true`).
- **Decorative SVG:** Seta pontilhada apontando para o botão/ícone.
