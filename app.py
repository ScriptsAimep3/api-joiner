from flask import Flask, request, jsonify
import time
import secrets
import os

app = Flask(__name__)

# ================= AUTH =================

API_TOKEN = os.getenv("39b95f577e6f0e1021fc122a9c5c0d2f0ce6dd68834339449ba7285b2fd04868")  # Configúralo en Render

def require_api_token():
    token = request.headers.get("Authorization")
    if not token or token != f"Bearer {API_TOKEN}":
        return False
    return True

# ================= STORAGE =================
# Simple (RAM). Si reinicias Render se borra.

keys = {}           # key -> {expires, used}
discord_users = {}  # discord_id -> {key, expires}
hwid_map = {}       # key -> hwid
logs = []           # logs de acciones

# ================= UTILS =================

def gen_key():
    return "VZe" + secrets.token_hex(16)

def log(action, data):
    logs.append({
        "time": int(time.time()),
        "action": action,
        "data": data
    })

# ================= ROUTES =================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "api-joiner",
        "status": "online",
        "time": time.time()
    })

# -------- CREATE KEY (BOT) --------

@app.route("/api/create-key", methods=["POST"])
def create_key():
    if not require_api_token():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    duration = data.get("duration")
    generated_by = data.get("generated_by")

    if not duration:
        return jsonify({"error": "duration required"}), 400

    key = gen_key()
    keys[key] = {
        "expires": int(time.time()) + int(duration),
        "used": False
    }

    log("create_key", {
        "key": key,
        "duration": duration,
        "generated_by": generated_by
    })

    return jsonify({"success": True, "key": key})

# -------- REDEEM KEY (DISCORD) --------

@app.route("/api/redeem-key", methods=["POST"])
def redeem_key():
    if not require_api_token():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    key = data.get("key")
    discord_id = data.get("discord_id")

    if key not in keys:
        return jsonify({"error": "Invalid key"}), 400

    if keys[key]["used"]:
        return jsonify({"error": "Key already used"}), 400

    keys[key]["used"] = True
    discord_users[discord_id] = {
        "key": key,
        "expires": keys[key]["expires"]
    }

    log("redeem_key", {
        "key": key,
        "discord_id": discord_id
    })

    return jsonify({"success": True})

# -------- COMPENSATE --------

@app.route("/api/compensate", methods=["POST"])
def compensate():
    if not require_api_token():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    seconds = data.get("seconds")

    if not seconds:
        return jsonify({"error": "seconds required"}), 400

    for user in discord_users.values():
        user["expires"] += int(seconds)

    log("compensate", {"seconds": seconds})

    return jsonify({"success": True})

# -------- WIPE ALL --------

@app.route("/api/wipe", methods=["POST"])
def wipe():
    if not require_api_token():
        return jsonify({"error": "Unauthorized"}), 401

    keys.clear()
    discord_users.clear()
    hwid_map.clear()

    log("wipe", {})

    return jsonify({"success": True})

# -------- DISCORD CHECK --------

@app.route("/api/discord-check", methods=["POST"])
def discord_check():
    data = request.json
    discord_id = data.get("discord_id")

    user = discord_users.get(discord_id)
    if not user:
        return jsonify({"active": False})

    if user["expires"] < time.time():
        return jsonify({"active": False})

    return jsonify({"active": True})

# -------- KEY VALIDATION (ROBLOX) --------

@app.route("/api/key-validation", methods=["POST"])
def key_validation():
    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    if key not in keys:
        return jsonify({"valid": False, "message": "Invalid key"}), 200

    if keys[key]["expires"] < time.time():
        return jsonify({"valid": False, "message": "Key expired"}), 200

    if key in hwid_map and hwid_map[key] != hwid:
        return jsonify({"valid": False, "message": "HWID mismatch"}), 200

    hwid_map[key] = hwid
    return jsonify({"valid": True, "message": "Access granted"}), 200

# -------- RESET HWID --------

@app.route("/api/reset-hwid", methods=["POST"])
def reset_hwid():
    if not require_api_token():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    discord_id = data.get("discord_id")

    user = discord_users.get(discord_id)
    if not user:
        return jsonify({"error": "No active key"}), 400

    key = user["key"]
    hwid_map.pop(key, None)

    log("reset_hwid", {
        "discord_id": discord_id,
        "key": key
    })

    return jsonify({"success": True})

# -------- LOGS --------

@app.route("/api/logs", methods=["GET"])
def get_logs():
    if not require_api_token():
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify(logs[-100:])  # últimos 100 logs

# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
