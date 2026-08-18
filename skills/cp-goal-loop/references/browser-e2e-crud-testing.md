# Browser-Based E2E CRUD Testing — All Artifact Types

Run the full CRUD loop through the web UI (browser) instead of raw API calls. Useful for validating that the frontend correctly renders, creates, edits, and manages all artifact types.

## Prerequisites

- Backend running at `http://localhost:8000`
- Frontend running at `http://localhost:8080`
- Celery worker running (for async indexing)
- Test user credentials (e.g. `renato.horta@gmail.com` / `teste123`)

## Celery Worker Startup (Windows)

The project venv can pick up Hermes' lxml from `sys.path`, causing:
```
ImportError: cannot import name 'etree' from 'lxml'
```

**Fix:** Create a wrapper script that cleans sys.path before starting celery:

```python
# run_celery_clean.py (in project root)
import sys, os
sys.path = [p for p in sys.path if "hermes" not in p.lower()]
os.environ["PATH"] = os.pathsep.join([
    p for p in os.environ.get("PATH", "").split(os.pathsep)
    if "hermes" not in p.lower()
])
from celery.__main__ import main
sys.argv = ["celery", "-A", "config", "worker", "--pool=solo", "--loglevel=INFO", "--concurrency=1"]
main()
```

Then run: `.venv/Scripts/python.exe run_celery_clean.py`

Verify: `.venv/Scripts/python.exe -m celery -A config inspect ping -t 5`

## Login Flow

1. Navigate to `http://localhost:8080`
2. Click "Entrar"
3. Type email + password
4. Click "ENTRAR"
5. Verify: Dashboard loads with user info in sidebar

## Phase 1: Base de Conhecimento (via Browser)

| Step | Action | Verification |
|------|--------|-------------|
| Navigate | Click "Conhecimento" in sidebar | Page shows folder tree + file list |
| Create folder | Click "Nova pasta" → type name → "Criar" | Folder appears in sidebar with "0 itens" |
| Upload file | Click "UPLOAD" → select file → confirm | File appears in list with indexStatus |
| Verify indexing | Refresh page or wait | File shows INDEXED status |
| View file actions | Click file row | Buttons: Visualizar, Renomear, Download, Mover para lixeira |

**Note:** Browser file upload requires a real file selection dialog. For automated testing, use the multipart API upload (see `references/e2e-crud-testing.md`) and verify the result in the browser.

## Phase 2: Páginas (via Browser)

| Step | Action | Verification |
|------|--------|-------------|
| Navigate | Click "Páginas" in sidebar | Page shows list of existing pages |
| Create page | Click "NOVA PAGINA" → select template → type title → "Criar" | Opens GrapesJS editor |
| Verify editor | Page loads in iframe with template content | Editor toolbar visible (Salvar, Publicar) |
| Publish | Click "Publicar" | Status changes to "Publicada", "Visualizar" link appears |
| View published | Click "Visualizar" | Full HTML page renders |
| Unpublish | Click "Despublicar" | Status changes to "Rascunho" |
| Delete | Click "Excluir" | Page removed from list |

## Phase 3: Apresentações (via Browser)

| Step | Action | Verification |
|------|--------|-------------|
| Navigate | Click "Apresentações" (if available in sidebar) | List of existing presentations |
| Create | Click "Nova apresentação" → fill form → confirm | Appears in list |
| Edit | Click presentation → edit title → save | Title updates |
| Download | Click download button | File downloads (.pptx) |
| Delete | Click delete → confirm | Removed from list |

**Note:** If Presentations don't have a dedicated frontend page yet, test via API (see `references/e2e-crud-testing.md` Phase 3).

## Phase 4: Chat e RAG (via Browser)

| Step | Action | Verification |
|------|--------|-------------|
| Navigate | Click "Copilot" in sidebar | Chat interface loads with conversation list |
| Start conversation | Click "NOVA CONVERSA" or select suggestion card | New conversation created |
| Send message | Type question → Enter | Response streams in (SSE tokens) |
| Verify RAG | Ask about content in knowledge base | Response cites document content |
| Check history | Previous messages visible in conversation | Scrollable history |

## LOOP Spec Template

Create `.hermes/docs/testes-de-loop/LOOP-NNN-<slug>.md` with:

```markdown
# Teste de Loop: <title>

**ID:** LOOP-NNN
**Data de Criação:** YYYY-MM-DD
**Status:** ⏳ Pendente

## Objetivo

<description>

## Critérios de Aprovação

### Fase 1: Base de Conhecimento
1. ✅ Criar pasta na base de conhecimento
2. ✅ Upload de arquivo .md
3. ✅ Verificar indexação
4. ✅ Renomear arquivo
5. ✅ Excluir (soft delete)
6. ✅ Restaurar da lixeira

### Fase 2: Páginas
7. ✅ Listar templates
8. ✅ Criar página a partir de template
9. ✅ Publicar página
10. ✅ Servir página publicada
11. ✅ Despublicar página
12. ✅ Excluir página

### Fase 3: Apresentações
13. ✅ Criar apresentação
14. ✅ Editar título
15. ✅ Regenerar .pptx
16. ✅ Excluir apresentação

### Fase 4: Chat e RAG
17. ✅ Conversar com o Copilot
18. ✅ Copilot responde com base no RAG

## Tabela de Resultados

| # | Tentativa | Data | Status | Observações |
|---|-----------|------|--------|-------------|
| 1 | Execução inicial | YYYY-MM-DD | ⏳ Pendente | |

## Bloco de Tratamento de Bugs

Se durante a execução do teste for encontrado um bug:
1. Diagnosticar a causa raiz
2. Criar arquivo em `.hermes/inbox/bugs/BUG-YYYYMMDD-<slug>.md`
3. Corrigir o código
4. Atualizar a tabela com o resultado
5. Reiniciar o teste da fase que falhou
```
