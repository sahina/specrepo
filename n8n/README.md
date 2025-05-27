# n8n Workflow Configuration

This directory contains n8n workflow configurations for the SpecRepo platform. These workflows handle automated notifications and integrations triggered by backend events.

## Workflows

### 1. API Specification Notification Workflow (`api-spec-notification.json`)

**Purpose**: Sends email notifications when API specifications are created or updated.

**Trigger**: Webhook endpoint at `/webhook/api-spec-notification`

**Expected Payload**:

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
    "info": {
      "title": "My API",
      "description": "API description",
      "version": "1.0.0"
    },
    "paths": {}
  }
}
```

**Actions**:

- Receives webhook data from the backend
- Checks event type (created vs updated)
- Formats appropriate email notification
- Sends email to configured recipients
- Returns success response to backend

**Email Recipients**: Currently configured to send to `altug@aecoffice.com`. Update the workflow configuration to change recipients.

## Setup Instructions

### 1. Import Workflow into n8n

1. Start the n8n service:

   ```bash
   docker-compose up n8n
   ```

2. Access n8n interface at `http://localhost:5679`

3. Import the workflow:
   - Go to "Workflows" in the n8n interface
   - Click "Import from File"
   - Select `workflows/api-spec-notification.json`
   - Save the workflow

### 2. Configure Email Settings

The workflow uses n8n's built-in email sending capability. You need to configure SMTP settings in n8n:

1. Go to "Settings" > "Credentials" in n8n
2. Add new credential of type "SMTP"
3. Configure your SMTP server details:
   - **Host**: Your SMTP server (e.g., `smtp.gmail.com`)
   - **Port**: SMTP port (e.g., `587` for TLS)
   - **Username**: Your email username
   - **Password**: Your email password or app password
   - **Security**: Choose appropriate security (TLS/SSL)

4. Update the email nodes in the workflow to use your SMTP credential

### 3. Configure Backend Environment Variables

Set the following environment variables in your backend configuration:

```bash
# Required: The n8n webhook URL
N8N_WEBHOOK_URL=http://n8n:5678/webhook/api-spec-notification

# Optional: Webhook secret for security
N8N_WEBHOOK_SECRET=your-secret-key

# Optional: Retry configuration
N8N_MAX_RETRIES=3
N8N_RETRY_DELAY_SECONDS=5
N8N_TIMEOUT_SECONDS=30
```

For Docker Compose, add these to the backend service environment:

```yaml
services:
  backend:
    environment:
      - N8N_WEBHOOK_URL=http://n8n:5678/webhook/api-spec-notification
      - N8N_WEBHOOK_SECRET=your-secret-key
```

### 4. Activate the Workflow

1. In n8n, open the imported workflow
2. Click the "Active" toggle to enable the workflow
3. The webhook endpoint will now be available

## Testing the Workflow

### 1. Test with Sample Data

You can test the workflow by sending a POST request to the webhook endpoint:

```bash
curl -X POST http://localhost:5679/webhook/api-spec-notification \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "created",
    "specification_id": 123,
    "specification_name": "Test API",
    "version_string": "v1.0",
    "user_id": 456,
    "timestamp": "2024-01-01T00:00:00Z",
    "openapi_content": {
      "openapi": "3.0.0",
      "info": {
        "title": "Test API",
        "description": "A test API specification",
        "version": "1.0.0"
      },
      "paths": {}
    }
  }'
```

### 2. Test via Backend API

Create or update an API specification through the backend API to trigger the workflow automatically:

```bash
# Create a new specification (triggers "created" event)
curl -X POST http://localhost:8000/api/specifications \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "Test API",
    "version_string": "v1.0",
    "openapi_content": {
      "openapi": "3.0.0",
      "info": {"title": "Test API"},
      "paths": {}
    }
  }'
```

## Customization

### Email Templates

To customize email content:

1. Open the workflow in n8n
2. Edit the "Send Created Email" or "Send Updated Email" nodes
3. Modify the subject and text fields
4. Use n8n expressions to include dynamic data from the webhook payload

### Recipients

To change email recipients:

1. Edit the email nodes in the workflow
2. Update the `toEmail` parameter
3. For multiple recipients, use comma-separated emails: `admin@example.com,team@example.com`

### Additional Actions

You can extend the workflow to:

- Send notifications to Slack/Teams
- Create tickets in project management tools
- Update external documentation systems
- Trigger additional automation workflows

## Troubleshooting

### Workflow Not Triggering

1. Check that the workflow is active in n8n
2. Verify the webhook URL in backend environment variables
3. Check n8n logs for errors: `docker-compose logs n8n`
4. Ensure the backend can reach the n8n service (network connectivity)

### Email Not Sending

1. Verify SMTP credentials are correctly configured
2. Check email node configuration in the workflow
3. Test SMTP settings with a simple email workflow
4. Check for firewall/security restrictions on SMTP ports

### Backend Connection Issues

1. Verify n8n service is running: `docker-compose ps n8n`
2. Check network connectivity between backend and n8n services
3. Review backend logs for webhook errors
4. Ensure correct webhook URL format (include protocol: `http://`)

## Security Considerations

1. **Webhook Secret**: Always use `N8N_WEBHOOK_SECRET` in production to validate webhook authenticity
2. **SMTP Credentials**: Store SMTP credentials securely in n8n's credential system
3. **Network Access**: Restrict n8n access to internal networks only
4. **Email Content**: Be careful not to include sensitive data in email notifications

## Monitoring

Monitor workflow execution through:

- n8n's execution history (Executions tab)
- Backend logs for webhook sending attempts
- Email delivery confirmations
- n8n system logs for errors

For production deployments, consider setting up:

- Workflow execution alerts
- Email delivery monitoring
- Performance metrics tracking
