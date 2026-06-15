"""
Master Launcher - Runs Bee Bot + Snap Bot + Sansa Bot on one instance
"""
import subprocess
import sys
import time
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

BOTS = {
    "Bee Bot":   {"script": Path("bee_bot/app.py"),        "cwd": "bee_bot"},
    "Snap Bot":  {"script": Path("snap_bot/snap_bot.py"),  "cwd": "snap_bot"},
    "Sansa Bot": {"script": Path("sansa_bot/bot.py"),      "cwd": "sansa_bot"},
}

processes = {}

def start_bot(name, cfg):
    if not cfg["script"].exists():
        log.error(f"❌ {name}: {cfg['script']} not found!")
        return None
    log.info(f"🚀 {name} starting...")
    proc = subprocess.Popen(
        [sys.executable, str(cfg["script"].resolve())],
        cwd=cfg["cwd"],
    )
    log.info(f"✅ {name} started with PID {proc.pid}")
    return proc

def main():
    log.info("=" * 50)
    log.info("🤖 Multi-Bot Launcher Starting")
    log.info("=" * 50)

    for name, cfg in BOTS.items():
        processes[name] = start_bot(name, cfg)

    while True:
        time.sleep(30)
        for name, cfg in BOTS.items():
            proc = processes.get(name)
            if proc is None or proc.poll() is not None:
                exit_code = proc.returncode if proc else "N/A"
                log.warning(f"⚠️ {name} crashed (exit: {exit_code}), restarting...")
                time.sleep(5)
                processes[name] = start_bot(name, cfg)

if __name__ == "__main__":
    main()
