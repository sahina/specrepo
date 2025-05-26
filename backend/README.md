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

## API Endpoints

### API Specifications

The backend provides a complete CRUD API for managing API specifications. All endpoints require **authentication** via API key.

#### Base URL

```text
/api/specifications
```

#### Endpoints

##### Create API Specification

```http
POST /api/specifications
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "name": "My API",
  "version_string": "v1.0",
  "openapi_content": {
    "openapi": "3.0.0",
    "info": {
      "title": "My API",
      "version": "1.0.0"
    },
    "paths": {}
  }
}
```

**Response:** `201 Created`

```json
{
  "id": 1,
  "name": "My API",
  "version_string": "v1.0",
  "openapi_content": {...},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "user_id": 1
}
```

##### List API Specifications

```http
GET /api/specifications?page=1&size=10&name=search&version_string=v1.0&sort_by=created_at&sort_order=desc
Authorization: Bearer <api_key>
```

**Query Parameters:**

- `page` (int, default: 1): Page number
- `size` (int, default: 10, max: 100): Page size
- `name` (string, optional): Filter by name (partial match, case-insensitive)
- `version_string` (string, optional): Filter by version (exact match)
- `sort_by` (string, default: "created_at"): Sort field (name, version_string, created_at, updated_at)
- `sort_order` (string, default: "desc"): Sort order (asc, desc)

**Response:** `200 OK`

```json
{
  "items": [...],
  "total": 25,
  "page": 1,
  "size": 10,
  "pages": 3
}
```

##### Get API Specification by ID

```http
GET /api/specifications/{id}
Authorization: Bearer <api_key>
```

**Response:** `200 OK` or `404 Not Found`

##### Update API Specification

```http
PUT /api/specifications/{id}
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "name": "Updated API Name",
  "openapi_content": {...}
}
```

**Response:** `200 OK`, `404 Not Found`, or `409 Conflict` (duplicate name/version)

##### Delete API Specification

```http
DELETE /api/specifications/{id}
Authorization: Bearer <api_key>
```

**Response:** `204 No Content` or `404 Not Found`

#### Features

- **Authentication Required**: All endpoints require a valid API key
- **User Isolation**: Users can only access their own specifications
- **Validation**: OpenAPI content is validated using JSON schema
- **Pagination**: List endpoint supports pagination with configurable page size
- **Filtering**: Filter by name (partial match) and version (exact match)
- **Sorting**: Sort by name, version, creation date, or update date
- **Duplicate Prevention**: Prevents duplicate name/version combinations per user
- **Comprehensive Error Handling**: Proper HTTP status codes and error messages
- **n8n Integration**: Automatic webhook notifications to n8n when specifications are created or updated

#### Testing

The API specifications endpoints are thoroughly tested with 23 test cases covering:

- All CRUD operations
- Authentication and authorization
- Input validation
- Pagination, filtering, and sorting
- User isolation
- Error handling and edge cases

Run the tests with:

```bash
pytest tests/test_api_specifications.py -v
```

## n8n Integration

The backend includes integration with n8n for workflow automation and notifications. When API specifications are created or updated, the system automatically sends webhook notifications to configured n8n workflows.

### n8n Features

- **Automatic Notifications**: Webhooks are triggered when API specifications are created or updated
- **Configurable Endpoints**: Support for different webhook URLs for different event types
- **Error Handling**: Comprehensive retry logic with configurable attempts and delays
- **Security**: Optional webhook secret validation
- **Background Processing**: Notifications are sent asynchronously to avoid blocking API responses

### n8n Configuration

Configure n8n integration using environment variables:

#### Required Variables

- `N8N_WEBHOOK_URL`: The n8n webhook URL to send notifications to

#### Optional Variables

- `N8N_WEBHOOK_SECRET`: Secret token for webhook authentication (recommended)
- `N8N_MAX_RETRIES`: Maximum number of retry attempts (default: 3)
- `N8N_RETRY_DELAY_SECONDS`: Delay between retry attempts in seconds (default: 5)
- `N8N_TIMEOUT_SECONDS`: HTTP request timeout in seconds (default: 30)

### Webhook Payload

The webhook payload includes the following information:

```json
{
  "event_type": "created|updated",
  "specification_id": 123,
  "specification_name": "My API",
  "version_string": "v1.0",
  "user_id": 456,
  "timestamp": "2024-01-01T00:00:00Z",
  "openapi_content": {
    "openapi": "3.0.0",
    "info": {"title": "My API"},
    "paths": {}
  }
}
```

### n8n Testing

The n8n integration is thoroughly tested with 25+ test cases covering:

- Service initialization and configuration
- Webhook payload creation and validation
- Success and failure scenarios
- Retry logic and error handling
- Integration with API endpoints
- Background task execution

Run the n8n integration tests with:

```bash
pytest tests/test_n8n_notifications.py -v
```

### Disabling n8n Integration

If `N8N_WEBHOOK_URL` is not set or is empty, the n8n integration will be automatically disabled. The API will continue to function normally without sending notifications.
