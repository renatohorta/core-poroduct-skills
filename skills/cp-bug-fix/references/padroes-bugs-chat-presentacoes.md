# Padrões de bugs desta sessão (título automático, SVG browser vs PPTX, download autenticado)

## 1. `is_new` vs "conversa já existente sem título" ao gerar título automático

**Sintoma:** conversas criadas via chat ficam com título vazio ("Nova Conversa" para sempre),
mesmo após várias mensagens. A geração automática de título nunca roda.

**Causa raiz:** o front cria a conversa vazia via `createSession()` (sem título) ANTES de o
usuário enviar a 1ª mensagem. Quando a mensagem chega ao backend, a conversa JÁ EXISTE →
`is_new=False`. Se o `generate_session_title` só for disparado quando `is_new=True`, ele
NUNCA roda.

**Correção** (`chat/agui/views.py`): `_build_task` retorna `needs_title`
(= `is_new` ou `title` vazio/placeholder `"Nova Conversa"`); o `post()` chama
`enqueue_task_sync("generate_session_title", ...)` quando `needs_title`.

```python
needs_title = is_new or (not conversation.title or conversation.title.strip() == "Nova Conversa")
return task, is_new, str(conversation.id), needs_title
```

Ver `BUG-20260809-titulo-conversa-nao-gerado`.

## 2. Caminho da imagem no SVG: browser vs conversor (PPTX)

**Sintoma:** carrossel/HTML exibidos no chat têm a imagem quebrada (SVG renderiza só o fundo),
mas o mesmo deck em PPTX fica correto.

**Causa raiz:** `render_slide_svg` convertia a URL do media (`/media/...`) em caminho de
arquivo LOCAL do disco (`C:\...\media\slide.png`). Isso é necessário para o conversor
DrawingML embutir o arquivo binário no PPTX. Mas o MESMO SVG é servido ao browser no
CarouselCard / página HTML — e o browser não resolve caminho local → imagem quebrada.

**Correção** (`presentations/services/svg_renderer.py`): separar por contexto com um kwarg.

```python
def _image_ref(url, *, browser):
    if url.startswith(media_url):
        if browser:
            return url                      # /media/... resolve via HTTP
        return str(Path(MEDIA_ROOT) / url[len(media_url):])  # caminho local p/ converter
```

- `browser=True` → SVGs/HTML servidos ao browser (chat, página HTML).
- `browser=False` (default) → SVGs intermediários que o conversor DrawingML lê p/ PPTX.

## 3. Download autenticado (fetch + blob) em vez de `<a href download>` com token em memória

**Sintoma:** o botão "Download" não funciona (401) em endpoints que exigem auth.

**Causa raiz:** auth híbrida — o access token vive só em memória. Um `<a href={downloadUrl} download>`
não envia o header `Authorization` → o endpoint responde 401.

**Correção** (frontend): trocar o `<a>` por um `<button onClick>` que usa o helper autenticado.

```tsx
const { blob, filename } = await api.downloadBlob(path);  // fetch com Bearer + retry de refresh
const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url; a.download = filename || `arquivo.ext`; a.click();
URL.revokeObjectURL(url);
```

**Pitfall:** se o `downloadUrl` do backend já inclui `/api/v1/`, remova o prefixo antes de
chamar `downloadBlob` (ele espera caminho relativo à base `/api/v1`).

```tsx
const path = downloadUrl.startsWith("/api/v1") ? downloadUrl.slice("/api/v1".length) : downloadUrl;
```

## Teste

- Título automático: `tests/chat/test_agui.py::test_agui_generates_title_for_existing_empty_conversation`
  (a task roda numa daemon thread quando a TaskQueue não tem workers — use `time.sleep` loop
  esperando o título aparecer antes de assert).
