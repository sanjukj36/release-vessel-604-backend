# # data-striming.py

# import asyncio
# import os
# import shutil
# import requests
# import subprocess
# import socket
# from datetime import datetime

# # ---------------------- CONFIG ----------------------
# HOSTS = [
#     {"name": "MDC", "ip": "192.168.18.99"},
#     {"name": "Tranxbox", "ip": "192.168.18.138"},
# ]

# API_URL = "http://192.168.18.143:5004/api/table/create"
# PAYLOAD_DIR = r"D:\development\React\for vessel\backend\payload"
# FAILED_DIR = r"D:\development\React\for vessel\backend\payload_edit"
# # ----------------------------------------------------


# def check_internet():
#     """Check internet connectivity, with fallback for China (ping Baidu)."""
#     test_hosts = ["8.8.8.8", "1.1.1.1", "www.baidu.com"]  # Google DNS, Cloudflare, Baidu
#     for host in test_hosts:
#         try:
#             socket.setdefaulttimeout(3)
#             socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 80))
#             return True
#         except Exception:
#             continue
#     return False


# # def ping_host(ip):
# #     """Ping a host and return True if reachable."""
# #     try:
# #         output = subprocess.run(
# #             ["ping", "-n", "1", ip] if os.name == "nt" else ["ping", "-c", "1", ip],
# #             stdout=subprocess.PIPE,
# #             stderr=subprocess.PIPE,
# #         )
# #         return output.returncode == 0
# #     except Exception:
# #         return False

# def ping_host(ip):
#     """Ping a host and return True if reachable, False otherwise."""
#     try:
#         output = subprocess.run(
#             ["ping", "-n", "1", ip] if os.name == "nt" else ["ping", "-c", "1", ip],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )
#         result = output.stdout.lower()

#         # Must succeed (returncode == 0) AND not contain 'unreachable' or 'timed out'
#         if output.returncode == 0 and "unreachable" not in result and "timed out" not in result:
#             return True
#         return False
#     except Exception:
#         return False



# async def process_files():
#     """Continuously process NDCTELE JSON files in order of timestamp."""
#     while True:
#         try:
#             net_ok = check_internet()
#             hosts_ok = all(ping_host(h["ip"]) for h in HOSTS)

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

#                 # Decide status
#                 transmission_status = "Processed" if (net_ok and hosts_ok) else "Not Processed"
#                 print(f"[{datetime.now().isoformat()}] File: {file} → {transmission_status}")

#                 # Build payload
#                 api_payload = {
#                     "CreatedOn": created_on,
#                     "FileName": file,
#                     "TransmissionStatus": transmission_status,
#                 }

#                 if transmission_status == "Processed":
#                     modified_on = datetime.now().replace(microsecond=0).isoformat()
#                     api_payload["ModifiedOn"] = modified_on

#                 # Call API
#                 try:
#                     response = requests.post(API_URL, json=api_payload, timeout=10)

#                     if response.status_code in (200, 201):  # ✅ accept 201 also
#                         print(f"📡 API updated for {file}")

#                         if transmission_status == "Processed":
#                             os.remove(filepath)  # delete file
#                             print(f"🗑️ Deleted {file}")
#                         else:
#                             os.makedirs(FAILED_DIR, exist_ok=True)
#                             shutil.move(filepath, os.path.join(FAILED_DIR, file))  # move file
#                             print(f"📂 Moved {file} → {FAILED_DIR}")
#                     else:
#                         print(f"⚠️ API error {response.status_code}: {response.text}")
#                 except Exception as api_err:
#                     print(f"❌ Failed API call for {file}: {api_err}")

#         except Exception as loop_err:
#             print(f"🔥 Error in main loop: {loop_err}")

#         await asyncio.sleep(5)  # small delay to continuously check new files


# if __name__ == "__main__":
#     try:
#         asyncio.run(process_files())
#     except KeyboardInterrupt:
#         print("🚪 Exiting gracefully...")


# data-striming.py

import asyncio
import os
import shutil
import requests
import socket
from datetime import datetime

# ---------------------- CONFIG ----------------------
API_URL = "http://192.168.18.143:5004/api/table/create"
PAYLOAD_DIR = r"D:\development\React\for vessel\backend\payload"
FAILED_DIR = r"D:\development\React\for vessel\backend\payload_edit"
# ----------------------------------------------------


def check_internet():
    """Check internet connectivity, with fallback for China (ping Baidu)."""
    test_hosts = ["8.8.8.8", "1.1.1.1", "www.baidu.com"]  # Google DNS, Cloudflare, Baidu
    for host in test_hosts:
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 80))
            return True
        except Exception:
            continue
    return False


async def process_files():
    """Continuously process NDCTELE JSON files in order of timestamp."""
    while True:
        try:
            net_ok = check_internet()

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

                # Decide status
                transmission_status = "Processed" if net_ok else "Not Processed"
                print(f"[{datetime.now().isoformat()}] File: {file} → {transmission_status}")

                # Build payload
                api_payload = {
                    "CreatedOn": created_on,
                    "FileName": file,
                    "TransmissionStatus": transmission_status,
                }

                if transmission_status == "Processed":
                    modified_on = datetime.now().replace(microsecond=0).isoformat()
                    api_payload["ModifiedOn"] = modified_on

                # Call API
                try:
                    response = requests.post(API_URL, json=api_payload, timeout=10)

                    if response.status_code in (200, 201):  # ✅ accept 201 also
                        print(f"📡 API updated for {file}")

                        if transmission_status == "Processed":
                            os.remove(filepath)  # delete file
                            print(f"🗑️ Deleted {file}")
                        else:
                            os.makedirs(FAILED_DIR, exist_ok=True)
                            shutil.move(filepath, os.path.join(FAILED_DIR, file))  # move file
                            print(f"📂 Moved {file} → {FAILED_DIR}")
                    else:
                        print(f"⚠️ API error {response.status_code}: {response.text}")
                except Exception as api_err:
                    print(f"❌ Failed API call for {file}: {api_err}")

        except Exception as loop_err:
            print(f"🔥 Error in main loop: {loop_err}")

        await asyncio.sleep(5)  # small delay to continuously check new files


if __name__ == "__main__":
    try:
        asyncio.run(process_files())
    except KeyboardInterrupt:
        print("🚪 Exiting gracefully...")
