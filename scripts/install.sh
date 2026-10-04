#!/usr/bin/env bash
# =============================================================================
# install.sh — Installs/updates the skills in the agents.
#
# The repository hosts TWO families under skills/:
#   • skills/rup/         — the ACTIVE family (Rational Unified Process), installed
#                           by default.
#   • skills/deprecated/  — the legacy cp-* family, only installed with --deprecated.
#
# Usage:
#   ./scripts/install.sh                       # installs the active rup family
#   ./scripts/install.sh --deprecated          # ALSO installs the deprecated cp-* family
#   ./scripts/install.sh --hermes              # Hermes only
#   ./scripts/install.sh --claude              # Claude only
#   ./scripts/install.sh --skill rup-requirements   # one skill only
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
ACTIVE_SRC="$SKILLS_SRC/rup"          # active family (RUP)
DEPRECATED_SRC="$SKILLS_SRC/deprecated"  # legacy cp-* family

# ── Flags ──
DO_HERMES=1
DO_CLAUDE=1
ONLY_SKILL=""
DRY_RUN=0
WITH_DEPRECATED=0

usage() {
  cat <<'EOF'
install.sh — Installs/updates the skills in the agents.

Active family: skills/rup/ (installed by default).
Deprecated family: skills/deprecated/ (cp-* — only with --deprecated).

Usage:
  ./scripts/install.sh                          # installs the active rup family
  ./scripts/install.sh --deprecated             # ALSO installs the deprecated cp-* family
  ./scripts/install.sh --hermes                 # Hermes only
  ./scripts/install.sh --claude                 # Claude only
  ./scripts/install.sh --skill rup-requirements # one skill only
  ./scripts/install.sh --dry-run                # shows what it would do, without copying
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --deprecated) WITH_DEPRECATED=1 ;;
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

# ── Roots to install ──
ROOTS=()
[[ -d "$ACTIVE_SRC" ]] && ROOTS+=("$ACTIVE_SRC")
if [[ "$WITH_DEPRECATED" -eq 1 && -d "$DEPRECATED_SRC" ]]; then
  ROOTS+=("$DEPRECATED_SRC")
fi

if [[ ${#ROOTS[@]} -eq 0 ]]; then
  echo "❌ No skills found in $SKILLS_SRC"
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

# Lists the skill directories of a root (excludes _shared, which is a helper, not a
# skill; and top-level files such as the family README).
skills_in() {
  find "$1" -mindepth 1 -maxdepth 1 -type d ! -name '_shared' ! -name '.*' \
    -printf '%f\n' 2>/dev/null | sort || true
}

# ── Banner ──
echo "════════════════════════════════════════════════════════"
echo "  Core Product Skills — Installation"
echo "  Source: ${ROOTS[*]}"
if [[ "$WITH_DEPRECATED" -eq 0 ]]; then
  echo "  (deprecated cp-* family omitted — pass --deprecated to include it)"
fi
echo "════════════════════════════════════════════════════════"
echo ""

# ── Collect the planned skills (across the selected roots) ──
PLANNED=()
for root in "${ROOTS[@]}"; do
  while IFS= read -r s; do
    [[ -z "$s" ]] && continue
    if [[ -n "$ONLY_SKILL" && "$s" != "$ONLY_SKILL" ]]; then
      continue
    fi
    PLANNED+=("$root::$s")
  done < <(skills_in "$root")
done

if [[ ${#PLANNED[@]} -eq 0 ]]; then
  if [[ -n "$ONLY_SKILL" ]]; then
    echo "❌ Skill '$ONLY_SKILL' not found in ${ROOTS[*]}"
  else
    echo "❌ No skills found in ${ROOTS[*]}"
  fi
  exit 1
fi

# ── Shared helper (_shared): it is NOT a skill — it goes to the skills root ──
SHARED_SRC=""
for root in "${ROOTS[@]}"; do
  if [[ -d "$root/_shared" ]]; then SHARED_SRC="$root/_shared"; break; fi
done

# ── Runs ──
if [[ "$DO_HERMES" -eq 1 ]]; then
  echo "📦 Hermes Agent → $HERMES_SKILLS_DIR/$HERMES_CATEGORY"
  if [[ -n "$SHARED_SRC" ]]; then
    copy_skill "$SHARED_SRC" "$HERMES_SKILLS_DIR/_shared" "_shared"
  fi
  for entry in "${PLANNED[@]}"; do
    root="${entry%%::*}"; s="${entry##*::}"
    copy_skill "$root/$s" "$HERMES_SKILLS_DIR/$HERMES_CATEGORY/$s" "$s"
  done
  echo ""
fi

if [[ "$DO_CLAUDE" -eq 1 ]]; then
  echo "📦 Claude Code → $CLAUDE_SKILLS_DIR"
  if [[ -n "$SHARED_SRC" ]]; then
    copy_skill "$SHARED_SRC" "$CLAUDE_SKILLS_DIR/_shared" "_shared"
  fi
  for entry in "${PLANNED[@]}"; do
    root="${entry%%::*}"; s="${entry##*::}"
    copy_skill "$root/$s" "$CLAUDE_SKILLS_DIR/$s" "$s"
  done
  echo ""
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "🧪 DRY RUN — nothing was copied. Remove --dry-run to execute."
else
  echo "✅ Installation complete (${#PLANNED[@]} skills)."
fi
