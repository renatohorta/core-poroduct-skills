---
name: cp-implementacao
description: "Implementação de Software — cria uma crew CrewAI com Dev Backend, Frontend, Mobile, Revisor e Integrador para codificar features, revisar código e integrar componentes. Use quando o usuário disser 'implementar', 'codificar', 'desenvolver', 'fazer code review', 'integrar front e back'."
---

# cp-implementacao — Implementação de Software

Cria uma crew CrewAI self-contained com 5 agentes especializados para implementar, revisar e integrar código de software.

## Agentes

| Agente | Função |
|--------|--------|
| **Desenvolvedor Backend** | Implementa APIs, lógica de negócio, modelos, migrações, endpoints REST/GraphQL |
| **Desenvolvedor Frontend** | Implementa UI, componentes React/Vue/Angular, estados, integração com API, acessibilidade |
| **Desenvolvedor Mobile** | Implementa versão mobile (React Native / Flutter), telas, navegação, integração com API |
| **Revisor de Código** | Code review: verifica padrões, boas práticas, segurança, performance, coesão |
| **Integrador** | Garante que front+back+mobile funcionam juntos, testes de integração, validação de contratos |

## Pipeline

```
[Dev Backend] ──► [Dev Frontend] ──► [Dev Mobile*] ──► [Revisor] ──► [Integrador]
      │                │                    │               │               │
      │  APIs,         │  UI,               │  telas,       │  code         │  integração
      │  modelos,      │  componentes,      │  navegação    │  review       │  + validação
      │  migrações     │  estados           │               │               │
      └────────────────┴────────────────────┴───────────────┴───────────────┴──► PASS/FAIL
```

*Dev Mobile é opcional — executado apenas quando `--type mobile` ou `--type full`.

## Entrada

- **Especificação técnica** — descrição do que implementar (features, endpoints, componentes)
- **Contratos de API** (opcional) — definição das interfaces entre frontend e backend
- Pode ser texto direto ou arquivo via `--input`

## Saída

- Código implementado (backend, frontend e/ou mobile)
- Relatório de code review com problemas encontrados e sugestões
- Relatório de integração com veredito PASS/FAIL

## Quality Gate

O Integrador emite veredito final PASS/FAIL. Se FAIL, lista os problemas de integração que precisam ser resolvidos.

## Uso

```bash
# Implementação completa (backend + frontend)
python .hermes/skills/cp-implementacao/scripts/run.py "implementar CRUD de usuários com autenticação JWT"

# Apenas backend
python .hermes/skills/cp-implementacao/scripts/run.py "criar endpoint de relatórios" --type backend

# Apenas frontend
python .hermes/skills/cp-implementacao/scripts/run.py "tela de login com validação" --type frontend

# Full stack + mobile
python .hermes/skills/cp-implementacao/scripts/run.py "sistema de agendamento" --type full

# Com especificação de arquivo
python .hermes/skills/cp-implementacao/scripts/run.py --input especificacao.md

# Salvar saída em diretório específico
python .hermes/skills/cp-implementacao/scripts/run.py "CRUD de produtos" --output ./implementacao

# Apenas ver a estrutura da crew
python .hermes/skills/cp-implementacao/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-implementacao/scripts/run.py \
  "implementar módulo de autenticação: registro (email+senha), login com JWT, \
   recuperação de senha, middleware de autenticação. Frontend: tela de login, \
   registro, dashboard protegido. Contrato: /api/auth/register POST, \
   /api/auth/login POST, /api/auth/forgot-password POST" \
  --type full --output ./modulo-auth
```

## Script

O script `scripts/run.py` é self-contained — todos os 5 agentes estão embutidos no próprio código Python. Não depende de diretório externo de agentes.

## Reference Files

- `references/django-windows-hermes-pitfalls.md` — Hermes venv contamination fix, git SSH on Windows, force-push to overwrite bot commits, TanStack Router routeTree.gen.ts exclusion
- `references/aws-ses-smtp-setup.md` — AWS SES SMTP setup for Django transactional email (password reset, invites), domain verification, IAM user creation, HTML email templates
