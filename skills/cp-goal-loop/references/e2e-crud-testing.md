# E2E CRUD Testing Pattern — All Artifact Types

Test every artifact type (knowledge, pages, presentations, chat) in sequence via REST API, using a single test user + JWT token. Document results in a LOOP-NNN spec under `.hermes/docs/testes-de-loop/`.

## Setup

```python
# 1. Create test user + org, get JWT
from accounts.models import Organization, User
from rest_framework_simplejwt.tokens import RefreshToken

org, _ = Organization.objects.get_or_create(name="Loop Test Org")
user, _ = User.objects.get_or_create(email="loop@teste.com", defaults={"name":"Loop Tester","organization":org})
user.set_password("teste123")
user.save()
token = str(RefreshToken.for_user(user).access_token)

# 2. API helper
API = "http://127.0.0.1:8000/api/v1"
H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def api(method, path, body=None, timeout=30):
    import urllib.request, json
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=H, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, raw
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        return e.code, err_body
```

## Phase 1: Base de Conhecimento

| Step | Method | Path | Body | Expected |
|------|--------|------|------|----------|
| Criar pasta | POST | /knowledge/folders/ | `{"name": "..."}` | 201 |
| Upload .md | POST | /knowledge/docs/ | multipart: file + folderId | 201 |
| Ler | GET | /knowledge/docs/{uuid}/ | — | 200 |
| Listar | GET | /knowledge/docs/?folderId={uuid} | — | 200 |
| Renomear | PATCH | /knowledge/docs/{uuid}/ | `{"title": "..."}` | 200 |
| Soft delete | DELETE | /knowledge/docs/{uuid}/ | — | 204 |
| Restaurar | POST | /knowledge/docs/{uuid}/restore/ | — | 200 |

**Pitfall:** Upload via JSON body with `title` + `content` fields returns 400 — the `DocumentCreateSerializer` requires `file` (multipart) or `url`. Use multipart form-data.

**Pitfall:** After upload, `indexStatus` is `PENDING`. Without a Celery worker, you must index manually:
```python
from knowledge.tasks import index_document
index_document(str(doc.id))
```

## Phase 2: Páginas

| Step | Method | Path | Body | Expected |
|------|--------|------|------|----------|
| Listar templates | GET | /page-templates/ | — | 200 (array) |
| Criar pasta | POST | /page-folders/ | `{"name": "..."}` | 201 |
| Criar página | POST | /pages/ | `{"title":"...","slug":"...","templateId":"...","folderId":"..."}` | 201 |
| Editar | PATCH | /pages/{uuid}/ | `{"htmlContent":"...","cssContent":"..."}` | 200 |
| Publicar | POST | /pages/{uuid}/publish/ | — | 200 |
| Servir slug | GET | /p/{slug}/ | — | 200 (HTML) |
| Despublicar | POST | /pages/{uuid}/unpublish/ | — | 200 |
| Excluir | DELETE | /pages/{uuid}/ | — | 204 |

## Phase 3: Apresentações

| Step | Method | Path | Body | Expected |
|------|--------|------|------|----------|
| Criar | POST | /presentations/ | `{"title":"...","state":{...}}` | 201 |
| Listar | GET | /presentations/ | — | 200 |
| Editar | PATCH | /presentations/{uuid}/ | `{"title":"..."}` | 200 |
| Regenerar | POST | /presentations/{uuid}/regenerate/ | — | 200 (timeout ≥60s) |
| Excluir | DELETE | /presentations/{uuid}/ | — | 204 |

**Pitfall:** `regenerate` takes ~33s. Set timeout ≥60s on the HTTP call.

## Phase 4: Chat e RAG

| Step | Method | Path | Body | Expected |
|------|--------|------|------|----------|
| Criar conversa | POST | /chat/conversations/ | `{"title":"..."}` | 201 |
| Chat completions | POST | /chat/completions/ | `{"conversationId":"...","messages":[{"role":"user","content":"..."}]}` | 200 (SSE) |
| Listar skills | GET | /chat/skills/ | — | 200 (array) |
| RAG search | POST | /chat/knowledge-search/ | `{"query":"...","conversationId":"..."}` | 200 |

**Pitfall:** Chat completions expects `messages` array (OpenAI format), NOT a `message` string. Returns SSE (Server-Sent Events), not JSON. Parse with:
```python
for line in raw.split("\n"):
    if line.startswith("data: "):
        event = json.loads(line[6:])
```

**Pitfall:** RAG returns 0 results if documents are still `PENDING`. Index manually first (see Phase 1 pitfall).

## LOOP Spec Template

Create `.hermes/docs/testes-de-loop/LOOP-NNN-<slug>.md` with:
- Objective
- Approval criteria (one per step, numbered)
- Results table (tentativa | data | status | observações)
- Bug handling block
