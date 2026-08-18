# Crewbotics-back: executor determinístico de carrossel (decisão do usuário)

## Contexto
O repo `crewbotics-back` tem sua própria skill Python `chat/skills/instagram_carousel_skill.py`.
Ela NÃO usa esta skill Hermes — segue o mesmo padrão determinístico, mas em código Django
na branch `feature/carrossel-deteccao-automatica-cards`.

## Os DOIS caminhos de renderização (histórico)
1. **Determinístico (desejado):** `chat/skills/executors/render_carousel.py` — layout
   codificado em PIL (fundo graphite #1B1B1D + terracota #A67561, arte estilizada à
   esquerda, título/data à direita). Não depende do LLM desenhar.
2. **Genérico (a evitar):** LLM → escolhe template (ex.: `sage`) → renderiza SVG→PNG
   via resvg_py. Quando o LLM desenha o layout do zero, os slides saem ralos.

## Como o desvio automático falhava
`parse_card_list()` só disparava para listas com data no formato `DD/MM – Título`
(>= 3 itens) — pensado para lançamento de jogos. Pedidos como roteiro de viagem
("8 lugares na América do Sul de carro partindo de BH") NÃO têm data, então o
prompt caía no caminho genérico → resultado ruim.

## Sintomas do caminho genérico (para diagnóstico rápido)
- Slides de destino com densidade de conteúdo ~0.6% (99% fundo liso vazio).
- Arquivos PNG de 18–22 KB vs 38–47 KB no determinístico.
- Apenas 1 linha de texto por slide ("3. Salar de Uyuni, Bolívia"), sem imagem.
- LLM inventa lista genérica ("Atacama, Patagônia, Uyuni, Machu Picchu") que nem
  é viável no briefing (ex.: road trip saindo de BH), em vez de responder ao pedido.

## DECISÃO DO USUÁRIO (11/08/2026)
**"Qualquer geração de carrossel deve cair no modelo determinístico."**
Ao perguntar o que fazer quando o usuário pedir template de marca explicitamente,
Renato respondeu: **"Ignorar o template: renderizar TUDO no determinístico, sempre."**

Regra dura a partir de então:
- Todo carrossel da skill `instagram_carousel` vai pelo executor determinístico.
- Pedido explícito de template NÃO muda o caminho — é ignorado.
- O LLM só produz o JSON de conteúdo (slides/cards); o layout fica 100% no código.
- A detecção automática (`parse_card_list`) deixa de ser o gate — o desvio é incondicional.

## Implementação (CONCLUÍDA 11/08/2026)
O caminho determinístico foi implementado e testado (suíte `tests/chat/` = 326 passed).
Concretamente, além do `render_carousel_slides` (carrossel genérico com layouts
`cover`/`cta`/`content`), foram adicionados:

- `chat/skills/executors/render_carousel.py`:
  - `SAFE = 90` (constante de margem que a `render_carousel_slides` usa — faltava).
  - `_hex2rgb()` + `_resolve_palette(colors)` → deriva `(BG, BG2, white, muted, accent)`
    de uma lista de hex da spec. Convenção: `colors[0]=fundo, [1]=texto, [2]=accent`.
    Mantém fallback graphite+terracota se a lista for insuficiente.
  - `render_carousel_slides(..., colors=None)` — o layout é sempre codificado; a
    paleta pode vir da spec do template.
- `chat/skills/instagram_carousel_skill.py`:
  - Novo método `_render_deterministic(self, slides, title, brand, handle, tpl)` —
    resolve `get_spec_colors(tpl)`, normaliza slides e chama o executor; arquiva os
    PNGs e devolve o `CarouselCard`. É o ÚNICO caminho de renderização.
  - `execute()` agora sempre chama `_render_deterministic` (ignora template/caminho
    SVG→PNG). O LLM só gera o JSON de conteúdo.
- `chat/skills/carousel_templates.py`: helpers `load_specs_index()`,
  `get_spec_colors(template_id)` (lê `### Colors` da spec `crewbotics-*.md`),
  `get_spec_n_slides(template_id)`, `_parse_spec_frontmatter()`.
- Testes: `tests/chat/test_carousel_executor.py` (+5 novos), `test_instagram_carousel_skill.py`
  (mocks trocados de `_render` para `_render_deterministic`, signature
  `(slides, title, brand, handle, tpl)`; format png não carousel). Snapshot de
  catálogo regenerado via `python manage.py dump_skill_catalog` (commit isolado).

## Specs de design geradas (11/08/2026)
O repo agora tem `chat/skills/carousel_specs/` com **12 specs .md de design**
(cada uma = um tema em `C:\Users\renat\Downloads\templates_crewbotics\`) + um
`templates-index.json` catalogando-as. Cada spec carrega `template_id` que
mapeia 1:1 para as chaves de `chat/skills/carousel_templates.py`
(beige_orange, bw_productivity, bw_marketing, bw_red, blue_running,
green_business, orange_social, orange_black, purple_marketing,
sage_advertising, yellow_black, yellow_green). Quando for trabalhar em carrossel
do crewbotics, essas specs são a fonte de estrutura/layout por tema.

Como foram geradas (técnica reutilizável): SVGs de template têm texto em paths e
imagens base64 (sem `<text>`), então para extrair estrutura → renderizar cada
SVG via Chrome headless (`--headless=new --disable-gpu --hide-scrollbars
--window-size=1080,1350 --screenshot=out.png file:///...`) e rodar tesseract
(`--psm 3`) para ler moldura/autor/títulos/layouts/nº de slides por tema.

## Ferramentas no Windows (host Renato)
- Fontes: `C:\Windows\Fonts\arialbd.ttf`, `arial.ttf`, `seguiemj.ttf` (emoji).
- Tesseract: `C:\Program Files\Tesseract-OCR\tesseract.exe` (--psm 3).
- write_file/terminal podem falhar com erro de relay WSL — usar execute_code com
  Python puro (os.makedirs + open()) para editar arquivos do repo.

## Pitfalls reais encontrados ao implementar (11/08/2026)
- **`\n` em strings de teste**: ao gerar arquivos de teste via Python que contêm
  `\n` literal nos títulos (ex.: `"LUGARES PARA\nVISITAR"`), o `\n` vira quebra de
  linha real dentro da string do arquivo e quebra o parse (`SyntaxError: unterminated
  string literal`). Sempre escrever `\\n` (duplo) no Python que gera o arquivo para
  que o `.py` final tenha o literal `\n`.
- **`uv run pytest` faz `uv sync` implícito**: altera `uv.lock` adicionando
  dependências já usadas pelo código mas ainda não registradas no lockfile
  (ex.: `jsonschema`, `pyyaml`, `resvg-py`). Isso aparece como `M uv.lock` no git
  status. Não é erro — é o lock sincronizando com o `pyproject.toml`; aceitar se as
  deps são legítimas do código.
- **Precedência de template**: `_resolve_template` dá precedência ao `template` do
  roteiro do LLM sobre o tema do prompt. Testes que mockam `_FAKE_ROTEIRO` com
  `"template": "coral"` hardcoded vão receber `coral` mesmo em prompt de marketing —
  ajustar a asserção do teste ao comportamento real, não ao tema esperado.
- **Snapshot de catálogo**: a skill tem teste de paridade
  (`test_skill_catalog_parity.py`) que compara o catálogo vivo com um snapshot. Ao
  mudar `parameters` (ex.: já existia `card_mode` não commitado), regenerar via
  `python manage.py dump_skill_catalog` e commitar em commit isolado.
- **Format**: o CarouselCard determinístico retorna `format: "png"` (não
  `"carousel"`). Ao atualizar testes que esperavam o caminho SVG, ajustar a
  asserção de format.

## Imagens POR SLIDE (opção B — 11/08/2026)

Motivo: o caminho determinístico original descartava silenciosamente a imagem
(`image_data` e `palette` eram calculados no `execute()` mas não passados ao
renderer). Para carrossel de destinos/lugares/produtos (ex.: "8 lugares de carro
saindo de BH") o usuário quer uma foto DIFERENTE por slide.

Como ficou:
- `render_carousel.py`:
  - `_resolve_slide_image(src)` — aceita URL http(s), data URI, bytes ou caminho
    local; retorna None se falhar (slide renderiza sem foto, nunca quebra).
  - `_paste_cover(img, photo)` — cola a foto em modo cover (preenche 1080x1350
    sem distorcer, recorta excesso) e aplica overlay escuro
    `(10,10,12,130)` para o texto ficar legível sobre a foto.
  - `render_carousel_slides` lê `slide.get("image") or slide.get("img")`; com
    foto usa overlay+texto branco fixo (`fg`/`mg`), sem foto usa gradiente/paleta.
- `instagram_carousel_skill.py`:
  - `_render_deterministic(..., image_data=None)` — propaga `slides[].image`
    (prioridade) ou `image_data` do execute (fallback p/ todos os slides).
  - System prompt agora instrui o LLM a preencher `image` por slide para
    destinos/lugares/produtos (campo opcional).
- Testes: `test_carousel_executor.py` +3 (bytes por slide, URL inválida→None,
  propagação via monkeypatch). `tests/chat/` = 304 passed.

## Varredura de paths de SO hardcoded (técnica — 11/08/2026)

Usuário chamou paths de máquina no código de "absurdo/inaceitável". Para auditar
o repo inteiro de forma precisa, a primeira regex crua retorna MUITOS falsos
positivos — filtrar antes de agir:

- Falsos positivos comuns: URLs `http(s)://` (pegam `[A-Za-z]:/`), namespaces XML
  (`http://www.w3.org/2000/svg` em svgpptx), shebangs `#!/usr/bin/env`, e o `\n`
  escapado dentro de strings JSON (backstory de seed) que o regex interpreta como
  backslash real.
- Regex precisa e eficaz: buscar só `C:\\Users` (pessoal), `C:\\Program Files`,
  `C:\\Windows\\Fonts`, e `r'([A-Za-z]:\\[^"\')\s]+)'` para drive absoluto;
  pular linha 1 se for shebang; pular dirs `.venv/node_modules/__pycache__/...`.
- Resultado real do repo: só `scripts/all_dev.ps1` tinha paths pessoais (corrigido
  para env vars `BACKEND_DIR`/`FRONTEND_DIR` + defaults relativos ao script) e
  `C:\Windows\Fonts` como candidato padrão de emoji (aceitável — é dir padrão de
  SO, não path pessoal). `C:/media/...` em docstring de `svg_renderer.py` era só
  exemplo ilustrativo.
- Regra: `C:\Windows\Fonts` num diretório padrão de SO = OK; `C:\Users\...` ou
  valores pessoais (handle `@renato.academy`, "NINTENDO SWITCH") = bug a corrigir.

## Portabilidade: reconciliação com host notes

A seção "Ferramentas no Windows (host Renato)" abaixo são NOTAS DE HOST para o
agente Hermes usar OCR/render localmente — não código do repo. O usuário proíbe
paths de SO hardcoded no CÓDIGO (que roda em ECS/outros devs). Manter as notas de
host, mas nunca copiá-las para dentro de código de produção.
