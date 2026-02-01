from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import requests
import re
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------- CONFIG ----------------
# Add all your switches here
# Switches will be numbered by their position: first = switch.1, second = switch.2, etc.
SWITCHES = [
    {
        "name": "SWITCH_NAME",  # Will be switch.1 in output
        "ip": "SWITCH_IP",
        "username": "admin",
        "password": "your_password"
    },
    {
        "name": "SWITCH_NAME",  # Will be switch.2 in output
        "ip": "SWITCH_IP",
        "username": "admin",
        "password": "your_password"
    },
]

PORT = 2137
TIMEOUT = 5

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
def login(session: requests.Session, switch_ip: str, username: str, password: str) -> None:
    """Authenticate with the TP-Link switch."""
    session.post(
        f"http://{switch_ip}/logon.cgi",
        data={"logon": "Login", "username": username, "password": password},
        timeout=TIMEOUT
    )

def parse_js_object(text: str, var_name: str) -> Dict:
    """Extract JavaScript object from HTML response."""
    m = re.search(rf"var {var_name}\s*=\s*{{(.*?)}};", text, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).split(",\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip()
    return result

def detect_port_count(html_text: str) -> int:
    """
    Detect actual port count from the PortStatisticsRpm.htm page.
    Looks for max_port_num variable or counts table rows.
    """
    m = re.search(r'var\s+max_port_num\s*=\s*(\d+)', html_text)
    if m:
        return int(m.group(1))
    
    m = re.search(r'var\s+port_num\s*=\s*(\d+)', html_text)
    if m:
        return int(m.group(1))
    
    stats = parse_js_object(html_text, "all_info")
    state_str = stats.get("state", "")
    if state_str:
        state_str = state_str.strip('"').strip("'")
        if ',' in state_str:
            return len([x for x in state_str.split(',') if x.strip()])
        else:
            return len([c for c in state_str if c.isdigit()])
    
    return 0

def detect_poe_ports(session: requests.Session, switch_ip: str) -> Tuple[Dict[int, str], int]:
    """
    Auto-detect which ports support PoE and their current status.
    Returns: (poe_status_dict, total_poe_port_count)
    """
    poe_data = {}
    poe_port_count = 0
    
    try:
        r = session.get(f"http://{switch_ip}/PoeRecoveryRpm.htm", timeout=TIMEOUT)
        
        if r.status_code != 200:
            return {}, 0
        
        m = re.search(r'var\s+poe_port_num\s*=\s*(\d+)', r.text)
        if not m:
            return {}, 0
        
        poe_port_count = int(m.group(1))
        
        cfg = parse_js_object(r.text, "portRecoveryConfig")
        
        ip_match = re.search(r'ip\s*:\s*\[([^\]]*)\]', r.text)
        if ip_match:
            ip_list_str = ip_match.group(1)
            ips = re.findall(r'"([^"]*)"', ip_list_str)
            
            for i in range(poe_port_count):
                port_num = i + 1
                if i < len(ips) and ips[i].strip():
                    poe_data[port_num] = "On"
                else:
                    poe_data[port_num] = "Off"
        else:
            for i in range(poe_port_count):
                poe_data[i + 1] = "Off"
                
    except requests.exceptions.RequestException:
        pass
    except Exception as e:
        if "RemoteDisconnected" not in str(e) and "Connection aborted" not in str(e):
            print(f"PoE detection error for {switch_ip}: {e}")
    
    return poe_data, poe_port_count

def get_single_switch_data(switch_config: Dict) -> Dict:
    """Fetch data for a single switch."""
    switch_ip = switch_config["ip"]
    username = switch_config["username"]
    password = switch_config["password"]
    name = switch_config["name"]
    
    try:
        session = requests.Session()
        login(session, switch_ip, username, password)

        r = session.get(f"http://{switch_ip}/PortStatisticsRpm.htm", timeout=TIMEOUT)
        html_text = r.text
        
        ports_count = detect_port_count(html_text)
        
        stats = parse_js_object(html_text, "all_info")
        
        states = re.findall(r"\d", stats.get("state", ""))
        links = re.findall(r"\d", stats.get("link_status", ""))
        
        if ports_count == 0:
            ports_count = min(len(states), len(links))
        
        poe_data, poe_port_count = detect_poe_ports(session, switch_ip)
        
        ports = []
        for i in range(ports_count):
            port_num = i + 1
            text = LINK_STATUS.get(links[i] if i < len(links) else "0", "unknown")
            
            if port_num in poe_data:
                text += f" – PoE: {poe_data[port_num]}"
            
            ports.append({"port": port_num, "text": text})

        return {
            "name": name,
            "ip": switch_ip,
            "status": "online",
            "ports_total": ports_count,
            "ports_up": sum(1 for p in ports if "Link Down" not in p["text"]),
            "poe_ports": poe_port_count,
            "ports": ports
        }
    
    except Exception as e:
        return {
            "name": name,
            "ip": switch_ip,
            "status": "offline",
            "error": str(e)
        }

def get_all_switches_data() -> Dict:
    """Fetch data from all switches concurrently."""
    switches_data = []
    
    with ThreadPoolExecutor(max_workers=len(SWITCHES)) as executor:
        future_to_switch = {
            executor.submit(get_single_switch_data, switch): (idx, switch) 
            for idx, switch in enumerate(SWITCHES)
        }
        
        for future in as_completed(future_to_switch):
            try:
                idx, switch = future_to_switch[future]
                data = future.result()
                switches_data.append((idx, data))
            except Exception as e:
                idx, switch = future_to_switch[future]
                switches_data.append((idx, {
                    "name": switch["name"],
                    "ip": switch["ip"],
                    "status": "error",
                    "error": str(e)
                }))
    
    switches_data.sort(key=lambda x: x[0])
    
    online_switches = sum(1 for _, s in switches_data if s.get("status") == "online")
    total_ports = sum(s.get("ports_total", 0) for _, s in switches_data if s.get("status") == "online")
    total_ports_up = sum(s.get("ports_up", 0) for _, s in switches_data if s.get("status") == "online")
    total_poe_ports = sum(s.get("poe_ports", 0) for _, s in switches_data if s.get("status") == "online")
    
    switch_dict = {}
    for idx, switch_data in switches_data:
        if "ports" in switch_data:
            port_dict = {}
            for port_info in switch_data["ports"]:
                port_num = port_info["port"]
                port_dict[str(port_num)] = {"text": port_info["text"]}
            switch_data["port"] = port_dict
            del switch_data["ports"]
        
        switch_dict[str(idx + 1)] = switch_data
    
    return {
        "switches_total": len(SWITCHES),
        "switches_online": online_switches,
        "total_ports": total_ports,
        "total_ports_up": total_ports_up,
        "total_poe_ports": total_poe_ports,
        "switch": switch_dict
    }

# ---------------- HTTP SERVER ----------------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            data = get_all_switches_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error = {"error": str(e)}
            self.wfile.write(json.dumps(error).encode())

    def log_message(self, *_):
        pass

if __name__ == "__main__":
    print(f"Switch API server running on 0.0.0.0:{PORT}")
    print(f"Monitoring {len(SWITCHES)} switch(es)...")
    print("\nTesting connections...")
    
    try:
        data = get_all_switches_data()
        print(f"\n✓ {data['switches_online']}/{data['switches_total']} switches online")
        print(f"✓ Total PoE ports across all switches: {data.get('total_poe_ports', 0)}")
        for switch_id, switch in data.get('switch', {}).items():
            status_icon = "✓" if switch.get("status") == "online" else "✗"
            if switch.get("status") == "online":
                poe_info = f", {switch['poe_ports']} PoE" if switch['poe_ports'] > 0 else ", no PoE"
                print(f"  {status_icon} {switch['name']} ({switch['ip']}): {switch['ports_total']} ports{poe_info}")
            else:
                print(f"  {status_icon} {switch['name']} ({switch['ip']}): {switch.get('error', 'offline')}")
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
    
    print(f"\nServer ready at http://localhost:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
