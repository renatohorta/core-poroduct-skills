# SVG → PNG sem browser: `resvg-py` (alternativa ao Playwright/Chromium)

## Quando usar

Quando o export de PNG de slides/carrosséis via Playwright é inviável:
- O download do Chromium falha (`python -m playwright install chromium` trava/timeout).
- O serviço vai para **produção em ECS Fargate (Linux)** — não há Chrome/Edge instalado
  no container, e o Chromium do Playwright nem está no `pyproject.toml` (foi instalado
  à mão via pip/uv, então não existe no build de produção).

## Solução: `resvg-py`

Renderizador SVG em Rust, distribuído como **wheel binário** — sem browser, sem lib
nativa externa, funciona igual em Windows (dev) e Linux (ECS). Converte o SVG que o
projeto **já gera** (`presentations/services/svg_renderer.py` → 1080×1350 para 4:5)
diretamente em PNG, sem precisar "fotografar" um HTML.

```bash
uv pip install resvg-py        # o venv do projeto usa uv, NÃO tem pip
```

```python
import resvg_py

png = resvg_py.svg_to_bytes(
    svg_string=svg,            # str, NÃO bytes (TypeError se passar bytes)
    width=1080, height=1350,
)
```

## API quirks do `resvg-py`

- O módulo de import é **`resvg_py`** (não `resvg`).
- A função é **`svg_to_bytes`** (não `render`).
- `svg_string` espera **`str`**, não `bytes` — passar bytes levanta
  `TypeError: 'bytes' object is not an instance of 'str'`.
- Retorna `bytes` do PNG (RGBA). Validar com Pillow: `Image.open(BytesIO(png))`.

## Por que as outras alternativas falham

| Opção | Problema |
|---|---|
| `cairosvg` | Precisa da lib nativa **libcairo** (C). No Windows: `OSError: no library called "cairo-2" was found`. No ECS exigiria `apt install libcairo2`. |
| `svglib` + `reportlab` | `renderPM` precisa do backend **rlPyCairo** (também cairo nativo). `RenderPMError: cannot import desired renderPM backend rlPyCairo`. |
| `resvg-py` ✅ | Wheel Rust puro, sem lib nativa. Funciona em Windows e Linux. |

## Verificação

- `resvg_py.svg_to_bytes(svg_string=svg, width=1080, height=1350)` retorna PNG com
  conteúdo (não branco): amostrar pixels via Pillow, conferir dimensões 1080×1350 e
  >1 cor única.

## Nota

O `channel="chrome"` do Playwright (usar o Chrome/Edge do sistema) resolve o download
no dev Windows, mas **não serve para produção ECS** (sem Chrome no container). O
`resvg-py` cobre os dois ambientes com um único caminho.

## Pitfall: traceback de Playwright quando o código já usa resvg-py (servidor com código antigo)

Quando o usuário cola um traceback com `NotImplementedError` em `_make_subprocess_transport`
(ou qualquer erro de uma implementação ANTIGA) mas o código no disco JÁ usa o resvg-py,
**NÃO re-corrija o código** — ele já está certo. O processo Daphne/runserver em execução
ainda tem o módulo antigo carregado em memória (o fix foi mergeado mas o servidor não foi
reiniciado). O Daphne não auto-recarrega módulos de implementação já importados no boot.

### Diagnóstico em 3 passos (antes de editar qualquer coisa)

1. **Varredura real de imports** — grepe por uso REAL do lib antigo no fluxo
   (`from playwright`, `async_playwright`, `sync_playwright`, `p.chromium`),
   ignorando comentários/docstrings. Se só houver referências em comentários, o código
   está correto. Não confunda o nome do lib em docstrings com uso real.

2. **Rodar a função atual diretamente contra dados reais** — em vez de depender do
   servidor, chame a função via `python -c`/`manage.py shell -c` com o state real do banco:
   ```python
   from presentations.services.png_export import export_carousel_pngs
   pres = Presentation.objects.filter(uuid="<uuid>").first()
   pngs = export_carousel_pngs(pres.state, "<dir>", len(pres.state["slides"]))
   print(len(pngs))  # se 7/7 e sem erro → código OK
   ```
   Gerar os artefatos corretos (ex: 7/7 PNGs) prova que a implementação no disco é boa.

3. **Reiniciar o servidor** — `netstat -ano | findstr :8000` → matar o PID →
   relançar o Daphne com o env Windows completo (USERPROFILE/HOME/LOCALAPPDATA).
   Só depois disso o usuário deve re-testar o download.

Regra: se o teste direto da função (passo 2) passa, o fix real é o **restart do processo**,
não um novo patch. Não desperdice retries do loop Dev→QA corrigindo código já correto.
