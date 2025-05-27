#!/bin/zsh
# Backend Virtual Environment Activation Script
# Usage: source backend/activate.sh

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="$SCRIPT_DIR/.venv"

if [ -d "$VENV_PATH" ]; then
    echo "🐍 Activating Python virtual environment: $VENV_PATH"
    source "$VENV_PATH/bin/activate"
    echo "✅ Virtual environment activated"
    echo "📁 Current directory: $(pwd)"
    echo "🐍 Python: $(which python)"
    echo "📦 Python version: $(python --version)"
else
    echo "❌ Virtual environment not found at: $VENV_PATH"
    echo "💡 Run: cd backend && uv venv .venv && uv sync"
fi 