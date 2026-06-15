try:
    from .config import SUB_ID, STORAGE_NAME, send_alert_payload
except ImportError:
    from config import SUB_ID, STORAGE_NAME, send_alert_payload

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

def test_storage_service_health():
    return send_alert_payload("3. Service Health Alert (Storage)", service_health_payload)

if __name__ == "__main__":
    test_storage_service_health()
