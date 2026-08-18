# Instalação e Atualização

Este repositório é a **fonte única de verdade** das Core Product Skills. O script
`scripts/install.sh` propaga as skills para os agentes (Hermes e Claude).

## Pré-requisitos

- **bash** (Git Bash no Windows, ou bash nativo em Linux/macOS)
- Acesso de escrita aos diretórios de skills dos agentes

## Instalação

```bash
# Instala/atualiza TODAS as skills no Hermes e no Claude
./scripts/install.sh

# Apenas no Hermes
./scripts/install.sh --hermes

# Apenas no Claude
./scripts/install.sh --claude

# Apenas uma skill específica
./scripts/install.sh --skill cp-requisitos

# Simulação (mostra o que faria, sem copiar)
./scripts/install.sh --dry-run
```

## Diretórios de destino

O script detecta o destino automaticamente, mas você pode sobrescrever via env vars:

| Env var | Default (Windows) | Default (Linux/macOS) |
|---------|-------------------|----------------------|
| `HERMES_SKILLS_DIR` | `%LOCALAPPDATA%\hermes\skills` | `~/.hermes/skills` |
| `CLAUDE_SKILLS_DIR` | `~/.claude/skills` | `~/.claude/skills` |

### Estrutura de destino

- **Hermes**: as skills são instaladas na categoria `creative`:
  `$HERMES_SKILLS_DIR/creative/<skill>/`
- **Claude**: as skills são instaladas flat:
  `$CLAUDE_SKILLS_DIR/<skill>/`

## Fluxo de atualização

1. Edite as skills **neste repositório** (em `skills/`).
2. Rode `./scripts/install.sh` para propagar.
3. Reinicie o agente (Hermes recarrega skills no próximo turno; Claude recarrega
   no próximo comando).

## Exemplo

```bash
# Atualiza só o orquestrador no Hermes
./scripts/install.sh --hermes --skill cp-orquestrador

# Atualiza tudo no Claude
./scripts/install.sh --claude
```

## Troubleshooting

- **"Nenhuma skill encontrada"**: confirme que `skills/` existe no repositório.
- **Permissão negada**: no Linux/macOS, rode `chmod +x scripts/install.sh`.
- **Claude não vê a skill**: confirme que `~/.claude/skills/<skill>/SKILL.md` existe
  e que o Claude foi reiniciado.
