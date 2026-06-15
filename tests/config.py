import os
import sys
import requests

def load_env():
    # Attempt to load from current directory, parent directory, or grandparent directory
    env_paths = [
        ".env",
        "../.env",
        "../../.env"
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
            break

# Load env variables on import
load_env()

# Resolve variables from environment with sane defaults
SUB_ID = os.getenv("ARM_SUBSCRIPTION_ID", "d78af5f4-5d2d-4141-a725-2088437da0ca")
STORAGE_NAME = os.getenv("REAL_STORAGE_ACCOUNT_NAME", "stdriftholt8j")
VM_NAME = os.getenv("REAL_VM_NAME", "vm-drift-test")
NSG_NAME = os.getenv("REAL_NSG_NAME", "nsg-landingzone-drift")
SQL_NAME = os.getenv("REAL_SQL_SERVER_NAME", "sqlserver-drift-test")

# Resolve API target endpoint
URL = "http://localhost:7071/api/swarm-triage"
if len(sys.argv) > 1 and not sys.argv[1].endswith(".py") and not sys.argv[1].startswith("-"):
    URL = sys.argv[1]

# Optional Function Key for Auth (e.g. production/remote Azure Function)
FUNCTION_KEY = ""
if len(sys.argv) > 2:
    FUNCTION_KEY = sys.argv[2]

# Build headers
headers = {"Content-Type": "application/json"}
if FUNCTION_KEY:
    headers["x-functions-key"] = FUNCTION_KEY

def send_alert_payload(payload_name, payload):
    print(f"Executing: {payload_name} ...")
    try:
        response = requests.post(URL, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print("Response:", response.text)
        return response
    except Exception as e:
        print("Error sending request:", str(e))
        return None
