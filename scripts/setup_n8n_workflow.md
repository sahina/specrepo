# n8n Workflow Setup Guide for Task 8

This guide will help you set up the n8n workflow for API specification notifications (Task 8).

## Prerequisites

1. **Docker Compose Stack Running**: Make sure the entire stack is running:

   ```bash
   docker-compose up -d
   ```

2. **Verify Services**: Check that all services are running:

   ```bash
   docker-compose ps
   ```

## Step 1: Access n8n Interface

1. Open your browser and go to: <http://localhost:5679>
2. If this is your first time, you'll need to set up an n8n account:
   - Create a username and password
   - Complete the initial setup

## Step 2: Import the Workflow

1. In the n8n interface, click on **"Workflows"** in the left sidebar
2. Click the **"+ Add workflow"** button or **"Import from file"**
3. Select **"Import from file"**
4. Navigate to and select: `n8n/workflows/api-spec-notification.json`
5. Click **"Import"**

## Step 3: Configure Email Settings (Important!)

The workflow needs SMTP settings to send emails:

1. Go to **"Settings"** → **"Credentials"** in n8n
2. Click **"+ Add credential"**
3. Search for and select **"SMTP"**
4. Configure your SMTP settings:
   - **Name**: `Email SMTP`
   - **Host**: Your SMTP server (e.g., `smtp.gmail.com`)
   - **Port**: `587` (for TLS) or `465` (for SSL)
   - **Security**: `TLS` or `SSL`
   - **Username**: Your email address
   - **Password**: Your email password or app-specific password
5. Click **"Save"**

### Gmail Example

- Host: `smtp.gmail.com`
- Port: `587`
- Security: `TLS`
- Username: `your-email@gmail.com`
- Password: Use an [App Password](https://support.google.com/accounts/answer/185833)

## Step 4: Update Email Nodes in Workflow

1. Open the imported workflow
2. Click on the **"Send Created Email"** node
3. In the **"Credentials"** dropdown, select the SMTP credential you just created
4. Update the **"To Email"** field to your desired recipient email
5. Repeat for the **"Send Updated Email"** node
6. Click **"Save"** in the top right

## Step 5: Activate the Workflow

1. In the workflow editor, click the **"Active"** toggle switch in the top right
2. The workflow should now show as "Active"
3. The webhook endpoint will be available at: `http://localhost:5678/webhook-test/api-spec-notification`

## Step 6: Test the Workflow

### Option 1: Use the Test Script

```bash
python scripts/test_n8n_webhook.py
```

### Option 2: Manual Test with curl

```bash
curl -X POST http://localhost:5678/webhook-test/api-spec-notification \
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

### Option 3: Test via Backend API

Create a new API specification through the backend to trigger the workflow:

```bash
curl -X POST http://localhost:8001/api/specifications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
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

## Step 7: Run Integration Tests

Once the workflow is set up and active, run the integration tests:

```bash
cd backend
python -m pytest tests/test_n8n_integration.py -v
```

## Troubleshooting

### Webhook Not Found (404 Error)

- **Cause**: Workflow is not active or not imported
- **Solution**: Make sure the workflow is imported and the "Active" toggle is ON

### Email Not Sending

- **Cause**: SMTP credentials not configured or incorrect
- **Solution**:
  1. Check SMTP credentials in n8n Settings → Credentials
  2. Test with a simple email workflow first
  3. For Gmail, use an App Password instead of your regular password

### Connection Refused

- **Cause**: n8n service not running
- **Solution**: `docker-compose up n8n`

### Backend Can't Reach n8n

- **Cause**: Incorrect webhook URL in environment variables
- **Solution**: Make sure `N8N_WEBHOOK_URL` uses the service name `n8n` in docker-compose:

  ```
  N8N_WEBHOOK_URL=http://n8n:5678/webhook-test/api-spec-notification
  ```

## Verification Checklist

- [ ] n8n service is running (`docker-compose ps`)
- [ ] n8n interface accessible at <http://localhost:5679>
- [ ] Workflow imported from `n8n/workflows/api-spec-notification.json`
- [ ] SMTP credentials configured
- [ ] Email nodes updated with correct credentials and recipient
- [ ] Workflow is **Active** (toggle switch ON)
- [ ] Test script passes: `python scripts/test_n8n_webhook.py`
- [ ] Integration tests pass: `pytest tests/test_n8n_integration.py`

## Expected Results

When working correctly:

1. **Test Script**: Should show ✅ success messages
2. **Email**: You should receive test emails for created/updated events
3. **Integration Tests**: All tests should pass
4. **Backend Integration**: Creating/updating API specs via the backend API should trigger email notifications

## Configuration Summary

The complete setup requires:

1. **Docker Compose**: n8n service running on port 5678
2. **Environment Variables**: Backend configured with n8n webhook URL
3. **n8n Workflow**: Imported and active
4. **SMTP Credentials**: Configured in n8n for email sending
5. **Email Recipients**: Updated in workflow nodes

Once all steps are complete, Task 8 (n8n workflow for API specification notifications) will be fully functional!
