# Padrões de bugs pós-migração (additions)

Pitfalls class-level adicionados em sessões recentes de bugfix no Crewbotics (Django/DRF + Postgres).

## 1. `operator does not exist: uuid = integer` em TODOS os endpoints filtrados por organização

**Sintoma:** dashboard, crews, crew-runs, outputs e knowledge usage todos retornam 500 com:
```
psycopg.errors.UndefinedFunction: operator does not exist: uuid = integer
LINE 1: ..._status" = 'DONE' AND "crews_crewrun"."organization_id" = 1)
HINT:  No operator matches the given name and argument types.
```

**Causa raiz:** numa migração de PK UUID→bigint (ex: `accounts/0009_retype_fk_columns_to_bigint.py` que faz `RESTART IDENTITY CASCADE` + retype das PKs), a migration retipou `organization_id` de apenas ALGUMAS tabelas (frequentemente `accounts_invite`, `accounts_user`, `pages_page`, `presentations_presentation`) e **esqueceu** as de domínio:
- `crews_crewrun`, `crews_crewinstance`, `crews_crewchatsession`, `crews_crewschedule`
- `agents_agentinstance`, `agents_agentoutput`
- `knowledge_productcontext`, `knowledge_knowledgefolder`
- `chat_conversation`
- `billing_invoice`, `billing_offer`
- `integrations_userintegration`, `integrations_webhookevent`, `integrations_assetlibraryitem`, `integrations_whatsappsession`, `integrations_whatsappmessagelog`
- `pages_pagefolder`
- `activity_activitylog`

Essas ficam com `organization_id` como `uuid`, enquanto `accounts_organization.id` virou `bigint`. A query `WHERE organization_id = 1` (inteiro) falha.

**Diagnóstico:**
```sql
SELECT table_name, data_type FROM information_schema.columns
WHERE column_name='organization_id' AND table_schema='public'
ORDER BY table_name;
```
Compare com o tipo de `accounts_organization.id` (deve ser bigint). Toda linha `uuid` = bug.

**Correção:** migration RunSQL idempotente, por tabela:
```sql
DO $$
DECLARE fk_name text;
BEGIN
  SELECT conname INTO fk_name FROM pg_constraint
  WHERE conrelid = '<t>'::regclass AND contype='f'
    AND confrelid = 'accounts_organization'::regclass LIMIT 1;
  IF fk_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE <t> DROP CONSTRAINT %I', fk_name);
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name='<t>' AND column_name='organization_id' AND data_type='uuid') THEN
    EXECUTE 'ALTER TABLE <t> ALTER COLUMN organization_id TYPE bigint USING NULL';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conrelid='<t>'::regclass AND contype='f'
                   AND confrelid='accounts_organization'::regclass) THEN
    EXECUTE 'ALTER TABLE <t> ADD CONSTRAINT <t>_organization_id_fk_cb FOREIGN KEY (organization_id) REFERENCES accounts_organization(id) DEFERRABLE INITIALLY DEFERRED';
  END IF;
END $$;
```
**Testar num banco já consistente** — deve rodar como no-op sem erro (valida a idempotência).
**Deploy:** se o erro está em produção, a migration precisa ser aplicada lá (o rollout do workflow de deploy roda `migrate`).

## 1b. MESMO bug, mas nas FKs de `user_id` (e `decision_by_id`) — a migration 0009 esqueceu AMBAS as classes de FK

**Sintoma:** depois de corrigir `organization_id`, um endpoint que filtra por `user` (ex: `GET /api/v1/chat/conversations/`) ainda retorna 500 com `operator does not exist: uuid = integer` na coluna `user_id`:
```
LINE 1: ...ization_id" = 1 AND "chat_conversation"."user_id" = 1 ...
```

**Causa raiz:** a migration de PK UUID→bigint retipou `organization_id` de algumas tabelas E as PKs, mas **esqueceu de retipar as FKs que referenciam `accounts_user`** (`user_id`) e `crews_crewrun.decision_by_id`. Em produção essas colunas ficaram `uuid` enquanto `User.id` virou `bigint`.

**Diagnóstico — listar TODAS as FKs que referenciam as PKs principais (não só organization):**
```sql
SELECT tc.table_name, kcu.column_name, ccu.table_name AS ref_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type='FOREIGN KEY'
  AND ccu.table_name IN ('accounts_user','accounts_organization')
ORDER BY ccu.table_name, tc.table_name;
```
Compare cada coluna com o tipo da PK referenciada. Toda linha `uuid` = bug.

**Correção:** mesma migration RunSQL idempotente, mas para as FKs de `user_id`/`decision_by_id` (referenciando `accounts_user`). Tabelas típicas: `activity_activitylog.user_id`, `chat_agenttask.user_id`, `chat_conversation.user_id`, `crews_crewchatsession.user_id`, `crews_crewrun.decision_by_id`, `accounts_passwordresettoken.user_id`, `accounts_user_groups.user_id`, `accounts_user_user_permissions.user_id`, `django_admin_log.user_id`, `token_blacklist_outstandingtoken.user_id`.

**PITFALL CRÍTICO — usar `to_regclass`, NÃO `'tabela'::regclass`:** quando a migration de retype vive no app `accounts` mas referencia tabelas de OUTROS apps (activity, chat, crews...), o `'activity_activitylog'::regclass` lança erro durante `pytest --create-db` porque a tabela ainda não foi criada (as migrations de activity rodam DEPOIS das de accounts). Use `to_regclass('tabela')` que retorna NULL em vez de lançar, e pule o bloco se NULL:
```sql
DO $$
DECLARE tbl_oid oid := to_regclass('activity_activitylog');
BEGIN
  IF tbl_oid IS NULL THEN RAISE NOTICE 'tabela ainda não existe — pulando'; RETURN; END IF;
  ...
END $$;
```
Sem isso, a migration passa no dev (banco já populado) mas quebra a suíte de testes que recria o schema do zero.

## 2. `exclude` / `__in` é case-sensitive no Postgres — não dar `.lower()` nos valores

**Sintoma:** ao implementar "exclua tudo exceto X", o item X que deveria ser mantido acaba excluído.

**Causa:** o código lowercasing os valores antes do match (`keep = [str(x).strip().lower() ...]`), mas o `title__in=[...]` no Postgres é case-sensitive. `'the ultimate...'` (lowercase) não casa com `'The Ultimate...'` (título real).

**Correção:** manter `str(x).strip()` (case original) para a query `__in`. Adicionar teste de regressão que verifica que o item com case exato é mantido e que um item com case divergente é excluído.
