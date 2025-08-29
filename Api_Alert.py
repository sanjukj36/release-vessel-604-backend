#!/usr/bin/env python3
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import subprocess, socket, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

# ========= Tunables (safe for high latency links) =========
PING_COUNT = 2                     # pings per sweep
PING_TIMEOUT_MS = 600              # per-echo timeout (Windows)
SUBPROC_HARD_TIMEOUT = 2.5         # cap per ping subprocess (seconds)

RAISE_AFTER_FAILS = 3              # N consecutive failed checks to raise
CLEAR_AFTER_SUCCESSES = 2          # M consecutive successes to clear
MIN_HOLD_SECONDS = 15              # keep alert raised at least this long

SWEEP_PERIOD_SEC = 1.0             # sweep frequency
INTERNET_CHECK_PERIOD_SEC = 5.0    # internet check frequency
INTERNET_SOCKET_TIMEOUT = 2.0      # tolerate ~1–2 s RTT

HOSTS = [
    {"name": "MDC",      "ip": "172.168.0.80"},
    {"name": "PRAXIS", "ip": "192.168.1.101"},
]

# ========= State (protect with lock) =========
state_lock = threading.Lock()
host_state = {
    h["ip"]: {
        "name": h["name"],
        "consec_fails": 0,
        "consec_oks": 0,
        "alert_active": False,
        "last_change": None,
        "last_ping_ok": None,
        "last_result_ts": None,
    } for h in HOSTS
}
internet_state = {"ok": True, "last_checked": None}
alerts_cache = []
alerts_cache_ts = 0.0

# ========= Helpers =========
def now_str(dt=None):
    return (dt or datetime.now()).strftime("%H:%M:%S %d-%m-%Y")

def check_internet_fast(timeout=INTERNET_SOCKET_TIMEOUT):
    """
    Quick connectivity check using TCP connects to common HTTPS IPs.
    Uses only IPs (no DNS). Returns True on first success.
    Falls back to recent ping results if TCP is filtered.
    """
    targets = [
        ("1.1.1.1", 443),   # Cloudflare
        ("8.8.8.8", 443),   # Google
        ("8.8.4.4", 443),   # Google secondary
    ]
    for host, port in targets:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue

    # Fallback: if any host pinged OK recently, assume basic internet
    try:
        return any(s.get("last_ping_ok") for s in host_state.values())
    except Exception:
        return False

def ping_ok(ip):
    """
    Windows ping. Returns True if majority of replies succeed.
    """
    cmd = ["ping", "-n", str(PING_COUNT), "-w", str(PING_TIMEOUT_MS), ip]
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=SUBPROC_HARD_TIMEOUT
        )
        out = res.stdout + res.stderr
        replies = sum(1 for line in out.splitlines() if "Reply from" in line)
        return replies >= (PING_COUNT // 2 + 1)
    except Exception:
        return False

def apply_hysteresis(ip, is_up, ts):
    s = host_state[ip]
    s["last_result_ts"] = ts
    if is_up:
        s["consec_oks"] += 1
        s["consec_fails"] = 0
        s["last_ping_ok"] = True
        if s["alert_active"]:
            held_long_enough = (
                s["last_change"] is None
                or (ts - s["last_change"]).total_seconds() >= MIN_HOLD_SECONDS
            )
            if s["consec_oks"] >= CLEAR_AFTER_SUCCESSES and held_long_enough:
                s["alert_active"] = False
                s["last_change"] = ts
    else:
        s["consec_fails"] += 1
        s["consec_oks"] = 0
        s["last_ping_ok"] = False
        if not s["alert_active"] and s["consec_fails"] >= RAISE_AFTER_FAILS:
            s["alert_active"] = True
            s["last_change"] = ts

def recompute_alerts(ts):
    alerts = []
    if not internet_state["ok"]:
        alerts.append({"label": "No internet connection available", "time": now_str(ts)})
    for ip, s in host_state.items():
        if s["alert_active"]:
            alerts.append({"label": f"{s['name']} Disconnected.", "time": now_str(ts)})
    return alerts

# ========= Background monitor =========
def monitor_loop(stop_event: threading.Event):
    last_net_check = 0.0
    with ThreadPoolExecutor(max_workers=max(4, len(HOSTS))) as pool:
        while not stop_event.is_set():
            ts = datetime.now()

            # Internet check (less frequent)
            if (time.time() - last_net_check) >= INTERNET_CHECK_PERIOD_SEC:
                ok = check_internet_fast()
                with state_lock:
                    internet_state["ok"] = ok
                    internet_state["last_checked"] = ts
                last_net_check = time.time()

            # Parallel pings
            futures = {pool.submit(ping_ok, h["ip"]): h["ip"] for h in HOSTS}
            results = {}
            for fut in as_completed(futures):
                ip = futures[fut]
                try:
                    results[ip] = fut.result()
                except Exception:
                    results[ip] = False

            # Update state + alerts
            with state_lock:
                for ip, is_up in results.items():
                    apply_hysteresis(ip, is_up, ts)
                global alerts_cache, alerts_cache_ts
                alerts_cache = recompute_alerts(ts)
                alerts_cache_ts = time.time()

            stop_event.wait(SWEEP_PERIOD_SEC)

# Start background thread
stop_flag = threading.Event()
threading.Thread(target=monitor_loop, args=(stop_flag,), daemon=True).start()

# ========= API =========
@app.route('/alerts', methods=['GET'])
def get_alerts():
    with state_lock:
        payload = {"alerts": list(alerts_cache), "success": True}
    return jsonify(payload), 200

@app.route('/status', methods=['GET'])
def get_status():
    with state_lock:
        hosts = [
            {
                "name": s["name"],
                "ip": ip,
                "up": bool(s["last_ping_ok"]),
                "alert_active": bool(s["alert_active"]),
                "last_change": now_str(s["last_change"]) if s["last_change"] else None,
                "last_result_ts": now_str(s["last_result_ts"]) if s["last_result_ts"] else None,
            }
            for ip, s in host_state.items()
        ]
        payload = {
            "internet_ok": internet_state["ok"],
            "internet_last_checked": now_str(internet_state["last_checked"]) if internet_state["last_checked"] else None,
            "hosts": hosts,
            "success": True,
        }
    return jsonify(payload), 200

if __name__ == '__main__':
    # Bind to your LAN IP (as you had). Change if needed.
    app.run(host='172.168.0.81', port=5001, debug=True, threaded=True, use_reloader=False)
