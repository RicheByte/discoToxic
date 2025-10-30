# dashboard.py
from flask import Flask, render_template, request, jsonify
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json

app = Flask(__name__)
DB_NAME = 'toxicity_tracker.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/users')
def get_users():
    conn = get_db_connection()
    
    # Get user statistics
    users = conn.execute('''
        SELECT u.*, 
               COUNT(ml.message_id) as total_messages,
               MAX(ml.timestamp) as last_activity
        FROM users u
        LEFT JOIN message_log ml ON u.user_id = ml.user_id
        GROUP BY u.user_id
        ORDER BY u.avg_toxicity DESC
    ''').fetchall()
    
    conn.close()
    
    users_list = []
    for user in users:
        users_list.append({
            'user_id': user['user_id'],
            'username': user['username'],
            'total_messages': user['total_messages'],
            'avg_toxicity': round(user['avg_toxicity'], 3),
            'toxicity_rank': user['toxicity_rank'],
            'last_activity': user['last_activity']
        })
    
    return jsonify(users_list)

@app.route('/api/user/<int:user_id>')
def get_user_detail(user_id):
    conn = get_db_connection()
    
    # User basic info
    user = conn.execute('''
        SELECT * FROM users WHERE user_id = ?
    ''', (user_id,)).fetchone()
    
    # Recent messages with scores
    messages = conn.execute('''
        SELECT * FROM message_log 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 50
    ''', (user_id,)).fetchall()
    
    # Daily toxicity trend (last 30 days)
    trend_data = conn.execute('''
        SELECT DATE(timestamp) as date,
               AVG(toxicity_score) as avg_toxicity,
               COUNT(*) as message_count
        FROM message_log 
        WHERE user_id = ? AND timestamp >= DATE('now', '-30 days')
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''', (user_id,)).fetchall()
    
    # Toxicity breakdown
    toxicity_breakdown = conn.execute('''
        SELECT 
            AVG(toxicity_score) as toxicity,
            AVG(severe_toxicity) as severe_toxicity,
            AVG(obscene) as obscene,
            AVG(threat) as threat,
            AVG(insult) as insult,
            AVG(identity_attack) as identity_attack
        FROM message_log 
        WHERE user_id = ?
    ''', (user_id,)).fetchone()
    
    conn.close()
    
    return jsonify({
        'user_info': dict(user),
        'recent_messages': [dict(msg) for msg in messages],
        'trend_data': [dict(trend) for trend in trend_data],
        'toxicity_breakdown': dict(toxicity_breakdown)
    })

@app.route('/api/overview')
def get_overview():
    conn = get_db_connection()
    
    # Overall statistics
    stats = conn.execute('''
        SELECT 
            COUNT(DISTINCT user_id) as total_users,
            COUNT(*) as total_messages,
            AVG(toxicity_score) as overall_toxicity,
            SUM(CASE WHEN toxicity_score > 0.7 THEN 1 ELSE 0 END) as toxic_messages,
            SUM(CASE WHEN toxicity_score > 0.9 THEN 1 ELSE 0 END) as severe_toxic_messages
        FROM message_log
    ''').fetchone()
    
    # Daily activity (last 7 days)
    daily_activity = conn.execute('''
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as message_count,
            AVG(toxicity_score) as avg_toxicity
        FROM message_log 
        WHERE timestamp >= DATE('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''').fetchall()
    
    # Toxicity distribution
    toxicity_dist = conn.execute('''
        SELECT 
            CASE 
                WHEN toxicity_score < 0.2 THEN 'Low'
                WHEN toxicity_score < 0.5 THEN 'Medium'
                WHEN toxicity_score < 0.8 THEN 'High'
                ELSE 'Very High'
            END as toxicity_level,
            COUNT(*) as count
        FROM message_log 
        GROUP BY toxicity_level
        ORDER BY 
            CASE toxicity_level
                WHEN 'Low' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'High' THEN 3
                WHEN 'Very High' THEN 4
            END
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'stats': dict(stats),
        'daily_activity': [dict(day) for day in daily_activity],
        'toxicity_distribution': [dict(dist) for dist in toxicity_dist]
    })

@app.route('/api/leaderboard')
def get_leaderboard():
    conn = get_db_connection()
    
    # Most toxic users
    most_toxic = conn.execute('''
        SELECT username, avg_toxicity, total_messages, toxicity_rank
        FROM users 
        WHERE total_messages >= 5
        ORDER BY avg_toxicity DESC 
        LIMIT 10
    ''').fetchall()
    
    # Least toxic users
    least_toxic = conn.execute('''
        SELECT username, avg_toxicity, total_messages, toxicity_rank
        FROM users 
        WHERE total_messages >= 5
        ORDER BY avg_toxicity ASC 
        LIMIT 10
    ''').fetchall()
    
    # Most active users
    most_active = conn.execute('''
        SELECT username, total_messages, avg_toxicity
        FROM users 
        ORDER BY total_messages DESC 
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'most_toxic': [dict(user) for user in most_toxic],
        'least_toxic': [dict(user) for user in least_toxic],
        'most_active': [dict(user) for user in most_active]
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)