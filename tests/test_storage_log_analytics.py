try:
    from .config import SUB_ID, STORAGE_NAME, send_alert_payload
except ImportError:
    from config import SUB_ID, STORAGE_NAME, send_alert_payload

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

def test_storage_log_analytics():
    return send_alert_payload("4. Log Analytics/Diagnostic Logging Alert (Storage)", log_analytics_payload)

if __name__ == "__main__":
    test_storage_log_analytics()
