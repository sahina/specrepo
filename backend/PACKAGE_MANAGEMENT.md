# Backend Package Management

This backend uses **uv** for Python package management, providing a fast and modern alternative to pip/poetry.

## Package Files

- **`pyproject.toml`** - Main project configuration and dependencies (like package.json)
- **`uv.lock`** - Lock file with exact versions (like package-lock.json)

## Common Commands

### Installation

```bash
# Install all dependencies (creates venv automatically)
uv sync

# Install with dev dependencies
uv sync --dev

# Or use the clean runner to avoid VIRTUAL_ENV warnings
python run_clean.py sync
```

### Adding Dependencies

```bash
# Add a runtime dependency
uv add fastapi

# Add a development dependency  
uv add --dev pytest

# Add with version constraint
uv add "fastapi>=0.100.0"
```

### Removing Dependencies

```bash
uv remove package-name
```

### Running Commands

```bash
# Run Python in the virtual environment
uv run python main.py

# Run pytest
uv run pytest

# Run any command in the venv
uv run uvicorn main:app --reload
```

### Updating Dependencies

```bash
# Update all dependencies to latest compatible versions
uv sync --upgrade

# Update lock file only
uv lock
```

## Makefile Integration

Use the Makefile for common tasks:

```bash
# Install all dependencies
make install-backend

# Add a new dependency
make add-dep PACKAGE=requests

# Add a dev dependency
make add-dev-dep PACKAGE=black

# Remove a dependency
make remove-dep PACKAGE=requests

# Update all dependencies
make update-deps

# Sync dependencies
make sync
```

## Keeping Dependencies in Sync

### Daily Development

1. **Always use `uv sync`** instead of `pip install`
2. **Commit `uv.lock`** to version control
3. **Use Makefile commands** for consistency

### Adding New Dependencies

```bash
# Use uv add (automatically updates pyproject.toml and uv.lock)
make add-dep PACKAGE=requests

# Or directly with uv
uv add requests
```

### Team Synchronization

```bash
# When pulling changes from git
make sync

# This ensures everyone has the same dependency versions
```

### Dependency Updates

```bash
# Update all dependencies to latest compatible versions
make update-deps

# Review changes in uv.lock before committing
git diff uv.lock
```

## Avoiding VIRTUAL_ENV Warnings

If you see warnings like:

```
warning: `VIRTUAL_ENV=/path/to/old/.venv` does not match the project environment path `.venv`
```

Use the `run_clean.py` script which temporarily removes the VIRTUAL_ENV variable:

```bash
# Instead of: uv sync
python run_clean.py sync

# Instead of: uv run python script.py
python run_clean.py run python script.py
```

Or use the Makefile commands which handle this automatically:

```bash
make sync
make configure-ide
```

## Why This Setup?

- **Single source of truth**: Only `pyproject.toml` defines dependencies
- **Fast**: uv is significantly faster than pip
- **Modern**: Follows Python packaging standards
- **Automatic venv**: uv manages virtual environments automatically
- **Lock file**: `uv.lock` ensures reproducible builds
- **No conflicts**: Eliminates the confusion of multiple package files
- **Clean execution**: `run_clean.py` eliminates VIRTUAL_ENV warnings

## Migration from Old Setup

We've simplified from:

- ❌ `requirements.txt` (removed)
- ❌ `requirements.lock` (removed)
- ✅ `pyproject.toml` (kept - main config)
- ✅ `uv.lock` (kept - lock file)

This gives you the same functionality with less complexity and better performance.
