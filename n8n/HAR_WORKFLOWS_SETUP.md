# HAR Processing Workflows Setup Guide

This guide provides step-by-step instructions for setting up the HAR processing notification workflows in n8n.

## Overview

Task 29 implements two dedicated n8n workflows for HAR processing notifications:

1. **Workflow 4.1**: "HAR Processed & Sketches Ready" - Notifies users when HAR processing completes
2. **Workflow 4.2**: "Review Request for AI-Generated Artifacts" - Notifies reviewers when AI-generated artifacts need approval

## Workflow Files

- `workflows/har-processed-notification.json` - Workflow 4.1
- `workflows/har-review-request.json` - Workflow 4.2
- `scripts/test_har_workflows.py` - Test script for both workflows

## Features Implemented

### Workflow 4.1: HAR Processed & Sketches Ready

**Webhook Path**: `/har-processed`

**Key Features**:

- ✅ Conditional formatting based on processing success/failure
- ✅ Detailed processing statistics in emails
- ✅ Artifact links and download URLs
- ✅ Success rate calculations and progress indicators
- ✅ Platform UI links for viewing artifacts
- ✅ Comprehensive error information for failed processing
- ✅ Processing options context (AI processing, data generalization)

**Email Templates**:

- **Success Email**: Includes processing statistics, artifact summary, download links, and platform navigation
- **Failure Email**: Includes error details, partial statistics, troubleshooting tips, and retry options

### Workflow 4.2: Review Request for AI-Generated Artifacts

**Webhook Path**: `/har-review-request`

**Key Features**:

- ✅ Dual email notifications (reviewers + user confirmation)
- ✅ Comprehensive review checklist and guidelines
- ✅ Direct links to review interface and artifact downloads
- ✅ Processing context and AI configuration details
- ✅ Review SLA and timeline information
- ✅ Artifact count and availability status

**Email Templates**:

- **Review Request Email**: Sent to reviewers with detailed artifact information and review checklist
- **User Confirmation Email**: Sent to users confirming their review request has been submitted

## Setup Instructions

### 1. Import Workflows into n8n

1. Start your n8n instance:

   ```bash
   docker-compose up n8n
   ```

2. Access n8n interface at `http://localhost:5679`

3. Import Workflow 4.1:
   - Go to "Workflows" in the n8n interface
   - Click "Import from File"
   - Select `n8n/workflows/har-processed-notification.json`
   - Save and activate the workflow

4. Import Workflow 4.2:
   - Click "Import from File" again
   - Select `n8n/workflows/har-review-request.json`
   - Save and activate the workflow

### 2. Configure Email Settings

Both workflows require SMTP configuration:

1. Go to "Settings" > "Credentials" in n8n
2. Add new credential of type "SMTP"
3. Configure your SMTP server details:
   - **Host**: Your SMTP server (e.g., `smtp.gmail.com`)
   - **Port**: SMTP port (e.g., `587` for TLS)
   - **Username**: Your email username
   - **Password**: Your email password or app password
   - **Security**: Choose appropriate security (TLS/SSL)

4. Update the email nodes in both workflows to use your SMTP credential

### 3. Configure Email Recipients

Update email recipients in the workflows:

**Workflow 4.1** (HAR Processed):

- Edit "Send Success Notification" and "Send Failure Notification" nodes
- Update the `toEmail` parameter to your desired recipient(s)

**Workflow 4.2** (Review Request):

- Edit "Send Review Request Email" node for reviewer notifications
- Edit "Send User Confirmation" node for user confirmations
- Update `toEmail` parameters as needed

### 4. Activate Workflows

1. In n8n, open each imported workflow
2. Click the "Active" toggle to enable the workflows
3. The webhook endpoints will now be available

## Webhook Endpoints

Once activated, the workflows will be available at:

- **Workflow 4.1**: `http://localhost:5679/webhook-test/har-processed`
- **Workflow 4.2**: `http://localhost:5679/webhook-test/har-review-request`

## Testing the Workflows

### Automated Testing

Run the comprehensive test script:

```bash
# From project root
cd backend && uv run python ../scripts/test_har_workflows.py
```

The test script will:

- Test both success and failure scenarios for Workflow 4.1
- Test review request functionality for Workflow 4.2
- Provide detailed output and results summary

### Manual Testing

Test individual workflows with curl:

**Test Workflow 4.1 (Success)**:

```bash
curl -X POST http://localhost:5679/webhook-test/har-processed \
  -H "Content-Type: application/json" \
  -d '{
    "upload_id": 123,
    "file_name": "test.har",
    "user_id": 456,
    "timestamp": "2024-01-01T00:00:00Z",
    "processing_status": "completed",
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
      "openapi_title": "Test API",
      "openapi_version": "1.0.0",
      "openapi_paths_count": 8,
      "wiremock_available": true,
      "wiremock_stubs_count": 23,
      "artifacts_generated_at": "2024-01-01T00:00:00Z"
    }
  }'
```

**Test Workflow 4.2 (Review Request)**:

```bash
curl -X POST http://localhost:5679/webhook-test/har-review-request \
  -H "Content-Type: application/json" \
  -d '{
    "upload_id": 124,
    "file_name": "complex.har",
    "user_id": 789,
    "timestamp": "2024-01-01T00:00:00Z",
    "artifacts_summary": {
      "openapi_available": true,
      "openapi_title": "Complex API",
      "openapi_version": "2.1.0",
      "openapi_paths_count": 15,
      "wiremock_available": true,
      "wiremock_stubs_count": 42,
      "artifacts_generated_at": "2024-01-01T00:00:00Z"
    },
    "review_url": "http://localhost:5173/har-uploads/124/review",
    "processing_statistics": {
      "interactions_count": 50,
      "processed_interactions_count": 48,
      "processing_options": {
        "enable_ai_processing": true,
        "enable_data_generalization": true
      }
    }
  }'
```

## Integration with Backend

The workflows are designed to work with the backend notification service implemented in Task 28. The backend should send webhook requests to these endpoints when:

1. HAR processing completes (success or failure) → Workflow 4.1
2. Review is requested for AI-generated artifacts → Workflow 4.2

## Email Template Features

### Processing Statistics

Both workflows include comprehensive processing statistics:

- HTTP interactions found and processed
- Success rates and progress indicators
- OpenAPI paths and WireMock stubs generated
- Processing steps completed
- AI processing options applied

### Conditional Formatting

- Success emails use positive language and green checkmarks
- Failure emails use warning language and red X marks
- Artifact availability is clearly indicated
- Processing options are highlighted

### Platform Integration

- Direct links to HAR upload details
- Artifact download links
- Review interface links
- Platform documentation links
- Retry and support options for failures

## Troubleshooting

### Workflow Not Triggering

1. Check that the workflow is active in n8n
2. Verify the webhook URL in backend configuration
3. Check n8n logs: `docker-compose logs n8n`
4. Ensure the backend can reach n8n (network connectivity)

### Email Not Sending

1. Verify SMTP credentials are correctly configured
2. Check email node configuration in the workflow
3. Test SMTP settings with a simple email workflow
4. Check n8n logs for email sending errors

### Test Script Failures

1. Ensure n8n is running and accessible
2. Verify workflows are imported and active
3. Check webhook URLs are correct
4. Confirm network connectivity to n8n

## Maintenance

### Updating Email Recipients

1. Open the workflow in n8n
2. Edit the email nodes
3. Update the `toEmail` parameter
4. Save the workflow

### Modifying Email Templates

1. Open the workflow in n8n
2. Edit the email nodes
3. Modify the `subject` and `text` fields
4. Use n8n expressions for dynamic data
5. Save the workflow

### Adding New Notification Types

1. Add new switch case in the routing node
2. Create new email node for the notification type
3. Connect the routing to the new email node
4. Update the webhook response node connections

## Compliance with Task Requirements

✅ **Workflow 4.1 Created**: "HAR Processed & Sketches Ready" workflow implemented
✅ **Workflow 4.2 Created**: "Review Request for AI-Generated Artifacts" workflow implemented
✅ **Processing Statistics**: Included in all email notifications
✅ **Artifact Links**: Direct links to platform UI for viewing artifacts
✅ **Conditional Formatting**: Success/failure formatting implemented
✅ **Platform UI Links**: Links to HAR uploads, artifacts, and review interfaces
✅ **Test Strategy**: Comprehensive test script created and executed
✅ **Email Formatting**: Rich formatting with emojis and structured information
✅ **Different Processing Results**: Success and failure scenarios handled

The HAR processing notification workflows are now fully implemented and ready for use!
