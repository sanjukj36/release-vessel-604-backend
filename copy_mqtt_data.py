import os
import shutil
import time
from datetime import datetime

# Paths
source_file = r"C:\Mqtt\__data\mqtt_live_data.json"
destination_folder = r"C:\Payloads\1036991\Processed\MDC"

def copy_with_creation_time():
    if not os.path.exists(source_file):
        print(f"Source file not found: {source_file}")
        return

    # Get file creation time
    creation_time = os.path.getctime(source_file)
    formatted_time = datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d_%H-%M-%S")

    # Create new filename with creation time
    base_name = "mqtt_live_data"
    new_filename = f"{base_name}_{formatted_time}.json"
    destination_file = os.path.join(destination_folder, new_filename)

    # Copy file
    shutil.copy2(source_file, destination_file)
    print(f"Copied: {source_file} -> {destination_file}")

if __name__ == "__main__":
    while True:
        copy_with_creation_time()
        time.sleep(60)  # wait 1 minute
