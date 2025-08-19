# import asyncio
# import os
# import requests
# import subprocess
# import socket
# from datetime import datetime

# # ---------------------- CONFIG ----------------------
# HOSTS = [
#     {"name": "MDC", "ip": "192.168.18.99"},
#     {"name": "Tranxbox", "ip": "192.168.18.138"},
# ]

# API_URL = "http://192.168.18.143:5004/api/table/update"
# PAYLOAD_DIR = r"D:\development\React\for vessel\backend\payload_edit"
# # ----------------------------------------------------


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


# def ping_host(ip, name=None):
#     """Ping a host and return True if reachable, False otherwise."""
#     try:
#         output = subprocess.run(
#             ["ping", "-n", "2", ip] if os.name == "nt" else ["ping", "-c", "2", ip],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )
#         result = output.stdout.lower()

#         # Failure indicators
#         bad_keywords = ["unreachable", "timed out", "100% loss", "could not find host"]

#         if any(bad in result for bad in bad_keywords):
#             print(f"❌ {name or ip} unreachable")
#             return False

#         # Success indicators
#         if "reply from" in result or "bytes from" in result:
#             print(f"✅ {name or ip} reachable")
#             return True

#         print(f"❌ {name or ip} unknown ping result → treating as unreachable")
#         return False
#     except Exception as e:
#         print(f"🔥 Ping failed for {name or ip}: {e}")
#         return False

# # def ping_host(ip):
# #     """Ping a host and return True if reachable, False otherwise."""
# #     try:
# #         output = subprocess.run(
# #             ["ping", "-n", "1", ip] if os.name == "nt" else ["ping", "-c", "1", ip],
# #             stdout=subprocess.PIPE,
# #             stderr=subprocess.PIPE,
# #             text=True
# #         )
# #         result = output.stdout.lower()

# #         # Must succeed (returncode == 0) AND not contain 'unreachable' or 'timed out'
# #         if output.returncode == 0 and "unreachable" not in result and "timed out" not in result:
# #             return True
# #         return False
# #     except Exception:
# #         return False


# async def process_files():
#     """Continuously retry NDCTELE JSON files in order of timestamp when network is up."""
#     while True:
#         try:
#             # Check internet + all hosts
#             net_ok = check_internet()
#             hosts_ok = all(ping_host(h["ip"], h["name"]) for h in HOSTS)

#             if not (net_ok and hosts_ok):
#                 print(f"[{datetime.now().isoformat()}] ⚠️ Network/hosts not ready → skipping API calls")
#                 await asyncio.sleep(10)
#                 continue  # skip this loop until all connections are OK

#             # Collect all files still present
#             files = [
#                 f for f in os.listdir(PAYLOAD_DIR)
#                 if f.startswith("NDCTELE_") and f.endswith(".json")
#             ]

#             # Sort strictly by timestamp in filename
#             files.sort(key=lambda x: datetime.strptime(x.split("_")[1].split(".")[0], "%Y%m%d%H%M%S"))

#             for file in files:
#                 filepath = os.path.join(PAYLOAD_DIR, file)

#                 # Extract timestamp → CreatedOn
#                 timestamp_str = file.split("_")[1].split(".")[0]
#                 created_on = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S").isoformat()
#                 modified_on = datetime.now().replace(microsecond=0).isoformat()

#                 # Build payload
#                 api_payload = {
#                     "CreatedOn": created_on,
#                     "TransmissionStatus": "Processed",
#                     "ModifiedOn": modified_on,
#                 }

#                 print(f"[{datetime.now().isoformat()}] Retrying {file} → {api_payload}")

#                 # Call API
#                 try:
#                     response = requests.put(API_URL, json=api_payload, timeout=10)

#                     if response.status_code in (200, 201):
#                         print(f"📡 API updated for {file}")
#                         os.remove(filepath)  # delete file after success
#                         print(f"🗑️ Deleted {file}")
#                     else:
#                         print(f"⚠️ API error {response.status_code}: {response.text}")
#                 except Exception as api_err:
#                     print(f"❌ Failed API call for {file}: {api_err}")

#         except Exception as loop_err:
#             print(f"🔥 Error in main loop: {loop_err}")

#         await asyncio.sleep(10)  # retry every 10 seconds


# if __name__ == "__main__":
#     try:
#         asyncio.run(process_files())
#     except KeyboardInterrupt:
#         print("🚪 Exiting gracefully...")

import asyncio
import os
import requests
import socket
from datetime import datetime

# ---------------------- CONFIG ----------------------
API_URL = "http://192.168.18.143:5004/api/table/update"
PAYLOAD_DIR = r"D:\development\React\for vessel\backend\payload_edit"
# ----------------------------------------------------


def check_internet():
    """Check internet connectivity, with fallback for China (ping Baidu)."""
    test_hosts = ["8.8.8.8", "1.1.1.1", "www.baidu.com"]
    for host in test_hosts:
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 80))
            print("🌍 Internet OK")
            return True
        except Exception:
            continue
    print("❌ No Internet")
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

