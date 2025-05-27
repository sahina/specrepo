# SpecRepo

A project for managing and collaborating on API specifications using a web interface and AI-powered task management.

## Architecture Overview

(A placeholder for an architecture diagram or description)

## Getting Started

### Prerequisites

- Node.js (with pnpm)
- Python (with uv)
- Git

### Installation

1. Clone the repo

   ```sh
   git clone https://github.com/sahina/specrepo.git # Replace with actual repo URL
   ```

2. Install dependencies

   ```sh
   # Root (if applicable, e.g., for monorepo tools)
   # pnpm install

   # Frontend
   cd frontend
   pnpm install

   # Backend
   cd backend
   uv venv  # Create .venv if it doesn't exist
   uv pip sync requirements.lock # Install dependencies
   ```

### Running the Application

- Frontend: `cd frontend && pnpm dev`
- Backend: `cd backend && uv run uvicorn main:app --reload`

### Running with Docker Compose

Alternatively, you can run the entire application stack using Docker Compose:

1. **Prerequisites:**
    - Docker Desktop (or Docker Engine + Docker Compose CLI) installed and running.

2. **Build and Run:**
    Navigate to the project root directory where `docker-compose.yml` is located and run:

    ```sh
    docker-compose up --build -d
    ```

    This command will build the Docker images for the frontend and backend services (if they don't exist or have changed) and then start all services defined in the `docker-compose.yml` file in detached mode.

3. **Accessing Services:**
    - **Frontend:** Typically available at `http://localhost:5173` (or the port configured in `docker-compose.yml` and `frontend/Dockerfile`).
    - **Backend API:** Typically available at `http://localhost:8000` (or the port configured in `docker-compose.yml`).
    - Other services like databases or message queues will be accessible within the Docker network as defined in `docker-compose.yml`.

4. **Viewing Logs:**
    To view the logs for a specific service:

    ```sh
    docker-compose logs -f <service_name>
    ```

    For example, for the frontend:

    ```sh
    docker-compose logs -f frontend
    ```

    Or for the backend:

    ```sh
    docker-compose logs -f backend
    ```

5. **Stopping the Application:**
    To stop all running services:

    ```sh
    docker-compose down
    ```

    To stop and remove volumes (useful for a clean restart):

    ```sh
    docker-compose down -v
    ```

## Testing

### Backend Tests

The backend includes a suite of automated tests using `pytest` for database migrations, SQLAlchemy models (CRUD operations, constraints), and potentially API endpoints in the future.

For detailed instructions on how to set up the test environment and run these tests, please refer to the [backend/README.md](backend/README.md).

**Quick Start (from project root):**

1. Ensure Docker and Docker Compose are running.
2. Ensure the test database (`appdb_test`) is created (see `backend/README.md` for details).
3. Run tests:

    ```bash
    cd backend
    # Activate your Python virtual environment if not already active
    # e.g., source ../.venv/bin/activate
    pytest
    cd ..
    ```
