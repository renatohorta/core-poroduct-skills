#!/usr/bin/env bash
# =============================================================================
# install.sh — Instala/atualiza as Core Product Skills nos agentes.
#
# Instala as skills deste repositório (skills/) tanto no Hermes Agent quanto
# no Claude Code. O repositório é a fonte única de verdade; este script propaga
# as mudanças para os agentes.
#
# Uso:
#   ./scripts/install.sh                 # Hermes + Claude
#   ./scripts/install.sh --hermes        # apenas Hermes
#   ./scripts/install.sh --claude        # apenas Claude
#   ./scripts/install.sh --skill cp-requisitos   # apenas uma skill
#   ./scripts/install.sh --dry-run       # mostra o que faria, sem copiar
#
# Portabilidade: usa env vars + defaults relativos. Nenhum path de SO/máquina
# hardcoded. Os diretórios de destino podem ser sobrescritos via env vars:
#   HERMES_SKILLS_DIR   (default: ~/AppData/Local/hermes/skills no Windows,
#                        ~/.hermes/skills no Linux/macOS)
#   CLAUDE_SKILLS_DIR   (default: ~/.claude/skills)
# =============================================================================
set -euo pipefail

# ── Resolve diretório raiz do repositório (independente de onde o script roda) ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"

# ── Flags ──
DO_HERMES=1
DO_CLAUDE=1
ONLY_SKILL=""
DRY_RUN=0

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hermes) DO_CLAUDE=0 ;;
    --claude) DO_HERMES=0 ;;
    --skill) ONLY_SKILL="$2"; shift ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage ;;
    *) echo "❌ Argumento desconhecido: $1"; usage ;;
  esac
  shift
done

# ── Resolve diretórios de destino ──
detect_os() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    Darwin*) echo "macos" ;;
    *) echo "linux" ;;
  esac
}
OS="$(detect_os)"

# Hermes
if [[ -z "${HERMES_SKILLS_DIR:-}" ]]; then
  if [[ "$OS" == "windows" ]]; then
    HERMES_SKILLS_DIR="${LOCALAPPDATA:-$HOME/AppData/Local}/hermes/skills"
  else
    HERMES_SKILLS_DIR="${HOME}/.hermes/skills"
  fi
fi

# Claude
CLAUDE_SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

# ── Categoria no Hermes ──
# As skills cp-* e de carrossel vivem na categoria "creative" no Hermes.
HERMES_CATEGORY="creative"

# ── Lista de skills (exclui _shared, que é helper compartilhado, não skill) ──
mapfile -t SKILLS < <(ls -1 "$SKILLS_SRC" 2>/dev/null | grep -v '^\.' | grep -v '^_shared$' || true)
if [[ ${#SKILLS[@]} -eq 0 ]]; then
  echo "❌ Nenhuma skill encontrada em $SKILLS_SRC"
  exit 1
fi

if [[ -n "$ONLY_SKILL" ]]; then
  if [[ ! -d "$SKILLS_SRC/$ONLY_SKILL" ]]; then
    echo "❌ Skill '$ONLY_SKILL' não encontrada em $SKILLS_SRC"
    exit 1
  fi
  SKILLS=("$ONLY_SKILL")
fi

# ── Função de cópia ──
copy_skill() {
  local src="$1" dst="$2" name="$3"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] $name → $dst"
    return
  fi
  rm -rf "$dst"
  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
  # Remove artefatos indesejados se houver
  rm -rf "$dst/__pycache__" "$dst/outputs" 2>/dev/null || true
  echo "  ✅ $name → $dst"
}

# ── Executa ──
echo "════════════════════════════════════════════════════════"
echo "  Core Product Skills — Instalação"
echo "  Origem: $SKILLS_SRC"
echo "════════════════════════════════════════════════════════"
echo ""

if [[ "$DO_HERMES" -eq 1 ]]; then
  echo "📦 Hermes Agent → $HERMES_SKILLS_DIR/$HERMES_CATEGORY"
  # Copia o helper compartilhado _shared para a raiz de skills (não é skill)
  if [[ -d "$SKILLS_SRC/_shared" ]]; then
    copy_skill "$SKILLS_SRC/_shared" "$HERMES_SKILLS_DIR/_shared" "_shared"
  fi
  for s in "${SKILLS[@]}"; do
    copy_skill "$SKILLS_SRC/$s" "$HERMES_SKILLS_DIR/$HERMES_CATEGORY/$s" "$s"
  done
  echo ""
fi

if [[ "$DO_CLAUDE" -eq 1 ]]; then
  echo "📦 Claude Code → $CLAUDE_SKILLS_DIR"
  # Copia o helper compartilhado _shared para a raiz de skills (não é skill)
  if [[ -d "$SKILLS_SRC/_shared" ]]; then
    copy_skill "$SKILLS_SRC/_shared" "$CLAUDE_SKILLS_DIR/_shared" "_shared"
  fi
  for s in "${SKILLS[@]}"; do
    copy_skill "$SKILLS_SRC/$s" "$CLAUDE_SKILLS_DIR/$s" "$s"
  done
  echo ""
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "🧪 DRY RUN — nada foi copiado. Remova --dry-run para executar."
else
  echo "✅ Instalação concluída (${#SKILLS[@]} skills)."
fi
