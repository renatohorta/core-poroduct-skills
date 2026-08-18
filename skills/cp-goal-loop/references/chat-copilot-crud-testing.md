# Chat-First CRUD Testing via Copilot

Test CRUD operations by acting as a **user typing natural language commands into the Copilot chat**, not by calling APIs directly or clicking UI buttons. The Copilot receives the command, interprets it, and executes the operation via MCP tools.

This catches a different failure class than API or browser-UI testing: the Copilot's ability to understand intent, map it to the right MCP tool, and execute correctly.

## When to Use This Pattern

- Testing the Copilot's ability to **operate the system** (create/edit/delete artifacts)
- Validating that **MCP tools** are wired correctly and return proper results
- Testing **natural language understanding** of domain-specific commands
- End-to-end validation of the **chat → MCP → backend** pipeline

## Prerequisites

1. Backend running at `http://localhost:8000`
2. Frontend running at `http://localhost:8080` (TanStack Start — NOT Vite on 5173)
3. Celery worker running (for async indexing)
4. Test user credentials (e.g. `renato.horta@gmail.com` / `teste123`)
5. Seed data loaded (page templates, etc.)

## Login Flow (Browser)

1. Navigate to `http://localhost:8080`
2. Click "Entrar" or locate the login form
3. Type email + password
4. Submit the form
5. Verify: Dashboard loads with user info visible

## Execution Pattern

For each test step:

1. **Type the natural language command** into the chat input field
2. **Press Enter** to send
3. **Wait for the Copilot's response** (SSE streaming — tokens appear incrementally)
4. **Verify the response** confirms the action was executed
5. **Validate persistence** by navigating to the relevant module or calling the API

### Example: Creating a Knowledge Folder

```
User types:  "Crie uma pasta chamada 'Documentos de Marketing' na base de conhecimento"
Copilot:     "Pronto! Criei a pasta 'Documentos de Marketing' na sua base de conhecimento."
Validation:  Navigate to Conhecimento → folder appears in sidebar
```

### Example: Creating a Page

```
User types:  "Crie uma landing page para um curso de marketing digital com o título 'Minha LP' e slug 'minha-lp'"
Copilot:     "Página 'Minha LP' criada com sucesso."
Validation:  Navigate to Páginas → card appears with title "Minha LP"
```

## Phase 1: Base de Conhecimento via Chat

| # | User Command | Expected Copilot Response | Validation |
|---|-------------|--------------------------|------------|
| 1 | "Crie uma pasta chamada 'Documentos de Marketing' na base de conhecimento" | Confirms folder creation | Navigate to Conhecimento → folder visible |
| 2 | "Crie um arquivo chamado 'briefing-produto.txt' dentro da pasta 'Documentos de Marketing' com o conteúdo: [briefing text]" | Confirms file creation | Navigate → file visible in folder |
| 3 | "Liste os arquivos da pasta 'Documentos de Marketing'" | Lists files in chat | Files match what's in the UI |
| 4 | "Edite o arquivo 'briefing-produto.txt' mudando o título para 'Novo Briefing'" | Confirms edit | Navigate → title updated |
| 5 | "Exclua o arquivo 'Novo Briefing.txt' da pasta 'Documentos de Marketing'" | Confirms deletion (soft delete) | Navigate → file in lixeira |
| 6 | "Restaure o arquivo 'Novo Briefing.txt' da lixeira" | Confirms restore | Navigate → file back in folder |

## Phase 2: Páginas via Chat

| # | User Command | Expected Copilot Response | Validation |
|---|-------------|--------------------------|------------|
| 7 | "Liste os templates de página disponíveis" | Lists templates in chat | Templates match catalog |
| 8 | "Crie uma landing page para um curso de marketing digital com o título 'Minha Landing Page' e slug 'minha-landing-page'" | Confirms page creation with link to editor | Navigate to Páginas → card visible |
| 9 | "Edite o HTML da página 'minha-landing-page' para: [novo HTML]" | Confirms content update | Navigate → content reflects changes |
| 10 | "Publique a página 'minha-landing-page'" | Confirms publication | GET /api/v1/p/minha-landing-page/ → 200 HTML |
| 11 | "Acesse a página publicada em /p/minha-landing-page/" | Returns URL or confirms | GET /api/v1/p/minha-landing-page/ → 200 HTML |
| 12 | "Despublique a página 'minha-landing-page'" | Confirms unpublish | Navigate → status "Rascunho" |
| 13 | "Exclua a página 'minha-landing-page'" | Confirms deletion | Navigate → page gone |

## Available MCP Tools for CRUD Operations

The following skills are registered and available to the Copilot for CRUD operations:

### Base de Conhecimento
| Skill Name | File | Operations |
|-----------|------|------------|
| `manage_knowledge_folders` | `write_knowledge_skill.py` | Create/rename folders, rename/move documents |
| `write_knowledge_file` | `write_knowledge_skill.py` | Create/overwrite text files in knowledge base |
| `read_knowledge_file` | `knowledge_files_skill.py` | Read document content |
| `manage_knowledge_base` | `manage_knowledge_skill.py` | Delete documents/folders (soft delete → trash) |
| `restore_knowledge_item` | `manage_knowledge_skill.py` | Restore documents/folders from trash |
| `search_knowledge_base` | `rag_skill.py` | Semantic search across knowledge base |

### Páginas
| Skill Name | File | Operations |
|-----------|------|------------|
| `list_page_templates` | `list_page_templates_skill.py` | List available page templates |
| `generate_landing_page` | `page_skill.py` | Create a landing page from description |
| `edit_page` | `edit_page_skill.py` | Edit HTML/CSS of existing page |
| `manage_page` | `manage_page_skill.py` | Publish, unpublish, delete page |

### Base de Conhecimento — Restore
| Skill Name | File | Operations |
|-----------|------|------------|
| `restore_knowledge_item` | `manage_knowledge_skill.py` | Restore documents/folders from trash (soft-delete reversal) |

## LOOP Spec Template

Create `.hermes/docs/testes-de-loop/LOOP-NNN-<slug>.md` with:

```markdown
# Teste de Loop: <title>

**ID:** LOOP-NNN
**Data de Criação:** YYYY-MM-DD
**Status:** ⏳ Pendente

## Objetivo

<description — emphasize chat-first, user-commands-Copilot pattern>

## Pré-condições

1. Ambiente dev rodando (Django + Celery worker + Redis + frontend)
2. Seed de templates executado
3. Usuário <email> / <senha> existe com papel PRODUCER

## Critérios de Aprovação

### Fase 1: Base de Conhecimento via Chat
1. ✅ Criar pasta via chat
2. ✅ Criar arquivo via chat
3. ✅ Listar arquivos via chat
4. ✅ Editar arquivo via chat
5. ✅ Excluir arquivo via chat
6. ✅ Restaurar arquivo via chat

### Fase 2: Páginas via Chat
7. ✅ Listar templates via chat
8. ✅ Criar página via chat
9. ✅ Editar HTML via chat
10. ✅ Publicar via chat
11. ✅ Servir página publicada
12. ✅ Despublicar via chat
13. ✅ Excluir via chat

## Tabela de Resultados

| # | Tentativa | Data | Status | Observações |
|---|-----------|------|--------|-------------|
|   |           |      |        |             |

## Bloco de Tratamento de Bugs

1. Diagnosticar a causa raiz
2. Criar arquivo em `.hermes/inbox/bugs/BUG-YYYYMMDD-<slug>.md`
3. Corrigir o código
4. Atualizar a tabela com o resultado
5. Reiniciar o teste da fase que falhou
```

## Pitfalls

### Copilot doesn't understand the command
The Copilot may misinterpret the intent or respond with "I can't do that." If this happens:
- Rephrase the command more explicitly
- Check if the MCP tool for that operation exists and is registered in `chat/skills/__init__.py`
- Check the browser console for JS errors during the chat request
- After adding a new skill, **restart Django** — skills are loaded at import time, not hot-reloaded

### Copilot asks for confirmation before executing
Some destructive operations (delete, unpublish) trigger a confirmation prompt from the Copilot. The Copilot will ask "Você gostaria de prosseguir?" or similar. You must send a follow-up message confirming before the action executes. This is expected behavior — the Copilot is being cautious. Simply reply "Sim, pode prosseguir" or similar.

### Adding new skills requires Django restart
Skills are registered via `@register_skill` decorators that execute at module import time. When you add a new skill file:
1. Create the `.py` file in `chat/skills/`
2. Add `import chat.skills.<new_skill>` to `chat/skills/__init__.py`
3. **Restart Django** — the runserver with `--noreload` won't pick up new imports
4. Verify the skill loads: `python -c "import chat.skills.<new_skill>; print('OK')"`

### Chat route is /chat, not /copilot
The sidebar label says "Copilot" but the actual TanStack route is `/chat`. Navigating to `/copilot` returns 404. Use `http://localhost:8080/chat` directly or click the "Copilot" sidebar link.

### Copilot response not visible in snapshot
The chat response renders via SSE streaming and may not appear in the accessibility tree snapshot immediately. The snapshot can get stuck showing stale data even after the Copilot has responded. To read the actual chat content:

```javascript
// In browser_console:
document.querySelector('main')?.innerText
```

This captures all visible text including the Copilot's responses, even when the snapshot shows stale data. If the snapshot hasn't changed after 3+ attempts, use this technique instead of polling the snapshot.

### Chat input field may be covered by overlays
After navigating between modules and back to chat, overlays/modals may cover the sidebar. Navigate directly to `http://localhost:8080/chat` to get a clean chat page.

### SSE streaming doesn't complete
The chat endpoint streams tokens via Server-Sent Events. If the stream cuts off:
- Check the Daphne/ASGI server is running (not just the WSGI dev server)
- Check browser console for WebSocket/SSE errors
- Restart the Daphne server if needed

### Validation shows stale data
After the Copilot confirms an action, the UI may not reflect it immediately:
- Refresh the page
- Check the API directly to confirm the backend persisted the change
- The frontend may need a cache invalidation or refetch

### Django fails to start (lxml path pollution)
When running `manage.py` from within `execute_code`, the Hermes agent's own `sys.path` is prepended, causing the project venv's `lxml` to be shadowed by Hermes' lxml (which lacks `etree`). Fix: run Django via `subprocess.Popen` with a **clean environment** — strip `HERMES_*` env vars and ensure the project venv's `Scripts` directory is first in `PATH`:

```python
env = os.environ.copy()
for key in list(env.keys()):
    if 'HERMES' in key.upper():
        del env[key]
env['PATH'] = os.pathsep.join([
    os.path.join(back_dir, ".venv", "Scripts"),
    os.environ.get('PATH', '')
])
```

### Bug registration during test execution
When a test step fails due to a system bug (not a test script error), follow this procedure:

1. **Register the bug**: Create `.hermes/inbox/bugs/BUG-YYYYMMDD-<slug>.md` with:
   - Status: [Aberto]
   - Descrição: The problem and current behavior
   - Passos para Reproduzir: Exact steps to reproduce
   - Comportamento Esperado: What should happen
   - App Atingido: The affected Django app

2. **Document in the LOOP spec**: Update the results table with the bug reference

3. **Continue testing**: If the bug blocks a phase, skip it and test the remaining phases. Note the gap in the results table.

4. **Fix later**: Bugs found during testing should be fixed in a separate pass, not during the test execution itself (unless the test is a goal-loop that includes auto-correction).

5. **Close when fixed**: After implementing the fix, update the bug file status to `[Corrigido]` and re-run the affected phase.

### Page model has no published_at field
The `Page` model in `pages/models.py` does NOT have a `published_at` field — only `is_published` (Boolean). When writing a `manage_page` skill, do NOT reference `published_at` or `timezone.now()` for publish/unpublish. Simply toggle `is_published`:

```python
# CORRECT:
page.is_published = True
page.save(update_fields=["is_published"])

# WRONG (will crash):
page.published_at = timezone.now()
page.save(update_fields=["is_published", "published_at"])
```

### New skills need clean import verification
After creating a new skill file and adding it to `__init__.py`, verify the import works before restarting Django:

```bash
python -c "import chat.skills.<new_skill>; print('OK')"
```

Run this with a clean environment (no HERMES_* vars) to catch import errors early. Common errors:
- Indentation errors (check the `execute` method body)
- Missing imports (e.g. `from django.utils import timezone` when the model doesn't need it)
- Wrong model field names (check the actual model definition first)
