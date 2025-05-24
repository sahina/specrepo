# MVP Implementation Overview

This plan outlines the development phases for the Minimum Viable Product (MVP) of the API lifecycle management platform, incorporating n8n for workflow automation.

## Phase 0: Foundation & Setup 🏗️

*Goal: Prepare the development environment and project scaffolding, including n8n.*

1. **Project Initialization:**
    * Set up a monorepo for frontend (React) and backend (FastAPI).
    * Initialize basic project structures for Python (FastAPI) and TypeScript (React) using latest recommended React project creation method.
2. **Docker Environment Setup:**
    * Create initial `Dockerfile` stubs for the FastAPI backend and React frontend.
    * Create an initial `docker-compose.yml` defining services:
        * `backend` (FastAPI)
        * `frontend` (React)
        * `postgres` (PostgreSQL)
        * `wiremock` (WireMock)
        * `n8n` (n8n service)
    * Configure basic networking (linking services) and volumes for data persistence (PostgreSQL, n8n).
3. **n8n Initial Configuration:**
    * Ensure the n8n service in `docker-compose.yml` is configured for persistence of its workflows and credentials.
    * Define placeholder n8n webhook URLs (e.g., as environment variables for the FastAPI backend or in a dedicated configuration file) that the backend will use to trigger specific n8n workflows.
4. **Basic CI/CD Placeholder:**
    * Set up a very basic Continuous Integration pipeline (e.g., using GitHub Actions) that triggers on code pushes/pull requests for initial linting and placeholder build/test steps.

## Phase 1: Core Backend - API Specification & Data Management 💾

*Goal: Establish the backend's ability to manage API specifications and trigger initial notifications via n8n.*

1. **Database Schema & Models (PostgreSQL & FastAPI):**
    * Define and implement the PostgreSQL schema for:
        * API Specifications (e.g., `id`, `name`, `version`, `openapi_content` as JSONB/Text, `created_at`, `updated_at`).
        * Basic Users (simplified for MVP, e.g., `id`, `username`, `api_key`).
    * Implement corresponding ORM models (e.g., using SQLAlchemy with Pydantic for FastAPI) for these entities.
    * Generate database migration scripts.
2. **FastAPI CRUD Endpoints for API Specifications:**
    * Implement RESTful API endpoints for Create, Read, List, Update, and Delete (CRUD) operations for API specifications.
    * Include request/response validation using Pydantic models.
    * **n8n Integration:** When a new API specification version is successfully created or published, the FastAPI backend will make an HTTP POST request to a predefined n8n webhook (e.g., `N8N_WEBHOOK_NEW_SPEC`) with relevant details like specification ID, name, version, and a link to view it.
3. **n8n Workflow 1.1: "New API Spec Notification" 📧 (Parallel with Task 1.2 Backend):**
    * **Trigger:** Receives webhook call from FastAPI upon new API specification publication.
    * **Action:** Formats a notification message.
    * **Output:** Sends an email (for MVP) to a configured administrator address or distribution list, notifying about the newly added/updated API specification.
4. **Basic Authentication Stub:**
    * Implement a simple authentication mechanism (e.g., API key passed in a header) for backend API endpoints to provide basic protection.

## Phase 2: Core Contract Testing Mechanics - Backend Integrations ⚙️

*Goal: Integrate WireMock for mocking and Schemathesis for provider validation into the backend, and notify on validation completions via n8n.*

1. **WireMock Integration (Backend):**
    * **Task 2.1.1 (Setup):** Configure the WireMock service in `docker-compose.yml` with its Admin API port exposed internally to the Docker network.
    * **Task 2.1.2 (Backend Module):** Develop a Python module within the FastAPI application to:
        * Programmatically configure WireMock stubs by making calls to WireMock's Admin REST API. This includes translating parts of an API specification (e.g., OpenAPI document) into WireMock JSON mapping configurations.
        * Provide functionality to clear or reset mock configurations for a specific API or all APIs.
2. **Schemathesis Integration (Backend):**
    * **Task 2.2.1 (Backend Module):** Develop a Python module within the FastAPI application to:
        * Utilize the Schemathesis Python library to run schema-based, stateful tests against a given provider's live service URL, using a provided API specification.
        * Parse and structure the Schemathesis test results into a format suitable for API responses or storage.
3. **Backend Endpoints for Mocking & Validation:**
    * Create FastAPI endpoints that:
        * Accept an API specification ID and trigger its setup as mocks in WireMock (using the module from Task 2.1.2).
        * Accept an API specification ID and a target provider URL, trigger Schemathesis validation (using the module from Task 2.2.1), and return the results.
    * **n8n Integration:** When Schemathesis validation (triggered via its FastAPI endpoint) completes, the backend makes an HTTP POST request to an n8n webhook (e.g., `N8N_WEBHOOK_SCHEMATHESIS_DONE`) with key validation results (e.g., API name, version, status: success/failure, summary, link to detailed results if available).
4. **n8n Workflow 2.1: "Schemathesis Validation Notification" 📊 (Parallel with Task 2.3 Backend):**
    * **Trigger:** Receives webhook call from FastAPI upon Schemathesis validation completion.
    * **Action:** Formats a message indicating success or failure, along with key details from the payload.
    * **Output:** Sends an email notification to the user/team who initiated the validation or a predefined admin list.

## Phase 3: Basic Frontend - UI for Core Features 🖥️ (Parallel with Phase 2)

*Goal: Develop the initial user interface to interact with the core backend functionalities. Users will indirectly benefit from n8n notifications triggered by their actions.*

1. **Frontend Project Setup (React, Zustand, Tailwind CSS, shadcn/ui):**
    * Initialize the React project, configure Tailwind CSS, and integrate shadcn/ui for UI components.
    * Set up Zustand for client-side state management.
    * Establish a basic folder structure and component hierarchy.
2. **UI for API Specification Management:**
    * Develop React components to:
        * List existing API specifications (fetches data from the backend List endpoint).
        * Display the content of a single API specification (e.g., using a library like `swagger-ui-react` or a simple pretty-printed JSON/YAML view for MVP).
        * Provide a form to create or upload a new API specification (submits data to the backend Create endpoint).
3. **UI for Interacting with Mocking & Validation:**
    * Develop React components to:
        * Allow users to select an API specification and trigger its deployment to WireMock (calls the backend endpoint from Task 2.3 for mock setup).
        * Display the base URL for the generated WireMock mock service (retrieved from the backend or constructed).
        * Allow users to input a provider's live service URL for a given API specification and trigger Schemathesis validation (calls the backend endpoint from Task 2.3 for validation).
        * Display the results returned from the Schemathesis validation process.

## Phase 4: Enhancing Input & Intelligence - HAR & Basic AI 🧠 (Backend Focus, can parallel with Phase 3)

*Goal: Implement HAR file import for "contract sketching," basic AI assistance for artifact generation, and n8n workflows for related notifications and review processes.*

1. **Basic HAR File Import & Processing (Backend):**
    * **Task 4.1.1 (Endpoint):** Create a FastAPI endpoint that accepts HAR file uploads.
    * **Task 4.1.2 (Parsing):** Implement Python logic to parse uploaded HAR files, extracting relevant information like requests, responses, headers, and bodies.
2. **Initial HAR-to-Artifact Transformation (Backend):**
    * Develop Python logic to transform parsed HAR data into draft artifacts:
        * Draft OpenAPI specification snippets (e.g., inferring paths, methods, basic request/response schemas from observed interactions).
        * Draft WireMock stub configurations (JSON mappings).
3. **Basic AI Assistance for Generalization (Backend):**
    * Integrate simple AI/NLP techniques (e.g., pattern matching, regular expressions, basic type inference from string values) to:
        * Suggest generalizations in the transformed artifacts (e.g., changing specific IDs like `/users/123` to `/users/{userId}` and inferring `userId` as an integer or string).
        * Flag potentially sensitive data patterns in HAR content for user review (for MVP, this involves identifying common patterns like "token", "password", "authorization" in headers or bodies and suggesting they might need masking, rather than performing complex PII detection).
    * **n8n Integration:** After HAR processing and artifact generation by the backend (Tasks 4.1, 4.2, and this task), FastAPI makes HTTP POST requests to two distinct n8n webhooks:
        * One for general notification to the user (e.g., `N8N_WEBHOOK_HAR_PROCESSED_USER`).
        * One to initiate a review request (e.g., `N8N_WEBHOOK_HAR_REVIEW_REQUEST`).
        * Payloads for these webhooks should include details of the processed HAR, links or references to the generated "contract sketches" within the platform, and the user who initiated the process.
4. **n8n Workflow 4.1: "HAR Processed & Sketches Ready Notification" 💡 (Parallel with Task 4.3 Backend):**
    * **Trigger:** Receives webhook call from FastAPI (e.g., `N8N_WEBHOOK_HAR_PROCESSED_USER`).
    * **Action:** Formats a notification message.
    * **Output:** Sends an email notification to the user who uploaded the HAR file, informing them that processing is complete and the generated "contract sketches" are available for review in the platform.
5. **n8n Workflow 4.2: "Review Request for AI-Generated Artifacts" ✅ (Parallel with Task 4.3 Backend):**
    * **Trigger:** Receives webhook call from FastAPI (e.g., `N8N_WEBHOOK_HAR_REVIEW_REQUEST`).
    * **Action:** Formats a detailed message containing links to the AI-generated artifacts (OpenAPI snippets, WireMock stubs).
    * **Output:** Creates a task for human review. For MVP, this could be sending a specially formatted email to a review distribution list or a designated reviewer. The email should prompt them to review, refine, and formally save/promote the artifacts within the platform.
6. **Frontend UI for HAR Upload & "Contract Sketching":**
    * Develop React components for:
        * Uploading HAR files to the backend endpoint (Task 4.1.1).
        * Displaying the AI-suggested/transformed OpenAPI snippets or WireMock stubs returned by the backend.
        * Allowing users to manually copy these suggestions to use in the main API specification editor or for direct mock setup.

## Phase 5: Workflow Orchestration & End-to-End MVP 🔄 (Tying it together)

*Goal: Implement the core mock-centric contract testing workflow and notify on outcomes via n8n.*

1. **Define "Consumer Test" Representation (Backend & Conceptual):**
    * For MVP, a "consumer test" is implicitly defined by consumers relying on the WireMock mocks generated from the provider's API specification. The core workflow ensures that the provider's actual service matches this specification.
    * No explicit storage of separate consumer test code is planned for this MVP iteration to keep complexity low; the focus is on spec compliance and mock accuracy from that spec.
2. **Backend Logic for "Producer Validates Consumer Contracts":**
    * This workflow involves the producer ensuring their actual service aligns with the specification from which consumer-facing mocks are derived. The steps orchestrated or checked by the backend are:
        1. Producer has an up-to-date API Specification in the platform.
        2. Platform has generated WireMock mocks from this specific version of the API Specification (using functionality from Task 2.1.2). Consumers would be using these mocks.
        3. Producer validates their *actual running service* against this *same API Specification* using Schemathesis (triggered via functionality from Task 2.2.1).
        4. The "contract validation" is deemed successful if the Schemathesis validation passes, indicating the provider's service behaves as per the spec (and thus as per the mocks).
    * **n8n Integration:** When the outcome of this overall validation process (primarily the Schemathesis result in this simplified model) is determined, the backend makes an HTTP POST request to an n8n webhook (e.g., `N8N_WEBHOOK_CONTRACT_VALIDATION_DONE`) with the summary (e.g., API name, version, overall status based on Schemathesis).
3. **n8n Workflow 5.1: "Contract Validation Results Notification" 🏁 (Parallel with Task 5.2 Backend):**
    * **Trigger:** Receives webhook call from FastAPI.
    * **Action:** Formats a message summarizing the contract validation outcome (e.g., "Provider service for API X vY successfully validated against the specification" or "Validation failed").
    * **Output:** Sends an email notification to the producer or relevant stakeholders.
4. **Frontend UI to Visualize Workflow Status:**
    * Enhance the UI to clearly display the status related to an API specification:
        * The current API specification content.
        * Status of WireMock mock deployment for that specific spec version.
        * Status and results of the latest Schemathesis validation run for that spec against a provider's service.
        * A clear indication of overall "contract health" based on these statuses.

## Phase 6: Packaging, Documentation & Polish 🎁 (Ongoing, with a final focus)

*Goal: Ensure the MVP is runnable, understandable by developers/users, and n8n workflows are documented.*

1. **Docker Configuration Refinement:**
    * Optimize `Dockerfile`s for all services (frontend, backend, n8n if custom image needed, though base image is usually fine) for smaller image sizes and faster, more efficient builds.
    * Ensure `docker-compose.yml` is robust for easy local development, clearly defining service dependencies, volumes for data persistence (PostgreSQL, n8n data), and exposed ports.
2. **Basic Documentation:**
    * Create a comprehensive `README.md` file in the root of the project (or for each sub-project if using separate repositories) that includes:
        * A clear overview of the MVP's features and architecture.
        * Prerequisites for running the platform (e.g., Docker, Docker Compose installed).
        * Step-by-step instructions to build and run the entire MVP stack locally using a single `docker-compose up` command.
        * A basic user guide outlining how to perform the core workflow (upload spec, generate mocks, validate provider, upload HAR).
    * Utilize FastAPI's built-in capabilities to provide auto-generated API documentation (Swagger UI and ReDoc) for all backend API endpoints.
    * **n8n Workflow Documentation:** For each n8n workflow created:
        * Document its purpose clearly.
        * Specify the trigger mechanism (e.g., the exact webhook URL that the FastAPI backend should call).
        * Detail the expected JSON payload structure from FastAPI.
        * Outline its main actions and outputs (e.g., email recipients, format of the message, any external services it interacts with). This documentation can be kept within the n8n workflow's notes section or in a shared project wiki/document.
3. **Testing & Bug Fixing:**
    * Conduct thorough end-to-end user flow testing for all core features.
    * Prioritize and fix critical bugs identified during testing to ensure a stable MVP.
    * Encourage development of unit and basic integration tests alongside feature implementation (AI agents can be tasked with generating these).
4. **Code Review & Refinement:**
    * Review key parts of the (AI-generated and human-written) code for quality, clarity, basic security considerations (e.g., input validation, no hardcoded secrets), and adherence to project coding standards.
    * Refactor code where necessary for better maintainability and performance.
