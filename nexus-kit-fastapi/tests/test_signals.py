import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PROBE = Path(__file__).with_name("_signal_probe.py")


def test_termination_signal_triggers_full_graceful_teardown():
    """Regression: uvicorn's stock capture_signals restores default handlers
    and re-raises the signal after its shutdown — killing the process before
    ServiceRunner stops the remaining services. The bridge owns signals now."""
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    env = os.environ | {"PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(
        [sys.executable, str(PROBE)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        env=env,
        creationflags=creationflags,
    )
    collected: list[str] = []
    try:
        deadline = time.time() + 30
        ready = False
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            collected.append(line)
            if line.startswith("READY"):
                ready = True
                break
        assert ready, f"probe never became ready:\n{''.join(collected)}"

        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # SIGBREAK in the child
        else:
            proc.send_signal(signal.SIGTERM)

        remainder = proc.communicate(timeout=30)[0]
        output = "".join(collected) + (remainder or "")
        assert proc.returncode == 0, f"exit={proc.returncode}\n{output}"
        assert "MARKER-STOPPED" in output, output  # teardown of OTHER services ran
        assert "CLEAN-EXIT" in output, output      # main() completed normally
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=10)
