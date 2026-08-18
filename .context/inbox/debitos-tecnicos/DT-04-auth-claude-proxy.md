# DT-04 — `claude_proxy.py` sem autenticação

**Tipo**: Segurança · **Prioridade**: Média · **Aberto em**: 2026-08-18
**Relacionado**: SEC-02 em `.context/docs/03-seguranca-lgpd.md`

## Contexto

`scripts/claude_proxy.py` expõe `/v1/chat/completions` delegando a `claude -p`, que
usa a sessão OAuth do Claude Code do usuário. O servidor **não valida nenhum
header** — qualquer processo local pode consumir a sessão e a cota.

Mitigação atual: bind em `127.0.0.1` (não exposto na rede). Risco residual: outros
processos/usuários na mesma máquina.

## Proposta

Validar `Authorization: Bearer <token>` contra `CLAUDE_PROXY_TOKEN`:

- Token ausente no ambiente → mantém comportamento atual + aviso no startup
  (não quebra quem já usa).
- Token presente → rejeitar requisição sem match com 401.

Combina bem com o `.env` das skills, que já precisa preencher `LLM_API_KEY`
(hoje ignorada pelo proxy).

## Critério de aceite

- Com `CLAUDE_PROXY_TOKEN` setado, requisição sem o header correto recebe 401.
- `.env.example` documenta a variável.
