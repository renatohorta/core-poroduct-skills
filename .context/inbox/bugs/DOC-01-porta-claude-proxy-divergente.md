# DOC-01 — Porta do claude_proxy divergente entre README e código

**Tipo**: Bug de documentação · **Severidade**: Baixa · **Aberto em**: 2026-08-18

## Sintoma

- `README.md` instrui `python scripts/claude_proxy.py --port 8090` e justifica:
  "evita conflito com frontends na 8080".
- `scripts/claude_proxy.py` define `DEFAULT_PORT = 8080`, e o docstring do módulo
  também exemplifica 8080 e `LLM_API_BASE=http://localhost:8080/v1`.

Quem rodar sem `--port` sobe na 8080 e configurar o `.env` conforme o README
(8090) resulta em conexão recusada.

## Correção proposta

Alinhar em **8090**: mudar `DEFAULT_PORT = 8090` e atualizar o docstring do módulo
(linhas de exemplo `--port` e `LLM_API_BASE`).

## Critério de aceite

- `python scripts/claude_proxy.py` sobe na 8090.
- README, docstring e código citam a mesma porta.
