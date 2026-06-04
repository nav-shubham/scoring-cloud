# /// script
# dependencies = [
#   "requests",
#   "python-dotenv",
# ]
# ///

import os
import re
import sys
import json
import time
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
import db

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def parse_questions():
    """Reads and parses questions from questions.txt."""
    questions_file = os.path.join(BASE_DIR, "questions.txt")
    if not os.path.exists(questions_file):
        raise FileNotFoundError(f"{questions_file} not found.")
        
    questions = []
    with open(questions_file, "r", encoding="utf-8") as f:
        fallback_idx = 1
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Match formats like "1.Grooming Complete" or "1. Grooming Complete"
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

def send_telegram_message(text, reply_markup=None):
    """Sends a Telegram message to the configured CHAT_ID with automatic retry."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
        
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Telegram send attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(1.5)  # Wait before retrying
    return None

def send_questions_for_date(date_str, questions):
    """Sends the set of questions with scoring buttons for a specific date."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    is_today = (date_str == today_str)
    
    if is_today:
        intro_text = f"🌅 *Good Morning!* Here are your questions for today, *{date_str}*:\n\nPlease score each habit when you are ready."
    else:
        intro_text = f"📅 *Missing Past Day!* Here are your questions for *{date_str}*:\n\nPlease score each habit to complete your history."
        
    print(f"Sending questions for {date_str}...")
    send_telegram_message(intro_text)
    time.sleep(0.5)
    
    success_count = 0
    for idx, q_text in questions:
        question_display = f"*{idx}. {q_text}*"
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🟢 1 (Yes)", "callback_data": f"score_{idx}_1_{date_str}"},
                    {"text": "🔴 0 (No)", "callback_data": f"score_{idx}_0_{date_str}"}
                ]
            ]
        }
        
        result = send_telegram_message(question_display, reply_markup)
        if result:
            success_count += 1
            print(f"Sent: {idx}. {q_text} (for {date_str})")
        else:
            print(f"Failed to send: {idx}. {q_text} (for {date_str})")
            
        time.sleep(1.0)  # Gentle spacing to avoid proxy throttling and rate limits
        
    print(f"Successfully sent {success_count}/{len(questions)} questions for {date_str}.")
    return success_count > 0

def main():
    if not TOKEN or not CHAT_ID:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in the .env file.")
        
    questions = parse_questions()
    if not questions:
        print("No questions found in questions.txt.")
        return
        
    # Initialize database schema if not already initialized
    db.init_db()
    
    # Determine date range to process (last 7 days + today)
    today = datetime.now()
    dates_to_process = []
    for i in range(7, -1, -1):
        date_obj = today - timedelta(days=i)
        date_str = date_obj.strftime("%Y-%m-%d")
        dates_to_process.append(date_str)
        
    # If this is the very first run (questions_sent table is empty),
    # pre-populate the past days in the database so we start fresh from today.
    if db.is_questions_sent_empty():
        print("First run detected. Pre-populating past days in questions_sent table to start fresh today.")
        for date_str in dates_to_process[:-1]:  # All dates except today
            db.record_questions_sent(date_str)
            
    sent_any = False
    for date_str in dates_to_process:
        # Check if we already sent or if scores already exist for this date
        if db.is_questions_sent(date_str):
            print(f"Skipping {date_str}: questions already sent.")
            continue
            
        if db.has_scores_for_date(date_str):
            print(f"Skipping {date_str}: scores already exist in database.")
            # Mark as sent so we don't check again
            db.record_questions_sent(date_str)
            continue
            
        # Send the questions for this day
        success = send_questions_for_date(date_str, questions)
        if success:
            db.record_questions_sent(date_str)
            sent_any = True
            time.sleep(1.0)  # Extra delay between days to be gentle on Telegram
            
    if not sent_any:
        print("All questions for the past 7 days are already sent/scored. Nothing to do.")

if __name__ == "__main__":
    main()
