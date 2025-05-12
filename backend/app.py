import queue
import random
import smtplib
import threading
import time
from email.mime.text import MIMEText

from openai import OpenAI
import pandas as pd
from flask import Flask, request, jsonify
from sklearn.ensemble import IsolationForest

import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

print('######## os.getenv("OPENAI_API_KEY")')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === OpenAI Client Setup ===
#client = OpenAI(api_key="you-api-key")  # Replace with env variable or secure config in production

# === Flask App ===
from flask_cors import CORS  # 👈 import this

app = Flask(__name__)
CORS(app)  # 👈 enable CORS for all routes

# === Email Configuration ===
EMAIL_FROM = "codefestmarriott@gmail.com"
EMAIL_TO = "ailogmonitor@yopmail.com"
SMTP_SERVER = "smtp.yopmail.com"
SMTP_PORT = 25

# === Queues and Anomalies ===
log_queue = queue.Queue()
anomalies = []

# === Log Generator ===
def generate_logs():
    log_levels = ['INFO', 'DEBUG', 'WARN', 'ERROR']
    messages = [
        "Service started",
        "Database connection established",
        "Cache miss",
        "User login successful",
        "Failed to connect to DB",
        "Timeout occurred while calling API",
        "Memory usage high",
        "Disk space low",
    ]
    while True:
        log = {
            'timestamp': time.time(),
            'level': random.choices(log_levels, weights=[60, 20, 15, 5])[0],
            'message': random.choice(messages),
        }
        log_queue.put(log)
        time.sleep(random.uniform(0.5, 1.5))

# === Preprocess Logs ===
def preprocess_logs(logs):
    df = pd.DataFrame(logs)
    df['level_encoded'] = df['level'].map({'INFO': 0, 'DEBUG': 1, 'WARN': 2, 'ERROR': 3})
    df['message_len'] = df['message'].str.len()
    df['time_diff'] = df['timestamp'].diff().fillna(0)
    return df[['level_encoded', 'message_len', 'time_diff']]

# === Get Fix Suggestion from OpenAI ===
def get_fix_suggestion(log_message):
    prompt = f"You are an AI DevOps assistant. Analyze the following log message and suggest a possible cause and fix.\n\nLog: {log_message}"
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM error: {e}"

# === Send Email Alert ===
def send_email_alert(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")

# === Anomaly Detection Loop ===
def detect_anomalies():
    buffer = []
    model = IsolationForest(contamination=0.05)
    while True:
        if not log_queue.empty():
            buffer.append(log_queue.get())
            if len(buffer) >= 20:
                structured = preprocess_logs(buffer)
                preds = model.fit_predict(structured)
                for i, pred in enumerate(preds):
                    if pred == -1:
                        anomaly = buffer[i]
                        anomaly['reason'] = "Anomalous log pattern detected"
                        anomaly['suggestion'] = get_fix_suggestion(anomaly['message'])
                        anomalies.append(anomaly)
                        email_body = f"""
Anomaly Detected:
Level: {anomaly['level']}
Message: {anomaly['message']}
Reason: {anomaly['reason']}
Suggestion: {anomaly['suggestion']}
                        """.strip()
                        send_email_alert("[Log Monitor] Anomaly Detected", email_body)
                buffer.clear()
        time.sleep(0.5)

# === API Routes ===
@app.route("/logs", methods=['GET'])
def get_logs():
    return jsonify(list(anomalies)[-10:])

@app.route("/ingest", methods=['POST'])
def ingest_log():
    log = request.json
    log_queue.put(log)
    return jsonify({"status": "received"})

# === App Runner ===
if __name__ == "__main__":
    threading.Thread(target=generate_logs, daemon=True).start()
    threading.Thread(target=detect_anomalies, daemon=True).start()
    app.run(port=5001, debug=True)


