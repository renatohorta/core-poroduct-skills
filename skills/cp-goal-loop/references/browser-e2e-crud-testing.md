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

## Phase 1: Knowledge Base (via Browser)

| Step | Action | Verification |
|------|--------|-------------|
| Navigate | Click "Conhecimento" in sidebar | Page shows folder tree + file list |
| Create folder | Click "Nova pasta" → type name → "Criar" | Folder appears in sidebar with "0 itens" |
| Upload file | Click "UPLOAD" → select file → confirm | File appears in list with indexStatus |
| Verify indexing | Refresh page or wait | File shows INDEXED status |
| View file actions | Click file row | Buttons: Visualizar, Renomear, Download, Mover para lixeira |

**Note:** Browser file upload requires a real file selection dialog. For automated testing, use the multipart API upload (see `references/e2e-crud-testing.md`) and verify the result in the browser.

## Phase 2: Pages (via Browser)

| Step | Action | Verification |
|------|--------|-------------|
| Navigate | Click "Páginas" in sidebar | Page shows list of existing pages |
| Create page | Click "NOVA PAGINA" → select template → type title → "Criar" | Opens GrapesJS editor |
| Verify editor | Page loads in iframe with template content | Editor toolbar visible (Salvar, Publicar) |
| Publish | Click "Publicar" | Status changes to "Publicada", "Visualizar" link appears |
| View published | Click "Visualizar" | Full HTML page renders |
| Unpublish | Click "Despublicar" | Status changes to "Rascunho" |
| Delete | Click "Excluir" | Page removed from list |

## Phase 3: Presentations (via Browser)

| Step | Action | Verification |
|------|--------|-------------|
| Navigate | Click "Apresentações" (if available in sidebar) | List of existing presentations |
| Create | Click "Nova apresentação" → fill form → confirm | Appears in list |
| Edit | Click presentation → edit title → save | Title updates |
| Download | Click download button | File downloads (.pptx) |
| Delete | Click delete → confirm | Removed from list |

**Note:** If Presentations don't have a dedicated frontend page yet, test via API (see `references/e2e-crud-testing.md` Phase 3).

## Phase 4: Chat and RAG (via Browser)

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
# Loop Test: <title>

**ID:** LOOP-NNN
**Creation Date:** YYYY-MM-DD
**Status:** ⏳ Pending

## Objective

<description>

## Approval Criteria

### Phase 1: Knowledge Base
1. ✅ Create folder in the knowledge base
2. ✅ Upload .md file
3. ✅ Verify indexing
4. ✅ Rename file
5. ✅ Delete (soft delete)
6. ✅ Restore from trash

### Phase 2: Pages
7. ✅ List templates
8. ✅ Create page from template
9. ✅ Publish page
10. ✅ Serve published page
11. ✅ Unpublish page
12. ✅ Delete page

### Phase 3: Presentations
13. ✅ Create presentation
14. ✅ Edit title
15. ✅ Regenerate .pptx
16. ✅ Delete presentation

### Phase 4: Chat and RAG
17. ✅ Chat with Copilot
18. ✅ Copilot responds based on RAG

## Results Table

| # | Attempt | Date | Status | Notes |
|---|-----------|------|--------|-------------|
| 1 | Initial execution | YYYY-MM-DD | ⏳ Pending | |

## Bug Handling Block

If a bug is found during test execution:
1. Diagnose the root cause
2. Create a file in `.hermes/inbox/bugs/BUG-YYYYMMDD-<slug>.md`
3. Fix the code
4. Update the table with the result
5. Restart the test from the phase that failed
```
