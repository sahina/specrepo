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

### Workflow Architecture

The unified workflow uses a **Switch node** to route incoming webhooks to the appropriate email template based on the `event_type`:

1. **Webhook Trigger** - Receives all notifications at `/notification`
2. **Route by Event Type** - Switch node that routes based on `event_type`
3. **Email Nodes** - Four specialized email templates:
   - Spec Created Email (for `created` events)
   - Spec Updated Email (for `updated` events)
   - Validation Completed Email (for `validation_completed` events)
   - Validation Failed Email (for `validation_failed` events)
4. **Webhook Response** - Returns success confirmation

### Benefits of Unified Approach

- **Single webhook endpoint** to configure and maintain
- **Consistent routing logic** for all notification types
- **Easy to extend** with new event types
- **Simplified configuration** - only one workflow to import and activate
- **Better maintainability** - changes to common logic affect all notifications

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
