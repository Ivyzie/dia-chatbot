import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pathlib import Path

from chat_engine import chat_once   # your Phase‑4 function

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)

# Set static and template folders relative to project root
BASE_DIR = Path(__file__).parent.parent.resolve()
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR)
)

# Allow cross‑origin for the API only (you can tighten this in prod)
CORS(app, resources={r"/chat": {"origins": "*"}})

@app.route("/")
def home():
    # Renders templates/index.html
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify(error="JSON body must contain 'message'"), 400

    user_msg = data["message"].strip()
    if not user_msg:
        return jsonify(error="Empty message"), 400

    try:
        reply = chat_once(user_msg)
        return jsonify(reply=reply.strip()), 200
    except Exception:
        logging.exception("chat_once failed")
        return jsonify(error="Internal server error"), 500

if __name__ == "__main__":
    # For development only; in production use a WSGI server
    app.run(host="0.0.0.0", port=5000, threaded=True)