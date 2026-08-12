"""
Runs plex_debrid in service mode and writes its combined output
(stdout + stderr) to console.log, rotating the log once it exceeds
the configured size (ui.ui_settings.log_size, in MB) so it cannot
grow without bound, even during a long-running session.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "console.log")
BACKUP = LOG + ".1"


def log_limit():
    try:
        from ui import ui_settings
        return max(int(float(ui_settings.log_size)) * 1024 * 1024, 1024)
    except Exception:
        return 10 * 1024 * 1024


def rotate():
    # keep only the current log plus one backup
    try:
        if os.path.exists(BACKUP):
            os.remove(BACKUP)
        if os.path.exists(LOG):
            os.replace(LOG, BACKUP)
    except Exception:
        pass


def pump(stream):
    limit = log_limit()
    handle = open(LOG, "ab")
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            handle.write(chunk)
            handle.flush()
            if handle.tell() >= limit:
                handle.close()
                rotate()
                handle = open(LOG, "ab")
    finally:
        try:
            handle.close()
        except Exception:
            pass


def main():
    proc = subprocess.Popen(
        [sys.executable, "main.py", "-service"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    pump(proc.stdout)
    proc.wait()
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
