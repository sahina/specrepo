#!/usr/bin/env python3
"""
IDE Configuration Helper

This script helps you configure your IDE to use the correct Python interpreter
for this project.
"""

import sys
from pathlib import Path


def main():
    print("🔧 IDE Configuration Helper")
    print("=" * 50)

    # Current Python executable
    python_path = sys.executable
    print(f"✅ Current Python executable: {python_path}")

    # Project root
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    print(f"📁 Backend directory: {backend_dir}")
    print(f"📁 Project root: {project_root}")

    # Virtual environment
    venv_path = project_root / ".venv"
    if venv_path.exists():
        print(f"🐍 Virtual environment: {venv_path}")
        print(f"🐍 Python in venv: {venv_path / 'bin' / 'python3'}")
    else:
        print("❌ Virtual environment not found!")
        return

    print("\n🎯 IDE Configuration Instructions:")
    print("-" * 40)

    print("\n📝 For VS Code/Cursor:")
    print("1. Open Command Palette (Cmd+Shift+P)")
    print("2. Type 'Python: Select Interpreter'")
    print("3. Choose 'Enter interpreter path...'")
    print(f"4. Enter: {venv_path / 'bin' / 'python3'}")

    print("\n📝 For PyCharm:")
    print("1. Go to Settings/Preferences")
    print("2. Project > Python Interpreter")
    print("3. Click gear icon > Add...")
    print("4. Select 'Existing environment'")
    print(f"5. Choose: {venv_path / 'bin' / 'python3'}")

    print("\n🧪 Test imports:")
    try:
        import httpx

        print(f"✅ httpx version: {httpx.__version__}")
    except ImportError:
        print("❌ httpx not found")

    try:
        import schemathesis

        print(f"✅ schemathesis version: {schemathesis.__version__}")
    except ImportError:
        print("❌ schemathesis not found")

    print(f"\n💡 If imports still fail, run: cd {backend_dir} && pnpm install")


if __name__ == "__main__":
    main()
