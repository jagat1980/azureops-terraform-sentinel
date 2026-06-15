try:
    from .config import SUB_ID, STORAGE_NAME, send_alert_payload
except ImportError:
    from config import SUB_ID, STORAGE_NAME, send_alert_payload

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

def test_storage_metric():
    return send_alert_payload("2. Azure Monitor Metric Alert (Storage)", metric_alert_payload)

if __name__ == "__main__":
    test_storage_metric()
