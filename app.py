import sqlite3
import json
import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import io

app = Flask(__name__)
CORS(app)

DB_FILE = "data/database.sqlite"

def get_db_connection():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Schema:
    # 1. id: INTEGER PRIMARY KEY (Auto-inc if not provided)
    # 2. date: TEXT NOT NULL (Mandatory)
    # 3. plan: TEXT (The specific text field you requested)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            plan TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize on start
init_db()

@app.route("/add", methods=["POST"])
def add_item():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    for entry in data:
        req_id = entry.get('id')
        req_date = entry.get('date')
        req_plan = entry.get('plan')

        if not req_date:
            return jsonify({"error": "Field 'date' is required"}), 400
        
        try:
            conn = get_db_connection()
            
            if req_id is not None:
                conn.execute(
                    'INSERT INTO records (id, date, plan) VALUES (?, ?, ?)',
                    (req_id, req_date, req_plan)
                )
            else:
                conn.execute(
                    'INSERT INTO records (date, plan) VALUES (?, ?)',
                    (req_date, req_plan)
                )
            
        except sqlite3.IntegrityError:
            return jsonify({"error": f"ID {req_id} already exists"}), 409
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    conn.commit()
    conn.close()
    return jsonify({"message": "Item added successfully"}), 200

@app.route("/upload-db", methods=["POST"])
def upload_db():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data_list = request.get_json()
    if not isinstance(data_list, list):
        data_list = [data_list]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM records')
            for item in data_list:
                i_id = item.get('id')
                i_date = item.get('date')
                i_plan = item.get('plan')
                if i_date is None:
                     raise ValueError("One of the items is missing the 'date' field")
                cursor.execute(
                    'INSERT INTO records (id, date, plan) VALUES (?, ?, ?)',
                    (i_id, i_date, i_plan)
                )
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        return jsonify({"message": "Database restored successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download-db", methods=["GET"])
def download_db():
    if not os.path.exists(DB_FILE):
        return jsonify({"error": "Database not initialized"}), 404

    try:
        conn = get_db_connection()
        rows = conn.execute('SELECT id, date, plan FROM records').fetchall()
        conn.close()

        results = [dict(row) for row in rows]
        
        mem_file = io.BytesIO()
        mem_file.write(json.dumps(results, indent=2).encode('utf-8'))
        mem_file.seek(0)

        return send_file(
            mem_file,
            mimetype="application/json",
            as_attachment=True,
            download_name="data.json",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5050)
