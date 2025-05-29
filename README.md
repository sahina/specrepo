# SpecRepo

**SpecRepo** is a comprehensive API lifecycle management platform that streamlines the development, testing, and collaboration around API specifications. It bridges the gap between API design and implementation by providing automated mocking, validation, and AI-powered contract generation from real-world traffic.

## Table of Contents

- [What is SpecRepo?](#what-is-specrepo)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Core Workflows](#core-workflows)
- [MVP Scope](#mvp-scope)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Application](#running-the-application)
  - [Running with Docker Compose](#running-with-docker-compose)
- [Usage Examples](#usage-examples)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

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

Before you begin, ensure you have the following installed on your system:

- **Node.js** (v18 or higher) with **pnpm** package manager
- **Python** (v3.11 or higher) with **uv** package manager
- **Git** for version control
- **Docker** and **Docker Compose** (for containerized deployment)
- **PostgreSQL** (v15 or higher) - if running locally without Docker

#### Installing Prerequisites

**Node.js and pnpm:**

```bash
# Install Node.js (using nvm recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Install pnpm
npm install -g pnpm
```

**Python and uv:**

```bash
# Install Python 3.11+ (using pyenv recommended)
curl https://pyenv.run | bash
pyenv install 3.11.0
pyenv global 3.11.0

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Docker:**

- Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Ensure Docker Compose is included (it comes with Docker Desktop)

### Package Management

This project uses modern package managers:

- **Frontend**: `pnpm` for Node.js dependencies
- **Backend**: `uv` for Python dependencies (faster than pip)

For detailed backend package management, see [backend/PACKAGE_MANAGEMENT.md](backend/PACKAGE_MANAGEMENT.md).

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/sahina/specrepo.git
   cd specrepo
   ```

2. **Install dependencies:**

   ```bash
   # Use the Makefile for easy setup
   make install

   # Or manually:
   # Frontend dependencies
   cd frontend && pnpm install && cd ..
   
   # Backend dependencies
   cd backend && uv sync && cd ..
   ```

3. **Set up environment variables:**

   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit the .env file with your configuration
   # See Configuration section below for details
   ```

### Configuration

SpecRepo uses environment variables for configuration. Copy `.env.example` to `.env` and configure the following:

#### Database Configuration

```bash
# PostgreSQL connection
DATABASE_URL=postgresql://user:password@localhost:5432/appdb
```

#### Service Integration

```bash
# WireMock Integration
WIREMOCK_URL=http://localhost:8081

# n8n Integration
N8N_WEBHOOK_URL=http://localhost:5679/webhook-test/api-spec-notification
N8N_WEBHOOK_SECRET=your-secret-key
N8N_MAX_RETRIES=3
N8N_RETRY_DELAY_SECONDS=5
N8N_TIMEOUT_SECONDS=30
```

#### Optional Configuration

```bash
# API Rate Limiting
RATE_LIMIT_MAX_ATTEMPTS=100
RATE_LIMIT_WINDOW_SECONDS=3600

# Logging
LOG_LEVEL=INFO
```

### Running the Application

#### Option 1: Local Development (Recommended for Development)

1. **Start the database:**

   ```bash
   # Using Docker for PostgreSQL
   docker run --name specrepo-postgres -e POSTGRES_PASSWORD=password -e POSTGRES_USER=user -e POSTGRES_DB=appdb -p 5432:5432 -d postgres:15-alpine
   ```

2. **Start both frontend and backend:**

   ```bash
   make dev
   ```

3. **Or start services individually:**

   ```bash
   # Backend only
   make dev-backend

   # Frontend only  
   make dev-frontend
   ```

#### Option 2: Docker Compose (Recommended for Production)

1. **Start all services:**

   ```bash
   docker-compose up --build -d
   ```

2. **View logs:**

   ```bash
   # All services
   docker-compose logs -f

   # Specific service
   docker-compose logs -f backend
   docker-compose logs -f frontend
   ```

3. **Stop services:**

   ```bash
   docker-compose down
   
   # Stop and remove volumes (clean restart)
   docker-compose down -v
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

## Usage Examples

### API Authentication

SpecRepo uses API key authentication. Here are examples of how to interact with the API:

#### Creating a User Account

```bash
curl -X POST "http://localhost:8000/api/users?username=myuser&email=my@email.com"
```

Response:

```json
{
  "message": "User created successfully",
  "username": "myuser",
  "api_key": "your-32-character-api-key-here"
}
```

#### Using API Keys

```bash
# Using X-API-Key header (recommended)
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/api/profile

# Using Authorization Bearer token
curl -H "Authorization: Bearer your-api-key-here" http://localhost:8000/api/specifications
```

### Managing API Specifications

#### Upload an OpenAPI Specification

```bash
curl -X POST "http://localhost:8000/api/specifications" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API",
    "version": "1.0.0",
    "specification": {
      "openapi": "3.0.0",
      "info": {
        "title": "My API",
        "version": "1.0.0"
      },
      "paths": {
        "/users": {
          "get": {
            "summary": "Get users",
            "responses": {
              "200": {
                "description": "Success"
              }
            }
          }
        }
      }
    }
  }'
```

#### Deploy to WireMock

```bash
curl -X POST "http://localhost:8000/api/wiremock/deploy/1" \
  -H "X-API-Key: your-api-key-here"
```

### HAR File Processing

#### Upload and Process HAR Files

```bash
curl -X POST "http://localhost:8000/api/har/upload" \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@sample_har_file.har"
```

## API Documentation

Once the application is running, you can access the interactive API documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

These interfaces provide:

- Complete API endpoint documentation
- Interactive "Try it out" functionality
- Request/response examples
- Authentication requirements
- Data model schemas

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

## Troubleshooting

### Common Issues

#### Database Connection Issues

**Problem**: `psycopg2.OperationalError: could not connect to server`

**Solution**:

1. Ensure PostgreSQL is running:

   ```bash
   # Check if PostgreSQL container is running
   docker ps | grep postgres
   
   # Start PostgreSQL if not running
   docker-compose up postgres -d
   ```

2. Verify database credentials in `.env` file
3. Check if the database exists:

   ```bash
   docker exec -it specrepo-postgres psql -U user -d appdb -c "\l"
   ```

#### Frontend Build Issues

**Problem**: `Module not found` or dependency issues

**Solution**:

1. Clear node_modules and reinstall:

   ```bash
   cd frontend
   rm -rf node_modules pnpm-lock.yaml
   pnpm install
   ```

2. Check Node.js version compatibility:

   ```bash
   node --version  # Should be v18+
   ```

#### Docker Issues

**Problem**: `Port already in use` errors

**Solution**:

1. Check what's using the port:

   ```bash
   lsof -i :8000  # For backend
   lsof -i :5173  # For frontend
   ```

2. Stop conflicting services or change ports in `docker-compose.yml`

#### API Key Authentication Issues

**Problem**: `401 Unauthorized` responses

**Solution**:

1. Verify API key format (should be 32 characters)
2. Check header format:

   ```bash
   # Correct format
   curl -H "X-API-Key: your-api-key-here" http://localhost:8000/api/profile
   ```

3. Ensure the user exists in the database

### Getting Help

If you encounter issues not covered here:

1. Check the application logs:

   ```bash
   # Docker Compose logs
   docker-compose logs backend
   docker-compose logs frontend
   
   # Local development logs
   # Backend logs appear in terminal where you ran `make dev-backend`
   # Frontend logs appear in terminal where you ran `make dev-frontend`
   ```

2. Verify your environment configuration matches `.env.example`

3. Try a clean restart:

   ```bash
   # Docker Compose
   docker-compose down -v
   docker-compose up --build -d
   
   # Local development
   make clean
   make install
   make dev
   ```

## Contributing

We welcome contributions to SpecRepo! Here's how to get started:

### Development Setup

1. **Fork the repository** on GitHub

2. **Clone your fork:**

   ```bash
   git clone https://github.com/your-username/specrepo.git
   cd specrepo
   ```

3. **Create a feature branch:**

   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Set up the development environment:**

   ```bash
   make install
   make dev
   ```

### Code Style and Standards

- **Backend**: Follow PEP 8 for Python code. Use `ruff` for linting and formatting.
- **Frontend**: Follow the project's ESLint and Prettier configurations.
- **Commits**: Use conventional commit messages (e.g., `feat:`, `fix:`, `docs:`).

### Running Tests

Before submitting a pull request, ensure all tests pass:

```bash
# Run all tests
make test

# Run backend tests only
cd backend && pytest

# Run frontend tests only
cd frontend && pnpm test
```

### Submitting Changes

1. **Ensure tests pass** and code follows style guidelines
2. **Update documentation** if you've changed functionality
3. **Commit your changes:**

   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

4. **Push to your fork:**

   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request** on GitHub with:
   - Clear description of changes
   - Reference to any related issues
   - Screenshots for UI changes

### Reporting Issues

When reporting bugs or requesting features:

1. **Search existing issues** to avoid duplicates
2. **Use issue templates** when available
3. **Provide detailed information:**
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Environment details (OS, versions, etc.)
   - Relevant logs or error messages

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Questions or need help?** Open an issue on GitHub or reach out to the maintainers.
