from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import sqlite3
 
app = Flask(__name__)
CORS(app)
 
DB_NAME = "mydatabase.db"
TABLE_NAME = "telemetry"
 
 
# Function to initialize DB and create table if not exists
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            CreatedOn TEXT,
            ModifiedOn TEXT,
            FileName TEXT,
            TransmissionStatus TEXT
        )
    """)
    conn.commit()
    conn.close()
 
 
@app.route('/api/table/create', methods=['POST'])
def create_and_insert():
    init_db()  # make sure table exists
    data = request.json
 
    created_on = data.get("CreatedOn")
    file_name = data.get("FileName")
    modified_on = data.get("ModifiedOn")   # ✅ take ModifiedOn from body
    transmission_status = data.get("TransmissionStatus")

    print(f"Updating status for CreatedOn: {created_on}, TransmissionStatus: {transmission_status}, ModifiedOn: {modified_on}")

 
    if not created_on or not file_name or not transmission_status:
        return jsonify({"success": False, "message": "CreatedOn, FileName,ModifiedOn, and TransmissionStatus are required"}), 400
 
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
 
    cursor.execute(f"""
        INSERT INTO {TABLE_NAME} (CreatedOn, ModifiedOn, FileName, TransmissionStatus)
        VALUES (?, ?, ?, ?)
    """, (created_on,  modified_on, file_name, transmission_status))
 
    conn.commit()
    conn.close()
 
    return jsonify({"success": True, "message": "Row inserted successfully"}), 201
 
 
@app.route('/api/table/', methods=['GET'])
def get_last_10():
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # cursor.execute(f"""
    #     SELECT ID, CreatedOn, ModifiedOn, FileName, TransmissionStatus
    #     FROM {TABLE_NAME}
    #     ORDER BY ID DESC
    #     LIMIT 5
    # """)
    cursor.execute(f"""
    SELECT ID, CreatedOn, ModifiedOn, FileName, TransmissionStatus
    FROM (
        SELECT ID, CreatedOn, ModifiedOn, FileName, TransmissionStatus
        FROM {TABLE_NAME}
        ORDER BY ID DESC
        LIMIT 10
    )
    ORDER BY ID ASC
    """)
# rows = cursor.fetchall()

    rows = cursor.fetchall()
    conn.close()
 
    # Convert rows to dict list
    data = [
        {
            "ID": row[0],
            "CreatedOn": row[1],
            "ModifiedOn": row[2],
            "FileName": row[3],
            "TransmissionStatus": row[4]
        }
        for row in rows
    ]
 
    return jsonify({"data": data}), 200
 
 
@app.route('/api/table/update', methods=['PUT'])
def update_status():
    init_db()
    data = request.json
 
    created_on = data.get("CreatedOn")
    modified_on = data.get("ModifiedOn")   # ✅ take ModifiedOn from body
    transmission_status = data.get("TransmissionStatus")

 
    if not created_on or not transmission_status or not modified_on:
        return jsonify({"success": False, "message": "CreatedOn, ModifiedOn, and TransmissionStatus are required"}), 400
 
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
 
    cursor.execute(f"""
        UPDATE {TABLE_NAME}
        SET TransmissionStatus = ?,
            ModifiedOn = ?
        WHERE CreatedOn = ?
    """, (transmission_status, modified_on, created_on))
 
    conn.commit()
    updated_rows = cursor.rowcount
    conn.close()
 
    if updated_rows == 0:
        return jsonify({"success": False, "message": "No record found with the given CreatedOn"}), 404
 
    return jsonify({"success": True, "message": "Status updated successfully"}), 200
 
 
if __name__ == '__main__':
    app.run(host='172.168.0.81', port=5004, debug=True)
    # app.run(host='192.168.18.143', port=5004, debug=True)