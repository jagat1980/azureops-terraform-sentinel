# AzureOps SecOps Swarm Triage: Deployment & Testing Guide

This document provides complete instructions for deploying the Python-based SecOps Swarm Triage Azure Function App and executing manual and automated test suites.

---

## 🛠️ Step 1: Local Development & Verification

Before publishing to Azure, verify your function locally using the Core Tools.

### 1. Prerequisites
- **Azure Functions Core Tools v4.x** installed.
- **Python 3.10** or **3.11** installed.
- Access to the target GitHub repository (`jagat1980/azureops-terraform-sentinel`).
- Azure OpenAI service deployment credentials.

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
# 1. Create a Resource Group (if you don't have one)
az group create --name rg-azureops-secops --location eastus

# 2. Create an Azure Storage Account (required by Function Apps)
az storage account create \
  --name stazureopsfunc \
  --location eastus \
  --resource-group rg-azureops-secops \
  --sku Standard_LRS

# 3. Create the Function App on Linux running Python 3.11 (v4 programming model)
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
Make sure you are logged into Azure via `az login`, navigate to the `azureops-brain/` directory, and run the publisher tool:

```powershell
cd c:\myailearn\projects\azureops-test-harness\azureops-brain
func azure functionapp publish func-secops-swarm-triage
```

---

## ⚡ Step 3: Event Grid webhook Integration

If triggering the remediation workflow from Azure Event Grid (e.g., Azure Policy or Sentinel alerts routed via Event Grid):

1. Go to **Azure Event Grid Partner Topics** / **System Topics**.
2. Create an **Event Subscription**.
3. Choose the **Webhook** Endpoint Type.
4. Set the Endpoint URL to:
   ```
   https://func-secops-swarm-triage.azurewebsites.net/api/swarm-triage
   ```
5. Click **Create**. Event Grid will trigger a handshake handshake check. The function contains native logic on lines 25–29 of [function_app.py](file:///c:/myailearn/projects/azureops-test-harness/azureops-brain/function_app.py#L25-L29) to intercept, validate, and respond to this verification request instantly.

---

## 🧪 Step 4: Core Validation Test Cases

### Test Case 1: Event Grid handshake Verification
Ensure the HTTP endpoint properly responds to Event Grid handshake verification requests.

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

## 🔮 Step 5: Advanced Polymorphic Alert Payload Testing

We have built a test runner script [test_all_payloads.py](file:///c:/myailearn/projects/azureops-test-harness/test_all_payloads.py) that you can run locally to verify how the Cognitive Triage handles multiple distinct Azure alert formats.

### Executing the Multi-Payload Test Runner
Activate your virtual environment and run the test suite:
```powershell
python c:\myailearn\projects\azureops-test-harness\test_all_payloads.py
```

Here are the payloads represented in the script:

### Payload 1: Azure Monitor Activity Log Alert (Common Alert Schema)
Sent when an administrative activity (like configuration change or policy failure) occurs.
```json
{
  "schemaId": "azureMonitorCommonAlertSchema",
  "data": {
    "essentials": {
      "alertId": "/subscriptions/test-sub/providers/Microsoft.AlertsManagement/alerts/act-log-001",
      "alertRule": "Storage Account Access Policy Drift Alert",
      "severity": "Sev3",
      "signalType": "Activity Log",
      "monitoringService": "Activity Log",
      "alertTargetIDs": [
        "/subscriptions/test-sub/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/stdriftabc123"
      ],
      "configurationItems": [
        "stdriftabc123"
      ],
      "description": "Storage account configuration changed to permit public blob access."
    }
  }
}
```

### Payload 2: Azure Monitor Metric Alert
Sent when system telemetry rules (e.g. storage transactions, ingress rates) are breached.
```json
{
  "schemaId": "azureMonitorCommonAlertSchema",
  "data": {
    "essentials": {
      "alertId": "/subscriptions/test-sub/providers/Microsoft.AlertsManagement/alerts/metric-alert-002",
      "alertRule": "High Storage Account Transaction Volume",
      "severity": "Sev2",
      "signalType": "Metric",
      "monitoringService": "Platform Metrics",
      "alertTargetIDs": [
        "/subscriptions/test-sub/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/stdriftabc123"
      ],
      "configurationItems": [
        "stdriftabc123"
      ],
      "description": "The transactions count exceeded the threshold."
    }
  }
}
```

### Payload 3: Azure Service Health Alert
Sent when Microsoft notifies about platform service incidents or maintenance.
```json
{
  "schemaId": "azureMonitorCommonAlertSchema",
  "data": {
    "essentials": {
      "alertId": "/subscriptions/test-sub/providers/Microsoft.AlertsManagement/alerts/sh-003",
      "alertRule": "Azure Storage Active Incident",
      "severity": "Sev1",
      "signalType": "Activity Log",
      "monitoringService": "ServiceHealth",
      "alertTargetIDs": [
        "/subscriptions/test-sub/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/stdriftabc123"
      ],
      "configurationItems": [
        "stdriftabc123"
      ],
      "description": "We are experiencing service performance degradation on Azure Storage resources in East US."
    }
  }
}
```

### Payload 4: Log Analytics Based Alert (e.g., Diagnostic Logging Alert)
Sent when log search queries detect anomalies (like suspicious configuration adjustments).
```json
{
  "schemaId": "azureMonitorCommonAlertSchema",
  "data": {
    "essentials": {
      "alertId": "/subscriptions/test-sub/providers/Microsoft.AlertsManagement/alerts/la-log-004",
      "alertRule": "Diagnostic Logging Ingress Drift Detected",
      "severity": "Sev2",
      "signalType": "Log",
      "monitoringService": "Log Analytics",
      "alertTargetIDs": [
        "/subscriptions/test-sub/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/stdriftabc123"
      ],
      "configurationItems": [
        "stdriftabc123"
      ],
      "description": "Diagnostic log searching query found public access logs on stdriftabc123."
    }
  }
}
```

### Payload 5: CPU Threshold Alert (Specific Metric Alert)
Sent when compute resources cross performance metrics.
```json
{
  "schemaId": "azureMonitorCommonAlertSchema",
  "data": {
    "essentials": {
      "alertId": "/subscriptions/test-sub/providers/Microsoft.AlertsManagement/alerts/cpu-alert-005",
      "alertRule": "High CPU Usage Warning",
      "severity": "Sev2",
      "signalType": "Metric",
      "monitoringService": "Platform Metrics",
      "alertTargetIDs": [
        "/subscriptions/test-sub/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Compute/virtualMachines/stdriftabc123"
      ],
      "configurationItems": [
        "stdriftabc123"
      ],
      "description": "CPU percentage usage has exceeded 90% threshold limit."
    }
  }
}
```

### Payload 6: Microsoft Defender for Cloud Security Alert
Sent when high-priority platform security detections identify exposed threat vectors.
```json
{
  "schemaId": "azureMonitorCommonAlertSchema",
  "data": {
    "essentials": {
      "alertId": "/subscriptions/test-sub/providers/Microsoft.AlertsManagement/alerts/def-sec-006",
      "alertRule": "Defender Storage Account Protection Alert",
      "severity": "Sev0",
      "signalType": "Security",
      "monitoringService": "Microsoft Defender for Cloud",
      "alertTargetIDs": [
        "/subscriptions/test-sub/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/stdriftabc123"
      ],
      "configurationItems": [
        "stdriftabc123"
      ],
      "description": "Microsoft Defender has detected anonymous public read access enabled on standard storage account stdriftabc123."
    }
  }
}
```
