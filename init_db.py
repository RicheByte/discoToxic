import sqlite3

conn = sqlite3.connect("toxicity_tracker.db")
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    total_messages INTEGER DEFAULT 0,
    avg_toxicity REAL DEFAULT 0,
    toxicity_rank TEXT DEFAULT 'Neutral'
);

CREATE TABLE IF NOT EXISTS message_log (
    message_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    content TEXT,
    toxicity_score REAL,
    severe_toxicity REAL,
    obscene REAL,
    threat REAL,
    insult REAL,
    identity_attack REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

-- Add performance indexes
CREATE INDEX IF NOT EXISTS idx_message_log_user_id ON message_log(user_id);
CREATE INDEX IF NOT EXISTS idx_message_log_timestamp ON message_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_message_log_toxicity ON message_log(toxicity_score);
""")

conn.commit()
print("Tables and indexes created successfully.")
conn.close()
