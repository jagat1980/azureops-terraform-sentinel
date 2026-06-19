import http.server
import socketserver
import urllib.request
import urllib.error
import json

PORT = 8080
FORWARD_URL = "http://localhost:7071/api/swarm-triage"

class WebhookProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        # We handle requests on both /webhook and /api/security/alert
        if self.path not in ["/webhook", "/api/security/alert"]:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        print(f"\n[Webhook Receiver] Received alert payload on {self.path}. Forwarding to Agent Brain on port 7071...")

        # Forward request to Azure Function (7071)
        req = urllib.request.Request(
            FORWARD_URL,
            data=post_data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            # We set a long timeout (120s) because agent reasoning takes time
            with urllib.request.urlopen(req, timeout=120) as response:
                resp_data = response.read()
                self.send_response(response.status)
                self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                self.end_headers()
                self.wfile.write(resp_data)
                print("[Webhook Receiver] Agent successfully processed payload.")
        except urllib.error.HTTPError as e:
            resp_data = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', e.headers.get('Content-Type', 'application/json'))
            self.end_headers()
            self.wfile.write(resp_data)
            print(f"[Webhook Receiver] Error from Agent (HTTP {e.code}): {resp_data.decode()}")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            error_msg = f"Failed to forward payload: {str(e)}"
            self.wfile.write(error_msg.encode())
            print(f"[Webhook Receiver] Connection error: {error_msg}")

if __name__ == "__main__":
    # Allow port reuse to prevent address-already-in-use errors
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), WebhookProxyHandler) as httpd:
        print(f"===========================================================")
        print(f" Codex App Mock Webhook Receiver listening on port {PORT}")
        print(f" Listening for POST on: /webhook and /api/security/alert")
        print(f" Forwarding to Azure Function at: {FORWARD_URL}")
        print(f"===========================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down webhook receiver...")
