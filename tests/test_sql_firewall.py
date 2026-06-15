try:
    from .config import SUB_ID, SQL_NAME, send_alert_payload
except ImportError:
    from config import SUB_ID, SQL_NAME, send_alert_payload

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

def test_sql_firewall():
    return send_alert_payload("8. SQL Server Firewall Open Alert (Database)", sql_firewall_payload)

if __name__ == "__main__":
    test_sql_firewall()
