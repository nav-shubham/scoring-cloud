import sqlite3
import os
from datetime import datetime

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scoring.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it does not exist."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    question_index INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, question_index)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS questions_sent (
                    date TEXT PRIMARY KEY,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    finally:
        conn.close()

def upsert_score(date_str, question_index, question_text, score):
    """Inserts or updates a score for a specific date and question index."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO daily_scores (date, question_index, question_text, score)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date, question_index) 
                DO UPDATE SET 
                    score = excluded.score,
                    question_text = excluded.question_text
            """, (date_str, question_index, question_text, score))
    finally:
        conn.close()

def get_scores_for_date(date_str):
    """Retrieves all scores for a specific date."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT question_index, question_text, score 
            FROM daily_scores 
            WHERE date = ? 
            ORDER BY question_index ASC
        """, (date_str,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_historical_percentages(limit=14):
    """Retrieves historical completion percentages for the last N days.
    Returns them in chronological (ascending) order.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, percentage FROM (
                SELECT date, SUM(score) * 100.0 / COUNT(score) as percentage 
                FROM daily_scores 
                GROUP BY date 
                ORDER BY date DESC 
                LIMIT ?
            ) ORDER BY date ASC
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def is_questions_sent(date_str):
    """Checks if questions have already been sent for a given date."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM questions_sent WHERE date = ?", (date_str,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def record_questions_sent(date_str):
    """Records that questions have been sent for a given date."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO questions_sent (date)
                VALUES (?)
                ON CONFLICT(date) DO NOTHING
            """, (date_str,))
    finally:
        conn.close()

def has_scores_for_date(date_str):
    """Checks if any scores exist for a given date."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM daily_scores WHERE date = ? LIMIT 1", (date_str,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def is_questions_sent_empty():
    """Checks if the questions_sent table is completely empty."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM questions_sent LIMIT 1")
        return cursor.fetchone() is None
    finally:
        conn.close()

if __name__ == "__main__":
    # If run directly, initialize database for testing
    print(f"Initializing database at: {DB_NAME}")
    init_db()
    print("Database initialized successfully.")
