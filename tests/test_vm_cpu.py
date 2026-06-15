try:
    from .config import SUB_ID, VM_NAME, send_alert_payload
except ImportError:
    from config import SUB_ID, VM_NAME, send_alert_payload

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

def test_vm_cpu():
    return send_alert_payload("5. CPU Threshold Alert (Compute/VM)", cpu_threshold_payload)

if __name__ == "__main__":
    test_vm_cpu()
