from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import requests
import re

# ---------------- CONFIG ----------------
# Replace these with your TP-Link data
SWITCH_IP = "YOUR_SWITCH_IP"       # e.g., 192.168.1.2
USERNAME = "YOUR_USERNAME"         # admin or custom
PASSWORD = "YOUR_PASSWORD"         # switch password
PORT = 2137
TIMEOUT = 5

MAX_PORTS = 8
POE_PORTS = 4

LINK_STATUS = {
    "0": "Link Down",
    "1": "LS 1",
    "2": "10M Half",
    "3": "10M Full",
    "4": "LS 4",
    "5": "100M Full",
    "6": "1 Gb/s Full"
}

# ---------------- FUNCTIONS ----------------
def login(session):
    # Log in to the switch using a session
    session.post(
        f"http://{SWITCH_IP}/logon.cgi",
        data={"logon": "Login", "username": USERNAME, "password": PASSWORD},
        timeout=TIMEOUT
    )

def parse_js_object(text, var_name):
    # Parse a JS object from the switch HTML/JS page
    m = re.search(rf"var {var_name}\s*=\s*{{(.*?)}};", text, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).split(",\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip()
    return result

def get_switch_data():
    session = requests.Session()
    login(session)

    ports = []
    poe_data = {}

    # --- Port statistics ---
    r = session.get(f"http://{SWITCH_IP}/PortStatisticsRpm.htm", timeout=TIMEOUT)
    stats = parse_js_object(r.text, "all_info")
    states = re.findall(r"\d", stats.get("state", ""))
    links = re.findall(r"\d", stats.get("link_status", ""))
    ports_count = min(MAX_PORTS, len(states), len(links))

    # --- PoE status ---
    try:
        r = session.get(f"http://{SWITCH_IP}/PoeRecoveryRpm.htm", timeout=TIMEOUT)
        m = re.search(r"var portRecoveryConfig\s*=\s*{.*?ip\s*:\s*\[([^\]]*)\]", r.text, re.DOTALL)
        if m:
            ips = [x.strip().strip('"') for x in m.group(1).split(",")]
            for i in range(len(ips)):
                poe_data[i + 1] = "On" if ips[i] else "Off"
    except Exception:
        pass

    # --- Build port list ---
    for i in range(ports_count):
        port_num = i + 1
        text = LINK_STATUS.get(links[i], "unknown")
        if port_num <= POE_PORTS:
            text += f" – PoE: {poe_data.get(port_num, 'Off')}"
        ports.append({"port": port_num, "text": text})

    return {
        "ports_total": ports_count,
        "ports_up": sum(1 for p in ports if "Link Down" not in p["text"]),
        "ports": ports
    }

# ---------------- HTTP SERVER ----------------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Serve JSON data of switch status
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(get_switch_data(), indent=2).encode())

    def log_message(self, *_):
        pass  # disable console logging

if __name__ == "__main__":
    print(f"Switch API server running on 0.0.0.0:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
