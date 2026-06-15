import sys
import os

# Ensure this directory is in the import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import URL
from test_storage_activity_log import test_storage_activity_log
from test_storage_metric import test_storage_metric
from test_storage_service_health import test_storage_service_health
from test_storage_log_analytics import test_storage_log_analytics
from test_vm_cpu import test_vm_cpu
from test_storage_defender import test_storage_defender
from test_nsg_exposure import test_nsg_exposure
from test_sql_firewall import test_sql_firewall

def run_all_tests():
    print(f"[*] Running all modular tests against target triage endpoint: {URL}\n")
    
    tests = [
        ("1. Azure Monitor Activity Log Alert (Storage)", test_storage_activity_log),
        ("2. Azure Monitor Metric Alert (Storage)", test_storage_metric),
        ("3. Service Health Alert (Storage)", test_storage_service_health),
        ("4. Log Analytics/Diagnostic Logging Alert (Storage)", test_storage_log_analytics),
        ("5. CPU Threshold Alert (Compute/VM)", test_vm_cpu),
        ("6. Microsoft Defender for Cloud Security Alert (Storage)", test_storage_defender),
        ("7. Network Security Group Public Port Rule Alert (Network)", test_nsg_exposure),
        ("8. SQL Server Firewall Open Alert (Database)", test_sql_firewall)
    ]
    
    results = []
    for name, test_func in tests:
        response = test_func()
        status_str = f"Status Code: {response.status_code}" if response is not None else "Failed to send (Error)"
        results.append((name, status_str))
        print("-" * 50)
        
    print("\n=== Test Execution Summary ===")
    for name, status in results:
        print(f"{name} -> {status}")

if __name__ == "__main__":
    run_all_tests()
