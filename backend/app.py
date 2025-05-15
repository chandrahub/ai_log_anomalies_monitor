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

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

EMAIL_FROM = "codefestmarriott@gmail.com"
EMAIL_TO = "ailogmonitor@yopmail.com"
SMTP_SERVER = "smtp.yopmail.com"
SMTP_PORT = 25

log_queue = queue.Queue()
anomalies = []

# === Log Generator with proper severity levels ===
def generate_logs():
    messages = [
        {"message": "Service started", "level": "INFO"},
        {"message": "Database connection established", "level": "INFO"},
        {"message": "Cache miss", "level": "DEBUG"},
        {"message": "User login successful", "level": "INFO"},
        {"message": "Failed to connect to DB", "level": "ERROR"},
        {"message": "Timeout occurred while calling API", "level": "ERROR"},
        {"message": "Memory usage high", "level": "WARN"},
        {"message": "Disk space low", "level": "WARN"},
    ]
    while True:
        entry = random.choice(messages)
        log = {
            'timestamp': time.time(),
            'level': entry['level'],
            'message': entry['message'],
        }
        log_queue.put(log)
        time.sleep(random.uniform(0.5, 1.5))

def preprocess_logs(logs):
    df = pd.DataFrame(logs)
    df['level_encoded'] = df['level'].map({'INFO': 0, 'DEBUG': 1, 'WARN': 2, 'ERROR': 3})
    df['message_len'] = df['message'].str.len()
    df['time_diff'] = df['timestamp'].diff().fillna(0)
    return df[['level_encoded', 'message_len', 'time_diff']]

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
                    log = buffer[i]
                    if pred == -1:
                        if log["level"] == "INFO":
                            log["reason"] = "Info-level log. No anomaly detected."
                            log["suggestion"] = "No action required for informational logs."
                        else:
                            log["reason"] = "Anomalous log pattern detected"
                            log["suggestion"] = get_fix_suggestion(log["message"])
                            email_body = f"""
Anomaly Detected:
Level: {log['level']}
Message: {log['message']}
Reason: {log['reason']}
Suggestion: {log['suggestion']}
                            """.strip()
                            send_email_alert("[Log Monitor] Anomaly Detected", email_body)
                        anomalies.append(log)
                buffer.clear()
        time.sleep(0.5)

@app.route("/logs", methods=['GET'])
def get_logs():
    return jsonify(list(anomalies)[-10:])

@app.route("/ingest", methods=['POST'])
def ingest_log():
    log = request.json
    log_queue.put(log)
    return jsonify({"status": "received"})

if __name__ == "__main__":
    threading.Thread(target=generate_logs, daemon=True).start()
    threading.Thread(target=detect_anomalies, daemon=True).start()
    app.run(port=5001, debug=True)