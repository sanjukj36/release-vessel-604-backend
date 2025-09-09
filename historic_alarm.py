#!/usr/bin/env python3
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import subprocess, socket, threading, time, sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

# ========= Tunables =========
PING_COUNT = 2
PING_TIMEOUT_MS = 600
SUBPROC_HARD_TIMEOUT = 2.5

RAISE_AFTER_FAILS = 3
CLEAR_AFTER_SUCCESSES = 2
MIN_HOLD_SECONDS = 15

SWEEP_PERIOD_SEC = 1.0
INTERNET_CHECK_PERIOD_SEC = 5.0
INTERNET_SOCKET_TIMEOUT = 2.0

HOSTS = [
    {"name": "MDC", "ip": "172.168.0.80"},
    {"name": "PRAXIS", "ip": "192.168.1.101"},
]

# ========= DB Setup =========
DB_NAME = "mydatabase.db"
TABLE_NAME = "historical"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Label TEXT,
            Time TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_alarm(label, time):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO {TABLE_NAME} (Label, Time) VALUES (?, ?)", (label, time))
    conn.commit()
    conn.close()

# ========= State =========
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
    targets = [
       ("1.1.1.1", 53),
       ("114.114.114.114", 53),
       ("8.8.8.8", 53),
       ("223.5.5.5", 53)
    ]
    for host, port in targets:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False

def ping_ok(ip):
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
        label = "No internet connection available"
        time_str = now_str(ts)
        alerts.append({"label": label, "time": time_str})
        insert_alarm(label, time_str)

    for ip, s in host_state.items():
        if s["alert_active"]:
            label = f"{s['name']} Disconnected."
            time_str = now_str(ts)
            alerts.append({"label": label, "time": time_str})
            insert_alarm(label, time_str)

    return alerts

# ========= Background Monitor =========
def monitor_loop(stop_event: threading.Event):
    last_net_check = 0.0
    with ThreadPoolExecutor(max_workers=max(4, len(HOSTS))) as pool:
        while not stop_event.is_set():
            ts = datetime.now()

            if (time.time() - last_net_check) >= INTERNET_CHECK_PERIOD_SEC:
                ok = check_internet_fast()
                with state_lock:
                    internet_state["ok"] = ok
                    internet_state["last_checked"] = ts
                last_net_check = time.time()

            futures = {pool.submit(ping_ok, h["ip"]): h["ip"] for h in HOSTS}
            results = {}
            for fut in as_completed(futures):
                ip = futures[fut]
                try:
                    results[ip] = fut.result()
                except Exception:
                    results[ip] = False

            with state_lock:
                for ip, is_up in results.items():
                    apply_hysteresis(ip, is_up, ts)
                global alerts_cache, alerts_cache_ts
                alerts_cache = recompute_alerts(ts)
                alerts_cache_ts = time.time()

            stop_event.wait(SWEEP_PERIOD_SEC)

stop_flag = threading.Event()
threading.Thread(target=monitor_loop, args=(stop_flag,), daemon=True).start()

# ========= API =========

@app.route('/historical', methods=['GET'])
def get_historical():
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # cursor.execute(f"SELECT Label, Time FROM {TABLE_NAME} ORDER BY ID ASC")
    cursor.execute(f"SELECT Label, Time FROM {TABLE_NAME} ORDER BY ID DESC LIMIT 20")

    rows = cursor.fetchall()
    conn.close()

    alerts = [{"label": row[0], "time": row[1]} for row in rows]
    return jsonify({"alerts": alerts, "success": True}), 200

if __name__ == '__main__':
    init_db()
    # app.run(host='192.168.18.143', port=5007, debug=True, threaded=True, use_reloader=False)
    app.run(host='172.168.0.81', port=5007, debug=True, threaded=True, use_reloader=False)
