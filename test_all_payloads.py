import json
import requests
import sys
import os

# Custom parser to load .env file
def load_env(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value

load_env()

SUB_ID = os.getenv("ARM_SUBSCRIPTION_ID", "d78af5f4-5d2d-4141-a725-2088437da0ca")
STORAGE_NAME = os.getenv("REAL_STORAGE_ACCOUNT_NAME", "stdriftholt8j")
VM_NAME = os.getenv("REAL_VM_NAME", "vm-drift-test")
NSG_NAME = os.getenv("REAL_NSG_NAME", "nsg-landingzone-drift")
SQL_NAME = os.getenv("REAL_SQL_SERVER_NAME", "sqlserver-drift-test")

# Target Endpoint URL (Defaulting to localhost, can be overridden by argument)
URL = "http://localhost:7071/api/swarm-triage"
if len(sys.argv) > 1:
    URL = sys.argv[1]

# Optional Function Key for Authenticated Endpoints (e.g. when deployed to Azure)
FUNCTION_KEY = ""
if len(sys.argv) > 2:
    FUNCTION_KEY = sys.argv[2]

# Build the request headers
headers = {"Content-Type": "application/json"}
if FUNCTION_KEY:
    headers["x-functions-key"] = FUNCTION_KEY

# 1. Azure Monitor Activity Log Alert (Common Alert Schema - Storage Account)
activity_log_payload = {
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
        "essentials": {
            "alertId": f"/subscriptions/{SUB_ID}/providers/Microsoft.AlertsManagement/alerts/act-log-001",
            "alertRule": "Storage Account Access Policy Drift Alert",
            "severity": "Sev3",
            "signalType": "Activity Log",
            "monitoringService": "Activity Log",
            "alertTargetIDs": [
                f"/subscriptions/{SUB_ID}/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}"
            ],
            "configurationItems": [
                STORAGE_NAME
            ],
            "description": f"Storage account configuration changed to permit public blob access on {STORAGE_NAME}.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 2. Azure Monitor Metric Alert (e.g., General Metric alert - Storage Account)
metric_alert_payload = {
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
        "essentials": {
            "alertId": f"/subscriptions/{SUB_ID}/providers/Microsoft.AlertsManagement/alerts/metric-alert-002",
            "alertRule": "High Storage Account Transaction Volume",
            "severity": "Sev2",
            "signalType": "Metric",
            "monitoringService": "Platform Metrics",
            "alertTargetIDs": [
                f"/subscriptions/{SUB_ID}/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}"
            ],
            "configurationItems": [
                STORAGE_NAME
            ],
            "description": "The transactions count exceeded the threshold.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 3. Azure Service Health Alert (Storage Account service issue)
service_health_payload = {
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
        "essentials": {
            "alertId": f"/subscriptions/{SUB_ID}/providers/Microsoft.AlertsManagement/alerts/sh-003",
            "alertRule": "Azure Storage Active Incident",
            "severity": "Sev1",
            "signalType": "Activity Log",
            "monitoringService": "ServiceHealth",
            "alertTargetIDs": [
                f"/subscriptions/{SUB_ID}/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}"
            ],
            "configurationItems": [
                STORAGE_NAME
            ],
            "description": f"We are experiencing service performance degradation on Azure Storage resources in East US.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 4. Log Analytics Based Alert (e.g., Diagnostic Logging Alert - Storage Account)
log_analytics_payload = {
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
        "essentials": {
            "alertId": f"/subscriptions/{SUB_ID}/providers/Microsoft.AlertsManagement/alerts/la-log-004",
            "alertRule": "Diagnostic Logging Ingress Drift Detected",
            "severity": "Sev2",
            "signalType": "Log",
            "monitoringService": "Log Analytics",
            "alertTargetIDs": [
                f"/subscriptions/{SUB_ID}/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}"
            ],
            "configurationItems": [
                STORAGE_NAME
            ],
            "description": f"Diagnostic log searching query found public access logs on {STORAGE_NAME}.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 5. CPU Threshold Alert (Specific Metric Alert - VM Compute Resource)
cpu_threshold_payload = {
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
        "essentials": {
            "alertId": f"/subscriptions/{SUB_ID}/providers/Microsoft.AlertsManagement/alerts/cpu-alert-005",
            "alertRule": "High CPU Usage Warning",
            "severity": "Sev2",
            "signalType": "Metric",
            "monitoringService": "Platform Metrics",
            "alertTargetIDs": [
                f"/subscriptions/{SUB_ID}/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Compute/virtualMachines/{VM_NAME}"
            ],
            "configurationItems": [
                VM_NAME
            ],
            "description": "CPU percentage usage has exceeded 90% threshold limit, password authentication is active and vulnerable.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 6. Microsoft Defender for Cloud Security Alert (Storage Account)
defender_security_payload = {
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
        "essentials": {
            "alertId": f"/subscriptions/{SUB_ID}/providers/Microsoft.AlertsManagement/alerts/def-sec-006",
            "alertRule": "Defender Storage Account Protection Alert",
            "severity": "Sev0",
            "signalType": "Security",
            "monitoringService": "Microsoft Defender for Cloud",
            "alertTargetIDs": [
                f"/subscriptions/{SUB_ID}/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Storage/storageAccounts/{STORAGE_NAME}"
            ],
            "configurationItems": [
                STORAGE_NAME
            ],
            "description": f"Microsoft Defender has detected anonymous public read access enabled on standard storage account {STORAGE_NAME}.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 7. Network Security Group Port Exposure Alert (Network Resource)
nsg_exposure_payload = {
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
        "essentials": {
            "alertId": f"/subscriptions/{SUB_ID}/providers/Microsoft.AlertsManagement/alerts/nsg-port-007",
            "alertRule": "Network Security Group Insecure Port Access Rule",
            "severity": "Sev1",
            "signalType": "Activity Log",
            "monitoringService": "Activity Log",
            "alertTargetIDs": [
                f"/subscriptions/{SUB_ID}/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Network/networkSecurityGroups/{NSG_NAME}"
            ],
            "configurationItems": [
                NSG_NAME
            ],
            "description": f"Network Security Group rule allows inbound ports 22 and 3389 from any source internet address prefix (*).",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

# 8. SQL Database Firewall Open Alert (Database Resource)
sql_firewall_payload = {
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
        "essentials": {
            "alertId": f"/subscriptions/{SUB_ID}/providers/Microsoft.AlertsManagement/alerts/sql-firewall-008",
            "alertRule": "SQL Server Firewall Rule Policy Violation",
            "severity": "Sev1",
            "signalType": "Activity Log",
            "monitoringService": "Activity Log",
            "alertTargetIDs": [
                f"/subscriptions/{SUB_ID}/resourceGroups/rg-azureops-drift-test/providers/Microsoft.Sql/servers/{SQL_NAME}"
            ],
            "configurationItems": [
                SQL_NAME
            ],
            "description": f"SQL firewall rule AllowAllInternet is configured to permit unrestricted public database access (0.0.0.0 to 255.255.255.255) on server {SQL_NAME}.",
            "eventDateTime": "2026-06-10T16:00:00Z"
        }
    }
}

tests = [
    ("1. Azure Monitor Activity Log Alert (Storage)", activity_log_payload),
    ("2. Azure Monitor Metric Alert (Storage)", metric_alert_payload),
    ("3. Service Health Alert (Storage)", service_health_payload),
    ("4. Log Analytics/Diagnostic Logging Alert (Storage)", log_analytics_payload),
    ("5. CPU Threshold Alert (Compute/VM)", cpu_threshold_payload),
    ("6. Microsoft Defender for Cloud Security Alert (Storage)", defender_security_payload),
    ("7. Network Security Group Public Port Rule Alert (Network)", nsg_exposure_payload),
    ("8. SQL Server Firewall Open Alert (Database)", sql_firewall_payload)
]

print(f"[*] Testing AzureOps Swarm Triage Endpoint: {URL}")
if FUNCTION_KEY:
    print("[*] Authentication Header (x-functions-key) Active.")
print()

for name, payload in tests:
    print(f"Executing: {name} ...")
    try:
        response = requests.post(URL, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print("Response:", response.text)
    except Exception as e:
        print("Error sending request:", str(e))
    print("-" * 50)
