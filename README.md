# TP-Link Switch Status API

Simple Python HTTP API that exposes port and PoE status from TP-Link Easy Smart switches.
Designed for monitoring dashboards such as [**gethomepage.dev**](https://github.com/gethomepage/homepage).

<img width="2267" height="1043" alt="image" src="https://github.com/user-attachments/assets/20b2576e-f9c1-4955-a734-14bea8b33d09" />


---

## Features

- Port link status
- PoE state per port
- Total ports / active ports count
- Simple JSON output

---

## Requirements

- TP-Link Easy Smart switch with web interface accessible, in my case TL-SG108PE 8 port with 4 POE ports. Feel free to test it with other switches, as I do not have access to this option for now.

## Configuration

Edit ```tplink.py``` and set your credentials and IP address on switch:

```python
SWITCH_IP = "YOUR_SWITCH_IP"       # Switch IP address
USERNAME = "YOUR_USERNAME"         # Admin username
PASSWORD = "YOUR_PASSWORD"         # Admin password
PORT = 2137                        # HTTP server port
```

Run ```tplink.py``` script with python on any machine.

Example response from my switch:
```json
{
  "ports_total": 8,
  "ports_up": 5,
  "ports": [
    {
      "port": 1,
      "text": "1 Gb/s Full \u2013 PoE: On"
    },
    {
      "port": 2,
      "text": "1 Gb/s Full \u2013 PoE: Off"
    },
    {
      "port": 3,
      "text": "1 Gb/s Full \u2013 PoE: Off"
    },
    {
      "port": 4,
      "text": "1 Gb/s Full \u2013 PoE: Off"
    },
    {
      "port": 5,
      "text": "1 Gb/s Full"
    },
    {
      "port": 6,
      "text": "Link Down"
    },
    {
      "port": 7,
      "text": "Link Down"
    },
    {
      "port": 8,
      "text": "Link Down"
    }
  ]
}
```
## Gethomepage usage:
Because of gethomepage widgets' limitation to 4 boxes, I had to use 2 widgets to display all ports in my SG108PE:

```services.yaml```
```yaml
    - TP-Link switch:
        description: SG108PE POE
        icon: tp-link.png
        ping: 192.168.1.2
        widget:
          type: customapi
          url: "IP_OF_TPLINK_API_SERVER"
          refreshInterval: 10000 
          display: block
          mappings:
            - field: ports.0.text
              label: Port 1
              format: text
            - field: ports.1.text
              label: Port 2
              format: text
            - field: ports.2.text
              label: Port 3
              format: text
            - field: ports.3.text
              label: Port 4
              format: text
    - TP-Link switch:
        description: SG108PE
        icon: tp-link.png
        ping: 192.168.1.2
        widget:
          type: customapi
          url: "IP_OF_TPLINK_API_SERVER"
          refreshInterval: 10000
          display: block
          mappings:
            - field: ports.4.text
              label: Port 5
              format: text
            - field: ports.5.text
              label: Port 6
              format: text
            - field: ports.6.text
              label: Port 7
              format: text
            - field: ports.7.text
              label: Port 8
              format: text
```




