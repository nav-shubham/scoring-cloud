from flask import Flask, request, jsonify
import os
import json
import time
import threading
from datetime import datetime
import requests
from dotenv import load_dotenv

# Import database helpers
import db

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)

# Parse questions
def parse_questions():
    import re
    questions_file = os.path.join(BASE_DIR, "questions.txt")
    if not os.path.exists(questions_file):
        return []
    questions = []
    with open(questions_file, "r", encoding="utf-8") as f:
        fallback_idx = 1
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^(\d+)\.(.*)$", line)
            if match:
                idx = int(match.group(1))
                text = match.group(2).strip()
            else:
                idx = fallback_idx
                text = line
            questions.append((idx, text))
            fallback_idx += 1
    return questions

# Answer callback query so the loading spinner stops on Telegram
def answer_callback_query(callback_id):
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        app.logger.error(f"Failed to answer callback: {e}")

# Send standard telegram message
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        app.logger.error(f"Telegram message failed: {e}")
        return None

# Send telegram photo
def send_telegram_photo(photo_path, caption):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            response = requests.post(url, data=payload, files=files, timeout=15)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        app.logger.error(f"Telegram photo failed: {e}")
        send_telegram_message(caption)
        return None

# Generate premium visual trend chart (using matplotlib)
def generate_chart(history, chart_path):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        # Premium dark styling
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)  # DPI set to 120 for extremely fast rendering
        
        # Deep dark navy background
        fig.patch.set_facecolor('#0E1117')
        ax.set_facecolor('#0E1117')
        
        dates = []
        for row in history:
            try:
                # Format YYYY-MM-DD to MM-DD
                dt = datetime.strptime(row['date'], "%Y-%m-%d")
                dates.append(dt.strftime("%m-%d"))
            except Exception:
                dates.append(str(row['date'])[-5:])
                
        percentages = [row['percentage'] for row in history]
        
        # Plot with soft glowing markers
        ax.plot(dates, percentages, color='#00F2FE', linewidth=3, marker='o', 
                markersize=8, markerfacecolor='#4FACFE', markeredgecolor='#00F2FE', 
                label='Success Rate')
                
        # Shadow/glow fill area below the line
        ax.fill_between(dates, percentages, color='#00F2FE', alpha=0.15)
        
        # Subtle horizontal guide lines
        for target in [50, 80, 100]:
            ax.axhline(target, color='#2D3748', linestyle=':', linewidth=0.8, alpha=0.7)
            
        # Clean up borders
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#2D3748')
        ax.spines['bottom'].set_color('#2D3748')
        
        # Tick parameters and grid lines
        ax.tick_params(colors='#A0AEC0', which='both', labelsize=9)
        ax.grid(True, color='#2D3748', linestyle='--', linewidth=0.5, alpha=0.3)
        
        # Sleek title and labels
        ax.set_title("Habit Success Rate Trend", fontsize=13, fontweight='bold', color='#FFFFFF', pad=15)
        ax.set_ylabel("Completion Rate (%)", color='#A0AEC0', fontsize=10, labelpad=8)
        ax.set_xlabel("Date", color='#A0AEC0', fontsize=10, labelpad=8)
        
        ax.set_ylim(-5, 105)
        
        plt.tight_layout()
        plt.savefig(chart_path, facecolor='#0E1117', bbox_inches='tight')
        plt.close()
        return True
    except Exception as e:
        app.logger.error(f"Failed to generate chart: {e}")
        return False

def get_motivational_message(percentage):
    """Returns a tailored motivational quote/message based on success percentage."""
    if percentage >= 100:
        return "🔥 *PERFECT DAY!* Absolute masterclass of discipline. Keep this streak alive!"
    elif percentage >= 80:
        return "🌟 *Excellent job!* You crushed almost all your habits today. Keep moving forward!"
    elif percentage >= 50:
        return "👍 *Decent effort.* A solid foundation, but there is room to finish stronger tomorrow!"
    else:
        return "💪 *Tomorrow is a new day.* Rest up, reset your focus, and hit it hard tomorrow!"

# Background thread processing to avoid Telegram webhook timeout
def process_scoring_in_background(date_str, q_idx, score, total_questions):
    try:
        # SQLite connection needs to be thread-local, which db helper handles
        db.init_db()
        
        questions = parse_questions()
        if not questions:
            return
            
        q_map = {idx: text for idx, text in questions}
        q_text = q_map.get(q_idx, f"Question {q_idx}")
        
        # Record/Upsert in SQLite
        db.upsert_score(date_str, q_idx, q_text, score)
        
        # Check total scored for this day
        day_scores = db.get_scores_for_date(date_str)
        scored_count = len(day_scores)
        
        if scored_count == total_questions:
            # All scored! Generate trend chart and send beautiful confirmation
            sum_score = sum(item['score'] for item in day_scores)
            percentage = round((sum_score / total_questions) * 100, 1)
            
            # Get historical percentages
            history = db.get_historical_percentages(limit=14)
            chart_path = os.path.join(BASE_DIR, "progress.png")
            chart_created = False
            if history:
                chart_created = generate_chart(history, chart_path)
                
            summary_lines = [
                f"✅ *Daily Scores Confirmed!*",
                f"📅 *Date:* {date_str}",
                f"📊 *Progress:* {sum_score}/{total_questions} ({percentage}%)",
                ""
            ]
            
            for item in day_scores:
                status_emoji = "🟢" if item['score'] == 1 else "🔴"
                summary_lines.append(f"{status_emoji} {item['question_index']}. {item['question_text']}")
                
            summary_lines.append("")
            summary_lines.append(get_motivational_message(percentage))
            
            caption = "\n".join(summary_lines)
            
            if chart_created and os.path.exists(chart_path):
                send_telegram_photo(chart_path, caption)
                try:
                    os.remove(chart_path)
                except Exception:
                    pass
            else:
                send_telegram_message(caption)
    except Exception as e:
        print(f"Error in background webhook execution: {e}")

# Webhook Endpoint (POST from Telegram Server)
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return jsonify({"status": "error", "message": "No JSON payload"}), 400
        
    callback = update.get("callback_query")
    if not callback:
        # Ignore normal text messages or non-button interactions
        return jsonify({"status": "ok", "message": "Ignored"}), 200
        
    callback_id = callback.get("id")
    from_id = callback.get("from", {}).get("id")
    data = callback.get("data", "")
    
    # Immediately answer callback to stop loading spinner on user's phone
    answer_callback_query(callback_id)
    
    # Authorize: Only accept callbacks from the configured chat ID
    if str(from_id) != str(CHAT_ID):
        app.logger.warning(f"Unauthorized access from user ID {from_id}. Expected {CHAT_ID}.")
        return jsonify({"status": "unauthorized"}), 403
        
    # Check if data matches habit format (score_{idx}_{score}_{date})
    if not data.startswith("score_"):
        return jsonify({"status": "ignored"}), 200
        
    parts = data.split("_")
    if len(parts) != 4:
        return jsonify({"status": "bad_format"}), 400
        
    try:
        q_idx = int(parts[1])
        score = int(parts[2])
        date_str = parts[3]
    except Exception as e:
        return jsonify({"status": "parse_error", "error": str(e)}), 400
        
    questions = parse_questions()
    if not questions:
        return jsonify({"status": "no_questions_configured"}), 500
        
    total_questions = len(questions)
    
    # Spawn background thread to handle database writing and chart sending asynchronously.
    # This responds to Telegram instantly (<10ms) and prevents any timeout/retry loops!
    threading.Thread(
        target=process_scoring_in_background,
        args=(date_str, q_idx, score, total_questions)
    ).start()
    
    return jsonify({"status": "success"}), 200

# Route to trigger sending morning questions securely
@app.route("/send", methods=["GET", "POST"])
def trigger_send():
    # Authorize with key parameter matching TELEGRAM_BOT_TOKEN
    key = request.args.get("key")
    if key != TOKEN:
        app.logger.warning("Unauthorized attempt to trigger sending questions.")
        return jsonify({"status": "unauthorized"}), 403
        
    try:
        import send_questions
        send_questions.main()
        return jsonify({"status": "success", "message": "Questions sent successfully!"}), 200
    except Exception as e:
        app.logger.error(f"Error executing send_questions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Base route for browser preview
@app.route("/", methods=["GET"])
def home():
    return """
    <html>
        <head>
            <title>Habit Tracker Webhook</title>
            <style>
                body {
                    background-color: #0E1117;
                    color: #FFFFFF;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                    border-radius: 16px;
                    background: rgba(255, 255, 255, 0.05);
                    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }
                h1 {
                    color: #00F2FE;
                    margin-bottom: 10px;
                }
                p {
                    color: #A0AEC0;
                    font-size: 1.1em;
                }
                .badge {
                    display: inline-block;
                    padding: 6px 12px;
                    background-color: #4FACFE;
                    color: #0E1117;
                    font-weight: bold;
                    border-radius: 20px;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Habit Tracker Webhook</h1>
                <p>Your Telegram Bot server is running successfully in the cloud!</p>
                <div class="badge">Webhook Status: ACTIVE</div>
            </div>
        </body>
    </html>
    """, 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
