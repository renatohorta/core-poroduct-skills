#!/usr/bin/env bash
# =============================================================================
# install.sh — Installs/updates the Core Product Skills in the agents.
#
# Installs the skills of this repository (skills/) in both the Hermes Agent and
# Claude Code. The repository is the single source of truth; this script
# propagates the changes to the agents.
#
# Usage:
#   ./scripts/install.sh                 # Hermes + Claude
#   ./scripts/install.sh --hermes        # Hermes only
#   ./scripts/install.sh --claude        # Claude only
#   ./scripts/install.sh --skill cp-requirements   # one skill only
#   ./scripts/install.sh --dry-run       # shows what it would do, without copying
#
# Portability: uses env vars + relative defaults. No hardcoded OS/machine path.
# The destination directories can be overridden via env vars:
#   HERMES_SKILLS_DIR   (default: ~/AppData/Local/hermes/skills on Windows,
#                        ~/.hermes/skills on Linux/macOS)
#   CLAUDE_SKILLS_DIR   (default: ~/.claude/skills)
# =============================================================================
set -euo pipefail

# ── Resolves the repository root directory (independent of where the script runs) ──
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
    *) echo "❌ Unknown argument: $1"; usage ;;
  esac
  shift
done

# ── Resolves destination directories ──
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

# ── Category in Hermes ──
# The cp-* and carousel skills live in the "creative" category in Hermes.
HERMES_CATEGORY="creative"

# ── Skill list (excludes _shared, which is a shared helper, not a skill) ──
mapfile -t SKILLS < <(ls -1 "$SKILLS_SRC" 2>/dev/null | grep -v '^\.' | grep -v '^_shared$' || true)
if [[ ${#SKILLS[@]} -eq 0 ]]; then
  echo "❌ No skills found in $SKILLS_SRC"
  exit 1
fi

if [[ -n "$ONLY_SKILL" ]]; then
  if [[ ! -d "$SKILLS_SRC/$ONLY_SKILL" ]]; then
    echo "❌ Skill '$ONLY_SKILL' not found in $SKILLS_SRC"
    exit 1
  fi
  SKILLS=("$ONLY_SKILL")
fi

# ── Copy function ──
copy_skill() {
  local src="$1" dst="$2" name="$3"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] $name → $dst"
    return
  fi
  rm -rf "$dst"
  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
  # Removes unwanted artifacts if any
  rm -rf "$dst/__pycache__" "$dst/outputs" 2>/dev/null || true
  echo "  ✅ $name → $dst"
}

# ── Runs ──
echo "════════════════════════════════════════════════════════"
echo "  Core Product Skills — Installation"
echo "  Source: $SKILLS_SRC"
echo "════════════════════════════════════════════════════════"
echo ""

if [[ "$DO_HERMES" -eq 1 ]]; then
  echo "📦 Hermes Agent → $HERMES_SKILLS_DIR/$HERMES_CATEGORY"
  # Copies the shared helper _shared to the skills root (it is not a skill)
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
  # Copies the shared helper _shared to the skills root (it is not a skill)
  if [[ -d "$SKILLS_SRC/_shared" ]]; then
    copy_skill "$SKILLS_SRC/_shared" "$CLAUDE_SKILLS_DIR/_shared" "_shared"
  fi
  for s in "${SKILLS[@]}"; do
    copy_skill "$SKILLS_SRC/$s" "$CLAUDE_SKILLS_DIR/$s" "$s"
  done
  echo ""
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "🧪 DRY RUN — nothing was copied. Remove --dry-run to execute."
else
  echo "✅ Installation complete (${#SKILLS[@]} skills)."
fi
