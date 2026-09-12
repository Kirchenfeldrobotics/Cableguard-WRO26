#!/usr/bin/env bash
#
# One-time graphify setup for a fresh clone of Cableguard-WRO26.
#
# Git hooks live in .git/hooks and cannot be committed, so every developer
# has to run this script once themselves after cloning.
#
# Usage:  ./scripts/setup-graphify.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

info() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$1" >&2; }

# Make sure tools installed into the user-local bin dir are reachable in this
# shell, even if the login shell has not picked them up yet.
export PATH="$HOME/.local/bin:$PATH"

# --- 1. uv ------------------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
    info "uv found: $(uv --version)"
else
    info "uv not found - installing..."
    case "$(uname -s)" in
        MINGW*|MSYS*|CYGWIN*)
            powershell -NoProfile -ExecutionPolicy Bypass \
                -Command "irm https://astral.sh/uv/install.ps1 | iex"
            ;;
        *)
            curl -LsSf https://astral.sh/uv/install.sh | sh
            ;;
    esac
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv >/dev/null 2>&1 || {
        warn "uv is still not on PATH. Open a new terminal and re-run this script."
        exit 1
    }
    info "uv installed: $(uv --version)"
fi

# --- 2. graphify ------------------------------------------------------------
# The PyPI package is 'graphifyy' (double y); the CLI command is 'graphify'.
info "Installing/updating graphify (PyPI package: graphifyy)..."
uv tool install graphifyy --upgrade

if ! command -v graphify >/dev/null 2>&1; then
    info "graphify not on PATH yet - running 'uv tool update-shell'..."
    uv tool update-shell || true
    export PATH="$HOME/.local/bin:$PATH"
fi

command -v graphify >/dev/null 2>&1 || {
    warn "graphify is still not on PATH. Open a new terminal and re-run this script."
    exit 1
}
info "graphify ready: $(graphify --version)"

# --- 3. Git hooks -----------------------------------------------------------
# Installs post-commit / post-checkout rebuild hooks and the merge driver for
# graphify-out/graph.json. Not committable - hence this script.
info "Installing git hooks and the graph.json merge driver..."
graphify hook install
graphify hook status

# --- 4. Bring the graph up to date -----------------------------------------
info "Updating the knowledge graph (local, tree-sitter only - no API cost)..."
graphify update .

info "Done. Run 'graphify update .' once after every 'git pull'."
