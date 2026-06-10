import json
import requests
import sys

# Target Endpoint URL (Defaulting to localhost, can be overridden by argument)
URL = "http://localhost:7071/api/swarm-triage"
if len(sys.argv) > 1:
    URL = sys.argv[1]

# 1. Azure Monitor Activity Log Alert (Common Alert Schema)
activity_log_payload = {
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
            "description": "Storage account configuration changed to permit public blob access.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 2. Azure Monitor Metric Alert (e.g., General Metric alert)
metric_alert_payload = {
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
            "description": "The transactions count exceeded the threshold.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 3. Azure Service Health Alert
service_health_payload = {
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
            "description": "We are experiencing service performance degradation on Azure Storage resources in East US.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 4. Log Analytics Based Alert (e.g., Diagnostic Logging Alert)
log_analytics_payload = {
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
            "description": "Diagnostic log searching query found public access logs on stdriftabc123.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 5. CPU Threshold Alert (Specific Metric Alert)
cpu_threshold_payload = {
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
            "description": "CPU percentage usage has exceeded 90% threshold limit.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 6. Microsoft Defender for Cloud Security Alert
defender_security_payload = {
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
            "description": "Microsoft Defender has detected anonymous public read access enabled on standard storage account stdriftabc123.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

tests = [
    ("1. Azure Monitor Activity Log Alert", activity_log_payload),
    ("2. Azure Monitor Metric Alert", metric_alert_payload),
    ("3. Service Health Alert", service_health_payload),
    ("4. Log Analytics/Diagnostic Logging Alert", log_analytics_payload),
    ("5. CPU Threshold Alert", cpu_threshold_payload),
    ("6. Microsoft Defender for Cloud Security Alert", defender_security_payload)
]

print(f"🚀 Testing AzureOps Swarm Triage Endpoint: {URL}\n")
for name, payload in tests:
    print(f"Executing: {name} ...")
    try:
        response = requests.post(URL, json=payload, headers={"Content-Type": "application/json"})
        print(f"Status Code: {response.status_code}")
        print("Response:", response.text)
    except Exception as e:
        print("Error sending request:", str(e))
    print("-" * 50)
