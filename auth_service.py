"""
Authentication Service - User Management
Handles user registration, login, and session management
"""

import os
import sqlite3
import hashlib
import secrets
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# Database path
AUTH_DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the users database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    
    # Create user_threads table to track which threads belong to which user
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            thread_id TEXT NOT NULL,
            title TEXT DEFAULT 'New Chat',
            is_pinned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, thread_id)
        )
    """)
    
    # Add is_pinned column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE user_threads ADD COLUMN is_pinned INTEGER DEFAULT 0")
    except:
        pass  # Column already exists
    
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = "langgraph_chatbot_salt_2024"  # In production, use per-user salt
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def register_user(username: str, password: str, email: str = None) -> Dict:
    """
    Register a new user.
    
    Returns:
        dict with success status and message
    """
    if not username or not password:
        return {"success": False, "error": "Username and password are required"}
    
    if len(username) < 3:
        return {"success": False, "error": "Username must be at least 3 characters"}
    
    if len(password) < 4:
        return {"success": False, "error": "Password must be at least 4 characters"}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username.lower(),))
        if cursor.fetchone():
            conn.close()
            return {"success": False, "error": "Username already exists"}
        
        # Insert new user
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username.lower(), password_hash, email)
        )
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "user_id": user_id,
            "username": username.lower(),
            "message": "Registration successful!"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def login_user(username: str, password: str) -> Dict:
    """
    Authenticate a user.
    
    Returns:
        dict with success status and user info
    """
    if not username or not password:
        return {"success": False, "error": "Username and password are required"}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute(
            "SELECT id, username FROM users WHERE username = ? AND password_hash = ?",
            (username.lower(), password_hash)
        )
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {"success": False, "error": "Invalid username or password"}
        
        # Update last login
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user["id"],)
        )
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "user_id": user["id"],
            "username": user["username"],
            "message": "Login successful!"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_user_thread(user_id: int, thread_id: str, title: str = "New Chat") -> bool:
    """Save a thread association for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT OR REPLACE INTO user_threads (user_id, thread_id, title, is_pinned) 
               VALUES (?, ?, ?, 0)""",
            (user_id, thread_id, title)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving user thread: {e}")
        return False


def update_thread_title(user_id: int, thread_id: str, title: str) -> bool:
    """Update the title of a user's thread."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE user_threads SET title = ? WHERE user_id = ? AND thread_id = ?",
            (title, user_id, thread_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating thread title: {e}")
        return False


def delete_thread(user_id: int, thread_id: str) -> bool:
    """Delete a thread for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM user_threads WHERE user_id = ? AND thread_id = ?",
            (user_id, thread_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting thread: {e}")
        return False


def pin_thread(user_id: int, thread_id: str) -> bool:
    """Pin a thread for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE user_threads SET is_pinned = 1 WHERE user_id = ? AND thread_id = ?",
            (user_id, thread_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error pinning thread: {e}")
        return False


def unpin_thread(user_id: int, thread_id: str) -> bool:
    """Unpin a thread for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE user_threads SET is_pinned = 0 WHERE user_id = ? AND thread_id = ?",
            (user_id, thread_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error unpinning thread: {e}")
        return False


def get_user_threads(user_id: int) -> list:
    """Get all threads for a specific user, pinned first."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT thread_id, title, is_pinned, created_at 
               FROM user_threads 
               WHERE user_id = ? 
               ORDER BY is_pinned DESC, created_at DESC""",
            (user_id,)
        )
        
        threads = [
            {
                "thread_id": row["thread_id"], 
                "title": row["title"],
                "is_pinned": bool(row["is_pinned"])
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return threads
    except Exception as e:
        print(f"Error getting user threads: {e}")
        return []


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user info by ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {"id": user["id"], "username": user["username"], "email": user["email"]}
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


# Initialize database when module is imported
init_db()


# For testing
if __name__ == "__main__":
    print("Auth Service initialized")
    print(f"Database path: {AUTH_DB_PATH}")
    
    # Test registration
    result = register_user("testuser", "test123")
    print(f"Register: {result}")
    
    # Test login
    result = login_user("testuser", "test123")
    print(f"Login: {result}")
