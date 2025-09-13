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
        
        # Create admin_users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Create admin_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES admin_users (id)
            )
        ''')
        
        # Create courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT UNIQUE NOT NULL,
                course_name TEXT NOT NULL,
                program TEXT NOT NULL,
                year TEXT NOT NULL,
                semester TEXT NOT NULL,
                pdf_filename TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create programs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_code TEXT UNIQUE NOT NULL,
                program_name TEXT NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create system_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create announcements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                priority INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    # Admin authentication methods
    def register_admin(self, username, email, password, full_name, role="admin"):
        """Register a new admin user"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute("SELECT id FROM admin_users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                return {"success": False, "error": "Username or email already exists"}
            
            # Hash password and insert admin
            password_hash = self.hash_password(password)
            cursor.execute('''
                INSERT INTO admin_users (username, email, password_hash, full_name, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, full_name, role))
            
            admin_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {"success": True, "admin_id": admin_id, "message": "Admin registered successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Admin registration failed: {str(e)}"}
    
    def login_admin(self, username, password):
        """Login admin and return session token"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check admin credentials
            password_hash = self.hash_password(password)
            cursor.execute('''
                SELECT id, username, email, full_name, role FROM admin_users 
                WHERE username = ? AND password_hash = ? AND is_active = 1
            ''', (username, password_hash))
            
            admin = cursor.fetchone()
            if not admin:
                conn.close()
                return {"success": False, "error": "Invalid username or password"}
            
            admin_id, username, email, full_name, role = admin
            
            # Generate session token
            import secrets
            session_token = secrets.token_urlsafe(32)
            
            # Store session (expires in 8 hours for admin)
            from datetime import datetime, timedelta
            expires_at = datetime.now() + timedelta(hours=8)
            
            cursor.execute('''
                INSERT INTO admin_sessions (admin_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (admin_id, session_token, expires_at))
            
            # Update last login
            cursor.execute('''
                UPDATE admin_users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (admin_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "session_token": session_token,
                "admin": {
                    "id": admin_id,
                    "username": username,
                    "email": email,
                    "full_name": full_name,
                    "role": role
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Admin login failed: {str(e)}"}
    
    def verify_admin_session(self, session_token):
        """Verify if admin session token is valid and return admin info"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if session exists and is not expired
            cursor.execute('''
                SELECT a.id, a.username, a.email, a.full_name, a.role, s.expires_at
                FROM admin_users a
                JOIN admin_sessions s ON a.id = s.admin_id
                WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP AND a.is_active = 1
            ''', (session_token,))
            
            admin = cursor.fetchone()
            if not admin:
                conn.close()
                return {"success": False, "error": "Invalid or expired admin session"}
            
            admin_id, username, email, full_name, role, expires_at = admin
            
            conn.close()
            return {
                "success": True,
                "admin": {
                    "id": admin_id,
                    "username": username,
                    "email": email,
                    "full_name": full_name,
                    "role": role
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Admin session verification failed: {str(e)}"}
    
    def logout_admin(self, session_token):
        """Logout admin by removing session"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM admin_sessions WHERE session_token = ?", (session_token,))
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Admin logged out successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Admin logout failed: {str(e)}"}
    
    # Admin management methods
    def get_all_users(self, limit=100, offset=0):
        """Get all users with pagination"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, email, mobile, created_at, last_login, is_active
                FROM users 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            users = cursor.fetchall()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM users")
            total_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "success": True,
                "users": [{
                    "id": user[0],
                    "name": user[1],
                    "email": user[2],
                    "mobile": user[3],
                    "created_at": user[4],
                    "last_login": user[5],
                    "is_active": user[6]
                } for user in users],
                "total_count": total_count
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get users: {str(e)}"}
    
    def update_user_status(self, user_id, is_active):
        """Update user active status"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET is_active = ? WHERE id = ?
            ''', (is_active, user_id))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "User status updated successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to update user status: {str(e)}"}
    
    def get_assignment_statistics(self):
        """Get assignment statistics for admin dashboard"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Total assignments
            cursor.execute("SELECT COUNT(*) FROM user_assignments")
            total_assignments = cursor.fetchone()[0]
            
            # Total revenue
            cursor.execute("SELECT SUM(amount) FROM user_assignments WHERE status = 'completed'")
            total_revenue = cursor.fetchone()[0] or 0
            
            # Assignments by status
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM user_assignments 
                GROUP BY status
            ''')
            status_counts = dict(cursor.fetchall())
            
            # Recent assignments (last 7 days)
            cursor.execute('''
                SELECT COUNT(*) 
                FROM user_assignments 
                WHERE created_at >= datetime('now', '-7 days')
            ''')
            recent_assignments = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "success": True,
                "statistics": {
                    "total_assignments": total_assignments,
                    "total_revenue": total_revenue,
                    "status_counts": status_counts,
                    "recent_assignments": recent_assignments
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get statistics: {str(e)}"}
    
    def create_default_admin(self):
        """Create default admin user if none exists"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if any admin exists
            cursor.execute("SELECT COUNT(*) FROM admin_users")
            admin_count = cursor.fetchone()[0]
            
            if admin_count == 0:
                # Create default admin
                default_password = "admin123"  # Change this in production!
                password_hash = self.hash_password(default_password)
                
                cursor.execute('''
                    INSERT INTO admin_users (username, email, password_hash, full_name, role)
                    VALUES (?, ?, ?, ?, ?)
                ''', ("admin", "admin@ignou.com", password_hash, "System Administrator", "super_admin"))
                
                conn.commit()
                print("✅ Default admin created: username='admin', password='admin123'")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Failed to create default admin: {str(e)}")
    
    # Course management methods
    def add_course(self, course_code, course_name, program, year, semester, pdf_filename=None):
        """Add a new course"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if course code already exists
            cursor.execute("SELECT id FROM courses WHERE course_code = ?", (course_code,))
            if cursor.fetchone():
                return {"success": False, "error": "Course code already exists"}
            
            cursor.execute('''
                INSERT INTO courses (course_code, course_name, program, year, semester, pdf_filename)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (course_code, course_name, program, year, semester, pdf_filename))
            
            course_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {"success": True, "course_id": course_id, "message": "Course added successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to add course: {str(e)}"}
    
    def get_all_courses(self, limit=100, offset=0):
        """Get all courses with pagination"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, course_code, course_name, program, year, semester, pdf_filename, is_active, created_at
                FROM courses 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            courses = cursor.fetchall()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM courses")
            total_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "success": True,
                "courses": [{
                    "id": course[0],
                    "course_code": course[1],
                    "course_name": course[2],
                    "program": course[3],
                    "year": course[4],
                    "semester": course[5],
                    "pdf_filename": course[6],
                    "is_active": course[7],
                    "created_at": course[8]
                } for course in courses],
                "total_count": total_count
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get courses: {str(e)}"}
    
    def update_course(self, course_id, course_code=None, course_name=None, program=None, year=None, semester=None, pdf_filename=None, is_active=None):
        """Update course information"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Build dynamic update query
            updates = []
            params = []
            
            if course_code is not None:
                updates.append("course_code = ?")
                params.append(course_code)
            if course_name is not None:
                updates.append("course_name = ?")
                params.append(course_name)
            if program is not None:
                updates.append("program = ?")
                params.append(program)
            if year is not None:
                updates.append("year = ?")
                params.append(year)
            if semester is not None:
                updates.append("semester = ?")
                params.append(semester)
            if pdf_filename is not None:
                updates.append("pdf_filename = ?")
                params.append(pdf_filename)
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(is_active)
            
            if not updates:
                return {"success": False, "error": "No fields to update"}
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(course_id)
            
            query = f"UPDATE courses SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Course updated successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to update course: {str(e)}"}
    
    def delete_course(self, course_id):
        """Delete a course"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Course deleted successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to delete course: {str(e)}"}
    
    # Program management methods
    def add_program(self, program_code, program_name, description=None):
        """Add a new program"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if program code already exists
            cursor.execute("SELECT id FROM programs WHERE program_code = ?", (program_code,))
            if cursor.fetchone():
                return {"success": False, "error": "Program code already exists"}
            
            cursor.execute('''
                INSERT INTO programs (program_code, program_name, description)
                VALUES (?, ?, ?)
            ''', (program_code, program_name, description))
            
            program_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {"success": True, "program_id": program_id, "message": "Program added successfully"}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to add program: {str(e)}"}
    
    def get_all_programs(self):
        """Get all programs"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, program_code, program_name, description, is_active, created_at
                FROM programs 
                WHERE is_active = 1
                ORDER BY program_name
            ''')
            
            programs = cursor.fetchall()
            conn.close()
            
            return {
                "success": True,
                "programs": [{
                    "id": program[0],
                    "program_code": program[1],
                    "program_name": program[2],
                    "description": program[3],
                    "is_active": program[4],
                    "created_at": program[5]
                } for program in programs]
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get programs: {str(e)}"}
    
    def initialize_default_data(self):
        """Initialize default programs and courses"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if programs already exist
            cursor.execute("SELECT COUNT(*) FROM programs")
            program_count = cursor.fetchone()[0]
            
            if program_count == 0:
                # Add default programs
                default_programs = [
                    ("MBA", "Master of Business Administration", "MBA program for working professionals"),
                    ("MCA", "Master of Computer Applications", "MCA program for computer science graduates"),
                    ("BCA", "Bachelor of Computer Applications", "BCA program for computer applications"),
                    ("BBA", "Bachelor of Business Administration", "BBA program for business administration"),
                    ("BTECH", "Bachelor of Technology", "B.Tech program for engineering"),
                    ("MTECH", "Master of Technology", "M.Tech program for engineering")
                ]
                
                for program_code, program_name, description in default_programs:
                    cursor.execute('''
                        INSERT INTO programs (program_code, program_name, description)
                        VALUES (?, ?, ?)
                    ''', (program_code, program_name, description))
                
                print("✅ Default programs created")
            
            # Check if courses already exist
            cursor.execute("SELECT COUNT(*) FROM courses")
            course_count = cursor.fetchone()[0]
            
            if course_count == 0:
                # Add some default courses
                default_courses = [
                    ("MMPC-001", "Management Functions and Behaviour", "MBA", "1st Year", "1st Semester", "MMPC-001.pdf"),
                    ("MMPC-002", "Human Resource Management", "MBA", "1st Year", "1st Semester", "MMPC-002.pdf"),
                    ("MMPC-003", "Economics for Managers", "MBA", "1st Year", "1st Semester", "MMPC-003.pdf"),
                    ("MCS-011", "Problem Solving and Programming", "MCA", "1st Year", "1st Semester", "MCS-011.pdf"),
                    ("MCS-012", "Computer Organization and Assembly Language Programming", "MCA", "1st Year", "1st Semester", "MCS-012.pdf"),
                    ("BCS-011", "Computer Basics and PC Software", "BCA", "1st Year", "1st Semester", "BCS-011.pdf"),
                    ("BCS-012", "Basic Mathematics", "BCA", "1st Year", "1st Semester", "BCS-012.pdf")
                ]
                
                for course_code, course_name, program, year, semester, pdf_filename in default_courses:
                    cursor.execute('''
                        INSERT INTO courses (course_code, course_name, program, year, semester, pdf_filename)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (course_code, course_name, program, year, semester, pdf_filename))
                
                print("✅ Default courses created")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Failed to initialize default data: {str(e)}")

# Initialize database
db = Database()
# Create default admin if none exists
db.create_default_admin()
# Initialize default data
db.initialize_default_data()
