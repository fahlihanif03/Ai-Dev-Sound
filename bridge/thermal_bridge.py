"""
thermal_bridge.py

Bridges the CY8CPROTO-062-4343W's live thermal-monitor-fw UART output to the
deployed dashboard (web-dashboard/), so the Predictive Maintenance page's
temperature card shows real readings instead of the simulator.

Reads lines like:
    temp=29.19C rate=-0.018C/s normal
    temp=32.55C rate=+1.743C/s ANOMALY [rising-too-fast]
(see ../thermal-monitor-fw/main.c's printf in the main loop - this format
must stay in sync with that if the firmware's print format ever changes)
and POSTs each reading to the dashboard's /api/ingest endpoint.

Usage:
    python thermal_bridge.py                  # auto-detects the KitProg3 COM port
    python thermal_bridge.py --port COM5       # or specify it explicitly

Requires INGEST_TOKEN, either as an environment variable or read from
../web-dashboard/ingest-token.local (the file `wrangler secret put` wrote it
to when the secret was set) if that env var isn't set.
"""
import argparse
import os
import re
import sys
import time

import requests
import serial
import serial.tools.list_ports

DASHBOARD_URL = "https://demo-kit-dashboard.anepfadhli5.workers.dev/api/ingest"
BAUD_RATE = 115200

# Must match thermal-monitor-fw/main.c's TEMP_THRESHOLD_C - the firmware
# doesn't print the threshold itself, only whether it was exceeded.
TEMP_THRESHOLD_C = 50.0

LINE_RE = re.compile(
    r"temp=(?P<temp>[-\d.]+)C\s+rate=(?P<rate>[-+\d.]+)C/s\s+(?P<flag>ANOMALY|normal)"
)


def find_ingest_token() -> str:
    env_token = os.environ.get("INGEST_TOKEN")
    if env_token:
        return env_token

    token_file = os.path.join(os.path.dirname(__file__), "..", "web-dashboard", "ingest-token.local")
    if os.path.exists(token_file):
        with open(token_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Value:"):
                    return line.split(":", 1)[1].strip()

    raise SystemExit(
        "No INGEST_TOKEN found. Set the INGEST_TOKEN environment variable, "
        "or make sure web-dashboard/ingest-token.local exists (written by "
        "`wrangler secret put INGEST_TOKEN`)."
    )


def kitprog3_ports():
    return [p.device for p in serial.tools.list_ports.comports() if "KitProg3" in (p.description or "")]


def peek_port(device: str, seconds: float = 3.0) -> str:
    """Reads whatever a port prints for a couple seconds, for disambiguating
    which physical board (thermal vs audio) is on which COM port."""
    try:
        with serial.Serial(device, BAUD_RATE, timeout=1) as ser:
            end = time.time() + seconds
            buf = ""
            while time.time() < end:
                raw = ser.readline()
                if raw:
                    buf += raw.decode("utf-8", errors="replace")
                if "score=" in buf or "temp=" in buf:
                    break
            return buf
    except serial.SerialException as e:
        return f"<error: {e}>"


def find_kitprog3_port() -> str:
    ports = kitprog3_ports()
    if not ports:
        raise SystemExit(
            "No KitProg3 USB-UART port found. Is the CY8CPROTO-062-4343W plugged "
            "in? Pass --port COMx to specify it manually."
        )
    if len(ports) == 1:
        return ports[0]

    # Multiple KitProg3 boards connected (e.g. audio + thermal at once) -
    # peek at each to find the one printing thermal-firmware-shaped lines.
    print(f"  multiple KitProg3 ports found ({', '.join(ports)}) - probing each...")
    for device in ports:
        sample = peek_port(device)
        if "temp=" in sample:
            print(f"  {device} looks like the thermal board (saw 'temp=')")
            return device
        print(f"  {device} does not look like the thermal board, skipping")

    raise SystemExit(
        f"Could not identify which of {ports} is the thermal board (CY8CPROTO-062-4343W). "
        "Pass --port COMx explicitly."
    )


def post_reading(session: requests.Session, token: str, temp_c: float, flag: str):
    payload = {
        "channel": "temperature",
        "value": temp_c,
        "flag": "abnormal" if flag == "ANOMALY" else "normal",
        "threshold": TEMP_THRESHOLD_C,
        "unit": "C",
    }
    try:
        resp = session.post(
            DASHBOARD_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code != 200:
            print(f"  ! ingest failed: HTTP {resp.status_code} {resp.text[:200]}")
    except requests.RequestException as e:
        print(f"  ! ingest request error: {e}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="COM port (auto-detected if omitted)")
    args = parser.parse_args()

    token = find_ingest_token()
    port_name = args.port or find_kitprog3_port()

    print(f"thermal_bridge: reading {port_name} @ {BAUD_RATE}, forwarding to {DASHBOARD_URL}")

    session = requests.Session()

    while True:
        try:
            with serial.Serial(port_name, BAUD_RATE, timeout=2) as ser:
                print(f"  connected to {port_name}")
                while True:
                    raw = ser.readline()
                    if not raw:
                        continue
                    try:
                        line = raw.decode("utf-8", errors="replace").strip()
                    except UnicodeDecodeError:
                        continue

                    match = LINE_RE.search(line)
                    if not match:
                        continue

                    temp_c = float(match.group("temp"))
                    flag = match.group("flag")
                    post_reading(session, token, temp_c, flag)
                    print(f"  temp={temp_c:.2f}C flag={flag}")
        except serial.SerialException as e:
            print(f"  ! serial error ({e}) - retrying in 5s")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nstopped")
            sys.exit(0)


if __name__ == "__main__":
    main()
