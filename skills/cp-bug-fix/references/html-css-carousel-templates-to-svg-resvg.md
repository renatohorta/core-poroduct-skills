# Portar templates HTML/CSS de carrossel → SVG renderer + resvg-py (sem browser)

**Quando:** receber templates de carrossel HTML/CSS (ex.: Freepik/sketch/swoosh da
skill `universal-carousel-template-creator`, ou qualquer pacote de `slide.html` com
placeholders `{{TITLE}} {{BODY}} {{LAYOUT}} {{SLIDE_NUM}}`) e precisar gerar PNG
1080×1350 em produção.

**Por que não renderizar o HTML direto:** os templates são HTML/CSS. Browser headless
(Chrome/Edge/Puppeteer/Playwright) NÃO existe no ECS Linux de produção. A skill
`universal-carousel-template-creator` assume Playwright/Chrome — seguir essa rota
quebra no deploy. O usuário escolheu portar para SVG + resvg-py (sem browser, roda
no Windows e ECS Linux).

## Estratégia de portabilidade

1. **Não tente converter o HTML inteiro automaticamente** (invariável/frágil).
   Extraia a ESSÊNCIA de cada template: paleta (variáveis `:root` do CSS) + família
   de fontes + tipos de layout (cover/intro/list/steps/quote/pricing/cta).
2. **Crie um renderer SVG próprio** por template com:
   - fundo sólido (o conversor SVG→DrawingML não materializa gradiente; resvg-py
     renderiza gradiente, mas mantenha `* fill` sólido + `fill-opacity` para portar
     fácil e funcionar em ambos os caminhos),
   - formas decorativas (círculos/arcos/estrelas) aproximando o template,
   - tipografia hierárquica usando as fontes reais.
3. **Copie as fontes reais** dos templates (`_shared_fonts/*.ttf`) para
   `static/carousel_templates/fonts/` no projeto.
4. **Renderize com resvg-py passando `font_files=`** para as fontes do template:

```python
import resvg_py
png = resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350, font_files=fonts)
```

Sem `font_files`, o resvg usa fontes de sistema (Arial) e perde a tipografia da marca.

## Estrutura do renderer (ex.: `chat/skills/carousel_templates.py`)

- `TEMPLATES = {nome: {bg, ink, accent, card, font_heading, font_body, font_files}}`
  — dicionário de paletas/fontes por template.
- `TEMPLATE_NAMES = tuple(TEMPLATES.keys())` — exposto para o LLM escolher o template.
- `render_carousel_svg(template, slides, *, title, brand, handle) -> list[str]` —
  gera um SVG por slide; propaga `handle`/`brand` para slides que não os definem;
  preenche `slide_num`/`total` automaticamente (ex.: `01`/`07`).
- Helpers: `_wrap(text, max_chars)` (quebra por contagem de caracteres), `_esc`
  (html escape), `_wrap_svg(lines, x, y, font, size, fill, lh, weight, max_lines)`.
- Cada slide é um dict `{layout, title, body, eyebrow, items, cta, handle, slide_num, total}`.

## Skill que consome o renderer

A skill (`instagram_carousel_skill.py`) NÃO usa o pipeline de apresentações (PPTX/SVG
genérico). Ela:
1. Chama `llm_client.complete_json(messages, system=...)` (PROVIDER-AGNOSTIC, LiteLLM)
   com um system prompt que pede `{title, template, slides[]}` + lista os TEMPLATES
   válidos e os LAYOUTS (cover/bullets/steps/list/quote/pricing/cta) + regras de arco
   narrativo de Instagram (slide 1 = hook que para o scroll, último = CTA).
2. Valida template (`_validate_template` cai para default se inválido).
3. Renderiza SVG→PNG e arquiva via `archive_conversation_file` na pasta da conversa.
4. Devolve `{"component": "CarouselCard", "props": {title, slides:[{imageUrl, caption}], slideCount, format:"carousel"}}`.

Mantenha o MESMO nome de skill e o MESMO contrato do CarouselCard → frontend não muda.

## Pitfalls

- **`_FONTS_DIR` depende da profundidade do arquivo:** `Path(__file__).resolve().parents[2] / "static" / ...`
  funciona de `chat/skills/` mas NÃO de `presentations/services/` (profundidade
  diferente). Verifique ao mover o módulo.
- **resvg aceita `font_files` (lista de caminhos)** e `font_dirs` — use `font_files`
  para fontes específicas do template.
- **Validar template do LLM:** o LLM pode inventar nome de template — fallback para
  um default seguro (`constellation`).
- **Skill long-running no chat:** a resposta é "⏳ Estou gerando… recarregue se
  necessário" e o CarouselCard só aparece no reload (o front re-fetcha o histórico).
  Isso é esperado — não é bug.
- **Mock nos testes:** mock `llm_client.complete_json` E `_render` (não o resvg);
  teste o renderer separadamente com `font_files` para não depender de rede/browser.
