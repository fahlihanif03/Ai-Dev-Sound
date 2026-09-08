"""
sound_bridge.py

Bridges the CY8CKIT-062S2-AI's live fan-anomaly-detector-fw UART output to
the deployed dashboard (web-dashboard/), so the Predictive Maintenance
page's sound card shows real readings instead of the simulator.

Reads lines like:
    score=3.3367 threshold=0.9324 ANOMALY
    score=0.6202 threshold=0.9324 normal
(see ../fan-anomaly-detector-fw/main.cpp's printf in the main loop - this
format must stay in sync with that if the firmware's print format ever
changes) and POSTs each reading to the dashboard's /api/ingest endpoint.

Usage:
    python sound_bridge.py                  # auto-detects the KitProg3 COM port
    python sound_bridge.py --port COM6      # or specify it explicitly
    python sound_bridge.py --list-kitprog3  # list all KitProg3 ports found,
                                             # with a peek at what each prints -
                                             # use this when two boards (audio +
                                             # thermal) are connected at once

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

LINE_RE = re.compile(
    r"score=(?P<score>[-\d.]+)\s+threshold=(?P<threshold>[-\d.]+)\s+(?P<flag>ANOMALY|normal)"
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
    which physical board (audio vs thermal) is on which COM port."""
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


def find_this_boards_port() -> str:
    ports = kitprog3_ports()
    if not ports:
        raise SystemExit(
            "No KitProg3 USB-UART port found. Is the CY8CKIT-062S2-AI plugged "
            "in? Pass --port COMx to specify it manually, or run with "
            "--list-kitprog3 to see what's connected."
        )
    if len(ports) == 1:
        return ports[0]

    # Multiple KitProg3 boards connected (e.g. audio + thermal at once) -
    # peek at each to find the one printing sound-firmware-shaped lines.
    print(f"  multiple KitProg3 ports found ({', '.join(ports)}) - probing each...")
    for device in ports:
        sample = peek_port(device)
        if "score=" in sample:
            print(f"  {device} looks like the audio board (saw 'score=')")
            return device
        print(f"  {device} does not look like the audio board, skipping")

    raise SystemExit(
        f"Could not identify which of {ports} is the audio board (CY8CKIT-062S2-AI). "
        "Pass --port COMx explicitly."
    )


def post_reading(session: requests.Session, token: str, score: float, threshold: float, flag: str):
    payload = {
        "channel": "sound",
        "value": score,
        "flag": "abnormal" if flag == "ANOMALY" else "normal",
        "threshold": threshold,
        "unit": "",
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
    parser.add_argument("--list-kitprog3", action="store_true", help="List KitProg3 ports and what each prints, then exit")
    args = parser.parse_args()

    if args.list_kitprog3:
        for device in kitprog3_ports():
            print(f"{device}:")
            print("  " + peek_port(device).replace("\n", "\n  "))
        return

    token = find_ingest_token()
    port_name = args.port or find_this_boards_port()

    print(f"sound_bridge: reading {port_name} @ {BAUD_RATE}, forwarding to {DASHBOARD_URL}")

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

                    score = float(match.group("score"))
                    threshold = float(match.group("threshold"))
                    flag = match.group("flag")
                    post_reading(session, token, score, threshold, flag)
                    print(f"  score={score:.4f} flag={flag}")
        except serial.SerialException as e:
            print(f"  ! serial error ({e}) - retrying in 5s")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nstopped")
            sys.exit(0)


if __name__ == "__main__":
    main()
