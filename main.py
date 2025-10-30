import os
import discord
import sqlite3
import asyncio
from detoxify import Detoxify
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise ValueError("Discord token not found. Make sure it is set in the .env file.")

# Initialize Discord client and Detoxify model
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Initialize Detoxify - using the 'unbiased' model
toxicity_model = Detoxify('unbiased')

# Database setup
DB_NAME = 'toxicity_tracker.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            total_messages INTEGER DEFAULT 0,
            avg_toxicity REAL DEFAULT 0,
            toxicity_rank TEXT DEFAULT 'Neutral'
        )
    ''')
    
    cursor.execute('''
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
        )
    ''')
    
    conn.commit()
    conn.close()

def analyze_toxicity(text):
    try:
        results = toxicity_model.predict(text)
        return {
            'toxicity': results['toxicity'],
            'severe_toxicity': results['severe_toxicity'],
            'obscene': results['obscene'],
            'threat': results['threat'],
            'insult': results['insult'],
            'identity_attack': results['identity_attack']
        }
    except Exception as e:
        print(f"Error in toxicity analysis: {e}")
        return None

def update_user_profile(user_id, username, toxicity_score):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT total_messages, avg_toxicity FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        total_msgs, avg_tox = result
        new_total = total_msgs + 1
        new_avg = ((avg_tox * total_msgs) + toxicity_score) / new_total
        
        if new_avg < 0.2:
            rank = 'Low'
        elif new_avg < 0.5:
            rank = 'Medium'
        elif new_avg < 0.8:
            rank = 'High'
        else:
            rank = 'Very High'
        
        cursor.execute('''
            UPDATE users 
            SET total_messages = ?, avg_toxicity = ?, toxicity_rank = ?
            WHERE user_id = ?
        ''', (new_total, new_avg, rank, user_id))
    else:
        rank = 'Low' if toxicity_score < 0.2 else 'Medium'
        cursor.execute('''
            INSERT INTO users (user_id, username, total_messages, avg_toxicity, toxicity_rank)
            VALUES (?, ?, 1, ?, ?)
        ''', (user_id, username, toxicity_score, rank))
    
    conn.commit()
    conn.close()

def log_message(message_id, user_id, content, scores):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO message_log 
        (message_id, user_id, content, toxicity_score, severe_toxicity, obscene, threat, insult, identity_attack)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (message_id, user_id, content, 
          scores['toxicity'], scores['severe_toxicity'], 
          scores['obscene'], scores['threat'], 
          scores['insult'], scores['identity_attack']))
    
    conn.commit()
    conn.close()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print('Bot is ready to analyze messages!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    scores = analyze_toxicity(message.content)
    
    if scores:
        user_id = message.author.id
        username = str(message.author)
        
        update_user_profile(user_id, username, scores['toxicity'])
        log_message(message.id, user_id, message.content, scores)
        
        if scores['toxicity'] > 0.7:
            print(f"⚠️  High toxicity detected from {username}: {message.content}")
            print(f"   Toxicity Score: {scores['toxicity']:.3f}")
        
        if scores['toxicity'] > 0.9:
            warning_msg = "⚠️ Warning: Your message was flagged as highly toxic. Please maintain respectful discourse."
            await message.channel.send(warning_msg)

if __name__ == "__main__":
    init_db()
    client.run(DISCORD_TOKEN)
