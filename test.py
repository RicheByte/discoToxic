import sqlite3

conn = sqlite3.connect("toxicity_tracker.db")
cursor = conn.cursor()

# Show tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables:", cursor.fetchall())

# Show indexes
cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
print("Indexes:", cursor.fetchall())

conn.close()
