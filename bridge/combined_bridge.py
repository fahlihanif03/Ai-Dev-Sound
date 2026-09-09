"""
combined_bridge.py

Bridges the CY8CPROTO-062-4343W's combined predictive-maintenance-fw UART
output (sound AND temperature, both fused on this one board - see
../ModusToolbox-Projects/thermal-monitor-fw/main.cpp) to the deployed
dashboard's /api/ingest endpoint. Replaces running thermal_bridge.py and
sound_bridge.py separately against the same board - both line patterns
appear on the same serial stream, so this just dispatches each line to
whichever channel its shape matches.

Usage:
    python combined_bridge.py                  # local dev (wrangler dev on :8787) by default
    python combined_bridge.py --target prod     # the deployed Cloudflare Worker
    python combined_bridge.py --url http://localhost:8787/api/ingest   # explicit override
    python combined_bridge.py --port COM5       # COM port override, any target

Local dev needs `npm run backend:dev` running in web-dashboard/ first (no
INGEST_TOKEN required there - local Durable Objects aren't behind the
deployed Worker's auth check). --target prod requires INGEST_TOKEN, either
as an environment variable or read from ../web-dashboard/ingest-token.local.

NOTE (2026-09-08): the deployed instance hit the Durable Object free tier's
daily SQL-row-read quota after hours of continuous ticking (see
backend/dashboard-do.ts's fix + comment) - that's why local is the default
here for now. Switch back to --target prod once the quota window resets.
"""
import argparse
import os
import re
import sys
import time

import requests
import serial
import serial.tools.list_ports

LOCAL_URL = "http://localhost:8787/api/ingest"
PROD_URL = "https://demo-kit-dashboard.anepfadhli5.workers.dev/api/ingest"
BAUD_RATE = 115200

# Must match predictive-maintenance-fw/main.cpp's printf formats exactly.
TEMP_RE = re.compile(r"temp=(?P<temp>[-\d.]+)C\s+rate=(?P<rate>[-+\d.]+)C/s\s+(?P<flag>ANOMALY|normal)")
SOUND_RE = re.compile(r"score=(?P<score>[-\d.]+)\s+threshold=(?P<threshold>[-\d.]+)\s+(?P<flag>ANOMALY|normal)")

TEMP_THRESHOLD_C = 50.0  # matches TEMP_THRESHOLD_C in main.cpp (not printed by the firmware)


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
        "or make sure web-dashboard/ingest-token.local exists."
    )


def find_kitprog3_port() -> str:
    ports = [p.device for p in serial.tools.list_ports.comports() if "KitProg3" in (p.description or "")]
    if not ports:
        raise SystemExit("No KitProg3 USB-UART port found. Pass --port COMx to specify it manually.")
    if len(ports) > 1:
        print(f"  multiple KitProg3 ports found ({', '.join(ports)}) - using the first: {ports[0]}")
    return ports[0]


def post_reading(session: requests.Session, url: str, token: str | None, payload: dict):
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = session.post(url, json=payload, headers=headers, timeout=5)
        if resp.status_code != 200:
            print(f"  ! ingest failed: HTTP {resp.status_code} {resp.text[:200]}")
    except requests.RequestException as e:
        print(f"  ! ingest request error: {e}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="COM port (auto-detected if omitted)")
    parser.add_argument("--target", choices=["local", "prod"], default="local", help="local dev server (default) or the deployed Worker")
    parser.add_argument("--url", help="explicit ingest URL override, takes precedence over --target")
    args = parser.parse_args()

    url = args.url or (PROD_URL if args.target == "prod" else LOCAL_URL)
    token = find_ingest_token() if (args.target == "prod" or args.url) else os.environ.get("INGEST_TOKEN")
    port_name = args.port or find_kitprog3_port()

    print(f"combined_bridge: reading {port_name} @ {BAUD_RATE}, forwarding to {url}")

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

                    temp_match = TEMP_RE.search(line)
                    if temp_match:
                        temp_c = float(temp_match.group("temp"))
                        flag = temp_match.group("flag")
                        post_reading(session, url, token, {
                            "channel": "temperature", "value": temp_c,
                            "flag": "abnormal" if flag == "ANOMALY" else "normal",
                            "threshold": TEMP_THRESHOLD_C, "unit": "C",
                        })
                        print(f"  temp={temp_c:.2f}C flag={flag}")
                        continue

                    sound_match = SOUND_RE.search(line)
                    if sound_match:
                        score = float(sound_match.group("score"))
                        threshold = float(sound_match.group("threshold"))
                        flag = sound_match.group("flag")
                        post_reading(session, url, token, {
                            "channel": "sound", "value": score,
                            "flag": "abnormal" if flag == "ANOMALY" else "normal",
                            "threshold": threshold, "unit": "",
                        })
                        print(f"  score={score:.4f} flag={flag}")
        except serial.SerialException as e:
            print(f"  ! serial error ({e}) - retrying in 5s")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nstopped")
            sys.exit(0)


if __name__ == "__main__":
    main()
