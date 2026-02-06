"""
Analytics Service - Usage Tracking and Statistics
Tracks token usage, tool calls, response times, and costs
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# Database path
ANALYTICS_DB_PATH = os.path.join(os.path.dirname(__file__), "analytics.db")

# Pricing (approximate, per 1K tokens)
PRICING = {
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
}


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the analytics database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create usage table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            thread_id TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            model TEXT DEFAULT 'gpt-3.5-turbo',
            tool_used TEXT,
            response_time_ms INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create tool usage table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tool_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tool_name TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def log_usage(user_id: int, thread_id: str, input_tokens: int, output_tokens: int, 
              model: str = "gpt-3.5-turbo", tool_used: str = None, response_time_ms: int = None):
    """Log a usage event."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        total_tokens = input_tokens + output_tokens
        
        cursor.execute("""
            INSERT INTO usage_logs (user_id, thread_id, input_tokens, output_tokens, 
                                   total_tokens, model, tool_used, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, thread_id, input_tokens, output_tokens, total_tokens, 
              model, tool_used, response_time_ms))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging usage: {e}")
        return False


def log_tool_usage(user_id: int, tool_name: str):
    """Log a tool usage event."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tool_usage (user_id, tool_name)
            VALUES (?, ?)
        """, (user_id, tool_name))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging tool usage: {e}")
        return False


def get_user_stats(user_id: int) -> Dict:
    """Get usage statistics for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total tokens and messages
        cursor.execute("""
            SELECT 
                COUNT(*) as total_messages,
                COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(AVG(response_time_ms), 0) as avg_response_time
            FROM usage_logs 
            WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        
        # Calculate estimated cost
        total_input = row["total_input_tokens"] or 0
        total_output = row["total_output_tokens"] or 0
        estimated_cost = (total_input / 1000 * PRICING["gpt-3.5-turbo"]["input"] + 
                         total_output / 1000 * PRICING["gpt-3.5-turbo"]["output"])
        
        # Get tool usage breakdown
        cursor.execute("""
            SELECT tool_name, COUNT(*) as count
            FROM tool_usage
            WHERE user_id = ?
            GROUP BY tool_name
            ORDER BY count DESC
            LIMIT 10
        """, (user_id,))
        
        tool_breakdown = {row["tool_name"]: row["count"] for row in cursor.fetchall()}
        
        # Get today's stats
        cursor.execute("""
            SELECT 
                COUNT(*) as messages_today,
                COALESCE(SUM(total_tokens), 0) as tokens_today
            FROM usage_logs 
            WHERE user_id = ? AND DATE(timestamp) = DATE('now')
        """, (user_id,))
        
        today = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_messages": row["total_messages"] or 0,
            "total_tokens": row["total_tokens"] or 0,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "estimated_cost": round(estimated_cost, 4),
            "avg_response_time_ms": round(row["avg_response_time"] or 0),
            "tool_breakdown": tool_breakdown,
            "messages_today": today["messages_today"] or 0,
            "tokens_today": today["tokens_today"] or 0
        }
        
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {
            "total_messages": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0,
            "avg_response_time_ms": 0,
            "tool_breakdown": {},
            "messages_today": 0,
            "tokens_today": 0
        }


def get_tool_usage_for_chart(user_id: int) -> tuple:
    """Get tool usage data formatted for a pie chart."""
    stats = get_user_stats(user_id)
    breakdown = stats.get("tool_breakdown", {})
    
    if not breakdown:
        return ["No tools used"], [1]
    
    labels = list(breakdown.keys())
    values = list(breakdown.values())
    
    return labels, values


# Initialize database when module is imported
init_db()


# For testing
if __name__ == "__main__":
    print("Analytics Service initialized")
    print(f"Database path: {ANALYTICS_DB_PATH}")
    
    # Test logging
    log_usage(1, "test-thread", 100, 200)
    log_tool_usage(1, "search_tool")
    
    # Test stats
    stats = get_user_stats(1)
    print(f"Stats: {stats}")
