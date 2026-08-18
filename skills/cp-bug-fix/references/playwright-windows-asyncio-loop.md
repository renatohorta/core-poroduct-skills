# Playwright async on Windows — NotImplementedError in `_make_subprocess_transport`

## Sintoma

Export PNG de slides de carrossel via Playwright (`playwright_export.py`) falha com:

```
ERROR    Task exception was never retrieved
File "...\playwright\_impl\_transport.py", line 120, in connect
    self._proc = await asyncio.create_subprocess_exec(...)
File "...\asyncio\base_events.py", line 528, in _make_subprocess_transport
    raise NotImplementedError
NotImplementedError
```

O HTML do carrossel é gerado OK ("Carrossel HTML gerado: ..."), mas o export dos
PNGs falha silenciosamente (a exceção é engolida no `except` do `_build_carousel`).

## Causa raiz

`asyncio.create_subprocess_exec` só funciona em loops que suportam subprocess. No
Windows:

- **ProactorEventLoop** → suporta subprocess (usado pelo `WindowsProactorEventLoopPolicy`,
  que é o default do Python 3.8+)
- **SelectorEventLoop** → NÃO suporta subprocess → `NotImplementedError` em
  `_make_subprocess_transport`

O Playwright async precisa de um loop com suporte a subprocess. Se a função roda sob
`asyncio.run()` num contexto onde a policy efetiva é a Selector (ex: o processo herdou
uma policy, ou o loop foi criado explicitamente), o launch do Chromium quebra no
subprocess.

## Correção

Forçar a policy Proactor antes de `asyncio.run()`:

```python
import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def export_carousel_pngs(...):
    ...
    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("Falha no export PNG do carrossel: %s", exc)
        return []
```

Colocar a chamada a `set_event_loop_policy` no início da função que roda o Playwright
(ou no módulo), ANTES do `asyncio.run()`.

## Verificação

- `type(asyncio.new_event_loop()).__name__` deve ser `ProactorEventLoop` (não
  `SelectorEventLoop`).
- Rodar `python -c "from playwright.async_api import async_playwright; import asyncio; asyncio.run(async_playwright().start().chromium.launch())"`
  deve lançar o Chromium sem `NotImplementedError`.

## Pitfall adicional (não confundir com o de cima)

Se o launch falhar com `Executable doesn't exist at ...\ms-playwright\...`, NÃO é o bug
do loop — é o browser não instalado: `python -m playwright install chromium`.

## PREFRIDO: trocar Playwright/Chromium por `resvg-py` (cross-platform, ECS-safe)

Para export PNG de SVG (ex: carrossel 1080x1350), **não use Playwright/Chromium em
produção**. Ele exige baixar ~150MB de Chromium (download pode falhar) e o container
ECS Fargate Linux não tem Chrome/Edge instalado para `channel=`. O `resvg-py` é um
renderizador SVG em Rust (wheel binário, sem lib nativa externa, sem browser) que
funciona igual no Windows e no ECS Linux.

```python
# presentations/services/png_export.py (substitui playwright_export.py)
import resvg_py
def export_carousel_pngs(state, output_dir, total_slides):
    # render_slide_svg(slide, theme, "4:5", browser=True) -> svg (já 1080x1350)
    png_bytes = resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350)
```

- Import é `import resvg_py` (não `resvg`), função `svg_to_bytes(svg_string=..., width=..., height=...)`.
- `svg_string` espera `str` (não bytes).
- Reusa o SVG que `svg_renderer.render_slide_svg` já gera (mesmo motor do PPTX/HTML).
- Adicionar `resvg-py>=0.3` ao `pyproject.toml`; NÃO precisa mudar o Dockerfile.
- O `_build_carousel` (orchestrator) e o endpoint `/pngs/` (views) passam a chamar `png_export` com o `state` (não o html_path).

Testes: `tests/presentations/test_png_export.py` (3 testes: disponível, gera PNG 1080x1350, vazio sem slides).

## MELHOR ALTERNATIVA — trocar Playwright por `resvg-py` (recomendado para prod)

Se o usuário não consegue instalar o Chromium (`playwright install` falha no download
de ~150MB) OU o serviço vai para produção em **ECS Fargate Linux** (onde não há
Chrome/Edge e o Chromium precisa ser baixado no container), abandone o Playwright e
converta o **SVG que o projeto já gera** em PNG via **`resvg-py`**:

- Renderizador SVG em Rust, **wheel binário** — sem browser, sem lib nativa externa
  (diferente de `cairosvg`/`reportlab.renderPM` que exigem `libcairo` C, ausente no
  Windows e chato no ECS). Funciona igual em dev (Windows) e produção (Linux).
- Uso: `resvg_py.svg_to_bytes(svg_string=str, width=1080, height=1350)` → PNG bytes.
  O módulo de import é **`resvg_py`** (não `resvg`); a função é **`svg_to_bytes`**
  (não `render`). `svg_string` espera `str`, não bytes.
- Pré-requisito: os slides já são renderizados como SVG canônico 1080x1350
  (`svg_renderer.render_slide_svg(..., "4:5")`) — o PNG reflete o mesmo design do
  HTML/PPTX sem precisar de browser para "fotografar" o HTML.
- Dependência: adicionar `resvg-py>=0.3` ao `pyproject.toml` (não precisa mudar o
  Dockerfile — o wheel instala via `uv sync`).
- Exemplo de módulo de export: `presentations/services/png_export.py` (aceita o
  `state` dict, não o caminho HTML, pois o PNG vem do SVG de cada slide).

**Teste de sanidade:** `resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350)`
deve retornar bytes PNG. Verificar dimensões com `PIL.Image`; usar
`with Image.open(p) as img:` (fechar a imagem ou o `TemporaryDirectory` falha com
`PermissionError` no Windows).

**`channel="chrome"` como opção rápida (dev):** `p.chromium.launch(channel="chrome")`
usa o Google Chrome/Edge já instalado no sistema (sem baixar Chromium). Bom para dev
rápido, MAS não funciona no ECS (sem browser instalado). Se a prod é Linux, prefira
`resvg-py`.

## Alternativa PRODUÇÃO: resvg-py (preferida quando há container/ECS)

Quando o serviço roda em produção (ex.: AWS ECS Fargate, Linux) e o export PNG de um
carrossel/slide vai rodar lá, **não use Playwright+Chromium** — não há Chrome/Edge no
container e baixar o Chromium (~150MB) falha ou incha a imagem. A alternativa
open-source é **`resvg-py`** (renderizador SVG em Rust, wheel binário, sem browser e
sem lib nativa externa). Funciona no Windows dev E no Linux de produção, sem mudar o
Dockerfile.

- Adicionar `resvg-py>=0.3` ao `pyproject.toml` (não ao extra tools — é dependência do
  serviço de export PNG).
- Instalação em venv gerido por `uv`: **não há `pip`** (`No module named pip`) — usar
  `uv pip install resvg-py`, ou adicionar ao pyproject e `uv sync`.
- Import: `import resvg_py` (nome do módulo é `resvg_py`, NÃO `resvg`).
- Conversão: `resvg_py.svg_to_bytes(svg_string=<str>, width=1080, height=1350)` —
  `svg_string` espera **`str`**, não bytes (erro: `'bytes' object is not an instance of 'str'`).
  Escreva o retorno com `Path(...).write_bytes(png_bytes)`.
- Reusa o SVG canônico que o projeto já gera (ex.: `render_slide_svg(slide, theme, "4:5")`,
  que já sai em 1080×1350) — sem precisar "fotografar" o HTML.

**Por que as outras alternativas falham (testadas):**
- `cairosvg` → precisa da lib C `libcairo` nativa (`OSError: no library called "cairo-2"`) — não roda puro no Windows.
- `svglib` + `reportlab` `renderPM` → também exige o backend nativo `rlPyCairo` (`RenderPMError: cannot import desired renderPM backend rlPyCairo`).
- `Pillow` → NÃO renderiza SVG (`UnidentifiedImageError`).

Só o `resvg-py` (Rust binário) funciona sem dependência de sistema.

**Assinatura da função:** `svg_to_bytes(svg_string=None, svg_path=None, width=None, height=None, ...)` — se passar `svg_path`, pode passar bytes; se passar `svg_string`, tem que ser `str`.

## Diagnóstico chave: traceback de Playwright no runtime ≠ código ainda usa Playwright

O erro mais enganoso deste fluxo: o **log de runtime continua mostrando o traceback
do Playwright** (`playwright/_impl/_transport.py` → `NotImplementedError`) mesmo depois
de você já ter trocado o código para `resvg-py`. Antes de voltar a editar código,
verifique se o servidor está rodando com código **antigo em memória**.

Causa: o fix resvg já foi mergeado na main, mas o processo **Daphne não foi reiniciado**
após o merge — o módulo antigo (`playwright_export.py`) ficou carregado na memória do
processo. O `manage.py runserver`/Daphne **NÃO faz auto-reload** dessas mudanças.

Fluxo de diagnóstico (ordem):
1. **Verificar o código no disco** — grep real (não comentários) por `from playwright`,
   `async_playwright`, `sync_playwright`, `p.chromium`, `async with async_playwright`.
   Se só há menções em comentários/docstrings, o código já migrou.
2. **Verificar se o servidor está rodando** — `netstat -ano | findstr :8000`. Se não há
   processo escutando, o traceback foi de uma execução antiga.
3. **Testar o export diretamente via shell** com o estado real do objeto (ex. pegar a
   `Presentation` pelo uuid e chamar `export_carousel_pngs(state, dir, n)`). Se gera os
   PNGs sem erro, o código está correto e o problema é o processo velho.
4. **Reiniciar o Daphne** — matar o processo da porta 8000 (`taskkill /PID <pid> /F`) e
   relançar com o env Windows completo (USERPROFILE/HOME/LOCALAPPDATA/APPDATA — ver
   `crewai-stub-on-subprocess-restart.md`). Depois re-testar o download.

Regra: **se o código no disco está certo e o teste shell gera os PNGs, NÃO edite mais
código — reinicie o servidor.** O traceback de runtime com Playwright após a migração é
quase sempre o processo velho em memória, não um caminho residual de código.

## Migração completa: NÃO é só mudar a função — a assinatura e TODOS os call-sites mudam

Ao substituir o Playwright pelo resvg-py, o novo módulo `export_carousel_pngs` muda a
assinatura e **há mais de um call-site**. A migração em `crewbotics-back`:
- Novo `presentations/services/png_export.py` com assinatura `export_carousel_pngs(state: dict, output_dir: str, total_slides: int)` — precisa do `state` (para renderizar o SVG por slide), NÃO do `html_path`.
- **`playwright_export.py` deletado** (substituído).
- **`orchestrator.py`** (`_build_carousel`): passou a chamar `export_carousel_pngs(state, png_dir, len(slides))`.
- **`presentations/views.py`** (endpoint `GET .../pngs/` → ZIP): ANTES chamava `export_carousel_pngs(carousel_path, png_dir, len(slides))` com o caminho do HTML; DEPOIS `export_carousel_pngs(pres.state, png_dir, len(slides))` com o `state` da apresentação.

Pitfalls da migração:
- **Sempre procurar TODOS os call-sites** antes de mudar a assinatura — `grep` por `export_carousel_pngs` e `playwright_export` em todo o repo (não só no arquivo). Deixar um call-site antigo (com `html_path` posicional) quebra com `TypeError`.
- Verificar imports stale após deletar `playwright_export.py`: nenhum `from .playwright_export import ...` deve sobrar.
- `resvg-py` vai nas **dependências principais** do `pyproject.toml` (não num extra) — o serviço de export PNG roda em produção.

## Pitfall de TESTE no Windows: Pillow lazy-open bloqueia o cleanup do TemporaryDirectory

Ao testar `export_carousel_pngs` (que escreve PNGs) com `tempfile.TemporaryDirectory()`, o
`Image.open(p)` do Pillow abre o arquivo **lazy** — o handle fica aberto até a imagem ser
descartada. No Windows, o `TemporaryDirectory.cleanup()` falha ao deletar o PNG ainda em uso:

```
PermissionError: [WinError 32] The process cannot access the file because it is
being used by another process: '...\\tmpXXX\\slide_2.png'
```

Correção no teste: usar o context manager do Pillow para fechar o handle antes do cleanup:

```python
with tempfile.TemporaryDirectory() as tmp:
    paths = export_carousel_pngs(SAMPLE, tmp, 2)
    for p in paths:
        with open(p, "rb") as f:
            assert f.read(8) == b"\x89PNG\r\n\x1a\n"
        from PIL import Image
        with Image.open(p) as img:   # fecha o handle
            assert img.size == (1080, 1350)
```

Sem o `with Image.open(...)` o teste falha só no teardown (não no assert), o que é confuso.
O mesmo vale para qualquer teste que escreva arquivos com Pillow dentro de um TemporaryDirectory.
