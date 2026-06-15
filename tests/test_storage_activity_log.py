try:
    from .config import SUB_ID, STORAGE_NAME, send_alert_payload
except ImportError:
    from config import SUB_ID, STORAGE_NAME, send_alert_payload

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

def test_storage_activity_log():
    return send_alert_payload("1. Azure Monitor Activity Log Alert (Storage)", activity_log_payload)

if __name__ == "__main__":
    test_storage_activity_log()
