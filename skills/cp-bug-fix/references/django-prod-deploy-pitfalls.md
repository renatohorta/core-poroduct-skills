# Django em Produção (ECS/ALB) — Pitfalls de Deploy e Migração

Pitfalls reais encontrados ao corrigir bugs de produção no Crewbotics (Django 5 + DRF,
Postgres, ECS Fargate + ALB). Todos causaram 500/400 em produção e foram resolvidos.

## 1. DisallowedHost do health check do ALB/ECS (IP privado)

**Sintoma:** em produção, TODOS os endpoints retornam 400 (inclusive `/api/v1/health/`),
com log:
```
django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: '10.0.10.100:8000'.
You may need to add '10.0.10.100' to ALLOWED_HOSTS.
```
O ALB marca o target como unhealthy e o serviço cai.

**Causa raiz:** o ALB com `target_type = "ip"` bate no container usando o **IP privado**
do container como Host header (ex: `10.0.x.x`). Esse IP não está em `DJANGO_ALLOWED_HOSTS`
(que só tem o domínio público). `ALLOWED_HOSTS` só aceita o que vem da env var.

**Correção (segura, sem abrir para Hosts arbitrários):** um middleware que adiciona Hosts
de IP privado RFC 1918 ao `ALLOWED_HOSTS` em runtime, ANTES do `CommonMiddleware` (que
valida o host). `config/middleware.py`:

```python
import ipaddress
from django.conf import settings
from django.http import HttpRequest

def _is_private_ip(host: str) -> bool:
    raw = (host or "").strip()
    if ":" in raw:
        parts = raw.rsplit(":", 1)
        if len(parts) == 2 and parts[1].isdigit() and "." in parts[0]:
            raw = parts[0]
    try:
        return ipaddress.ip_address(raw).is_private
    except ValueError:
        return False

class AllowPrivateIpHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request: HttpRequest):
        allowed = getattr(settings, "ALLOWED_HOSTS", [])
        if "*" not in allowed:
            host = request.META.get("HTTP_HOST") or ""
            if _is_private_ip(host):
                domain = host
                if ":" in host and host.rsplit(":", 1)[1].isdigit():
                    domain = host.rsplit(":", 1)[0]
                if domain not in allowed:
                    allowed.append(domain)  # mutação in-place respeitada pelo CommonMiddleware
        return self.get_response(request)
```

Registrar no `MIDDLEWARE` logo após `SecurityMiddleware` (antes do `CommonMiddleware`).

**Pitfalls de implementação:**
- NÃO chamar `request.get_host()` dentro do middleware — ele já valida contra
  `ALLOWED_HOSTS` e levanta `DisallowedHost` antes do seu check. Ler `request.META["HTTP_HOST"]`.
- Adicionar o **domínio sem porta** ao ALLOWED_HOSTS (o `validate_host` usa
  `split_domain_port` e compara só o domínio). Adicionar `10.0.10.100:8000` (com porta)
  não casa.
- `ALLOWED_HOSTS` não aceita CIDR (`10.0.0.0/8`) — só `*` e nomes/IPs exatos.
- Em DEBUG, `ALLOWED_HOSTS` já tem `*`; o middleware só precisa agir em produção.

**Teste de regressão:** rodar a cadeia real `AllowPrivateIpHostMiddleware → CommonMiddleware`
com `RequestFactory` e `HTTP_HOST` de IP privado (deve passar), domínio público (passa),
e `evil.com` (deve levantar `DisallowedHost`). Usar `HttpResponse` real como `get_response`
(o `CommonMiddleware` espera uma HttpResponse; retornar string causa `AttributeError`).

## 2. Migration com `'tabela'::regclass` falha quando a tabela não existe

**Sintoma:** ao rodar `pytest --create-db`, a migration de um app falha com:
```
django.db.utils.ProgrammingError: relation "activity_activitylog" does not exist
LINE 2: WHERE conrelid = 'activity_activitylog'::regclass AND cont...
```

**Causa raiz:** `'tabela'::regclass` lança erro se a tabela ainda não foi criada. Durante
`migrate`/testes, as migrations de `accounts` rodam ANTES das de `activity`/`crews`/etc.
Uma migration de `accounts` que referencia tabelas de outros apps quebra.

**Correção:** usar `to_regclass('tabela')` (retorna NULL se não existe) e validar antes de
agir:
```sql
DO $$
DECLARE tbl_oid oid := to_regclass('activity_activitylog');
BEGIN
  IF tbl_oid IS NULL THEN
    RAISE NOTICE 'tabela ainda não existe — pulando';
    RETURN;
  END IF;
  -- ... usa tbl_oid em vez de 'tabela'::regclass ...
END $$;
```

## 3. Retype de PK uuid→bigint: retipar TODAS as FKs para a PK

**Sintoma:** em produção, TODOS os endpoints filtrados por `organization` retornam 500:
```
psycopg.errors.UndefinedFunction: operator does not exist: uuid = integer
HINT: No operator matches the given name and argument types.
```
Afeta `/dashboard/kpis/`, `/crews/`, `/crew-runs/`, `/outputs/`, `/knowledge/docs/usage/`.

**Causa raiz:** a migration que retipou as PKs para bigint (via `RESTART IDENTITY`) só
retipou `organization_id` de ALGUMAS tabelas (ex: accounts_invite, accounts_user,
pages_page, presentations_presentation). As demais tabelas de domínio (crews_crewrun,
agents_agentoutput, knowledge_productcontext, chat_conversation, billing_invoice,
integrations_*, pages_pagefolder, etc.) ficaram com `organization_id` como **uuid**
enquanto `Organization.id` virou **bigint**. A query `WHERE organization_id = 1`
(inteiro) falha.

**Correção:** criar uma migration que retipa `organization_id` de TODAS as tabelas
restantes de uuid→bigint, idempotente (só age se a coluna ainda for uuid) e que recria
a FK. Combinar com o pitfall #2 (`to_regclass`).

**Regra:** ao retipar uma PK de uuid→bigint, verifique TODAS as colunas FK que apontam
para ela (via `information_schema.columns WHERE column_name='<pk>_id'`) e retipe todas.
Uma omissão parcial derruba todos os endpoints que filtram por aquela FK.

## 4. Deploy workflow referencia Dockerfile removido

**Sintoma:** o GitHub Action de deploy falha com:
```
ERROR: failed to build: failed to solve: failed to read dockerfile: open Dockerfile.celery: no such file or directory
```

**Causa raiz:** o projeto migrou de Celery para asyncio/TaskQueue (roda dentro do Daphne
ASGI), mas o workflow `.github/workflows/deploy.yml` ainda tinha um step que buildava
`Dockerfile.celery` (worker separado) que não existe mais.

**Correção:** remover o step do worker Celery do workflow. O deploy builda apenas a imagem
Django (Daphne ASGI), que já roda o TaskQueue/Scheduler em background. Validar o YAML com
`python -c "import yaml; yaml.safe_load(open('...deploy.yml'))"`.

**Regra:** ao remover um componente de infra (Celery, worker, beat), varrer o workflow de
deploy e o `.env.example` por referências órfãs ao componente removido.

## 5. LLM_MODEL aponta para modelo inexistente → 404 NOT_FOUND, Copilot mudo

**Sintoma:** em produção, o Copilot não responde. Log:
```
litellm.NotFoundError: Vertex_ai_betaException - models/gemini-3-flash is not found
for API version v1alpha ... status: NOT_FOUND
```
O `.env` local usa um modelo válido (ex: `gemini-2.5-flash`), mas produção quebra.

**Causa raiz:** o `LLM_MODEL` de produção vem de um **secret AWS** (`valueFrom =
"${local.secret_prefix}:LLM_MODEL::"` no terraform), NÃO do código. O secret foi
configurado com um modelo que não existe no provedor (ex: `gemini-3-flash`). O código
(`chat/llm_client.py` → `get_model()`) só retorna `settings.LLM_MODEL` ou o default —
**sem fallback de modelo**.

**Correção (defensiva, no código):** adicionar fallback de modelo em `chat/llm_client.py`.
Se o modelo configurado retornar 404/NotFoundError, tentar com um modelo conhecido-bom
antes de desistir:
```python
_FALLBACK_MODEL = "gemini/gemini-2.5-flash"

def _is_not_found_error(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    if "notfound" in name or "not_found" in name:
        return True
    msg = str(exc).lower()
    return "not found" in msg or "404" in msg or "does not exist" in msg
```
Aplicar em `astream_with_tools`, `complete` e `complete_json`: no `except`, se
`_is_not_found_error(exc)` e o modelo atual != `_FALLBACK_MODEL`, re-chamar com
`model=_FALLBACK_MODEL` (e `force_tool` preservado no astream). Só cair no fallback para
erro 404 — erros de rate-limit/chave não devem trocar de modelo.

**Teste de regressão:** mockar `litellm.completion` com `side_effect=[_NotFound(...), _Ok(...)]`
e verificar que a 2ª chamada usou `_FALLBACK_MODEL`; e que erro não-404 não dispara fallback
(`call_count == 1`).

**Nota:** o fallback resolve o sintoma, mas o correto é corrigir o secret `LLM_MODEL` no
AWS para um modelo válido. O fallback usa um modelo mais antigo como rede de segurança.
