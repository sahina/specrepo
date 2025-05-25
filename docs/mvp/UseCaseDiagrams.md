# MVP Use Case Sequence Diagrams

Here are the Mermaid sequence diagrams for the identified MVP use cases:

## 1. API Specification Management & New Spec Notification

This use case covers a user creating a new API specification, which is then saved by the backend, and a notification is triggered via n8n.

```mermaid
sequenceDiagram
    actor User
    participant ReactFrontend as React Frontend
    participant FastAPIBackend as FastAPI Backend
    participant PostgreSQLDB as PostgreSQL Database
    participant N8N as n8n

    User->>+ReactFrontend: Fills form to create new API Specification (name, version, content)
    ReactFrontend->>+FastAPIBackend: POST /api/specifications (spec details)
    FastAPIBackend->>+PostgreSQLDB: Save API Specification
    PostgreSQLDB-->>-FastAPIBackend: Confirm save
    FastAPIBackend->>+N8N: POST N8N_WEBHOOK_NEW_SPEC (spec ID, name, version) [Task 1.2]
    N8N-->>-FastAPIBackend: Webhook received
    activate N8N
    N8N->>N8N: Workflow 1.1: Format "New API Spec Notification" [Task 1.3]
    N8N->>User: Send Email Notification (to admin/list) [Task 1.3]
    deactivate N8N
    FastAPIBackend-->>-ReactFrontend: Success response (e.g., new spec ID)
    ReactFrontend-->>-User: Display success message & new specification
```

## 2. Mocking an API Specification

This use case shows a user triggering the deployment of an API specification to WireMock through the UI. No specific n8n notification is defined for *just* mock deployment completion in Phase 2 of the MVP.

```mermaid
sequenceDiagram
    actor User
    participant ReactFrontend as React Frontend
    participant FastAPIBackend as FastAPI Backend
    participant PostgreSQLDB as PostgreSQL Database
    participant WireMockService as WireMock

    User->>+ReactFrontend: Selects API Spec, Clicks "Deploy to Mock"
    ReactFrontend->>+FastAPIBackend: POST /api/specifications/{spec_id}/deploy-mock (API Spec ID) [Task 3.3, 2.3]
    FastAPIBackend->>+PostgreSQLDB: Retrieve API Specification content (for spec_id)
    PostgreSQLDB-->>-FastAPIBackend: Return API Specification content
    FastAPIBackend->>FastAPIBackend: Module (Task 2.1.2): Transform spec to WireMock JSON mappings
    FastAPIBackend->>+WireMockService: Admin API Calls: Configure stubs (JSON mappings) [Task 2.1.2]
    WireMockService-->>-FastAPIBackend: Confirm stubs configured
    FastAPIBackend-->>-ReactFrontend: Success response (e.g., WireMock base URL)
    ReactFrontend-->>-User: Display WireMock base URL & success message [Task 3.3]
```

## 3. Validating a Provider against an API Specification & Notification

This use case details a user initiating a Schemathesis validation for an API specification against a live provider URL. The backend performs the validation and triggers an n8n notification with the results.

```mermaid
sequenceDiagram
    actor User
    participant ReactFrontend as React Frontend
    participant FastAPIBackend as FastAPI Backend
    participant PostgreSQLDB as PostgreSQL Database
    participant SchemathesisLib as Schemathesis (Library)
    participant ProviderService as External Provider Service
    participant N8N as n8n

    User->>+ReactFrontend: Inputs Provider URL for API Spec, Clicks "Validate Provider" [Task 3.3]
    ReactFrontend->>+FastAPIBackend: POST /api/specifications/{spec_id}/validate (API Spec ID, provider_url) [Task 2.3]
    FastAPIBackend->>+PostgreSQLDB: Retrieve API Specification content (for spec_id)
    PostgreSQLDB-->>-FastAPIBackend: Return API Specification content
    FastAPIBackend->>+SchemathesisLib: Run schema-based tests (spec_content, provider_url) [Task 2.2.1]
    SchemathesisLib->>+ProviderService: HTTP Requests (based on spec)
    ProviderService-->>-SchemathesisLib: HTTP Responses
    SchemathesisLib-->>-FastAPIBackend: Validation results
    FastAPIBackend->>FastAPIBackend: Parse and structure Schemathesis results [Task 2.2.1]
    FastAPIBackend->>+N8N: POST N8N_WEBHOOK_SCHEMATHESIS_DONE (results summary) [Task 2.3]
    N8N-->>-FastAPIBackend: Webhook received
    activate N8N
    N8N->>N8N: Workflow 2.1: Format "Schemathesis Validation Notification" [Task 2.4]
    N8N->>User: Send Email Notification (success/failure, details) [Task 2.4]
    deactivate N8N
    FastAPIBackend-->>-ReactFrontend: Return Schemathesis validation results
    ReactFrontend-->>-User: Display validation results [Task 3.3]
```

## 4. HAR File Upload, "Contract Sketching," & Notifications

This use case covers a user uploading a HAR file. The backend processes it, uses basic AI for generalization, generates draft artifacts ("contract sketches"), and triggers n8n notifications for the user and for a review process.

```mermaid
sequenceDiagram
    actor User
    participant ReactFrontend as React Frontend
    participant FastAPIBackend as FastAPI Backend
    note over FastAPIBackend: Includes Basic AI Module
    participant N8N as n8n

    User->>+ReactFrontend: Uploads HAR file [Task 4.6]
    ReactFrontend->>+FastAPIBackend: POST /api/har/upload (HAR file) [Task 4.1.1]
    FastAPIBackend->>FastAPIBackend: Parse HAR file [Task 4.1.2]
    FastAPIBackend->>FastAPIBackend: Transform HAR to draft OpenAPI snippets & WireMock stubs [Task 4.2]
    FastAPIBackend->>FastAPIBackend: Basic AI: Generalize artifacts, flag sensitive data [Task 4.3]
    
    FastAPIBackend->>+N8N: POST N8N_WEBHOOK_HAR_PROCESSED_USER (details, links to sketches) [Task 4.3]
    N8N-->>-FastAPIBackend: Webhook received
    activate N8N
    N8N->>N8N: Workflow 4.1: Format "HAR Processed & Sketches Ready" message [Task 4.4]
    N8N->>User: Send Email: "HAR Processed & Sketches Ready" [Task 4.4]
    deactivate N8N

    FastAPIBackend->>+N8N: POST N8N_WEBHOOK_HAR_REVIEW_REQUEST (details, links for review) [Task 4.3]
    N8N-->>-FastAPIBackend: Webhook received
    activate N8N
    N8N->>N8N: Workflow 4.2: Format "Review Request for AI-Generated Artifacts" message [Task 4.5]
    N8N->>User: Send Email: "Review Request for AI-Generated Artifacts" (to reviewer/list) [Task 4.5]
    deactivate N8N

    FastAPIBackend-->>-ReactFrontend: Return AI-suggested/transformed artifacts
    ReactFrontend-->>-User: Display contract sketches for review/copying [Task 4.6]
```

## 5. End-to-End Mock-Centric Contract Validation & Notification

This use case outlines the producer validating their actual service against the API specification. The success of this validation (primarily based on Schemathesis results) implies that the producer's service aligns with the specification from which consumer-facing mocks are derived. The outcome is notified via n8n.

```mermaid
sequenceDiagram
    actor User as Producer
    participant ReactFrontend as React Frontend
    participant FastAPIBackend as FastAPI Backend
    participant PostgreSQLDB as PostgreSQL Database
    participant SchemathesisLib as Schemathesis (Library)
    participant ProviderService as Producer's Live Service
    participant N8N as n8n

    Note over User, ProviderService: Assumes API Spec exists & WireMock mocks are deployed from it [Task 5.2.1, 5.2.2]

    Producer->>+ReactFrontend: Initiates "Contract Validation" for an API Spec (provides Provider's Live Service URL) [Task 5.4]
    ReactFrontend->>+FastAPIBackend: POST /api/contract-validation (API Spec ID, provider_live_url)
    FastAPIBackend->>+PostgreSQLDB: Retrieve API Specification (for spec_id)
    PostgreSQLDB-->>-FastAPIBackend: Return API Specification content
    
    Note over FastAPIBackend, SchemathesisLib: This step is similar to Use Case 3 but in context of overall contract validation.
    FastAPIBackend->>+SchemathesisLib: Run Schemathesis: validate Provider's Live Service against Spec [Task 5.2.3, 2.2.1]
    SchemathesisLib->>+ProviderService: HTTP Requests (based on spec)
    ProviderService-->>-SchemathesisLib: HTTP Responses
    SchemathesisLib-->>-FastAPIBackend: Schemathesis validation results
    
    FastAPIBackend->>FastAPIBackend: Determine overall contract validation outcome (based on Schemathesis) [Task 5.2.4]
    FastAPIBackend->>+N8N: POST N8N_WEBHOOK_CONTRACT_VALIDATION_DONE (API name, version, status) [Task 5.2 n8n Integration]
    N8N-->>-FastAPIBackend: Webhook received
    activate N8N
    N8N->>N8N: Workflow 5.1: Format "Contract Validation Results Notification" [Task 5.3]
    N8N->>Producer: Send Email Notification (summary of validation outcome) [Task 5.3]
    deactivate N8N
    
    FastAPIBackend-->>-ReactFrontend: Return contract validation outcome
    ReactFrontend-->>-Producer: Display overall "contract health" status [Task 5.4]
```
