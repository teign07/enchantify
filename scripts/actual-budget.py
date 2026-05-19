#!/usr/bin/env python3
"""Local Actual Budget server wrapper for Enchantify.

The npm install and budget data live outside the workspace so OpenClaw does not
load dependency trees into context.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen


INSTALL_DIR = Path("/Users/bj/.openclaw/actual-budget-server")
DATA_DIR = Path("/Users/bj/.openclaw/actual-budget-data")
BIN = INSTALL_DIR / "node_modules" / ".bin" / "actual-server"
CONFIG = DATA_DIR / "config.json"
PID = DATA_DIR / "actual-server.pid"
LOG = DATA_DIR / "actual-server.log"
HOST = "127.0.0.1"
PORT = 5006
URL = f"http://{HOST}:{PORT}"


def ensure_config() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG.exists():
        CONFIG.write_text(json.dumps({
            "port": PORT,
            "hostname": HOST,
            "dataDir": str(DATA_DIR),
            "serverFiles": str(DATA_DIR / "server-files"),
            "userFiles": str(DATA_DIR / "user-files"),
            "loginMethod": "password",
        }, indent=2) + "\n", encoding="utf-8")


def read_pid() -> int | None:
    try:
        pid = int(PID.read_text().strip())
    except Exception:
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


def health() -> bool:
    try:
        with urlopen(URL, timeout=2) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def status() -> int:
    ensure_config()
    pid = read_pid()
    print("ACTUAL BUDGET SERVER")
    print(f"Install: {INSTALL_DIR}")
    print(f"Data: {DATA_DIR}")
    print(f"Config: {CONFIG}")
    print(f"URL: {URL}")
    print(f"PID: {pid or 'not running'}")
    print(f"Health: {'reachable' if health() else 'not reachable'}")
    return 0


def start() -> int:
    ensure_config()
    if not BIN.exists():
        raise SystemExit(f"Actual server binary not found: {BIN}")
    pid = read_pid()
    if pid:
        print(f"Actual Budget already running: {URL} (pid {pid})")
        return 0
    log_f = LOG.open("ab")
    proc = subprocess.Popen(
        [str(BIN), "--config", str(CONFIG)],
        cwd=str(DATA_DIR),
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    PID.write_text(str(proc.pid) + "\n", encoding="utf-8")
    for _ in range(20):
        if health():
            print(f"Actual Budget running: {URL} (pid {proc.pid})")
            return 0
        time.sleep(0.5)
    print(f"Actual Budget started but health check is not ready yet: {URL} (pid {proc.pid})")
    print(f"Log: {LOG}")
    return 0


def stop() -> int:
    pid = read_pid()
    if not pid:
        try:
            PID.unlink()
        except FileNotFoundError:
            pass
        print("Actual Budget is not running.")
        return 0
    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        time.sleep(0.25)
        if not read_pid():
            try:
                PID.unlink()
            except FileNotFoundError:
                pass
            print("Actual Budget stopped.")
            return 0
    print(f"Actual Budget did not stop cleanly; pid still alive: {pid}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage local Actual Budget server")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "init":
        ensure_config()
        return status()
    if args.command == "start":
        return start()
    if args.command == "stop":
        return stop()
    if args.command == "status":
        return status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
