import queue
import random
import smtplib
import threading
import time
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os

from openai import OpenAI
import pandas as pd
from flask import Flask, request, jsonify
from sklearn.ensemble import IsolationForest
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Flask app setup
app = Flask(__name__)
CORS(app)

# Email Configuration
EMAIL_FROM = "codefestmarriott@gmail.com"
EMAIL_TO = "ailogmonitor@yopmail.com"
SMTP_SERVER = "smtp.yopmail.com"
SMTP_PORT = 25

# Queues and buffers
log_queue = queue.Queue()
anomalies = []
all_logs = []  # Store all logs

# Log Generator with realistic levels
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

# Preprocess logs for model
def preprocess_logs(logs):
    df = pd.DataFrame(logs)
    df['level_encoded'] = df['level'].map({'INFO': 0, 'DEBUG': 1, 'WARN': 2, 'ERROR': 3})
    df['message_len'] = df['message'].str.len()
    df['time_diff'] = df['timestamp'].diff().fillna(0)
    return df[['level_encoded', 'message_len', 'time_diff']]

# Get AI-based fix suggestion
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

# Email alert sender
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

# Anomaly detection loop
def detect_anomalies():
    buffer = []
    model = IsolationForest(contamination=0.05)
    while True:
        if not log_queue.empty():
            log = log_queue.get()
            all_logs.append(log)
            buffer.append(log)
            if len(buffer) >= 20:
                structured = preprocess_logs(buffer)
                preds = model.fit_predict(structured)
                for i, pred in enumerate(preds):
                    current_log = buffer[i]
                    if pred == -1:
                        if current_log['level'] == 'INFO':
                            current_log['reason'] = "Not an anomaly - informational message"
                            current_log['suggestion'] = "No action required for INFO level logs."
                        else:
                            current_log['reason'] = "Anomalous log pattern detected"
                            current_log['suggestion'] = get_fix_suggestion(current_log['message'])
                            email_body = f"""
Anomaly Detected:
Level: {current_log['level']}
Message: {current_log['message']}
Reason: {current_log['reason']}
Suggestion: {current_log['suggestion']}
                            """.strip()
                            send_email_alert("[Log Monitor] Anomaly Detected", email_body)
                        anomalies.append(current_log)
                buffer.clear()
        time.sleep(0.5)

# API to get recent anomalies
@app.route("/logs", methods=['GET'])
def get_logs():
    return jsonify(list(anomalies)[-10:])

# Ingest a new log entry manually
@app.route("/ingest", methods=['POST'])
def ingest_log():
    log = request.json
    log['timestamp'] = time.time()
    log_queue.put(log)
    return jsonify({"status": "received"})

# Chat-style query for error logs
@app.route("/chat-query", methods=['POST'])
def chat_query():
    data = request.json
    query = data.get("query", "").lower()

    now = time.time()
    level = None
    hours = 24

    for lvl in ["error", "warn", "info", "debug"]:
        if lvl in query:
            level = lvl.upper()
            break

    for part in query.split():
        if part.isdigit():
            hours = int(part)
            break

    start_time = now - (hours * 3600)

    filtered = [
        log for log in anomalies
        if log["timestamp"] >= start_time and (level is None or log["level"] == level)
    ]

    return jsonify(filtered)

# Start threads and run server
if __name__ == "__main__":
    threading.Thread(target=generate_logs, daemon=True).start()
    threading.Thread(target=detect_anomalies, daemon=True).start()
    app.run(port=5001, debug=True)