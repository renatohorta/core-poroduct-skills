# Testes com Async — Padrões Pós-Migração (Celery → TaskQueue)

## Problema: `sync_to_async` não vê dados do teste

**Sintoma:** `DoesNotExist` ao chamar `asyncio.run(index_document(str(doc.pk)))` — o documento foi criado no teste mas a função async não o encontra.

**Causa:** `APITestCase` (e `TestCase`) envolvem cada teste em uma transação que é revertida no final. `sync_to_async` executa a função síncrona em uma **thread pool**. Por padrão, `sync_to_async` usa `thread_sensitive=True`, que compartilha a conexão com a thread principal — mas em alguns casos (especialmente com `database_sync_to_async`), uma **nova conexão** é criada, que não vê os dados não comitados da transação do teste.

**Solução:** Usar `TransactionTestCase` em vez de `APITestCase` para classes de teste que chamam funções async com operações ORM:

```python
from django.test import TransactionTestCase

class DocTests(TransactionTestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Alpha")
        self.user = User.objects.create_user(...)
        self.client.credentials(HTTP_AUTHORIZATION=*** {issue_tokens(self.user)['access']}")

    def test_async_index(self):
        resp = self.client.post("/api/v1/knowledge/docs/", {...}, format="json")
        doc = ProductContext.objects.get(uuid=resp.json()["id"])
        asyncio.run(index_document(str(doc.pk)))  # ← funciona com TransactionTestCase
        doc.refresh_from_db()
        self.assertEqual(doc.index_status, IndexStatus.INDEXED)
```

**`TransactionTestCase` vs `APITestCase`:**

| Característica | `APITestCase` | `TransactionTestCase` |
|---|---|---|
| Transação por teste | Sim (rollback) | Não (commita) |
| Velocidade | Mais rápido | Mais lento (commita de verdade) |
| Dados visíveis em threads async | ❌ Não | ✅ Sim |
| Quando usar | Testes puramente síncronos | Testes que chamam `asyncio.run(fn_com_orm())` |

**Regra prática:** Se o teste chama `asyncio.run()` com uma função que faz ORM, use `TransactionTestCase`. Caso contrário, mantenha `APITestCase`.

## `sync_to_async` vs `database_sync_to_async`

- **`sync_to_async`** — usa `thread_sensitive=True` por padrão. Tenta reutilizar a conexão da thread principal. Funciona com `TransactionTestCase` porque os dados estão commitados.
- **`database_sync_to_async`** — cria uma nova conexão. **NÃO funciona** com dados não commitados de `APITestCase`. Prefira `sync_to_async` para operações ORM em tasks async.

```python
# tasks_async.py — usar sync_to_async, NÃO database_sync_to_async
from asgiref.sync import sync_to_async

async def index_document(document_id):
    doc = await sync_to_async(ProductContext.objects.get)(pk=document_id)
    await sync_to_async(doc.save)(update_fields=["index_status"])
```

## Checklist para testes quebrados pós-migração

1. **`@override_settings(CELERY_TASK_ALWAYS_EAGER=True)`** — remover (não existe mais)
2. **`funcao_que_era_celery.delay(args)`** — substituir por `enqueue_task_sync("nome", funcao_async, args)`
3. **`funcao_async(args)` sem await** — envolver em `asyncio.run(funcao_async(args))`
4. **`doc.id` vs `doc.pk`** — usar `doc.pk` (PK interno, não UUID público)
5. **`run_pipeline`** — está em `crews.crew_runner_async`, não em `crews.tasks_async`
6. **Embedding dimension** — `[0.1] * 768`, não `[0.1, 0.2, 0.3]`
7. **Lambda mock** — `lambda *a, **kw: ...` (aceitar args posicionais), não `lambda **kw: ...`
8. **`asyncio.run(asyncio.run(...))`** — remover duplicação
