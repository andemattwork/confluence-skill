#!/usr/bin/env bash
# Create a skill-local virtual environment and install the Python dependencies.
#
# Using a .venv avoids the PEP 668 "externally-managed-environment" error that a
# global "pip3 install" triggers on Homebrew Python and recent Debian/Ubuntu,
# and keeps the skill's dependencies isolated from the system interpreter.
#
# Usage (from anywhere):
#   ./scripts/setup.sh
# Then run scripts with:
#   .venv/bin/python scripts/upload_confluence.py ...
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$SKILL_DIR/.venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "Installing dependencies from $REQUIREMENTS"
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"

echo
echo "Done. Run skill scripts with:"
echo "  $VENV_DIR/bin/python scripts/<script>.py ..."
