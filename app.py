from flask import Flask, request, jsonify
import sqlite3
import time

app = Flask(__name__)
DB = "database.db"

def db():
    return sqlite3.connect(DB)

@app.route("/api/key-validation", methods=["POST"])
def validate():
    data = request.get_json(force=True)

    key = data.get("key")
    hwid = data.get("hwid")

    if not key or not hwid:
        return jsonify(valid=False, message="Datos incompletos"), 400

    con = db()
    c = con.cursor()

    c.execute("""
        SELECT key, expires_at, user_id
        FROM keys
        WHERE key=? AND used=1
    """, (key,))
    row = c.fetchone()

    if not row:
        return jsonify(valid=False, message="Key inválida"), 403

    if row[1] and row[1] < int(time.time()):
        return jsonify(valid=False, message="Key expirada"), 403

    c.execute("SELECT hwid FROM stats WHERE user_id=?", (row[2],))
    s = c.fetchone()

    if s and s[0]:
        if s[0] != hwid:
            return jsonify(valid=False, message="HWID incorrecto"), 403
    else:
        c.execute(
            "UPDATE stats SET hwid=? WHERE user_id=?",
            (hwid, row[2])
        )
        con.commit()

    return jsonify(valid=True), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
