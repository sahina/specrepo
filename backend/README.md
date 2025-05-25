# Backend Development Guide

## Code Quality & Linting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and code formatting. Ruff is a fast Python linter and formatter that combines the functionality of flake8, black, isort, and many other tools.

### Running the Linter

To check for linting issues:

```bash
cd backend
uv tool run ruff check .
```

To automatically fix linting issues:

```bash
uv tool run ruff check . --fix
```

### Code Formatting

To check if code is properly formatted:

```bash
uv tool run ruff format --check .
```

To automatically format code:

```bash
uv tool run ruff format .
```

### Running All Quality Checks

To run both linting and formatting checks:

```bash
cd backend
uv tool run ruff check . && uv tool run ruff format --check .
```

### Configuration

Ruff configuration is defined in `pyproject.toml`. The project follows standard Python conventions with Ruff's default settings.

## Running Tests

To run the automated tests for the backend:

1. **Ensure the Docker Compose stack is running**, especially the PostgreSQL service. You can start it with:

    ```bash
    docker-compose up -d postgres
    # Or to bring up the whole stack:
    # docker-compose up -d
    ```

2. **Make sure the test database exists.** The tests are configured to run against a database named `appdb_test` by default (see `backend/tests/conftest.py`). You may need to create this database manually in your PostgreSQL instance if the test user (`user` with password `password` as per `docker-compose.yml`) doesn't have rights to create databases.

    ```sql
    -- Connect to your PostgreSQL instance (e.g., using psql or a GUI tool)
    CREATE DATABASE appdb_test OWNER user;
    ```

3. **Navigate to the `backend` directory:**

    ```bash
    cd backend
    ```

4. **Activate your virtual environment** (if you haven't already):

    ```bash
    # Example if your .venv is in the project root
    source ../.venv/bin/activate 
    # Or if it's in the backend directory itself
    # source .venv/bin/activate 
    ```

5. **Run pytest:**

    ```bash
    pytest
    ```

    To run with a specific database URL (overriding the default in `conftest.py` and `alembic.ini` if `TEST_DATABASE_URL` is not set):

    ```bash
    TEST_DATABASE_URL="postgresql://your_user:your_password@your_host:your_port/your_test_db_name" pytest
    ```

This will discover and execute all tests within the `backend/tests` directory.
