
from flask import Flask, render_template_string, request, jsonify, session
import requests
from user_model import User, SessionLocal, create_db_tables
from auth_utils import hash_password, verify_password

app = Flask(__name__)

app.secret_key = 'medimate_secret_key'  # For session management

# Load the HTML file
with open("index.html", "r", encoding="utf-8") as f:
    HTML_PAGE = f.read()

FASTAPI_URL = "http://127.0.0.1:8000/predict"

# Ensure DB tables exist
create_db_tables()


@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


@app.route("/send", methods=["POST"])
def send():
    user_text = request.json.get("text", "")
    try:
        response = requests.post(FASTAPI_URL, json={"text": user_text})
        data = response.json()
        return jsonify({"reply": data.get("prediction", "No response")})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)