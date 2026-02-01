<h1 align="center">TP-Link Switch Status API</h1>
<p align="center">
Simple Python HTTP API that exposes port and PoE status from TP-Link Easy Smart switches.<br><br>
Designed for monitoring dashboards such as <a href="https://github.com/gethomepage/homepage" target="_blank"><b>gethomepage.dev</b></a>.<br><br>
<img width="761" height="151" alt="image" src="https://github.com/user-attachments/assets/8e3a90ab-4dca-4a07-90a2-3385d89e6ae9" />

</p>

## Features
- **Multi-switch support** - Monitor multiple switches from a single API server
- **Auto-detection** - Automatically detects total ports and PoE capabilities per switch
- **Port link status** - Real-time port connection status
- **PoE state per port** - Shows which PoE ports are active/inactive
- **Concurrent requests** - Fetches all switches simultaneously for fast response
- **Simple JSON output** - Clean structure with `switch.X.port.Y.text` format
- **Total statistics** - Aggregate counts across all switches

## Requirements
- Python 3.7+
- `requests` library (`pip install requests`)
- TP-Link Easy Smart switch(es) with web interface

**Tested switches:**
- TL-SG108PE (8 ports, 4 PoE)
- TL-SG105E (5 ports, no PoE)

Feel free to test with other TP-Link Easy Smart models and report compatibility!

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Piorek99/tplink-status-api.git
cd tplink-status-api
```

2. Install dependencies:
```bash
pip install requests
```

## Configuration

Edit `tplink.py` and configure your switches in the `SWITCHES` list:

```python
SWITCHES = [
    {
        "name": "SG108PE",          # Switch name
        "ip": "192.168.1.2",        # Switch IP address
        "username": "admin",         # Admin username
        "password": "your_password"  # Admin password
    },
    # Add more switches as needed
]

PORT = 2137  # HTTP server port
```

**Note:** Switches are numbered by their position in the list. First switch = `switch.1`, second = `switch.2`, etc.

## Usage

Run the script:
```bash
python tplink.py
```

The API will be available at `http://localhost:2137`

### Example Response

```json
{
  "switches_total": 2,
  "switches_online": 2,
  "total_ports": 13,
  "total_ports_up": 7,
  "total_poe_ports": 4,
  "switch": {
    "1": {
      "name": "SG108PE",
      "ip": "192.168.1.2",
      "status": "online",
      "ports_total": 8,
      "ports_up": 6,
      "poe_ports": 4,
      "port": {
        "1": {
          "text": "1 Gb/s Full \u2013 PoE: On"
        },
        "2": {
          "text": "1 Gb/s Full \u2013 PoE: Off"
        },
        "3": {
          "text": "1 Gb/s Full \u2013 PoE: Off"
        },
        "4": {
          "text": "1 Gb/s Full \u2013 PoE: Off"
        },
        "5": {
          "text": "1 Gb/s Full"
        },
        "6": {
          "text": "Link Down"
        },
        "7": {
          "text": "1 Gb/s Full"
        },
        "8": {
          "text": "Link Down"
        }
      }
    },
    "2": {
      "name": "SG105E",
      "ip": "192.168.1.6",
      "status": "online",
      "ports_total": 5,
      "ports_up": 1,
      "poe_ports": 0,
      "port": {
        "1": {
          "text": "Link Down"
        },
        "2": {
          "text": "Link Down"
        },
        "3": {
          "text": "1 Gb/s Full"
        },
        "4": {
          "text": "Link Down"
        },
        "5": {
          "text": "Link Down"
        }
      }
    }
  }
}
```

## GetHomepage Integration

The API uses a clean structure where:
- **Switches** are numbered by position starting from 1: `switch.1`, `switch.2`, etc.
- **Ports** are numbered by their actual port number: `port.1`, `port.2`, etc.

This means `switch.1.port.4` refers to **first switch, port 4**.

### Example Configuration

Add to your `services.yaml`:

```yaml
- TP-Link SG108PE:
    description: 8-Port Switch
    icon: tp-link.png
    ping: YOUR_SWITCH_IP
    widget:
      type: customapi
      url: http://YOUR_API_SERVER_IP:2137
      refreshInterval: 10000
      display: block
      mappings:
        - field: switch.1.port.1.text
          label: Port 1
          format: text
        - field: switch.1.port.2.text
          label: Port 2
          format: text
        - field: switch.1.port.3.text
          label: Port 3
          format: text
        - field: switch.1.port.4.text
          label: Port 4
          format: text
```

## How It Works

1. **Auto-detection**: The script automatically detects:
   - Total number of ports per switch
   - Which ports support PoE
   - Current PoE status (On/Off based on configured IP monitoring)

2. **Concurrent fetching**: All switches are queried simultaneously using ThreadPoolExecutor for fast response times

3. **Error handling**: If a switch is offline or unreachable, it's marked as offline while other switches continue to work

4. **Clean JSON structure**: Uses dictionaries with numeric keys instead of arrays, making the data easier to access in dashboard widgets

## Troubleshooting

**Q: I'm getting "PoE detection failed" errors**  
A: This is normal for switches without PoE capability (like SG105E). The script handles this gracefully and won't show PoE status for those ports.

**Q: Port counts are wrong**  
A: Make sure your switch firmware is up to date. The script reads the `max_port_num` variable from the switch's web interface.

**Q: Dashboard shows no data**  
A: Check that:
- The API server is running
- You're using the correct switch numbers in your `services.yaml` (switch.1, switch.2, etc.)
- Your firewall allows connections to port 2137

