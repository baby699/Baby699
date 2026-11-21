import os, sqlite3, secrets, hashlib
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template, abort
from cryptography.fernet import Fernet, InvalidToken
from werkzeug.security import generate_password_hash, check_password_hash

APP_SECRET = os.environ.get("APP_SECRET")
FERNET_KEY = os.environ.get("FERNET_KEY")
DB_PATH = os.environ.get("DB_PATH", "/data/secretbox.sqlite3")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
MAX_AGE_HOURS = int(os.environ.get("MAX_AGE_HOURS", "168"))

if not APP_SECRET or not FERNET_KEY:
    raise RuntimeError("Set APP_SECRET and FERNET_KEY environment variables.")

cipher = Fernet(FERNET_KEY.encode())
app = Flask(__name__)
app.config["SECRET_KEY"] = APP_SECRET
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

def connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS notes (
          token_hash TEXT PRIMARY KEY,
          ciphertext BLOB NOT NULL,
          password_hash TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0
        )
        """)
init_db()

def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/api/notes")
def create_note():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    password = str(data.get("password", ""))
    if not message or not password:
        return jsonify(error="Message and password are required."), 400
    if len(message) > 10000 or len(password) > 256:
        return jsonify(error="Message or password is too long."), 400
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=MAX_AGE_HOURS)).isoformat()
    encrypted = cipher.encrypt(message.encode("utf-8"))
    pwh = generate_password_hash(password, method="scrypt")
    with connect() as con:
        con.execute(
            "INSERT INTO notes(token_hash,ciphertext,password_hash,expires_at) VALUES(?,?,?,?)",
            (token_digest(token), encrypted, pwh, expires)
        )
    url = f"{PUBLIC_BASE_URL}/n/{token}" if PUBLIC_BASE_URL else f"/n/{token}"
    return jsonify(url=url, expires_in_hours=MAX_AGE_HOURS)

@app.get("/n/<token>")
def note_page(token):
    return render_template("read.html", token=token)

@app.post("/api/notes/<token>/read")
def read_note(token):
    data = request.get_json(silent=True) or {}
    password = str(data.get("password", ""))
    digest = token_digest(token)
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT * FROM notes WHERE token_hash=?", (digest,)).fetchone()
        if row is None:
            con.execute("ROLLBACK")
            return jsonify(error="This secret has already been opened, expired, or does not exist."), 404
        if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
            con.execute("DELETE FROM notes WHERE token_hash=?", (digest,))
            con.execute("COMMIT")
            return jsonify(error="This secret has expired."), 410
        if row["attempts"] >= 10:
            con.execute("DELETE FROM notes WHERE token_hash=?", (digest,))
            con.execute("COMMIT")
            return jsonify(error="Too many incorrect password attempts. Secret deleted."), 410
        if not check_password_hash(row["password_hash"], password):
            con.execute("UPDATE notes SET attempts=attempts+1 WHERE token_hash=?", (digest,))
            con.execute("COMMIT")
            return jsonify(error="Incorrect password."), 401
        try:
            message = cipher.decrypt(row["ciphertext"]).decode("utf-8")
        except InvalidToken:
            con.execute("DELETE FROM notes WHERE token_hash=?", (digest,))
            con.execute("COMMIT")
            return jsonify(error="Secret could not be decrypted and has been deleted."), 410
        # Delete in the same write transaction before returning the plaintext.
        con.execute("DELETE FROM notes WHERE token_hash=?", (digest,))
        con.execute("COMMIT")
        return jsonify(message=message)
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()

@app.get("/health")
def health():
    return jsonify(status="ok")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
