# n8n Manual Setup Instructions for Email Delivery Testing

## Current Status ✅

- **Email Configuration**: Correctly set to `altug@aecoffice.com`
- **Workflow File**: Ready for import (`n8n/workflows/api-spec-notification.json`)
- **Services**: n8n and backend are running
- **Templates**: Email templates are properly formatted

## Manual Setup Steps

### 1. Access n8n Interface

1. Open your browser and go to: **<http://localhost:5679>**
2. If this is your first time:
   - Complete the initial setup (create username/password)
   - Skip any optional setup steps

### 2. Import the Workflow

1. In the n8n interface, click **"Workflows"** in the left sidebar
2. Click **"+ Add workflow"** or **"Import from file"**
3. Select **"Import from file"**
4. Navigate to and select: `n8n/workflows/api-spec-notification.json`
5. Click **"Import"**
6. The workflow should now appear in your workflows list

### 3. Configure SMTP Settings (Required for Email Delivery)

1. Go to **"Settings"** → **"Credentials"** in n8n
2. Click **"+ Add credential"**
3. Search for and select **"SMTP"**
4. Configure your SMTP settings:

#### For Gmail (Recommended)

- **Name**: `Email SMTP`
- **Host**: `smtp.gmail.com`
- **Port**: `587`
- **Security**: `TLS`
- **Username**: Your Gmail address
- **Password**: Use an [App Password](https://support.google.com/accounts/answer/185833) (not your regular password)

#### For Other Email Providers

- **Outlook/Hotmail**: `smtp-mail.outlook.com`, Port `587`, TLS
- **Yahoo**: `smtp.mail.yahoo.com`, Port `587`, TLS
- **Custom SMTP**: Use your provider's settings

Click **"Save"**

### 4. Update Email Nodes in Workflow

1. Open the imported workflow by clicking on it
2. Click on the **"Send Created Email"** node
3. In the **"Credentials"** dropdown, select the SMTP credential you just created
4. Verify the **"To Email"** field shows: `altug@aecoffice.com` ✅
5. Repeat for the **"Send Updated Email"** node
6. Click **"Save"** in the top right corner

### 5. Activate the Workflow

1. In the workflow editor, click the **"Active"** toggle switch in the top right
2. The workflow should now show as "Active" with a green indicator
3. The webhook endpoint will be available at: `http://localhost:5678/webhook-test/api-spec-notification`

## Testing Email Delivery

### Option 1: Test via n8n Interface

1. In the workflow editor, click **"Test workflow"** button
2. This will make the webhook temporarily available for testing
3. Run the webhook test script:

   ```bash
   python scripts/test_n8n_webhook.py
   ```

### Option 2: Test via Backend API

1. Create a new API specification through the backend:

   ```bash
   curl -X POST http://localhost:8000/api/specifications \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer your-token" \
     -d '{
       "name": "Test Email API",
       "version_string": "v1.0",
       "openapi_content": {
         "openapi": "3.0.0",
         "info": {"title": "Test Email API"},
         "paths": {}
       }
     }'
   ```

### Option 3: Direct Webhook Test

1. After activating the workflow, test directly:

   ```bash
   curl -X POST http://localhost:5678/webhook-test/api-spec-notification \
     -H "Content-Type: application/json" \
     -d '{
       "event_type": "created",
       "specification_id": 123,
       "specification_name": "Manual Test API",
       "version_string": "v1.0",
       "user_id": 456,
       "timestamp": "2025-05-26T18:30:00Z",
       "openapi_content": {
         "openapi": "3.0.0",
         "info": {
           "title": "Manual Test API",
           "description": "Testing email delivery",
           "version": "1.0.0"
         },
         "paths": {}
       }
     }'
   ```

## Expected Results

When working correctly, you should:

1. **Receive an email** at `altug@aecoffice.com` with:
   - Subject: "🆕 New API Specification Created: [API Name]" or "📝 API Specification Updated: [API Name]"
   - Formatted content with specification details
   - Links to view the specification and API docs

2. **See successful webhook response**:

   ```json
   {
     "status": "success",
     "message": "Notification processed",
     "event_type": "created",
     "specification_id": 123
   }
   ```

3. **View execution history** in n8n:
   - Go to "Executions" tab in n8n
   - See successful workflow runs
   - Check for any error messages

## Troubleshooting

### Workflow Not Triggering

- ✅ Verify workflow is **Active** (green toggle)
- ✅ Check webhook URL format in backend environment
- ✅ Ensure n8n service is running: `docker-compose ps n8n`

### Email Not Sending

- ✅ Verify SMTP credentials are correctly configured
- ✅ For Gmail, ensure you're using an App Password
- ✅ Check email node configuration in workflow
- ✅ Test SMTP settings with a simple email workflow first

### 404 Webhook Error

- ✅ Import the workflow if not already done
- ✅ Activate the workflow (toggle switch)
- ✅ For testing mode, click "Test workflow" button first

## Verification Checklist

- [ ] n8n accessible at <http://localhost:5679>
- [ ] Workflow imported from `n8n/workflows/api-spec-notification.json`
- [ ] SMTP credentials configured and tested
- [ ] Email nodes updated with SMTP credentials
- [ ] Workflow is **Active** (green toggle)
- [ ] Test email received at `altug@aecoffice.com`
- [ ] Webhook responds with success status
- [ ] Backend integration working (creates specs → triggers emails)

## Success Confirmation

Once setup is complete, run the integration tests to verify everything works:

```bash
cd backend
python -m pytest tests/test_n8n_integration.py -v
```

The tests should pass and you should receive test emails at `altug@aecoffice.com`.

---

**Note**: The email configuration is already correctly set to `altug@aecoffice.com` in the workflow file. The main remaining step is to import the workflow into n8n and configure SMTP settings for actual email delivery.
