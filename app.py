from flask import Flask, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

# ====== CONFIG ======
DATA_FILE = "keys.json"

# ====== UTILIDADES ======
def load_keys():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_keys(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ====== RUTA PRINCIPAL ======
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "service": "api-joiner",
        "time": datetime.utcnow().isoformat()
    })

# ====== VALIDAR KEY (ROBLOX) ======
@app.route("/api/key-validation", methods=["POST"])
def validate_key():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "valid": False,
            "message": "Body JSON requerido"
        }), 400

    key = data.get("key")
    hwid = data.get("hwid")

    if not key or not hwid:
        return jsonify({
            "valid": False,
            "message": "Key y HWID requeridos"
        }), 400

    keys_db = load_keys()

    if key not in keys_db:
        return jsonify({
            "valid": False,
            "message": "Key inválida"
        }), 403

    key_data = keys_db[key]

    # Si la key no tiene HWID asignado, se asigna al primero
    if key_data["hwid"] is None:
        key_data["hwid"] = hwid
        keys_db[key] = key_data
        save_keys(keys_db)

    # Verificar HWID
    if key_data["hwid"] != hwid:
        return jsonify({
            "valid": False,
            "message": "HWID no autorizado"
        }), 403

    return jsonify({
        "valid": True,
        "message": "Acceso autorizado"
    }), 200

# ====== CREAR KEY (DISCORD / ADMIN) ======
@app.route("/api/create-key", methods=["POST"])
def create_key():
    data = request.get_json(silent=True)
    if not data or "key" not in data:
        return jsonify({"error": "Key requerida"}), 400

    key = data["key"]

    keys_db = load_keys()

    if key in keys_db:
        return jsonify({"error": "La key ya existe"}), 409

    keys_db[key] = {
        "hwid": None,
        "created_at": datetime.utcnow().isoformat()
    }

    save_keys(keys_db)

    return jsonify({
        "success": True,
        "key": key
    }), 201

# ====== BORRAR KEY ======
@app.route("/api/delete-key", methods=["POST"])
def delete_key():
    data = request.get_json(silent=True)
    if not data or "key" not in data:
        return jsonify({"error": "Key requerida"}), 400

    key = data["key"]
    keys_db = load_keys()

    if key not in keys_db:
        return jsonify({"error": "Key no existe"}), 404

    del keys_db[key]
    save_keys(keys_db)

    return jsonify({
        "success": True,
        "deleted": key
    }), 200

# ====== MAIN ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
