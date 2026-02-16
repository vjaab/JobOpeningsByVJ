
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
