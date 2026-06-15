try:
    from .config import SUB_ID, NSG_NAME, send_alert_payload
except ImportError:
    from config import SUB_ID, NSG_NAME, send_alert_payload

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

def test_nsg_exposure():
    return send_alert_payload("7. Network Security Group Public Port Rule Alert (Network)", nsg_exposure_payload)

if __name__ == "__main__":
    test_nsg_exposure()
