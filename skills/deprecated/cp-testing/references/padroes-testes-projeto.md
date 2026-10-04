# Padrões de Teste do Projeto Crewbotics

Convenções e padrões usados nos testes do backend Django/DRF. Siga-os ao criar novos arquivos de teste.

## Estrutura

```
tests/
├── <app>/                  # Espelha os apps Django
│   ├── test_core.py        # Testes principais do app
│   ├── test_<feature>.py   # Testes de feature específica
│   └── ...
├── conftest.py             # Config global (hermético: remove chaves de API)
```

## Padrão de Classe Base

```python
from rest_framework.test import APITestCase
from accounts.models import Organization, User
from accounts.serializers import issue_tokens

class _Base(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Alpha")
        self.user = User.objects.create_user(
            email="p@a.com", password="x", name="Prod", organization=self.org
        )
        self.client.credentials(HTTP_AUTHORIZATION=*** {issue_tokens(self.user)['access']}")
```

## Padrão de Teste (4 casos mínimos)

```python
class NomeTests(_Base):
    def test_success_case(self):
        resp = self.client.post(self.url, {...}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_requires_auth(self):
        self.client.credentials()  # limpa auth
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_validation_error(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_scoped_by_org(self):
        other = Organization.objects.create(name="Beta")
        # Cria dados em outra org
        resp = self.client.get(self.url)
        # Verifica que não vazam
```

## Autenticação

- **`issue_tokens(user)['access']`** — gera JWT para o header Authorization
- **`force_authenticate(user)`** — alternativa (pula validação JWT, útil quando o endpoint não usa JWT)
- **`client.credentials()`** sem argumentos → limpa o header (testa 401)

## ViewSets vs APIViews

- **ViewSets** (CRUD via router): testar list, create, retrieve, update, partial_update, destroy
- **APIViews** (custom): testar get/post/patch/delete conforme o método implementado

## Pós-Migração Asyncio (Celery → TaskQueue)

- `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` **não existe mais** — remover o decorator
- Funções `async def` chamadas em testes síncronos: usar `asyncio.run(fn())`
- Embeddings em DocumentChunk: usar `[0.1] * 768` (não `[0.1, 0.2, 0.3]`)
- Tasks rodam inline por padrão (sem broker) — não precisa de setting especial
