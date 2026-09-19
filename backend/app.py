from flask import Flask, request, jsonify, send_from_directory
import os

from engine import TriageService

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
service = TriageService()


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/status")
def status():
    return jsonify({"mode": service.mode})


@app.route("/api/triage", methods=["POST"])
def triage():
    payload = request.get_json(force=True, silent=True) or {}
    ticket_text = payload.get("ticket_text", "")
    history = payload.get("history", [])
    if not isinstance(history, list):
        history = []
    result = service.triage(ticket_text, history)
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"IT Support Triage Assistant running at http://localhost:{port}  (mode: {service.mode})")
    app.run(host="0.0.0.0", port=port, debug=False)
