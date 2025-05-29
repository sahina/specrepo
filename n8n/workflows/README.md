# n8n Workflows

This directory contains n8n workflow configurations for the SpecRepo platform.

## Unified Notification System

The SpecRepo platform uses a **single unified notification workflow** (`unified-notification.json`) that handles all types of notifications through intelligent routing based on the `event_type` field.

### Unified Notification Workflow (`unified-notification.json`)

**Purpose**: Handles all notifications from the SpecRepo platform using a single webhook endpoint with intelligent routing.

**Webhook Path**: `/notification`

**Supported Event Types**:

- `created` - When a new API specification is created
- `updated` - When an existing API specification is updated  
- `validation_completed` - When a validation run completes successfully
- `validation_failed` - When a validation run fails or is cancelled
- `har_processing_completed` - When HAR file processing completes successfully
- `har_processing_failed` - When HAR file processing fails
- `har_review_requested` - When review is requested for AI-generated HAR artifacts

### Payload Structures

#### API Specification Events (`created`, `updated`)

```json
{
  "event_type": "created|updated",
  "specification_id": 123,
  "specification_name": "My API",
  "version_string": "v1.0",
  "user_id": 456,
  "timestamp": "2023-01-01T00:00:00",
  "openapi_content": {
    "openapi": "3.0.0",
    "info": { "title": "My API" }
  }
}
```

#### Validation Events (`validation_completed`, `validation_failed`)

```json
{
  "event_type": "validation_completed|validation_failed",
  "validation_run_id": 789,
  "specification_id": 123,
  "specification_name": "My API",
  "provider_url": "https://api.example.com",
  "user_id": 456,
  "status": "completed|failed|cancelled",
  "timestamp": "2023-01-01T00:00:00",
  "validation_results": {
    "total_tests": 10,
    "passed_tests": 8,
    "failed_tests": 2
  },
  "validation_statistics": {
    "success_rate": 80.0,
    "execution_time": 30.5,
    "error_count": 0,
    "total_tests": 10,
    "passed_tests": 8,
    "failed_tests": 2
  }
}
```

#### HAR Processing Events (`har_processing_completed`, `har_processing_failed`)

```json
{
  "event_type": "har_processing_completed|har_processing_failed",
  "upload_id": 123,
  "file_name": "example.har",
  "user_id": 456,
  "timestamp": "2023-01-01T00:00:00",
  "processing_status": "completed|failed",
  "processing_statistics": {
    "interactions_count": 25,
    "processed_interactions_count": 23,
    "openapi_paths_count": 8,
    "wiremock_stubs_count": 23,
    "processing_steps_completed": 5,
    "total_processing_steps": 5,
    "processing_progress": 100,
    "processing_options": {
      "enable_ai_processing": true,
      "enable_data_generalization": true
    }
  },
  "artifacts_summary": {
    "openapi_available": true,
    "openapi_title": "Generated API",
    "openapi_version": "1.0.0",
    "openapi_paths_count": 8,
    "wiremock_available": true,
    "wiremock_stubs_count": 23,
    "artifacts_generated_at": "2023-01-01T00:00:00"
  },
  "error_message": "Error details (only for failed events)"
}
```

#### HAR Review Request Events (`har_review_requested`)

```json
{
  "event_type": "har_review_requested",
  "upload_id": 123,
  "file_name": "example.har",
  "user_id": 456,
  "timestamp": "2023-01-01T00:00:00",
  "artifacts_summary": {
    "openapi_available": true,
    "openapi_title": "Generated API",
    "openapi_version": "1.0.0",
    "openapi_paths_count": 8,
    "wiremock_available": true,
    "wiremock_stubs_count": 23,
    "artifacts_generated_at": "2023-01-01T00:00:00"
  },
  "review_url": "http://localhost:5173/har-uploads/123/review",
  "processing_statistics": {
    "interactions_count": 25,
    "processed_interactions_count": 23,
    "processing_options": {
      "enable_ai_processing": true,
      "enable_data_generalization": true
    }
  }
}
```

### Workflow Architecture

The workflow uses a **switch node** to route incoming webhooks based on the `event_type` field:

1. **Webhook Trigger** - Receives POST requests at `/notification`
2. **Route by Event Type** - Switch node that routes to appropriate email handler
3. **Email Nodes** - Send formatted emails for each event type:
   - `Send Spec Created Email` - For API specification creation
   - `Send Spec Updated Email` - For API specification updates
   - `Send Validation Completed Email` - For successful validations
   - `Send Validation Failed Email` - For failed validations
   - `Send HAR Completed Email` - For successful HAR processing
   - `Send HAR Failed Email` - For failed HAR processing
   - `Send HAR Review Email` - For HAR artifact review requests
4. **Webhook Response** - Returns success response to caller

### Email Templates

Each event type has a customized email template that includes:

- **HAR Processing Completed**: Processing statistics, artifact summary, download links
- **HAR Processing Failed**: Error details, partial statistics, retry options
- **HAR Review Requested**: Artifact details, review links, processing context

### Configuration

The workflow is configured to:

- Accept webhooks at `http://n8n:5678/webhook-test/notification`
- Send emails to `altug@aecoffice.com` (configurable)
- Include rich formatting with emojis and structured information
- Provide direct links to relevant platform pages

### Setup Instructions

1. Import the workflow JSON file into your n8n instance
2. Configure SMTP settings for email sending
3. Update email recipients as needed
4. Activate the workflow
5. Test with the provided webhook endpoints

### Testing

Use the test scripts in the `scripts/` directory:

- `test_n8n_webhook.py` - Manual webhook testing
- `setup_n8n_workflow.py` - Automated workflow setup and testing

The workflow automatically handles all notification types and provides comprehensive information for each event.

## Configuration

### Environment Variables

The following environment variables control n8n webhook behavior:

- `N8N_WEBHOOK_URL` - Base URL for n8n webhooks (should point to `/notification` endpoint)
- `N8N_WEBHOOK_SECRET` - Optional secret for webhook authentication
- `N8N_MAX_RETRIES` - Maximum retry attempts (default: 3)
- `N8N_RETRY_DELAY_SECONDS` - Delay between retries (default: 5)
- `N8N_TIMEOUT_SECONDS` - Request timeout (default: 30)

### Email Configuration

The workflow is configured to send emails to `altug@aecoffice.com`. Update the `toEmail` parameter in each email node to change the recipient.

## Importing the Workflow

1. Open your n8n instance
2. Go to Workflows
3. Click "Import from File"
4. Select `unified-notification.json`
5. Save and activate the workflow

## Testing

The unified workflow can be tested by:

1. **API Specification Notifications**: Create or update an API specification through the SpecRepo API
2. **Validation Notifications**: Trigger a validation run through the validation endpoints

All notifications will automatically be routed to the appropriate email template based on the `event_type`.

## Webhook URL

When the unified workflow is active, it will be available at:

**Unified Endpoint**: `{N8N_BASE_URL}/webhook/notification`

Make sure to set the `N8N_WEBHOOK_URL` environment variable to point to this unified endpoint.

## Migration from Separate Workflows

If you were previously using separate workflows (`api-spec-notification.json` and `validation-notification.json`), you can:

1. Import the new `unified-notification.json` workflow
2. Update your `N8N_WEBHOOK_URL` to point to `/notification`
3. Deactivate and delete the old separate workflows
4. Test that all notification types work correctly

The unified workflow maintains the same email templates and functionality as the separate workflows.
