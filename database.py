import sqlite3
import hashlib
import os
from datetime import datetime

class Database:
    def __init__(self, db_name="users.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                mobile TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Create user_sessions table for tracking login sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create user_assignments table to track assignment history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subjects TEXT NOT NULL,
                courses TEXT,
                transaction_id TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Ensure new column 'courses' exists for migration from 'subjects'
        cursor.execute("PRAGMA table_info(user_assignments)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'courses' not in columns:
            try:
                cursor.execute("ALTER TABLE user_assignments ADD COLUMN courses TEXT")
            except Exception:
                pass
        
        # Backfill courses from subjects where missing
        try:
            cursor.execute("UPDATE user_assignments SET courses = subjects WHERE (courses IS NULL OR courses = '') AND subjects IS NOT NULL")
        except Exception:
            pass
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, name, email, mobile, password):
        """Register a new user"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return {"success": False, "error": "Email already registered"}
            
            # Check if mobile already exists
            cursor.execute("SELECT id FROM users WHERE mobile = ?", (mobile,))
            if cursor.fetchone():
                return {"success": False, "error": "Mobile number already registered"}
            
            # Hash password and insert user
            password_hash = self.hash_password(password)
            cursor.execute('''
                INSERT INTO users (name, email, mobile, password_hash)
                VALUES (?, ?, ?, ?)
            ''', (name, email, mobile, password_hash))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {"success": True, "user_id": user_id, "message": "User registered successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Registration failed: {str(e)}"}
    
    def login_user(self, email, password):
        """Login user and return session token"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check user credentials
            password_hash = self.hash_password(password)
            cursor.execute('''
                SELECT id, name, email, mobile FROM users 
                WHERE email = ? AND password_hash = ? AND is_active = 1
            ''', (email, password_hash))
            
            user = cursor.fetchone()
            if not user:
                conn.close()
                return {"success": False, "error": "Invalid email or password"}
            
            user_id, name, email, mobile = user
            
            # Generate session token
            import secrets
            session_token = secrets.token_urlsafe(32)
            
            # Store session (expires in 24 hours)
            from datetime import datetime, timedelta
            expires_at = datetime.now() + timedelta(hours=24)
            
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at))
            
            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "session_token": session_token,
                "user": {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "mobile": mobile
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Login failed: {str(e)}"}
    
    def verify_session(self, session_token):
        """Verify if session token is valid and return user info"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if session exists and is not expired
            cursor.execute('''
                SELECT u.id, u.name, u.email, u.mobile, s.expires_at
                FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP
            ''', (session_token,))
            
            user = cursor.fetchone()
            if not user:
                conn.close()
                return {"success": False, "error": "Invalid or expired session"}
            
            user_id, name, email, mobile, expires_at = user
            
            conn.close()
            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "mobile": mobile
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Session verification failed: {str(e)}"}
    
    def logout_user(self, session_token):
        """Logout user by removing session"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM user_sessions WHERE session_token = ?", (session_token,))
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Logged out successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Logout failed: {str(e)}"}
    
    def save_assignment_request(self, user_id, courses, transaction_id, amount):
        """Save assignment request to database with courses"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Always store into 'courses'. Keep 'subjects' in sync for backward compatibility
            courses_csv = ','.join(courses)
            try:
                cursor.execute('''
                    INSERT INTO user_assignments (user_id, courses, subjects, transaction_id, amount)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, courses_csv, courses_csv, transaction_id, amount))
            except Exception:
                # Fallback if older schema without 'courses'
                cursor.execute('''
                    INSERT INTO user_assignments (user_id, subjects, transaction_id, amount)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, courses_csv, transaction_id, amount))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Assignment request saved"}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to save assignment: {str(e)}"}

# Initialize database
db = Database()
