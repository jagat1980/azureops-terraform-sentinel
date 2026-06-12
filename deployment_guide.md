# AzureOps SecOps Swarm Triage: Deployment & Testing Guide

This document provides complete instructions for deploying the Python-based SecOps Swarm Triage Azure Function App and executing manual and automated test suites.

---

## 📐 End-to-End GitOps Architecture Blueprint

The following diagram illustrates the lifecycle of a cloud security event, from ingestion of polymorphic alerts to dynamic Landing Zone targeting, ending in the Human-in-the-Loop approval gate:

```mermaid
graph TD
    %% Telemetry Sources
    subgraph Detection [1. DETECTION & INGEST]
        DF[Defender for Cloud] --> |Security Alert| EG[Azure Event Grid]
        LA[Log Analytics] --> |Diagnostic Log Drift| EG
        MA[Azure Monitor Metrics] --> |CPU/Threshold Breached| EG
        AL[Activity Log Alerts] --> |Storage Config Altered| EG
        SH[Service Health] --> |Maintenance Event| EG
    end

    %% Webhook Endpoint & AI processing
    subgraph Swarm [2. HYBRID SWARM ORCHESTRATOR]
        EG --> |Secure Webhook AuthLevel.FUNCTION| FN[Azure Function Webhook]
        FN --> |Get Repo Tree| GH_API[GitHub Tree API]
        GH_API --> |FileList| FN
        FN --> |Tier 1: Deterministic Parsing| DET[Pure Python Parser]
        DET -.-> |Fallback| OpenAI1[Azure OpenAI Cognitive Triage]
        DET --> |incident_id, target_file_path| FN
        OpenAI1 --> |incident_id, target_file_path| FN
        FN --> |Fetch File Content| GH_Content[GitHub File Retrieval]
        GH_Content --> |Raw HCL Code| FN
        FN --> |Load Remediation Policy| POL[remediation_policies.json]
        POL --> |Rules| OpenAI2[Azure OpenAI Patch Engineer]
        FN --> |Patch Vulnerability & Validate| OpenAI2
        OpenAI2 --> |Remediated HCL Code| FN
        FN --> |Syntax Validation Check| VAL{HCL Syntax OK?}
        VAL -->|No: Self-Correction| OpenAI2
    end

    %% Git Control Plane (PR human-in-the-loop gate)
    subgraph GitOps [3. GIT CONTROL PLANE & HUMAN GATE]
        VAL --> |Yes| BRANCH[Create Temp Git Branch]
        BRANCH --> |Commit Code Fix| COMMIT[Commit Remediation]
        COMMIT --> |Draft PR Description| OpenAI3[Azure OpenAI PR Copywriter]
        OpenAI3 --> |Structured Markdown Analysis| PR[Open Pull Request]
        PR --> |Blocker| GATE[SRE Human-in-the-Loop Review Gate]
    end

    %% CD Deployment Pipeline
    subgraph Deploy [4. TRANSACTIONAL CI/CD]
        GATE --> |Approve & Merge| MERGE[Merge PR to main]
        MERGE --> |Trigger Pipeline| GHA[GitHub Actions / ADO Pipelines]
        GHA --> |Execution Plan| PLAN[terraform plan]
        PLAN --> |Idempotent Apply| APPLY[terraform apply]
        APPLY --> |State Remedied| LIVE[Live Azure Environment]
    end

    classDef source fill:#f9f,stroke:#333,stroke-width:2px;
    classDef ai fill:#bbf,stroke:#333,stroke-width:2px;
    classDef git fill:#bfb,stroke:#333,stroke-width:2px;
    classDef deploy fill:#fbb,stroke:#333,stroke-width:2px;
    class DF,LA,MA,AL,SH source;
    class FN,OpenAI1,OpenAI2,OpenAI3,VAL ai;
    class GATE,PR,BRANCH,COMMIT git;
    class GHA,PLAN,APPLY,LIVE deploy;
```

---

## ⏱️ Realistic MTTR Breakdown

By employing this automated GitOps model with a **Human-in-the-Loop (HITL)** gate, organizations dramatically lower their Mean Time to Remediate (MTTR) while preserving strict compliance boundaries:

1. **Detection & Event Ingress (1 – 3 minutes)**: Telemetry systems scan the cloud environment, identify the drift, and publish the alert to Azure Event Grid.
2. **Hybrid Swarm Orchestration (10 – 15 seconds)**: The Azure Function ingests the alert using a tiered approach. Known alert schemas are parsed deterministically (0ms, 0 tokens), while unrecognized schemas fall back to LLM cognitive routing. The function then fetches the file, injects config-driven remediation rules, generates the patch, validates the HCL syntax, and opens a PR.
3. **SRE Peer Review & Approval (2 – 5 minutes)**: An engineer reviews the OpenAI-generated PR risk analysis, verifies the terraform diff, and clicks "Merge".
4. **CI/CD Execution & Deployment (1 – 2 minutes)**: The GitHub Actions runner executes `terraform apply`, remediating the cloud infrastructure to align with Git source.
5. **Total Remediation MTTR (~5 – 10 minutes)**: Historically, manual remediation cycles take between **24 to 72 hours**. This solution reduces that window to minutes.

---

## 🛠️ Step 1: Local Development & Verification

Before publishing to Azure, verify your function locally using the Core Tools.

### 1. Prerequisites
- **Azure Functions Core Tools v4.x** installed.
- **Python 3.10** or **3.11** installed.
- Access to the target GitHub repository (`jagat1980/azureops-terraform-sentinel`).
- Azure OpenAI service credentials.

### 2. Configure Environment Variables
Create or verify the `azureops-brain/local.settings.json` file:
```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "GITHUB_TOKEN": "<your-github-pat-token>",
    "GITHUB_REPO": "jagat1980/azureops-terraform-sentinel",
    "AZURE_OPENAI_ENDPOINT": "https://<your-openai-endpoint>.openai.azure.com/",
    "AZURE_OPENAI_KEY": "<your-openai-key>",
    "OPENAI_DEPLOYMENT_NAME": "gpt-5.4"
  }
}
```

### 3. Run Locally
Navigate to the function app directory and start the local runtime host:
```powershell
cd c:\myailearn\projects\azureops-test-harness\azureops-brain
func start
```

---

## 🚀 Step 2: Deploy to Azure

To move from local testing to your Azure cloud tenant, follow these deployment steps:

### 1. Create the Azure Function App (CLI)
Run the following Azure CLI commands to spin up the required resources:

```bash
# 1. Create a Resource Group
az group create --name rg-azureops-secops --location eastus

# 2. Create an Azure Storage Account (required by Function Apps)
az storage account create \
  --name stazureopsfunc \
  --location eastus \
  --resource-group rg-azureops-secops \
  --sku Standard_LRS

# 3. Create the Function App on Linux running Python 3.11 with secure system settings
az functionapp create \
  --name func-secops-swarm-triage \
  --storage-account stazureopsfunc \
  --resource-group rg-azureops-secops \
  --consumption-plan-location eastus \
  --functions-version 4 \
  --os-type Linux \
  --runtime python \
  --runtime-version 3.11
```

### 2. Configure Azure App Settings
Apply your environment variables directly to the Azure Function App configuration. This is the cloud equivalent to `local.settings.json`:

```bash
az functionapp config appsettings set --name func-secops-swarm-triage --resource-group rg-azureops-secops --settings \
  GITHUB_TOKEN="<your-github-pat-token>" \
  GITHUB_REPO="jagat1980/azureops-terraform-sentinel" \
  AZURE_OPENAI_ENDPOINT="https://<your-openai-endpoint>.openai.azure.com/" \
  AZURE_OPENAI_KEY="<your-openai-key>" \
  OPENAI_DEPLOYMENT_NAME="gpt-5.4"
```

### 3. Publish Code to Azure
Log into Azure via `az login`, navigate to the `azureops-brain/` directory, and run the publisher tool:

```powershell
cd c:\myailearn\projects\azureops-test-harness\azureops-brain
func azure functionapp publish func-secops-swarm-triage
```

---

## ⚡ Step 3: Event Grid webhook Integration

If triggering the remediation workflow from Azure Event Grid:

1. Go to **Azure Event Grid Partner Topics** / **System Topics**.
2. Create an **Event Subscription**.
3. Choose the **Webhook** Endpoint Type.
4. Set the Endpoint URL to:
   ```
   https://func-secops-swarm-triage.azurewebsites.net/api/swarm-triage?code=<FUNCTION_KEY>
   ```
   *Note: Under AuthLevel.FUNCTION, the `code` query parameter contains the authorization host key generated by Azure Functions.*
5. Click **Create**. Event Grid will trigger a handshake check. The function contains native logic on lines 47–51 of [function_app.py](file:///c:/myailearn/projects/azureops-test-harness/azureops-brain/function_app.py#L47-L51) to validate and respond to this verification request.

---

## 🧪 Step 4: Core Validation Test Cases

Ensure the HTTP endpoint responds to Event Grid handshake verification requests.

* **Target URL**: `http://localhost:7071/api/swarm-triage` (Local)
* **HTTP Method**: `POST`
* **Request Payload**:
```json
[
  {
    "id": "2d17db39-8067-45f5-b66a-38292261277f",
    "topic": "/subscriptions/test-sub/resourceGroups/rg-test",
    "subject": "",
    "data": {
      "validationCode": "512d38b6-c7b8-40c8-87da-a419f403aa23",
      "validationUrl": "https://rp-eastus.eventgrid.azure.net:553/eventsubscriptions/sub/validate?id=512d38b6"
    },
    "eventType": "Microsoft.EventGrid.SubscriptionValidationEvent",
    "eventTime": "2026-06-10T15:00:00.0000000Z",
    "metadataVersion": "1",
    "dataVersion": "2"
  }
]
```

* **Expected Response Status**: `200 OK`
* **Expected Response Body**:
```json
{
  "validationResponse": "512d38b6-c7b8-40c8-87da-a419f403aa23"
}
```

---

## 🔮 Step 5: Landing Zone Polymorphic Alert Testing

We have built a test runner script [test_all_payloads.py](file:///c:/myailearn/projects/azureops-test-harness/test_all_payloads.py) that you can run locally to verify how the Cognitive Triage handles multiple distinct Azure alert formats across storage, compute, database, and network resources.

### Executing the Multi-Payload Test Runner
Activate your virtual environment and run the test suite:
```powershell
python c:\myailearn\projects\azureops-test-harness\test_all_payloads.py
```

This script will run eight tests:
1. **Azure Monitor Activity Log Alert (Storage)**
2. **Azure Monitor Metric Alert (Storage)**
3. **Service Health Alert (Storage)**
4. **Log Analytics/Diagnostic Logging Alert (Storage)**
5. **CPU Threshold Alert (Compute/VM)** - Targets `modules/compute/main.tf`
6. **Microsoft Defender for Cloud Security Alert (Storage)**
7. **Network Security Group Public Port Rule Alert (Network)** - Targets `modules/network/main.tf`
8. **SQL Server Firewall Open Alert (Database)** - Targets `modules/database/main.tf`

---

## 💰 End-to-End Cost & Total Cost of Ownership (TCO) Analysis

This section outlines the financial details of deploying and operating the **AzureOps SecOps Swarm Triage** solution in an enterprise environment. It breaks down the costs into **One-Time Setup Costs** and **Recurring Monthly Operational Costs**.

### 1. One-Time Setup Costs

| Setup Component | Description | Cost |
| :--- | :--- | :--- |
| **Azure Resource Group** | Creating isolated logical containers for SecOps. | **$0.00** |
| **GitHub / DevOps Repos** | Hosting source control repository (leveraging existing subscription). | **$0.00** |
| **Telemetry Ingress Rules** | Configuring Azure Policy, Defender alerts, and Monitor metric scopes. | **$0.00** |
| **Initial Deployment** | Publishing Python functions and initial HCL Landing Zone setup. | **$0.00** |
| **Total One-Time Cost** | **Zero Setup Expenses** (runs entirely on native platform APIs). | **$0.00** |

### 2. Recurring Monthly Operational Costs (Assuming 1,000 alert events / month)

Operating under a serverless, pay-as-you-go architecture, the system remains dormant and costs nothing unless actively processing an alert.

| Service Component | Pricing Tier | Monthly Consumption | Monthly Cost |
| :--- | :--- | :--- | :--- |
| **Azure Event Grid** | Basic (First 100k events free; then $0.60/M) | ~1,000 alert routings | **$0.00** |
| **Azure Functions (Serverless)** | Premium/Consumption (1M free executions, then $0.20/M; 400k GB-sec free) | ~1,000 executions (avg. 30s at 1.5GB) | **~$0.80** |
| **Azure Storage (Metadata & Logs)** | Hot LRS ($0.02 / GB + transaction costs) | ~2 GB active storage & operational logs | **~$0.50** |
| **Azure OpenAI Service** | GPT-4o Pay-as-you-go ($5.00/1M input, $15.00/1M output tokens) | ~1,000 hybrid events (patch & PR only) | **~$22.00** |
| **GitHub Actions / CI/CD** | Team / Enterprise (includes free minutes) | ~50 PR plan & apply builds | **$0.00** (Included) |
| **Total Recurring Cost** | **Estimated Enterprise Cloud Overhead** | **~1,000 auto-remediations / month** | **~$23.30 / month** |

> [!TIP]
> **Average Cost per Remediation**: ~$0.04 (predominantly OpenAI token fees). 
> **Compared to Manual Remediation**: Standard enterprise operations spend an average of **$150 to $300 in engineering labor** per incident ticket. SecOps Swarm achieves a **99.98% cost reduction** per event.

