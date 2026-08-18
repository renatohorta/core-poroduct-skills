# Crewbotics Presentations Renderer — pitfalls & root-cause of "apresentações feias"

Arquitetura atual (`presentations/services/`):
- `agent_service.py::process_presentation_prompt` — LLM gera/edita o `state` JSON
  (`{title, theme, slides}`). Theme = 4 cores soltas (`background_color`,
  `text_color`, `accent_color`, `font_family`) + layout por slide.
- `svg_renderer.py::render_slide_svg` — desenha o slide como SVG minimalista
  (rect + text + bullets), posicionado por coordenadas x/y fixas. Este SVG é
  achatado para DrawingML editável no PPTX.
- `orchestrator.py` — monta html/pptx/svg.

## Por que apresentações saem feias (arquitetural, não do LLM)
O renderizador foi desenhado para conversão a PPTX (DrawingML só entende formas
básicas), então não suporta o que deixa um carrossel bonito:
- **Tipografia**: tudo `Arial`, caixa alta, um tamanho por tipo. Sem pares de
  fontes Google (ex: Playfair Display + DM Sans), sem escala de tamanhos, sem
  hierarquia. `_wrap()` quebra por contagem de chars, não mede fonte.
- **Cor**: 4 cores soltas, sem sistema derivado de 1 cor de marca (BRAND_PRIMARY/
  LIGHT/DARK + LIGHT_BG/DARK_BG). Sem alternância claro/escuro entre slides.
- **Componentes**: só 5 layouts (title_hero, standard_bullets, two_column_*,
  full_image_background), cada um = título + bullets + um `accent_bar` retângulo.
  Sem progress bar, CTA button, feature list, numbered steps, pills, logo lockup.
- **Imagem**: overlay scrim preto 55% sobre a imagem → perde o visual.
- **Sequência**: layout livre por slide; sem arco narrativo (hook → problem →
  solution → features → how-to → CTA), sem ritmo.

**Caminho de correção (se pedirem para turbinar):** introduzir renderizador
HTML/CSS rico (como a skill `instagram-carousel`) para `html`/`svg`/`carrossel`,
mantendo o SVG simplificado só para o caminho PPTX. Concretamente: (1) derivar
6 tokens de cor + par de fontes Google a partir da cor primária; (2) componentes
ricos (progress bar, swipe arrow, feature list, numbered steps, CTA, pills, logo);
(3) prompt do `agent_service` para estruturar 7 slides com arco e alternar fundos;
(4) renderizador HTML para preview/export.

## Bug 1 — SVGs não renderizavam no chat/carrossel (imagem quebrada)
`_local_image_path()` convertia a URL do MEDIA (`/media/...`) em caminho de
arquivo LOCAL (`C:\...\slide.png`). Necessário para o conversor DrawingML embutir
a imagem no PPTX, MAS o mesmo SVG servido ao browser no CarouselCard usa esse
caminho → o browser não resolve → imagem quebrada.

**Fix:** `_image_ref(url, *, browser)`. `browser=True` usa `/media/...`;
`browser=False` mantém caminho local (para PPTX). Callers que geram SVG/HTML
servido ao browser passam `browser=True`:
- `chat/skills/presentation_skill.py` (SVGs do card no chat)
- `presentations/services/orchestrator.py` (HTML servido ao browser)
- `pptx_builder.py` mantém default False.
Regenerar SVGs antigos (já arquivados na base de conhecimento) sobrescrevendo o
arquivo no MEDIA_ROOT no caminho correto. **Pitfall:** `doc.file.save(name, ...)`
com o mesmo `name` duplica o path (`rag/.../rag/...`); usar `open(real_path, "w")`
diretamente e corrigir `doc.file.name` para `rag/YYYY/MM/<basename>`.

## Bug 2 — Download de arquivo gerado dava 401
O CarouselCard usava `<a href={downloadUrl} download>`. O access token vive só em
memória (auth híbrida) → link direto não envia header Authorization → 401.

**Fix:** usar `api.downloadBlob(path)` (fetch autenticado Bearer + retry de
refresh) → blob → `URL.createObjectURL` → `<a>.click()`. Normalizar prefixo:
`downloadUrl` do backend já vem com `/api/v1/`; `downloadBlob` espera caminho
relativo à base, então remover o prefixo antes (`startsWith("/api/v1") ? slice(5)`).
O downloadUrl já absoluto quebrado era `/api/v1/api/v1/...`.

## Bug 3 — Export PNG do carrossel falha com `NotImplementedError` no Windows

`playwright_export.py::export_carousel_pngs` roda `asyncio.run(_run())` para
lançar o Chromium e capturar os slides. No Windows, se o event loop ativo for um
**Selector** loop (não Proactor), `asyncio.subprocess_exec` levanta
`NotImplementedError` em `_make_subprocess_transport` — o Playwright não consegue
lançar o subprocess do Chromium. Sintoma no log:

```
Task exception was never retrieved
... asyncio/base_events.py:528 in _make_subprocess_transport
    raise NotImplementedError
ERROR Falha no export PNG do carrossel:
```

**Causa raiz:** o Playwright async exige um event loop **Proactor** no Windows
(que suporta subprocess). Se o loop atual for Selector (ou o `asyncio.run` herdar
uma policy errada), o launch do browser quebra.

**Fix:** garantir a policy Proactor antes de `asyncio.run` no export:
```python
import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
return asyncio.run(_run())
```
**Pitfall adicional:** o export é **não-bloqueante** por design — `_build_carousel`
em `orchestrator.py` envolve `export_carousel_pngs` em try/except e segue só com o
HTML se o PNG falhar. Então um erro de Playwright não derruba a geração do
carrossel, mas o usuário fica sem os PNGs 1080×1350. Verificar o log
(`Falha no export PNG do carrossel`) ao reportar "carrossel sem download de PNG".
Também confirmar que o Chromium está instalado (`playwright install chromium`) —
`Executable doesn't exist at ...ms-playwright\chromium_headless_shell-...` é um
erro separado de browser ausente, não o bug do event loop.
