import asyncio
import os
import requests
import socket
from datetime import datetime
from dotenv import load_dotenv

# ---------------------- LOAD ENV ----------------------
load_dotenv()  # load variables from .env file if present

INTERNET_SOCKET_TIMEOUT = 2.0      # tolerate ~1–2 s RTT
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5004")
API_URL = f"{BASE_URL}/api/table/update"
# API_URL = os.getenv("API_URL", "http://127.0.0.1:5004/api/table/update")
PAYLOAD_DIR = os.getenv("FAILED_DIR", r"./payload_edit")
# ------------------------------------------------------


# def check_internet():
#     """Check internet connectivity, with fallback for China (ping Baidu)."""
#     test_hosts = ["8.8.8.8", "1.1.1.1", "www.baidu.com"]
#     for host in test_hosts:
#         try:
#             socket.setdefaulttimeout(3)
#             socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 80))
#             print("🌍 Internet OK")
#             return True
#         except Exception:
#             continue
#     print("❌ No Internet")
#     return False

def check_internet(timeout=INTERNET_SOCKET_TIMEOUT):
    targets = [
       ("1.1.1.1", 53),          # Cloudflare DNS (may be blocked in China)
       ("114.114.114.114", 53),  # China DNS (China-friendly)
       ("8.8.8.8", 53),          # Google DNS (may be blocked)
       ("223.5.5.5", 53)         # Alibaba DNS (China-friendly)
    ]
    for host, port in targets:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue

    return False

async def process_files():
    """Continuously retry NDCTELE JSON files in order of timestamp when network is up."""
    while True:
        try:
            # Check internet only
            if not check_internet():
                print(f"[{datetime.now().isoformat()}] ⚠️ Internet not ready → skipping API calls")
                await asyncio.sleep(10)
                continue

            # Collect all files still present
            files = [
                f for f in os.listdir(PAYLOAD_DIR)
                if f.startswith("NDCTELE_") and f.endswith(".json")
            ]

            # Sort strictly by timestamp in filename
            files.sort(key=lambda x: datetime.strptime(x.split("_")[1].split(".")[0], "%Y%m%d%H%M%S"))

            for file in files:
                filepath = os.path.join(PAYLOAD_DIR, file)

                # Extract timestamp → CreatedOn
                timestamp_str = file.split("_")[1].split(".")[0]
                created_on = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S").isoformat()
                modified_on = datetime.now().replace(microsecond=0).isoformat()

                # Build payload
                api_payload = {
                    "CreatedOn": created_on,
                    "TransmissionStatus": "Processed",
                    "ModifiedOn": modified_on,
                }

                print(f"[{datetime.now().isoformat()}] Retrying {file} → {api_payload}")

                # Call API
                try:
                    response = requests.put(API_URL, json=api_payload, timeout=10)

                    if response.status_code in (200, 201):
                        print(f"📡 API updated for {file}")
                        os.remove(filepath)  # delete file after success
                        print(f"🗑️ Deleted {file}")
                    else:
                        print(f"⚠️ API error {response.status_code}: {response.text}")
                except Exception as api_err:
                    print(f"❌ Failed API call for {file}: {api_err}")

        except Exception as loop_err:
            print(f"🔥 Error in main loop: {loop_err}")

        await asyncio.sleep(10)  # retry every 10 seconds


if __name__ == "__main__":
    try:
        asyncio.run(process_files())
    except KeyboardInterrupt:
        print("🚪 Exiting gracefully...")
