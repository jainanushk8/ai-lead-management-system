# n8n Workflow Automation Setup Guide

## Overview

This directory contains the production-ready n8n workflow JSON (`workflow.json`) orchestrating the end-to-end AI-Powered Lead Management & Automation System.

## Architecture Pipeline

```
[ Inbound Lead Webhook ] -> [ Validation Node ]
                                  |
                   +--------------+--------------+
                   |                             |
             [ Valid? YES ]                [ Valid? NO ]
                   |                             |
      [ Create Lead via FastAPI ]      [ 422 Validation Error ]
                   |
         +---------+---------+
         |                   |
   [ Duplicate? 409 ]   [ New Lead? 201 ]
         |                   |
 [ 409 Abort/Notify ]   [ Ollama AI Classification ]
                             |
                     [ Hermes Agent Tool ]
                             |
                     [ 200 Success Response ]
```

## How to Import & Run in n8n

### Option A: Local Native Execution (Recommended, lightweight)

Run the PowerShell launcher script:

```powershell
powershell -File scripts/start_n8n.ps1
```

Open your browser at `http://localhost:5678`.

### Option B: Docker Execution

```powershell
docker run -it --rm --name n8n -p 5678:5678 -v "${PWD}/n8n/.n8n:/home/node/.n8n" docker.n8n.io/n8nio/n8n
```

### Importing the Workflow

1. In the n8n web interface (`http://localhost:5678`), click **Workflows** -> **Add Workflow** (or **+**).
2. Click the three dots `...` in the top right corner of the canvas.
3. Select **Import from File** and choose `n8n/workflow.json`.
4. Click **Save** and toggle the workflow to **Active**.

## Testing the Webhook

Send a POST request to your n8n webhook URL:

```bash
curl -X POST http://localhost:5678/webhook/lead \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Arjun Mehta",
    "email": "arjun@cloudscale.in",
    "phone": "+91 9988776655",
    "company": "CloudScale Technologies",
    "message": "Looking for custom CRM integration and AI lead triage by Q1."
  }'
```
