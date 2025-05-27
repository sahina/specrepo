# SpecRepo

**SpecRepo** is a comprehensive API lifecycle management platform that streamlines the development, testing, and collaboration around API specifications. It bridges the gap between API design and implementation by providing automated mocking, validation, and AI-powered contract generation from real-world traffic.

## What is SpecRepo?

SpecRepo transforms how teams work with APIs by providing a unified platform for:

- **API Specification Management**: Create, version, and manage OpenAPI specifications with an intuitive web interface
- **Automated Mocking**: Deploy specifications as live mock services using WireMock integration
- **Contract Validation**: Validate real API implementations against specifications using Schemathesis
- **AI-Powered Contract Generation**: Upload HAR files and let AI generate draft API specifications and mock configurations
- **Workflow Automation**: Automated notifications and task management through n8n integration

## Key Features

### 🔧 **API Specification Management**

- Full CRUD operations for OpenAPI specifications
- Version control and lifecycle tracking
- Interactive documentation generation
- User authentication and authorization

### 🎭 **Smart Mocking**

- One-click deployment of specifications to WireMock
- Automatic generation of mock endpoints
- Live mock services for frontend development and testing

### ✅ **Automated Validation**

- Schemathesis integration for comprehensive API testing
- Validate live services against specifications
- Detailed validation reports and notifications

### 🤖 **AI-Powered Features**

- HAR file processing with AI generalization
- Automatic generation of draft OpenAPI specifications
- Smart detection and flagging of sensitive data
- Contract "sketching" from real traffic patterns

### 🔄 **Workflow Automation**

- n8n integration for automated notifications
- Email alerts for specification changes, validation results
- Review workflows for AI-generated artifacts

## Architecture Overview

```mermaid
graph TB
    subgraph "User Interface"
        UI[React Frontend<br/>TypeScript, Tailwind CSS]
    end

    subgraph "Core Platform"
        API[FastAPI Backend<br/>Python, SQLAlchemy]
        DB[(PostgreSQL<br/>Database)]
        API --> DB
    end

    subgraph "Services"
        WM[WireMock<br/>Mock Server]
        N8N[n8n<br/>Workflow Automation]
        ST[Schemathesis<br/>API Testing]
    end

    subgraph "AI Modules"
        HAR[HAR Processor]
        GEN[Contract Generator]
        VAL[Data Validator]
    end

    UI <--> API
    API --> WM
    API --> N8N
    API --> ST
    API --> HAR
    API --> GEN
    API --> VAL

    N8N --> EMAIL[Email Notifications]
    WM --> MOCK[Mock Endpoints]
    ST --> PROVIDER[Live API Services]
```

## Core Workflows

```mermaid
graph LR
    subgraph "Specification Lifecycle"
        A[Create/Upload<br/>API Spec] --> B[Deploy to<br/>WireMock]
        B --> C[Validate Against<br/>Live Service]
        C --> D[Generate<br/>Reports]
    end

    subgraph "AI-Powered Generation"
        E[Upload<br/>HAR File] --> F[AI Processing<br/>& Analysis]
        F --> G[Generate Draft<br/>Specifications]
        G --> H[Review &<br/>Refine]
        H --> A
    end

    subgraph "Automation"
        I[Workflow<br/>Triggers] --> J[n8n<br/>Processing]
        J --> K[Email<br/>Notifications]
    end

    B -.-> I
    C -.-> I
    F -.-> I
```

## MVP Scope

The current MVP focuses on delivering core functionalities that demonstrate the platform's value:

### ✅ **Phase 1: Foundation**

- **API Specification Management**: Complete CRUD operations for OpenAPI specifications
- **User Authentication**: API key-based authentication system
- **Database Layer**: PostgreSQL with SQLAlchemy ORM and Alembic migrations

### ✅ **Phase 2: Core Services**

- **WireMock Integration**: Deploy specifications as live mock services
- **Schemathesis Integration**: Validate provider services against specifications
- **n8n Workflow Automation**: Automated email notifications for key events

### 🚧 **Phase 3: AI Features**

- **HAR File Processing**: Upload and process HAR files with basic AI
- **Contract Generation**: Generate draft OpenAPI specifications from traffic
- **Smart Analysis**: Detect and flag sensitive data in API traffic

### 🔮 **Future Enhancements**

- Advanced AI capabilities for specification optimization
- Enhanced collaboration features and user management
- CI/CD integration for automated contract validation
- Support for GraphQL and other API specification formats

## Technology Stack

### **Frontend**

- **React** with TypeScript for type safety
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **Zustand** for state management
- **Vite** for fast development and building

### **Backend**

- **FastAPI** for high-performance API development
- **SQLAlchemy** ORM with PostgreSQL
- **Alembic** for database migrations
- **Pydantic** for data validation
- **Python** with modern async/await patterns

### **Services & Infrastructure**

- **PostgreSQL** for persistent data storage
- **WireMock** for API mocking capabilities
- **Schemathesis** for automated API testing
- **n8n** for workflow automation and notifications
- **Docker & Docker Compose** for containerization

### **AI & Processing**

- **Python AI libraries** integrated into FastAPI backend
- **HAR file processing** for traffic analysis
- **OpenAPI generation** from real-world API usage

## Getting Started

### Prerequisites

- Node.js (with pnpm)
- Python (with uv)
- Git

### Package Management

This project uses modern package managers:

- **Frontend**: `pnpm` for Node.js dependencies
- **Backend**: `uv` for Python dependencies (faster than pip)

For detailed backend package management, see [backend/PACKAGE_MANAGEMENT.md](backend/PACKAGE_MANAGEMENT.md).

### Installation

1. Clone the repo

   ```sh
   git clone https://github.com/sahina/specrepo.git # Replace with actual repo URL
   ```

2. Install dependencies

   ```sh
   # Use the Makefile for easy setup
   make install

   # Or manually:
   # Frontend: cd frontend && pnpm install
   # Backend: cd backend && uv sync
   ```

### Running the Application

```sh
# Start both frontend and backend
make dev

# Or individually:
# Frontend: make dev-frontend
# Backend: make dev-backend
```

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

### Quick Start for API Testing

The easiest way to get started is to use the development environment with pre-seeded test data:

1. **Start the full development environment:**

   ```bash
   make dev
   ```

   This will:
   - Start the PostgreSQL database
   - Run database migrations
   - Seed the database with test users and sample data
   - Start both frontend and backend servers

2. **Access the application:**
   - **Frontend:** <http://localhost:5173>
   - **Backend API:** <http://localhost:8000>
   - **API Documentation:** <http://localhost:8000/docs>

### Test Accounts

The `make dev` command automatically creates test accounts with known API keys:

| Username | Email | API Key | Purpose |
|----------|-------|---------|---------|
| `admin` | <admin@specrepo.dev> | `admin-dev-key-12345678901234567890` | Administrative testing |
| `developer` | <dev@specrepo.dev> | `dev-test-key-12345678901234567890` | Development testing |
| `tester` | <test@specrepo.dev> | `test-api-key-12345678901234567890` | QA testing |

### Manual API Testing

If you prefer to test the API directly:

1. **Start just the backend:**

   ```bash
   make dev-backend
   ```

2. **Test protected endpoints:**

   ```bash
   # Using X-API-Key header
   curl -H "X-API-Key: admin-dev-key-12345678901234567890" http://localhost:8000/api/profile
   
   # Or using Authorization Bearer token
   curl -H "Authorization: Bearer admin-dev-key-12345678901234567890" http://localhost:8000/api/specifications
   ```

### Available Test Endpoints

- **Health Check** (no auth): `GET /health`
- **User Profile** (auth required): `GET /api/profile`
- **API Specifications** (auth required): `GET /api/specifications`
- **Create Specification** (auth required): `POST /api/specifications`

### Creating Additional Test Users

If you need additional test users, you can create them via the API:

```bash
curl -X POST "http://localhost:8000/api/users?username=newuser&email=new@example.com"
```

This will return a response with a generated API key:

```json
{
  "message": "User created successfully",
  "username": "newuser", 
  "api_key": "your-32-character-api-key-here"
}
```

### Seeding Test Data

The development environment automatically seeds test data, but you can also run it manually:

```bash
# Seed test users and sample API specifications
make seed-data
```

### Backend Tests

The backend includes a suite of automated tests using `pytest` for database migrations, SQLAlchemy models (CRUD operations, constraints), and API endpoints.

For detailed instructions on how to set up the test environment and run these tests, please refer to the [backend/README.md](backend/README.md).

**Quick Start (from project root):**

1. Ensure Docker and Docker Compose are running.
2. Ensure the test database (`appdb_test`) is created (see `backend/README.md` for details).
3. Run tests:

    ```bash
    cd backend
    # Activate your Python virtual environment if not already active
    # e.g., source .venv/bin/activate
    pytest
    cd ..
    ```
