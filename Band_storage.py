from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import uuid
import subprocess
import socket
import random


app = Flask(__name__)
CORS(app)  # Allow all domains by default


# Multiple test hosts (mix of China-friendly and global)
TEST_HOSTS = [
    ("1.1.1.1", 53),          # Cloudflare DNS (may be blocked in China)
    ("114.114.114.114", 53),  # China DNS (China-friendly)
    ("8.8.8.8", 53),          # Google DNS (may be blocked)
    ("223.5.5.5", 53)         # Alibaba DNS (China-friendly)
]

def is_connected(timeout: float = 2.0) -> bool:
    for host, port in TEST_HOSTS:
        try:
            socket.create_connection((host, port), timeout=timeout)
            return True  # If any host works, we’re online
        except OSError:
            continue
    return False

@app.route('/bandwidth', methods=['GET'])
def get_bandwidth():
    range_value = 100

    if not is_connected():
        speed_value = 0.0
    else:
        # Generate a random float between 0.5 and 1.5 Mbps
        speed_value = round(random.uniform(0.5, 1.5), 2)

    response = {
        "data": {
            "range": range_value,
            "speed": speed_value,
            "unit": "Mbps"
        },
        "success": True
    }
    return jsonify(response), 200



@app.route('/storage', methods=['GET'])
def storage_dummy():
    dummy_data = {
        "data": {
            "mdc": {
                "free_storage": 236,
                "total_storage": 256,
                "used_storage": 20,
                "unit": "Gb"
            },
            "transbox": {
                "free_storage": 153,
                "total_storage": 256,
                "used_storage": 103,
                "unit": "Gb"
            }
        },
        "success": True
    }
    return jsonify(dummy_data), 200


if __name__ == '__main__':
    app.run(host='172.168.0.81', port=5002, debug=True)
