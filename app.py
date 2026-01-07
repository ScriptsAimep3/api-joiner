from flask import Flask, request, jsonify
import time
import secrets

app = Flask(__name__)

# ================= STORAGE (SIMPLE) =================
# En producción puedes cambiar a DB real

keys = {}
discord_users = {}
hwid_map = {}

# ================= UTILS =================

def gen_key():
    return "VZe" + secrets.token_hex(16)

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
    data = request.json
    duration = data.get("duration")

    if not duration:
        return jsonify({"error": "duration required"}), 400

    key = gen_key()
    keys[key] = {
        "expires": int(time.time()) + int(duration),
        "used": False
    }

    return jsonify({
        "success": True,
        "key": key
    })

# -------- REDEEM KEY (DISCORD) --------

@app.route("/api/redeem-key", methods=["POST"])
def redeem_key():
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
    data = request.json
    discord_id = data.get("discord_id")

    user = discord_users.get(discord_id)
    if not user:
        return jsonify({"error": "No active key"}), 400

    key = user["key"]
    hwid_map.pop(key, None)

    return jsonify({"success": True})

# ================= RUN =================

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
