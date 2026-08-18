# Apresentações: SVG dual-use (media URL vs caminho local) + download autenticado

Padrões de bug recorrentes no fluxo de apresentações/carrossel (Crewbotics).

## 1. O MESMO SVG serve para dois públicos com referências de imagem diferentes

`presentations/services/svg_renderer.py` gera o SVG canônico de um slide. O SVG é usado
em DOIS lugares que precisam de referências de imagem DIFERENTES:

- **Conversor DrawingML para PPTX** (`pptx_builder.py`): precisa do **caminho local do
  disco** (`C:\...\media\slide.png`) para EMBUTIR a imagem binária no deck.
- **Browser** (CarouselCard no chat / página HTML): precisa da **URL do MEDIA**
  (`/media/...`) que o browser resolve via HTTP. Caminho local (`C:\...`) NÃO resolve →
  imagem quebrada (naturalWidth=0).

### Bug
A função original `_local_image_path(url)` SEMPRE convertia a URL do media em caminho
local. O SVG gerado com caminho local era arquivado na base de conhecimento e servido
como `imageUrl` no CarouselCard → o `<img>` exibia imagem quebrada.

### Correção — parâmetro `browser`
```python
def _image_ref(url: str | None, *, browser: bool) -> str | None:
    if not url:
        return None
    media_url = settings.MEDIA_URL
    if url.startswith(media_url):
        if browser:
            return url                     # /media/...  → browser resolve
        return str(Path(settings.MEDIA_ROOT) / url[len(media_url):])  # caminho local → PPTX embute
    return url.lstrip("/")

def render_slide_svg(slide, theme, aspect_ratio="16:9", *, browser=False) -> str:
    ...
    img_path = _image_ref(image.get("url"), browser=browser)
```

Callers que servem ao browser passam `browser=True`:
- `chat/skills/presentation_skill.py` (arquiva SVGs para o CarouselCard no chat)
- `presentations/services/orchestrator.py` (gera HTML servido ao browser)

`pptx_builder.py` continua default (`browser=False`, caminho local para embutir).

### Regenerar SVGs já arquivados (conversas antigas)
SVGs gerados ANTES do fix continuam com caminho local no storage. Para corrigir uma
conversa existente, regenerar a partir do `state` da apresentação:
```python
p = Presentation.objects.get(uuid="...")
svg = render_slide_svg(slide, p.state["theme"], "1:1", browser=True)
path = os.path.join(settings.MEDIA_ROOT, doc.file.name)
open(path, "w", encoding="utf-8").write(svg)
```

## 2. Pitfall do FileField: `doc.file.save(nome, ...)` DUPLICA o caminho

Quando o `ProductContext.file.name` já contém o subcaminho (`rag/2026/08/slide.svg`) e
você chama `doc.file.save(doc.file.name, content, save=True)`, o Django pré-pendura o
`upload_to` de novo → `rag/2026/08/rag/2026/08/slide.svg`. O arquivo que o browser serve
(`/media/rag/2026/08/slide.svg`) fica com o conteúdo antigo.

**Fix:** escrever direto no arquivo via `open(doc.file.path, "w")` OU corrigir o
`file.name` antes de salvar. Sempre conferir `doc.file.name` após salvar.

## 3. Download autenticado — `<a href>` NÃO envia o JWT (auth híbrida em memória)

Quando o access token vive só em memória (auth híbrida com cookie httpOnly só pro
refresh), um link `<a href={downloadUrl} download>` abre um request do browser SEM o
header `Authorization` → o endpoint de download responde **401**.

### Sintoma
"O card gerou os SVGs mas o botão de download falhou" — o download abre e retorna erro.

### Correção — `api.downloadBlob()` (fetch autenticado → blob → createObjectURL)
`src/lib/api/client.ts` expõe `api.downloadBlob(path)` que:
1. injeta `Authorization: Bearer <access>`
2. em 401 tenta refresh uma vez e repete
3. extrai o filename do `Content-Disposition`
4. retorna `{ blob, filename }`

No componente (ex: `CarouselCard.tsx`):
```tsx
const handleDownload = async () => {
  // downloadUrl do backend já inclui /api/v1/; downloadBlob espera caminho relativo à base.
  const path = downloadUrl.startsWith("/api/v1") ? downloadUrl.slice("/api/v1".length) : downloadUrl;
  const { blob, filename } = await api.downloadBlob(path);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename || "arquivo.ext";
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
};
// botão: <button onClick={handleDownload}> em vez de <a href={downloadUrl} download>
```
Normalizar o prefixo `/api/v1`: `downloadBlob` concatena `BASE_URL (/api/v1) + path`;
se `downloadUrl` já vem com `/api/v1/`, passa o caminho relativo (strip do prefixo).

**Verificação no browser:** botão deve ser um `<button>` com `onClick` (não `<a href>`);
console limpo (sem 401); botão volta de "Baixando..." para o estado normal.

## 4. Título automático de conversa NUNCA dispara quando a conversa é criada antes do 1º prompt

### Bug
Frontend cria a conversa vazia via `createSession()` (fluxo "Nova conversa") ANTES de
enviar a primeira mensagem. No backend, `_build_task` vê a conversa JÁ EXISTENTE →
`is_new=False` → o `generate_session_title` só rodava quando `is_new=True` → a conversa
fica com título vazio para sempre.

### Correção — retornar `needs_title` (não só `is_new`)
```python
needs_title = is_new or (not conversation.title or conversation.title.strip() == "Nova Conversa")
return task, is_new, str(conversation.id), needs_title
```
E no `post()`: disparar o título quando `needs_title` (não quando `is_new`). Cobre o caso
da conversa pré-criada vazia. Atualizar TODOS os desempacotadores do tuple.

### Pitfall de teste
A task de título roda numa **daemon thread** (TaskQueue sem workers em teste) que persiste
DEPOIS do `refresh_from_db()`. No teste, fazer poll com sleep até o título aparecer:
```python
for _ in range(20):
    conv.refresh_from_db()
    if conv.title and conv.title != "Nova Conversa": break
    time.sleep(0.2)
```
