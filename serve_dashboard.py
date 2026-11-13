"""
Local Live Dashboard Server.
Serves the web dashboard, exposes /api/state, and allows live 1-click status updates.
"""
import http.server
import json
import os
import socketserver
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.resolve()
STATE_FILE = BASE_DIR / "state" / "applications.json"
DASHBOARD_DIR = BASE_DIR / "dashboard"
REPORTS_DIR = BASE_DIR / "reports"

PORT = 8080


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        # Enable CORS
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path in ["/", "/index.html"]:
            self.send_response(302)
            self.send_header("Location", "/dashboard/index.html")
            self.end_headers()
            return

        if self.path == "/api/state":
            try:
                if STATE_FILE.exists():
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {}
                payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/mark_applied":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                req = json.loads(body.decode("utf-8"))
                job_id = req.get("job_id")

                if not job_id:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'{"error": "job_id is required"}')
                    return

                # Update State
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state_data = json.load(f)

                if job_id in state_data:
                    state_data[job_id]["status"] = "APPLIED"
                    state_data[job_id]["applied_at"] = datetime.now().isoformat()
                    notes = req.get("notes") or "Marked as applied via Web Dashboard."
                    state_data[job_id]["action_notes"] = notes

                    with open(STATE_FILE, "w", encoding="utf-8") as f:
                        json.dump(state_data, f, indent=2, ensure_ascii=False)

                    # Update dashboard/data.js
                    try:
                        out_file = DASHBOARD_DIR / "data.js"
                        with open(out_file, "w", encoding="utf-8") as f:
                            f.write("window.INITIAL_APPLICATIONS_DATA = ")
                            json.dump(state_data, f, indent=2, ensure_ascii=False)
                            f.write(";\n")
                    except Exception:
                        pass

                    # Regenerate daily markdown report
                    try:
                        from src.state_manager import StateManager
                        from src.reporter import ReportGenerator
                        sm = StateManager(STATE_FILE)
                        rg = ReportGenerator(REPORTS_DIR)
                        rg.generate_daily_report(sm.get_all_records())
                    except Exception as e:
                        print(f"Warning regenerating report: {e}")

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok", "job_id": job_id}).encode("utf-8"))
                    return
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'{"error": "Job not found"}')
                    return

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()


def find_free_port(start_port=8080):
    import socket
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
        port += 1
    return start_port


def main():
    port = find_free_port(PORT)
    url = f"http://localhost:{port}/dashboard/index.html"
    print(f"\n=======================================================")
    print(f"  🚀 Job Applier Web Dashboard Server")
    print(f"  Candidate: Kaushal Francis J")
    print(f"  URL: {url}")
    print(f"=======================================================\n")

    # Launch browser after a short delay
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        print(f"Serving live dashboard at {url} (Press Ctrl+C to stop)...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard server.")


if __name__ == "__main__":
    main()
