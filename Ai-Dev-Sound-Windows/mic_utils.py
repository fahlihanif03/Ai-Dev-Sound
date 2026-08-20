"""
mic_utils.py

Checks for a usable microphone before any live_monitor.py-family script
starts its capture loop, and fails with an actionable message instead of
a raw PortAudioError traceback three frames deep in a recording call.
"""
import sounddevice as sd


def require_input_device(device=None):
    """Raises SystemExit with a clear explanation if no usable input
    device is available - call this once at startup, before entering
    the capture loop. `device` is the --device index/name the user
    passed, or None for "use the system default"."""
    devices = sd.query_devices()
    input_devices = [d for d in devices if d["max_input_channels"] > 0]

    if not input_devices:
        raise SystemExit(
            "No microphone found. Every audio device this Mac can see has 0 input "
            "channels (run `python -m sounddevice` to check yourself) - Mac minis "
            "have no built-in mic, so you'll need to plug one in (USB mic, headset, "
            "webcam, or audio interface) and select it in System Settings > Sound > "
            "Input, then try again."
        )

    if device is not None:
        info = sd.query_devices(device)
        if info["max_input_channels"] == 0:
            raise SystemExit(
                f"Device {device!r} ({info['name']}) has no input channels - it's "
                f"output-only. Run `python -m sounddevice` to see which devices have "
                f"input channels, then pass one of those with --device."
            )
        return

    try:
        default_input = sd.query_devices(kind="input")
    except Exception:
        raise SystemExit(
            "No default input device is set for this Mac, even though some input "
            "devices exist. Run `python -m sounddevice`, then pass the one you want "
            "explicitly with --device <index>."
        )
    if default_input is None or default_input["max_input_channels"] == 0:
        raise SystemExit(
            "The default input device has no input channels. Run `python -m "
            "sounddevice` and pass a working one explicitly with --device <index>."
        )
