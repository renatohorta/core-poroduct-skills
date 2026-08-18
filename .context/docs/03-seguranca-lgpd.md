# Segurança e LGPD — Core Product Skills

> Disciplina: Segurança/Compliance (`cp-seguranca`). Atualizado em 2026-08-18.

## Status

- [x] Concluído (baseline de segurança levantado)

## Classificação do projeto

| Aspecto | Situação |
|---------|----------|
| Tipo | Ferramenta de desenvolvimento (skills/CLI), **uso interno** |
| Exposição de rede | Nenhuma por padrão; apenas `claude_proxy.py` abre socket local |
| Dados pessoais tratados | **Nenhum dado pessoal de terceiros** é coletado ou armazenado |
| Superfície de ataque | Execução local: leitura de `.env`, `subprocess`, chamadas a APIs de LLM |

## Baseline verificado (2026-08-18)

| Verificação | Resultado |
|-------------|-----------|
| Segredos versionados no Git | ✅ Nenhum — `git ls-files` só retorna `.env.example` |
| Chaves de API hardcoded em código | ✅ Nenhuma (`sk-…`/`AIza…` não encontrados) |
| `.gitignore` cobre segredos | ✅ `.env`, `.env.local`, `.env.*.local` |
| Bind do proxy local | ✅ `127.0.0.1` (não `0.0.0.0`) — sem exposição na rede |
| Paths pessoais/máquina hardcoded | ✅ Nenhum nas skills (env var + default relativo) |

## Riscos e controles

| ID | Risco | Severidade | Controle atual | Ação |
|----|-------|-----------|----------------|------|
| SEC-01 | Chave de LLM vaza via `.env` copiado junto com a skill | Média | `install.sh` copia só `skills/`; `.env` fica na raiz e é ignorado pelo Git | Manter — não mover `.env` para dentro de `skills/` |
| SEC-02 | `claude_proxy.py` **não exige autenticação** — qualquer processo local pode consumir a sessão OAuth do Claude Code | Média | Bind restrito a `127.0.0.1` | Documentado; não subir o proxy em máquina compartilhada. Ver DT-04 |
| SEC-03 | Briefings enviados às crews vão para o provider de LLM configurado | Média | Escolha explícita do provider via `.env` | Não colocar segredo/dado pessoal em briefing |
| SEC-04 | `subprocess.run` do orquestrador executa o `run.py` das skills | Baixa | Lista fixa `SKILL_PATHS`, sem `shell=True` | Manter — nunca montar comando por string |
| SEC-05 | `install.sh` faz `rm -rf "$dst"` antes de copiar | Baixa | Destino derivado de env vars conhecidas | Nunca apontar `HERMES_SKILLS_DIR`/`CLAUDE_SKILLS_DIR` para diretório com conteúdo próprio |
| SEC-06 | Artefatos de pipeline podem conter trechos de código do projeto-alvo | Baixa | `outputs/` no `.gitignore` | Manter |

## LGPD

O repositório **não é controlador nem operador de dados pessoais**: não coleta,
não armazena e não processa dados de titulares. Consequências práticas:

- Não há base legal a declarar, nem RIPD aplicável a este repositório.
- **Atenção derivada**: quando as skills rodam sobre um projeto-alvo que trata
  dados pessoais, o conteúdo enviado ao LLM (código, briefings, logs) pode conter
  dados pessoais desse projeto. A avaliação LGPD pertence ao **projeto-alvo**, que
  deve registrá-la no seu próprio `.context/docs/03-seguranca-lgpd.md`.
- Regra operacional: **não colar dados reais de produção** em briefings de skill.

## Gestão de segredos

| Segredo | Onde vive | Nunca |
|---------|-----------|-------|
| `LLM_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` … | `.env` local (não versionado) ou env var do agente | Em `SKILL.md`, `run.py`, `references/` ou commit |

Template público de configuração: `.env.example` (sem valores reais).

## Pendências de segurança

- **DT-04** — `claude_proxy.py` sem autenticação: avaliar token compartilhado
  simples (header `Authorization`) validado contra env var.
- **DOC-01** — Divergência de porta: o `README.md` recomenda `--port 8090` mas
  `DEFAULT_PORT = 8080` em `scripts/claude_proxy.py`. Alinhar (8080 conflita com
  frontends comuns).

## Decisões

- Sem varredura SAST/dependabot por ora: o repositório não tem dependências
  declaradas (sem `requirements.txt`/`pyproject.toml`) — ver DT-05 em
  `.context/docs/05-devops-operacoes.md`.
