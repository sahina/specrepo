#!/usr/bin/env python3
"""
IDE Configuration Helper

This script helps you configure your IDE to use the correct Python interpreter
for this project when working from the project root with a multi-service structure.
"""

import sys
from pathlib import Path


def main():
    print("🔧 IDE Configuration Helper")
    print("=" * 50)

    # Current Python executable
    python_path = sys.executable
    print(f"✅ Current Python executable: {python_path}")

    # Project directories
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    print(f"📁 Backend directory: {backend_dir}")
    print(f"📁 Project root: {project_root}")

    # Virtual environment (should be in backend directory)
    venv_path = backend_dir / ".venv"
    if venv_path.exists():
        print(f"🐍 Virtual environment: {venv_path}")
        print(f"🐍 Python in venv: {venv_path / 'bin' / 'python3'}")
    else:
        print("❌ Virtual environment not found in backend directory!")
        print(f"💡 Run: cd {backend_dir} && uv venv .venv && uv sync")
        return

    print("\n🎯 IDE Configuration Instructions:")
    print("-" * 40)
    print("📝 When working from project root with multi-service structure:")

    print("\n🔹 For VS Code/Cursor:")
    print("1. Open Command Palette (Cmd+Shift+P)")
    print("2. Type 'Python: Select Interpreter'")
    print("3. Choose 'Enter interpreter path...'")
    print(f"4. Enter: {venv_path / 'bin' / 'python3'}")
    print("5. Alternatively, create .vscode/settings.json with:")
    print(f'   {{"python.defaultInterpreterPath": "{venv_path / "bin" / "python3"}"}}')

    print("\n🔹 For PyCharm:")
    print("1. Go to Settings/Preferences")
    print("2. Project > Python Interpreter")
    print("3. Click gear icon > Add...")
    print("4. Select 'Existing environment'")
    print(f"5. Choose: {venv_path / 'bin' / 'python3'}")
    print("6. Set 'Content Root' to include both project root and backend directory")

    print("\n🔹 Additional Configuration:")
    print("• Add backend/ to your IDE's Python path")
    print("• Configure your IDE to recognize backend/ as a Python source directory")
    print("• For VS Code: Add to settings.json:")
    print('  "python.analysis.extraPaths": ["./backend"]')

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

    try:
        import fastapi

        print(f"✅ fastapi version: {fastapi.__version__}")
    except ImportError:
        print("❌ fastapi not found")

    print("\n💡 If imports still fail:")
    print(
        f"   1. Ensure virtual environment is activated: source {venv_path}/bin/activate"
    )
    print(f"   2. Reinstall dependencies: cd {backend_dir} && uv sync")
    print("   3. Restart your IDE after configuration changes")

    print("\n🏗️  Multi-service project structure:")
    print("   📁 project-root/")
    print("   ├── 📁 backend/          (Python service)")
    print("   │   ├── 📁 .venv/        (Python virtual environment)")
    print("   │   ├── 📄 pyproject.toml")
    print("   │   └── 📁 app/")
    print("   ├── 📁 frontend/         (Frontend service)")
    print("   ├── 📁 infrastructure/   (Infrastructure as code)")
    print("   └── 📁 docs/            (Documentation)")


if __name__ == "__main__":
    main()
