# Python Development Setup

This document explains how to set up Python development for this multi-service project when working from the project root.

## Project Structure

```text
project-root/
├── backend/                 # Python service
│   ├── .venv/              # Python virtual environment (local to backend)
│   ├── pyproject.toml      # Python dependencies
│   ├── app/                # Application code
│   ├── tests/              # Test files
│   └── activate.sh         # Virtual environment activation script
├── frontend/               # Frontend service
├── infrastructure/         # Infrastructure as code
└── docs/                   # Documentation
```

## Quick Start

### 1. Set up the virtual environment

```bash
# From project root
cd backend
uv venv .venv
uv sync
```

### 2. Activate the virtual environment

```bash
# Option 1: From project root (zsh)
source backend/activate.sh

# Option 2: From backend directory
cd backend
source .venv/bin/activate

# Option 3: Using uv (recommended)
cd backend
uv run python --version
```

### 3. Configure your IDE

Run the configuration helper:

```bash
# From backend directory
python configure_ide.py
```

## IDE Configuration

### VS Code/Cursor (Recommended)

The project includes pre-configured settings in `.vscode/settings.json`:

- **Python Interpreter**: `./backend/.venv/bin/python3`
- **Analysis Paths**: Includes `./backend` for proper import resolution
- **Testing**: Configured to run pytest from the backend directory
- **Terminal**: Sets `PYTHONPATH` to include backend directory

#### Manual Configuration

If you need to configure manually:

1. Open Command Palette (`Cmd+Shift+P`)
2. Type "Python: Select Interpreter"
3. Choose "Enter interpreter path..."
4. Enter: `./backend/.venv/bin/python3`

### PyCharm

1. Go to Settings/Preferences
2. Project > Python Interpreter
3. Click gear icon > Add...
4. Select "Existing environment"
5. Choose: `./backend/.venv/bin/python3`
6. Set "Content Root" to include both project root and backend directory

## Development Workflow

### Running the Application

```bash
# From project root
cd backend
uv run python main.py

# Or with activated environment
source backend/activate.sh
python backend/main.py
```

### Running Tests

```bash
# From backend directory
uv run pytest

# Or with activated environment
source backend/activate.sh
pytest
```

### Adding Dependencies

```bash
# From backend directory
uv add package-name

# For development dependencies
uv add --dev package-name
```

## Troubleshooting

### Import Errors in IDE

If you see import errors for packages like `httpx`, `schemathesis`, or `fastapi`:

1. **Check Python Interpreter**: Ensure your IDE is using `./backend/.venv/bin/python3`
2. **Restart IDE**: After changing interpreter settings
3. **Verify Installation**: Run `python configure_ide.py` from the backend directory
4. **Check PYTHONPATH**: Ensure `./backend` is in your IDE's Python analysis paths

### Virtual Environment Issues

```bash
# Recreate virtual environment
cd backend
rm -rf .venv
uv venv .venv
uv sync
```

### IDE Not Finding Packages

1. Ensure the virtual environment is properly activated
2. Check that `.vscode/settings.json` has the correct paths
3. Restart your IDE after configuration changes
4. Verify `python.analysis.extraPaths` includes `"./backend"`

## Multi-Service Benefits

This setup allows you to:

- **Work from project root**: Open the entire project in your IDE
- **Isolate Python dependencies**: Virtual environment is contained within the backend service
- **Add other services**: Easy to add Go, Rust, or other language services
- **Maintain clean structure**: Each service manages its own dependencies
- **Scale independently**: Each service can have different Python versions or dependencies

## Environment Variables

Create a `.env` file in the backend directory for service-specific environment variables:

```bash
# backend/.env
DATABASE_URL=postgresql://localhost/mydb
API_KEY=your-api-key
```

The IDE is configured to load environment variables from `backend/.env` automatically.

## Future Services

When adding new services (e.g., Go, Rust):

```text
project-root/
├── backend/           # Python service
│   └── .venv/        # Python virtual environment
├── api-gateway/      # Go service
│   └── go.mod        # Go dependencies
├── worker/           # Rust service
│   └── Cargo.toml    # Rust dependencies
└── frontend/         # Frontend service
    └── package.json  # Node.js dependencies
```

Each service maintains its own dependency management and virtual environments/workspaces.
