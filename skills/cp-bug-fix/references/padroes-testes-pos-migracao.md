# Padrões de Correção em Testes Pós-Migração

Reproduzidos nesta sessão (2026-08-04). Checklist ao encontrar `AttributeError` / `django.db.utils.DataError` / `AssertionError` em testes após migração de infraestrutura.

## 1. `AttributeError: 'Settings' object has no attribute 'CELERY_TASK_ALWAYS_EAGER'`

**Causa:** O setting `CELERY_TASK_ALWAYS_EAGER` foi removido junto com o Celery. Testes que usavam `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` para forçar execução inline agora quebram.

**Correção:** Remover o decorator `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` — com asyncio, tasks rodam inline por padrão (não precisa de broker).

**Ocorreu em:** `tests/chat/test_core.py`, `tests/chat/test_agui.py`

## 2. Chamada de `async def` em teste síncrono sem `asyncio.run()`

**Sintoma:** `AssertionError` — a função async foi chamada mas nunca executou (retornou uma corrotina, não o resultado).

**Causa:** Funções que eram `@shared_task` (síncronas) viraram `async def`. Testes que as chamavam diretamente agora precisam de `asyncio.run()`.

**Correção:**
```python
# Antes:
on_crew_run_approved_callback(crew_run_id=..., user_id=...)

# Depois:
import asyncio
asyncio.run(on_crew_run_approved_callback(crew_run_id=..., user_id=...))
```

**Ocorreu em:** `tests/chat/test_agui_resume_done.py`

## 3. `django.db.utils.DataError: expected 768 dimensions, not 3`

**Sintoma:** Erro de dimensão de embedding ao criar DocumentChunk em teste.

**Causa:** O pgvector espera vetores de 768 dimensões (configurado no schema), mas o teste mockava embeddings com `[0.1, 0.2, 0.3]` (3 dimensões).

**Correção:** Usar `[0.1] * 768` em vez de vetores pequenos nos testes que criam DocumentChunk diretamente.

**Ocorreu em:** `tests/chat/test_knowledge_search.py`

## 4. Settings de LLM deletadas acidentalmente

**Sintoma:** `AttributeError: 'Settings' object has no attribute 'LLM_MODEL'`

**Causa:** Durante a limpeza de settings do Celery, as settings de LLM (`LLM_MODEL`, `LLM_API_KEY`, etc.) foram removidas junto.

**Correção:** Restaurar o bloco completo de settings LLM. Verificar no git diff o que foi removido.

## 5. Teste assume dados de catálogo seedado que NÃO existem no banco de teste

**Sintoma:** `django.db.utils.IntegrityError: null value in column "<col>" violates not-null constraint` ao criar um registro com FK.

**Causa:** O teste faz um lookup de um registro de catálogo global que só existe via seed no dev (`Model.objects.filter(slug=...).first()` retorna `None`), depois cria um registro referenciando esse `None` por FK. O banco de teste **não roda o seed de catálogos grandes** (ex: 1000+ providers de integração, bots, etc.).

**Exemplo real (2026-08-10):** `tests/accounts/test_contract.py::test_integration_contract_hides_credentials` fazia:
```python
prov = IntegrationProvider.objects.filter(slug=Provider.META_ADS).first()  # → None
UserIntegration.objects.create(organization=self.org, provider=prov)  # provider_id null → IntegrityError
```
O provider `meta-ads` existe no dev (1010 providers seedados), mas não no banco de teste.

**Correção:** o teste deve **criar** o registro de catálogo com `get_or_create` (não depender do seed), com os campos obrigatórios do modelo:
```python
from integrations.enums import AuthType, ProviderStatus
prov, _ = IntegrationProvider.objects.get_or_create(
    slug=Provider.META_ADS,
    defaults={
        "name": "Meta Ads",
        "auth_type": AuthType.OAUTH2,
        "provider_status": ProviderStatus.ACTIVE,
    },
)
UserIntegration.objects.create(organization=self.org, provider=prov)
```

**Regra:** em testes de contrato/CRUD que referenciam catálogos globais, SEMPRE criar a entidade de catálogo com `get_or_create` (preencher campos obrigatórios) em vez de `filter(...).first()`. Não assumir que seed de dev existe no banco de teste.

**Ocorreu em:** `tests/accounts/test_contract.py` (após a adição do campo NOT NULL `provider_id`).

## Varredura Completa (obrigatória após migração de settings)

```python
# Verificar settings essenciais que podem ter sido removidos acidentalmente
essential_settings = ["LLM_MODEL", "LLM_API_KEY", "LLM_API_BASE", "LLM_TEMPERATURE", "LLM_TIMEOUT"]
with open("config/settings.py") as f:
    content = f.read()
for s in essential_settings:
    if s not in content:
        print(f"MISSING: {s}")
```
