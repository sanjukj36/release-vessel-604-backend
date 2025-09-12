# main.py
import subprocess

files_to_run = [
    "Api_Alert.py",
    "Band_storage.py",
    "data_striming.py",
    "data_striming_edit.py",
    "db.py",
    "historic_alarm.py",
    "mqtt.py",
    "Ping_satatus.py",
]

# Run each file one by one
for file in files_to_run:
    print(f"🚀 Running {file} ...")
    subprocess.Popen(["python", file])
