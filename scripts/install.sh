#!/usr/bin/env bash
# =============================================================================
# install.sh — Installs/updates the skills in the agents.
#
# Every directory under skills/ that has a SKILL.md is a skill (the RUP family,
# cp-*). skills/_shared/ is a helper, not a skill: it goes to the agent's skills
# root, never into a category.
#
# Usage:
#   ./scripts/install.sh                       # installs every skill
#   ./scripts/install.sh --hermes              # Hermes only
#   ./scripts/install.sh --claude              # Claude only
#   ./scripts/install.sh --skill cp-requirements   # one skill only
#   ./scripts/install.sh --dry-run             # shows what it would do, without copying
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
  cat <<'EOF'
install.sh — Installs/updates the skills in the agents.

Source: skills/ (every directory with a SKILL.md; _shared goes to the skills root).

Usage:
  ./scripts/install.sh                          # installs every skill
  ./scripts/install.sh --hermes                 # Hermes only
  ./scripts/install.sh --claude                 # Claude only
  ./scripts/install.sh --skill cp-requirements # one skill only
  ./scripts/install.sh --dry-run                # shows what it would do, without copying
EOF
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

# The skills live in the "creative" category in Hermes.
HERMES_CATEGORY="creative"

if [[ ! -d "$SKILLS_SRC" ]]; then
  echo "❌ Skills directory not found: $SKILLS_SRC"
  exit 1
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

# Lists the skills of a root: directories with a SKILL.md (so _shared, hidden dirs
# and top-level files such as README.md are skipped). Pure bash glob — `find
# -printf` is GNU-only and silently returned nothing on macOS/BSD.
skills_in() {
  local d name
  for d in "$1"/*/; do
    [[ -d "$d" ]] || continue
    name="${d%/}"; name="${name##*/}"
    [[ "$name" == "_shared" ]] && continue
    [[ -f "$d/SKILL.md" ]] || continue
    echo "$name"
  done | sort
}

# ── Banner ──
echo "════════════════════════════════════════════════════════"
echo "  Core Product Skills — Installation"
echo "  Source: $SKILLS_SRC"
echo "════════════════════════════════════════════════════════"
echo ""

# ── Collect the planned skills (across the selected roots) ──
PLANNED=()
while IFS= read -r s; do
  [[ -z "$s" ]] && continue
  if [[ -n "$ONLY_SKILL" && "$s" != "$ONLY_SKILL" ]]; then
    continue
  fi
  PLANNED+=("$s")
done < <(skills_in "$SKILLS_SRC")

if [[ ${#PLANNED[@]} -eq 0 ]]; then
  if [[ -n "$ONLY_SKILL" ]]; then
    echo "❌ Skill '$ONLY_SKILL' not found in $SKILLS_SRC"
  else
    echo "❌ No skills found in $SKILLS_SRC"
  fi
  exit 1
fi

# ── Shared helper (_shared): it is NOT a skill — it goes to the skills root ──
SHARED_SRC=""
[[ -d "$SKILLS_SRC/_shared" ]] && SHARED_SRC="$SKILLS_SRC/_shared"

# ── Runs ──
if [[ "$DO_HERMES" -eq 1 ]]; then
  echo "📦 Hermes Agent → $HERMES_SKILLS_DIR/$HERMES_CATEGORY"
  if [[ -n "$SHARED_SRC" ]]; then
    copy_skill "$SHARED_SRC" "$HERMES_SKILLS_DIR/_shared" "_shared"
  fi
  for s in "${PLANNED[@]}"; do
    copy_skill "$SKILLS_SRC/$s" "$HERMES_SKILLS_DIR/$HERMES_CATEGORY/$s" "$s"
  done
  echo ""
fi

if [[ "$DO_CLAUDE" -eq 1 ]]; then
  echo "📦 Claude Code → $CLAUDE_SKILLS_DIR"
  if [[ -n "$SHARED_SRC" ]]; then
    copy_skill "$SHARED_SRC" "$CLAUDE_SKILLS_DIR/_shared" "_shared"
  fi
  for s in "${PLANNED[@]}"; do
    copy_skill "$SKILLS_SRC/$s" "$CLAUDE_SKILLS_DIR/$s" "$s"
  done
  echo ""
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "🧪 DRY RUN — nothing was copied. Remove --dry-run to execute."
else
  echo "✅ Installation complete (${#PLANNED[@]} skills)."
fi
