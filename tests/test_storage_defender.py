try:
    from .config import SUB_ID, STORAGE_NAME, send_alert_payload
except ImportError:
    from config import SUB_ID, STORAGE_NAME, send_alert_payload

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

def test_storage_defender():
    return send_alert_payload("6. Microsoft Defender for Cloud Security Alert (Storage)", defender_security_payload)

if __name__ == "__main__":
    test_storage_defender()
