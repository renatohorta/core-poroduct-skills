# Carrossel Instagram com templates HTML → SVG → resvg-py (sem browser)

Padrão reutilizável para portar templates HTML/CSS de carrossel (ex: da skill
`universal-carousel-template-creator`, templates Freepik/sketch/swoosh) para o
backend Django do Crewbotics, renderizando PNG 1080×1350 **sem browser** (funciona
no Windows e no ECS Linux).

## Por que não usar browser
Os templates de referência são HTML/CSS e a skill original renderiza via Chrome/Edge
headless. Mas produção é ECS Linux **sem browser** — Playwright/Chromium não funciona.
A solução: portar a estética (paletas + tipografia + layouts) para SVG e renderizar
com `resvg-py` (wheel Rust, sem lib nativa), que aceita `font_files` com as fontes reais.

## Arquitetura da skill nova
```
prompt → llm_client.complete_json (provider-agnostic) → roteiro {title, template, slides[]}
    ↓
chat/skills/carousel_templates.py  (renderer SVG: paletas + layouts)
    ↓
resvg-py.svg_to_bytes(svg_string=..., width=1080, height=1350, font_files=[...])
    ↓
CarouselCard (PNGs arquivados na base de conhecimento)
```

## Passos-chave
1. **Copiar fontes** dos templates para `static/carousel_templates/fonts/` (Poppins,
   Montserrat, AbrilFatface, BebasNeue, etc.). O resvg-py usa `font_files` com caminhos
   absolutos — `get_font_paths(template)` resolve de `_FONTS_DIR`.
2. **Renderer SVG** (`carousel_templates.py`): dicionário `TEMPLATES` com paleta
   (bg/ink/card/accent) + `font_heading`/`font_body` + `font_files`. Layouts: cover,
   bullets, steps, list, quote, pricing, cta. Cada layout desenha o slide em SVG
   1080×1350 (retângulo de fundo + textos com `font-family` + formas decorativas).
3. **Skill** (`instagram_carousel_skill.py`): LLM gera o roteiro JSON; valida template;
   renderiza cada slide SVG→PNG; arquiva via `archive_conversation_file()`; retorna
   `CarouselCard` com `slides: [{imageUrl, caption}]`.

## "Sempre navegável" — garantir 5+ slides
O `CarouselCard` só mostra setas/contador/dots quando `total > 1`. Para garantir que o
resultado seja SEMPRE um carrossel navegável:
- Reforçar no system prompt: "OBRIGATÓRIO: entre 5 e 10 slides (NUNCA menos que 5)".
- Validar no `execute`: `if len(slides) < 5: return {"error": ...}` (pede reformulação
  em vez de retornar card sem navegação).

## Download individual de slide (frontend)
O `CarouselCard` precisa permitir baixar cada imagem, não só o ZIP. Adicionar botão
"Baixar slide N" que faz **fetch autenticado** (Bearer token) da `imageUrl` do slide
atual — `/media/` pode exigir auth em produção, então `<a href>` direto não basta:
```tsx
const headers: Record<string, string> = {};
if (tokenStore.access) headers["Authorization"] = `Bearer ${tokenStore.access}`;
const res = await fetch(slide.imageUrl, { method: "GET", headers, credentials: "include" });
const blob = await res.blob();
// URL.createObjectURL + <a download="slide-N.png"> + click
```

## Endpoint de download ZIP dos slides
Para o card ter `downloadUrl`/`pngsUrl` funcionais, adicionar um `@action` no
`ConversationViewSet` que gera ZIP dos slides arquivados:
- Filtrar `ProductContext` por `folder=conv.knowledge_folder` e **nome de arquivo**
  `slide-*` (via `os.path.basename(doc.file.name)`), NÃO pelo `title` (o título é o do
  carrossel, ex: "7 Dicas... 1").
- `FileResponse` é streaming — em teste usar `b"".join(resp.streaming_content)`, não
  `resp.content` (levanta AttributeError).
- `Content-Type` pode ser `application/zip` OU `application/x-zip-compressed` — aceitar
  ambos no teste.
- Nomear os arquivos no ZIP com `os.path.basename(doc.file.name)` (não `doc.title`).

## Pitfall: `@action` decorator roubado ao inserir action novo
Ao inserir um `@action` novo ANTES de um existente com `url_path` (ex: `branch_version`
com `url_path="branch-version"`), o decorator do existente fica empilhado sobre o novo
e o existente perde o `url_path` → rota some → 404 no teste. Após inserir, verificar os
decorators de TODOS os `def` afetados e restaurar `url_path`/decorator de cada um.
