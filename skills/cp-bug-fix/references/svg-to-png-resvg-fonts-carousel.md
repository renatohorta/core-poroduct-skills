# SVG→PNG com fontes reais via resvg-py (sem browser, ECS-safe)

Quando você precisa renderizar templates de carrossel/post (HTML/CSS de fontes como
Poppins, Montserrat, AbrilFatface) para PNG **sem depender de Chrome/Edge/Playwright** —
essencial porque produção roda em ECS Linux sem browser — use **resvg-py** que aceita
`font_files`/`font_dirs` para embutir as fontes reais na renderização do SVG.

## API

```python
import resvg_py
png_bytes = resvg_py.svg_to_bytes(
    svg_string=svg,          # str (NÃO bytes)
    width=1080, height=1350,
    font_files=[...abs paths .ttf/.otf...],   # fontes custom do template
)
```

- `svg_string` aceita `str` (não bytes).
- `font_files` aceita uma lista de caminhos absolutos de `.ttf`/`.otf`. O texto no SVG
  usa `font-family="Poppins"` etc. e o resvg resolve pelos arquivos fornecidos.
- Fontes que não são passadas → fallback embutido do resvg (texto ainda renderiza, mas
  sem a tipografia da marca). Passe TODAS as fontes do template.

## Por que isso funciona em produção
- resvg-py é wheel binário Rust — **sem lib nativa, sem browser**. Roda no Windows e no
  ECS Linux sem mudança no Dockerfile.
- Alternativas rejeitadas: cairosvg / svglib+reportlab exigem libcairo C nativa;
  Playwright/Chromium não existem em container Linux e o `channel="chrome"` só funciona
  no Windows.

## Padrão de portar template HTML/CSS → SVG
Em vez de converter automaticamente o HTML (inviável para templates multi-layout),
extraia a **paleta** (`:root { --bg, --ink, --accent ... }`), as **fontes**
(`font-family`) e os **layouts** (`data-layout="cover|intro|list|quote|cta"`) e
reimplemente-os como geradores de SVG 1080×1350. Templates Freepik/sketch típicos:
constellation, coral, fashion, pet, sketch, swoosh, sage, oliva, bebas. Deixe o LLM
selecionar o template/layout via `llm_client.complete_json` (provider-agnostic).

## Validação visual sem visão
Após gerar o PNG, confirme o design no browser abrindo o arquivo e lendo
`distinctColors` via canvas — um slide real tem 29-400+ cores (fundo + texto +
decoração); um PNG "vazio" teria 1-2. Isso confirma que texto/acentos renderizaram.

## Manter o contrato do CarouselCard
Ao reimplementar uma skill de carrossel, o `CarouselCard` do front já é navegável
quando `slides.length > 1` (setas ‹ › + contador n/N + dots). Garanta:
1. **Sempre 5-10 slides** — force no system prompt E valide no `execute`
   (`if len(slides) < 5: return {"error": ...}`) para nunca gerar card sem navegação.
2. **Download funcional** — retorne `downloadUrl`/`pngsUrl` reais. Para carrossel,
   adicione um endpoint que gera o ZIP dos slides arquivados:
   - Filtre os `ProductContext` pelo **nome do arquivo** (`os.path.basename(doc.file.name).startswith("slide-")`),
     NÃO pelo título (o título é o do carrossel, ex. "7 Dicas... 1").
   - Use `zipfile` + `FileResponse(io.BytesIO(...), as_attachment=True)`; no teste leia
     `b"".join(resp.streaming_content)` (FileResponse não tem `.content`).
   - `Content-Type` pode ser `application/x-zip-compressed` (não só `application/zip`).

## Pitfall de find-and-replace: decorator "roubado"
Inserir um novo method antes de um existente usando `def <nome>` como âncora pode fazer
o novo method herdar o decorator do vizinho e o vizinho perder o `@action`. Ver
SKILL.md "SEMPRE verificar se o find-and-replace não 'roubou' o decorator".
