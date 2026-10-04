# Post-migration bug patterns (additions)

Class-level pitfalls added in recent Crewbotics bugfix sessions (Django/DRF + Postgres).

## 1. `operator does not exist: uuid = integer` in ALL endpoints filtered by organization

**Symptom:** dashboard, crews, crew-runs, outputs and knowledge usage all return 500 with:
```
psycopg.errors.UndefinedFunction: operator does not exist: uuid = integer
LINE 1: ..._status" = 'DONE' AND "crews_crewrun"."organization_id" = 1)
HINT:  No operator matches the given name and argument types.
```

**Root cause:** in a PK UUID→bigint migration (e.g. `accounts/0009_retype_fk_columns_to_bigint.py` that does `RESTART IDENTITY CASCADE` + PK retype), the migration retyped `organization_id` of only SOME tables (often `accounts_invite`, `accounts_user`, `pages_page`, `presentations_presentation`) and **forgot** the domain ones:
- `crews_crewrun`, `crews_crewinstance`, `crews_crewchatsession`, `crews_crewschedule`
- `agents_agentinstance`, `agents_agentoutput`
- `knowledge_productcontext`, `knowledge_knowledgefolder`
- `chat_conversation`
- `billing_invoice`, `billing_offer`
- `integrations_userintegration`, `integrations_webhookevent`, `integrations_assetlibraryitem`, `integrations_whatsappsession`, `integrations_whatsappmessagelog`
- `pages_pagefolder`
- `activity_activitylog`

These keep `organization_id` as `uuid`, while `accounts_organization.id` became `bigint`. The query `WHERE organization_id = 1` (integer) fails.

**Diagnosis:**
```sql
SELECT table_name, data_type FROM information_schema.columns
WHERE column_name='organization_id' AND table_schema='public'
ORDER BY table_name;
```
Compare with the type of `accounts_organization.id` (must be bigint). Every `uuid` row = bug.

**Fix:** idempotent RunSQL migration, per table:
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
**Test on an already-consistent database** — it must run as a no-op without error (validates idempotency).
**Deploy:** if the error is in production, the migration must be applied there (the deploy workflow rollout runs `migrate`).

## 1b. SAME bug, but on the `user_id` FKs (and `decision_by_id`) — migration 0009 forgot BOTH FK classes

**Symptom:** after fixing `organization_id`, an endpoint that filters by `user` (e.g. `GET /api/v1/chat/conversations/`) still returns 500 with `operator does not exist: uuid = integer` on the `user_id` column:
```
LINE 1: ...ization_id" = 1 AND "chat_conversation"."user_id" = 1 ...
```

**Root cause:** the PK UUID→bigint migration retyped `organization_id` of some tables AND the PKs, but **forgot to retype the FKs that reference `accounts_user`** (`user_id`) and `crews_crewrun.decision_by_id`. In production these columns stayed `uuid` while `User.id` became `bigint`.

**Diagnosis — list ALL the FKs that reference the main PKs (not just organization):**
```sql
SELECT tc.table_name, kcu.column_name, ccu.table_name AS ref_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type='FOREIGN KEY'
  AND ccu.table_name IN ('accounts_user','accounts_organization')
ORDER BY ccu.table_name, tc.table_name;
```
Compare each column with the type of the referenced PK. Every `uuid` row = bug.

**Fix:** same idempotent RunSQL migration, but for the `user_id`/`decision_by_id` FKs (referencing `accounts_user`). Typical tables: `activity_activitylog.user_id`, `chat_agenttask.user_id`, `chat_conversation.user_id`, `crews_crewchatsession.user_id`, `crews_crewrun.decision_by_id`, `accounts_passwordresettoken.user_id`, `accounts_user_groups.user_id`, `accounts_user_user_permissions.user_id`, `django_admin_log.user_id`, `token_blacklist_outstandingtoken.user_id`.

**CRITICAL PITFALL — use `to_regclass`, NOT `'tabela'::regclass`:** when the retype migration lives in the `accounts` app but references tables from OTHER apps (activity, chat, crews...), the `'activity_activitylog'::regclass` throws an error during `pytest --create-db` because the table has not been created yet (the activity migrations run AFTER the accounts ones). Use `to_regclass('tabela')` which returns NULL instead of throwing, and skip the block if NULL:
```sql
DO $$
DECLARE tbl_oid oid := to_regclass('activity_activitylog');
BEGIN
  IF tbl_oid IS NULL THEN RAISE NOTICE 'tabela ainda não existe — pulando'; RETURN; END IF;
  ...
END $$;
```
Without this, the migration passes in dev (already-populated database) but breaks the test suite that recreates the schema from scratch.

## 2. `exclude` / `__in` is case-sensitive in Postgres — do not `.lower()` the values

**Symptom:** when implementing "exclude everything except X", the item X that should be kept ends up excluded.

**Cause:** the code lowercased the values before the match (`keep = [str(x).strip().lower() ...]`), but `title__in=[...]` in Postgres is case-sensitive. `'the ultimate...'` (lowercase) does not match `'The Ultimate...'` (real title).

**Fix:** keep `str(x).strip()` (original case) for the `__in` query. Add a regression test that verifies the exact-case item is kept and that an item with divergent case is excluded.
