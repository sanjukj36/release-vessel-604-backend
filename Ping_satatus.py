from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import subprocess
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)  # Allow all domains by default

HOSTS = [
    {"name": "MDC",    "ip": "172.168.0.80"},
    {"name": "PRAXIX", "ip": "192.168.1.101"},
]

# ---- Tunables ----
PING_COUNT = 1                 # one echo is enough for liveness
PING_TIMEOUT_MS = 600          # per-echo timeout (Windows) in milliseconds
SUBPROC_HARD_TIMEOUT = 2.0     # absolute cap per ping subprocess (seconds)
MAX_WORKERS = min(8, max(1, len(HOSTS)))  # parallelism for pings

def _build_ping_cmd(ip: str):
    """Build a cross-platform ping command with explicit timeouts."""
    system = platform.system().lower()
    if "windows" in system:
        # -n (count), -w (timeout per reply, ms)
        return ["ping", "-n", str(PING_COUNT), "-w", str(PING_TIMEOUT_MS), ip]
    else:
        # -c (count), -W (timeout per reply, seconds)
        per_reply_sec = max(1, int(round(PING_TIMEOUT_MS / 1000.0)))
        return ["ping", "-c", str(PING_COUNT), "-W", str(per_reply_sec), ip]

def ping_host(ip: str) -> bool:
    """Ping a host and return True if reachable (exit code 0)."""
    try:
        result = subprocess.run(
            _build_ping_cmd(ip),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=SUBPROC_HARD_TIMEOUT
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        # If ping is missing or any other OS error occurs, treat as down
        return False

@app.route('/ping', methods=['GET'])
def ping_real():
    now_str = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    results = []
    alerts = []

    # Run pings in parallel to keep endpoint responsive
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(ping_host, h["ip"]): h for h in HOSTS}
        for future in as_completed(future_map):
            host = future_map[future]
            status = bool(future.result())
            results.append({
                "host_name": host["name"],
                "host": host["ip"],
                "status": status
            })
            if not status:
                alerts.append({
                    "label": f"{host['name']} Disconnected.",
                    "time": now_str
                })

    return jsonify({
        "data": results,
        "alerts": alerts,
        "success": True
    }), 200

if __name__ == '__main__':
    # 0.0.0.0 listens on all interfaces; change to 127.0.0.1 for local only.
    app.run(host='172.168.0.81', port=5002, debug=False)
