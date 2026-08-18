# AG-UI: resolver mensagens por uuid+id (evitar 500) + templates de carrossel HTML→SVG

Duas técnicas reutilizáveis encontradas ao trabalhar no chat do Copilot (crewbotics).

---

## 1. Resolver mensagens de chat por `uuid` + `id` inteiro, ignorando IDs otimistas do AG-UI

### Sintoma
O endpoint `/api/v1/chat/conversations/<id>/branches/?message=<id>` (e `/branch-version/`)
retorna **500 em loop** quando o frontend AG-UI chama. No log do Daphne:
```
ValueError: Field 'id' expected a number but got '3dccd053-f23d-4b71-b8e5-c1604a3174fd'.
```
Seguido de dezenas de `500 172522` para o mesmo endpoint (o front re-tenta).

### Causa raiz
O `ChatMessage.id` é `BigAutoField` (inteiro), mas o `message` que o front envia pode ser:
- o **`uuid`** da mensagem (o `toThreadMessage` do hook `useConversationThreadList.tsx`
  usa `id: m.uuid`), ou
- o **`pk` inteiro**, ou
- um **ID otimista ainda em streaming**: `__optimistic__Z0fS1y5`, `msg_29abe6cbe5ab`.

`filter(pk=<uuid_string>)` lança `ValueError` (campo inteiro) → 500.

### Correção (backend)
```python
def _looks_like_valid_message_id(value) -> bool:
    s = str(value).strip()
    if not s:
        return False
    if s.isdigit():
        return True            # pk inteiro
    try:
        uuid.UUID(s)
        return True            # uuid string
    except (ValueError, TypeError):
        return False           # __optimistic__/msg_ → False

def _resolve_message(conv, msg_id):
    s = str(msg_id).strip()
    if s.isdigit():
        return CM.objects.filter(conversation=conv, id=int(s)).first()
    return CM.objects.filter(conversation=conv, uuid=s).first()
```
Use `_resolve_message` em vez de `filter(pk=msg_id)` nos endpoints de mensagem. Rejeite IDs
otimistas cedo (retorne `{"branches": []}` / 404 em vez de 500).

### Correção (frontend)
O BranchPicker pula IDs otimistas antes de chamar o backend:
```tsx
useEffect(() => {
  if (!msgId) { setBranches([]); return; }
  if (/^(__optimistic__|msg_)/.test(msgId)) { setBranches([]); return; }
  // ... chama chatApi.messageBranches(convId, msgId)
}, [msgId, activeIdRef]);
```

### Testes
- `branches/?message=__optimistic__Z0fS1y5` → `200 {"branches":[]}` (não 500).
- `branches/?message=<root.uuid>` → `200` com a lista (o front envia uuid, não pk).

---

## 2. Templates de carrossel HTML/CSS → SVG + resvg-py (sem browser)

Quando o usuário fornece templates HTML/CSS de carrossel (ex: pasta `templates/` com
`slide.html`, paleta CSS, fontes TTF — típico de zips Freepik) e pede para reimplementar
uma skill de carrossel, **NÃO** renderize HTML→PNG com Playwright/Chromium: não existe
browser no ECS Linux (produção). A estratégia aprovada foi portar a estética para SVG e
renderizar com `resvg-py`, que aceita `font_files=[]` para usar as fontes reais dos templates.

### Passos
1. **Extrair paletas**: `:root { --bg:#CDC4FB; --accent:#7070F0; ... }` de cada `slide.html`.
2. **Copiar fontes TTF** para `static/<modulo>/fonts/` e montar um dict de templates:
```python
TEMPLATES = {
    "constellation": {
        "bg": "#CDC4FB", "ink": "#7E7AF5", "card": "#FFFFFF", "accent": "#7070F0",
        "font_heading": "Poppins", "font_body": "Poppins",
        "font_files": ["Poppins-ExtraBold.ttf", "Poppins-Bold.ttf", ...],
    },
    # ...
}
TEMPLATE_NAMES = tuple(TEMPLATES.keys())
```
3. **Renderer SVG** (1080×1350) com layouts por slide (cover, bullets, steps, list, quote,
   pricing, cta), usando `font-family` + `font-weight` — o resvg-py resolve via `font_files`.
4. **Converter**:
```python
import resvg_py
png = resvg_py.svg_to_bytes(
    svg_string=<str>,   # NÃO bytes
    width=1080, height=1350,
    font_files=<lista de caminhos absolutos TTF>,
)
```
5. **Roteiro via LLM provider-agnostic**: `llm_client.complete_json(..., system=SYSTEM_PROMPT)`
   devolve `{title, template, slides:[{layout, title, body, eyebrow, items}]}` — o LLM escolhe
   o template e o layout de cada slide. NUNCA importe SDK de provedor.

### Pitfalls do resvg-py
- `resvg_py.svg_to_bytes(svg_string=...)` espera `str`, não bytes.
- Sem `font_files`/`font_dirs`, cai em fontes do sistema e perde a identidade tipográfica
  (Poppins/Montserrat/AbrilFatface viram Arial genérica).
- Caminho das fontes: resolva com `Path(__file__).resolve().parents[N] / "static" / ...` —
  o N depende de onde o módulo vive.

### Contrato estável
Mantenha o CarouselCard (`slides: {imageUrl, caption}[]`) e o mesmo `name` da skill — assim
o frontend não precisa mudar; o Copilot passa a usar a nova implementação automaticamente.
Arquive cada PNG na base de conhecimento com `archive_conversation_file()` para o
`CarouselCard` exibir o preview inline.
