
import sqlite3
import logging
import os

DB_FILE = 'jobs.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posted_jobs (
            id TEXT PRIMARY KEY,
            url TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def is_job_posted(job_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM posted_jobs WHERE id = ?', (job_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_job_posted(job_id, url):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT OR IGNORE INTO posted_jobs (id, url) VALUES (?, ?)', (job_id, url))
        conn.commit()
    except Exception as e:
        logging.error(f"Error marking job as posted: {e}")
    finally:
        conn.close()

def get_state(key, default=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT value FROM agent_state WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result[0] if result else default
    except Exception as e:
        logging.error(f"Error getting state for key {key}: {e}")
        return default
    finally:
        conn.close()

def set_state(key, value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT OR REPLACE INTO agent_state (key, value) VALUES (?, ?)', (key, str(value)))
        conn.commit()
    except Exception as e:
        logging.error(f"Error setting state for key {key}: {e}")
    finally:
        conn.close()

