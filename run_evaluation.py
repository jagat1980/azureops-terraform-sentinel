import os
import json
import requests
import sys

WEBHOOK_URL_CODEX = "http://localhost:8080/webhook"
WEBHOOK_URL_FUNC = "http://localhost:7071/api/swarm-triage"
PAYLOADS_DIR = os.path.join(os.path.dirname(__file__), "payloads")

def get_payloads():
    if not os.path.exists(PAYLOADS_DIR):
        print(f"Error: {PAYLOADS_DIR} does not exist.")
        return []
    return [f for f in os.listdir(PAYLOADS_DIR) if f.endswith('.json')]

def send_payload(filename, target_url):
    filepath = os.path.join(PAYLOADS_DIR, filename)
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    print(f"\nSending {filename} to {target_url}...")
    try:
        response = requests.post(target_url, json=data, timeout=120)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to the target endpoint. Make sure the server is running.")
        print(f"Error details: {e}")

def main():
    print("===============================================")
    print(" Codex App Agentic Security - Hackathon Eval")
    print("===============================================")
    
    payloads = get_payloads()
    if not payloads:
        print("No payloads found to evaluate.")
        sys.exit(1)
        
    for i, payload in enumerate(payloads):
        print(f"[{i+1}] {payload}")
        
    print(f"[{len(payloads)+1}] Exit")
    
    try:
        choice = int(input("\nSelect a payload to trigger the agent: "))
        if choice == len(payloads) + 1:
            print("Exiting...")
            sys.exit(0)
        if 1 <= choice <= len(payloads):
            print("\nSelect the target webhook receiver:")
            print("[1] Local Azure Function App (Port 7071) - RUNNING")
            print("[2] Codex App Webhook (Port 8080)")
            target_choice = int(input("Select target: "))
            
            target_url = WEBHOOK_URL_FUNC if target_choice == 1 else WEBHOOK_URL_CODEX
            send_payload(payloads[choice-1], target_url)
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input. Please enter a number.")
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
