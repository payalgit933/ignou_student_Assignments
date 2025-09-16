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
                pdf_filename_en TEXT,
                pdf_filename_hi TEXT,
                credits INTEGER,
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

        # Create study_centers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_centers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                center_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT,
                state TEXT,
                pincode TEXT,
                phone TEXT,
                email TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # Migrate courses table to add medium-specific filenames and credits if missing
        cursor.execute("PRAGMA table_info(courses)")
        course_columns = [row[1] for row in cursor.fetchall()]
        if 'pdf_filename_en' not in course_columns:
            try:
                cursor.execute("ALTER TABLE courses ADD COLUMN pdf_filename_en TEXT")
            except Exception:
                pass
        if 'pdf_filename_hi' not in course_columns:
            try:
                cursor.execute("ALTER TABLE courses ADD COLUMN pdf_filename_hi TEXT")
            except Exception:
                pass
        if 'credits' not in course_columns:
            try:
                cursor.execute("ALTER TABLE courses ADD COLUMN credits INTEGER")
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
    def add_course(self, course_code, course_name, program, year, semester, pdf_filename=None, pdf_filename_en=None, pdf_filename_hi=None, credits=None):
        """Add a new course"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if course code already exists
            cursor.execute("SELECT id FROM courses WHERE course_code = ?", (course_code,))
            if cursor.fetchone():
                return {"success": False, "error": "Course code already exists"}
            
            cursor.execute('''
                INSERT INTO courses (course_code, course_name, program, year, semester, pdf_filename, pdf_filename_en, pdf_filename_hi, credits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (course_code, course_name, program, year, semester, pdf_filename, pdf_filename_en, pdf_filename_hi, credits))
            
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
                SELECT id, course_code, course_name, program, year, semester, pdf_filename, pdf_filename_en, pdf_filename_hi, credits, is_active, created_at
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
                    "pdf_filename_en": course[7],
                    "pdf_filename_hi": course[8],
                    "credits": course[9],
                    "is_active": course[10],
                    "created_at": course[11]
                } for course in courses],
                "total_count": total_count
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get courses: {str(e)}"}
    
    def get_courses_by_filter(self, program=None, year=None, semester=None, is_active=True):
        """Get courses filtered by program, year, and semester"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Build dynamic query
            query = '''
                SELECT id, course_code, course_name, program, year, semester, pdf_filename, pdf_filename_en, pdf_filename_hi, credits, is_active, created_at
                FROM courses 
                WHERE 1=1
            '''
            params = []
            
            if program:
                query += ' AND program = ?'
                params.append(program)
            
            if year:
                query += ' AND year = ?'
                params.append(year)
            
            if semester:
                if semester == 'Yearly':
                    # Include records saved with empty semester for yearly
                    query += " AND (semester = ? OR semester = '')"
                    params.append('Yearly')
                else:
                query += ' AND semester = ?'
                params.append(semester)
            
            if is_active is not None:
                query += ' AND is_active = ?'
                params.append(is_active)
            
            query += ' ORDER BY course_code'
            
            cursor.execute(query, params)
            courses = cursor.fetchall()
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
                    "pdf_filename_en": course[7],
                    "pdf_filename_hi": course[8],
                    "credits": course[9],
                    "is_active": course[10],
                    "created_at": course[11]
                } for course in courses]
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get filtered courses: {str(e)}"}
    
    def update_course(self, course_id, course_code=None, course_name=None, program=None, year=None, semester=None, pdf_filename=None, pdf_filename_en=None, pdf_filename_hi=None, credits=None, is_active=None):
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
            if pdf_filename_en is not None:
                updates.append("pdf_filename_en = ?")
                params.append(pdf_filename_en)
            if pdf_filename_hi is not None:
                updates.append("pdf_filename_hi = ?")
                params.append(pdf_filename_hi)
            if credits is not None:
                updates.append("credits = ?")
                params.append(credits)
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

    def get_course_by_code(self, course_code):
        """Fetch a single course by its code"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, course_code, course_name, program, year, semester,
                       pdf_filename, pdf_filename_en, pdf_filename_hi, credits, is_active
                FROM courses
                WHERE course_code = ? LIMIT 1
            ''', (course_code,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return {"success": False, "error": "Course not found"}
            return {
                "success": True,
                "course": {
                    "id": row[0],
                    "course_code": row[1],
                    "course_name": row[2],
                    "program": row[3],
                    "year": row[4],
                    "semester": row[5],
                    "pdf_filename": row[6],
                    "pdf_filename_en": row[7],
                    "pdf_filename_hi": row[8],
                    "credits": row[9],
                    "is_active": row[10]
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get course: {str(e)}"}
    # Study center management methods
    def add_study_center(self, center_code, name, address, city=None, state=None, pincode=None, phone=None, email=None):
        """Add a new study center"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM study_centers WHERE center_code = ?", (center_code,))
            if cursor.fetchone():
                return {"success": False, "error": "Study center code already exists"}
            cursor.execute('''
                INSERT INTO study_centers (center_code, name, address, city, state, pincode, phone, email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (center_code, name, address, city, state, pincode, phone, email))
            center_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return {"success": True, "center_id": center_id, "message": "Study center added successfully"}
        except Exception as e:
            return {"success": False, "error": f"Failed to add study center: {str(e)}"}

    def get_study_centers(self, limit=100, offset=0):
        """Get all study centers with pagination"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, center_code, name, address, city, state, pincode, phone, email, is_active, created_at
                FROM study_centers
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            centers = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) FROM study_centers")
            total_count = cursor.fetchone()[0]
            conn.close()
            return {
                "success": True,
                "centers": [{
                    "id": c[0],
                    "center_code": c[1],
                    "name": c[2],
                    "address": c[3],
                    "city": c[4],
                    "state": c[5],
                    "pincode": c[6],
                    "phone": c[7],
                    "email": c[8],
                    "is_active": c[9],
                    "created_at": c[10]
                } for c in centers],
                "total_count": total_count
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get study centers: {str(e)}"}

    def update_study_center(self, center_id, center_code=None, name=None, address=None, city=None, state=None, pincode=None, phone=None, email=None, is_active=None):
        """Update study center information"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            updates = []
            params = []
            if center_code is not None:
                updates.append("center_code = ?")
                params.append(center_code)
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if address is not None:
                updates.append("address = ?")
                params.append(address)
            if city is not None:
                updates.append("city = ?")
                params.append(city)
            if state is not None:
                updates.append("state = ?")
                params.append(state)
            if pincode is not None:
                updates.append("pincode = ?")
                params.append(pincode)
            if phone is not None:
                updates.append("phone = ?")
                params.append(phone)
            if email is not None:
                updates.append("email = ?")
                params.append(email)
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(is_active)
            if not updates:
                return {"success": False, "error": "No fields to update"}
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(center_id)
            query = f"UPDATE study_centers SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            return {"success": True, "message": "Study center updated successfully"}
        except Exception as e:
            return {"success": False, "error": f"Failed to update study center: {str(e)}"}

    def delete_study_center(self, center_id):
        """Delete a study center"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM study_centers WHERE id = ?", (center_id,))
            conn.commit()
            conn.close()
            return {"success": True, "message": "Study center deleted successfully"}
        except Exception as e:
            return {"success": False, "error": f"Failed to delete study center: {str(e)}"}
    
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
                # Add comprehensive course data for different years and semesters
                default_courses = [
                    # MBA 1st Year 1st Semester
                    ("MMPC-001", "Management Functions and Behaviour", "MBA", "1st Year", "1st Semester", "MMPC-001.pdf"),
                    ("MMPC-002", "Human Resource Management", "MBA", "1st Year", "1st Semester", "MMPC-002.pdf"),
                    ("MMPC-003", "Economics for Managers", "MBA", "1st Year", "1st Semester", "MMPC-003.pdf"),
                    ("MMPC-004", "Accounting for Managers", "MBA", "1st Year", "1st Semester", "MMPC-004.pdf"),
                    ("MMPC-005", "Quantitative Methods for Management", "MBA", "1st Year", "1st Semester", "MMPC-005.pdf"),
                    
                    # MBA 1st Year 2nd Semester
                    ("MMPC-006", "Marketing for Managers", "MBA", "1st Year", "2nd Semester", "MMPC-006.pdf"),
                    ("MMPC-007", "Information Systems for Managers", "MBA", "1st Year", "2nd Semester", "MMPC-007.pdf"),
                    ("MMPC-008", "Organizational Behaviour", "MBA", "1st Year", "2nd Semester", "MMPC-008.pdf"),
                    ("MMPC-009", "Business Environment", "MBA", "1st Year", "2nd Semester", "MMPC-009.pdf"),
                    ("MMPC-010", "Managerial Economics", "MBA", "1st Year", "2nd Semester", "MMPC-010.pdf"),
                    
                    # MBA 2nd Year 1st Semester
                    ("MMPC-011", "Strategic Management", "MBA", "2nd Year", "1st Semester", "MMPC-011.pdf"),
                    ("MMPC-012", "Financial Management", "MBA", "2nd Year", "1st Semester", "MMPC-012.pdf"),
                    ("MMPC-013", "Operations Management", "MBA", "2nd Year", "1st Semester", "MMPC-013.pdf"),
                    ("MMPC-014", "Business Research Methods", "MBA", "2nd Year", "1st Semester", "MMPC-014.pdf"),
                    ("MMPC-015", "International Business", "MBA", "2nd Year", "1st Semester", "MMPC-015.pdf"),
                    
                    # MBA 2nd Year 2nd Semester
                    ("MMPC-016", "Project Management", "MBA", "2nd Year", "2nd Semester", "MMPC-016.pdf"),
                    ("MMPC-017", "Entrepreneurship Development", "MBA", "2nd Year", "2nd Semester", "MMPC-017.pdf"),
                    ("MMPC-018", "Business Ethics and Corporate Governance", "MBA", "2nd Year", "2nd Semester", "MMPC-018.pdf"),
                    ("MMPC-019", "Total Quality Management", "MBA", "2nd Year", "2nd Semester", "MMPC-019.pdf"),
                    ("MMPC-020", "Business Communication", "MBA", "2nd Year", "2nd Semester", "MMPC-020.pdf"),
                    
                    # MCA 1st Year 1st Semester
                    ("MCS-011", "Problem Solving and Programming", "MCA", "1st Year", "1st Semester", "MCS-011.pdf"),
                    ("MCS-012", "Computer Organization and Assembly Language Programming", "MCA", "1st Year", "1st Semester", "MCS-012.pdf"),
                    ("MCS-013", "Discrete Mathematics", "MCA", "1st Year", "1st Semester", "MCS-013.pdf"),
                    ("MCS-014", "Systems Analysis and Design", "MCA", "1st Year", "1st Semester", "MCS-014.pdf"),
                    ("MCS-015", "Communication Skills", "MCA", "1st Year", "1st Semester", "MCS-015.pdf"),
                    
                    # MCA 1st Year 2nd Semester
                    ("MCS-021", "Data and File Structures", "MCA", "1st Year", "2nd Semester", "MCS-021.pdf"),
                    ("MCS-022", "Database Management Systems", "MCA", "1st Year", "2nd Semester", "MCS-022.pdf"),
                    ("MCS-023", "Introduction to Database Management Systems", "MCA", "1st Year", "2nd Semester", "MCS-023.pdf"),
                    ("MCS-024", "Object Oriented Technologies and Java Programming", "MCA", "1st Year", "2nd Semester", "MCS-024.pdf"),
                    ("MCS-025", "Computer Networks", "MCA", "1st Year", "2nd Semester", "MCS-025.pdf"),
                    
                    # MCA 2nd Year 1st Semester
                    ("MCS-031", "Design and Analysis of Algorithms", "MCA", "2nd Year", "1st Semester", "MCS-031.pdf"),
                    ("MCS-032", "Object Oriented Analysis and Design", "MCA", "2nd Year", "1st Semester", "MCS-032.pdf"),
                    ("MCS-033", "Advanced Discrete Mathematics", "MCA", "2nd Year", "1st Semester", "MCS-033.pdf"),
                    ("MCS-034", "Software Engineering", "MCA", "2nd Year", "1st Semester", "MCS-034.pdf"),
                    ("MCS-035", "Accountancy and Financial Management", "MCA", "2nd Year", "1st Semester", "MCS-035.pdf"),
                    
                    # MCA 2nd Year 2nd Semester
                    ("MCS-041", "Operating Systems", "MCA", "2nd Year", "2nd Semester", "MCS-041.pdf"),
                    ("MCS-042", "Data Communication and Computer Networks", "MCA", "2nd Year", "2nd Semester", "MCS-042.pdf"),
                    ("MCS-043", "Advanced Database Management Systems", "MCA", "2nd Year", "2nd Semester", "MCS-043.pdf"),
                    ("MCS-044", "Mini Project", "MCA", "2nd Year", "2nd Semester", "MCS-044.pdf"),
                    ("MCS-045", "Unix Programming", "MCA", "2nd Year", "2nd Semester", "MCS-045.pdf"),
                    
                    # BCA 1st Year 1st Semester
                    ("BCS-011", "Computer Basics and PC Software", "BCA", "1st Year", "1st Semester", "BCS-011.pdf"),
                    ("BCS-012", "Basic Mathematics", "BCA", "1st Year", "1st Semester", "BCS-012.pdf"),
                    ("BCS-013", "Programming Methodology Using C", "BCA", "1st Year", "1st Semester", "BCS-013.pdf"),
                    ("BCS-014", "Computer System Architecture", "BCA", "1st Year", "1st Semester", "BCS-014.pdf"),
                    ("BCS-015", "Communication Skills", "BCA", "1st Year", "1st Semester", "BCS-015.pdf"),
                    
                    # BCA 1st Year 2nd Semester
                    ("BCS-021", "Data Structures and Algorithms", "BCA", "1st Year", "2nd Semester", "BCS-021.pdf"),
                    ("BCS-022", "Assembly Language Programming", "BCA", "1st Year", "2nd Semester", "BCS-021.pdf"),
                    ("BCS-023", "Computer Networks", "BCA", "1st Year", "2nd Semester", "BCS-023.pdf"),
                    ("BCS-024", "Database Management Systems", "BCA", "1st Year", "2nd Semester", "BCS-024.pdf"),
                    ("BCS-025", "Operating Systems", "BCA", "1st Year", "2nd Semester", "BCS-025.pdf"),
                    
                    # BCA 2nd Year 1st Semester
                    ("BCS-031", "Programming in Java", "BCA", "2nd Year", "1st Semester", "BCS-031.pdf"),
                    ("BCS-032", "Web Programming", "BCA", "2nd Year", "1st Semester", "BCS-032.pdf"),
                    ("BCS-033", "Software Engineering", "BCA", "2nd Year", "1st Semester", "BCS-033.pdf"),
                    ("BCS-034", "Computer Graphics", "BCA", "2nd Year", "1st Semester", "BCS-034.pdf"),
                    ("BCS-035", "Internet Concepts and Web Design", "BCA", "2nd Year", "1st Semester", "BCS-035.pdf"),
                    
                    # BCA 2nd Year 2nd Semester
                    ("BCS-041", "Fundamentals of Computer Networks", "BCA", "2nd Year", "2nd Semester", "BCS-041.pdf"),
                    ("BCS-042", "Introduction to Algorithm Design", "BCA", "2nd Year", "2nd Semester", "BCS-042.pdf"),
                    ("BCS-043", "Introduction to Database Management Systems", "BCA", "2nd Year", "2nd Semester", "BCS-043.pdf"),
                    ("BCS-044", "Statistical Techniques", "BCA", "2nd Year", "2nd Semester", "BCS-044.pdf"),
                    ("BCS-045", "Introduction to Software Engineering", "BCA", "2nd Year", "2nd Semester", "BCS-045.pdf"),
                    
                    # BCA 3rd Year 1st Semester
                    ("BCS-051", "Introduction to Programming Logic", "BCA", "3rd Year", "1st Semester", "BCS-051.pdf"),
                    ("BCS-052", "Network Programming and Administration", "BCA", "3rd Year", "1st Semester", "BCS-052.pdf"),
                    ("BCS-053", "Web Technologies", "BCA", "3rd Year", "1st Semester", "BCS-053.pdf"),
                    ("BCS-054", "Computer Oriented Numerical Methods", "BCA", "3rd Year", "1st Semester", "BCS-054.pdf"),
                    ("BCS-055", "Business Communication", "BCA", "3rd Year", "1st Semester", "BCS-055.pdf"),
                    
                    # BCA 3rd Year 2nd Semester
                    ("BCS-061", "Computer Networks and Internet Technology", "BCA", "3rd Year", "2nd Semester", "BCS-061.pdf"),
                    ("BCS-062", "E-Commerce", "BCA", "3rd Year", "2nd Semester", "BCS-062.pdf"),
                    ("BCS-063", "Unix Programming", "BCA", "3rd Year", "2nd Semester", "BCS-063.pdf"),
                    ("BCS-064", "Introduction to Microprocessors", "BCA", "3rd Year", "2nd Semester", "BCS-064.pdf"),
                    ("BCS-065", "Computer Graphics and Multimedia", "BCA", "3rd Year", "2nd Semester", "BCS-065.pdf"),
                    
                    # BBA 1st Year 1st Semester
                    ("BBAR-101", "Business Communication", "BBA", "1st Year", "1st Semester", "BBAR-101.pdf"),
                    ("BBAR-102", "Principles of Management", "BBA", "1st Year", "1st Semester", "BBAR-102.pdf"),
                    ("BBAR-103", "Business Mathematics", "BBA", "1st Year", "1st Semester", "BBAR-103.pdf"),
                    ("BBAR-104", "Financial Accounting", "BBA", "1st Year", "1st Semester", "BBAR-104.pdf"),
                    ("BBAR-105", "Business Environment", "BBA", "1st Year", "1st Semester", "BBAR-105.pdf"),
                    
                    # BBA 1st Year 2nd Semester
                    ("BBAR-106", "Business Economics", "BBA", "1st Year", "2nd Semester", "BBAR-106.pdf"),
                    ("BBAR-107", "Computer Applications in Business", "BBA", "1st Year", "2nd Semester", "BBAR-107.pdf"),
                    ("BBAR-108", "Organizational Behaviour", "BBA", "1st Year", "2nd Semester", "BBAR-108.pdf"),
                    ("BBAR-109", "Business Statistics", "BBA", "1st Year", "2nd Semester", "BBAR-109.pdf"),
                    ("BBAR-110", "Marketing Management", "BBA", "1st Year", "2nd Semester", "BBAR-110.pdf"),
                    
                    # BBA 2nd Year 1st Semester
                    ("BBAR-201", "Human Resource Management", "BBA", "2nd Year", "1st Semester", "BBAR-201.pdf"),
                    ("BBAR-202", "Financial Management", "BBA", "2nd Year", "1st Semester", "BBAR-202.pdf"),
                    ("BBAR-203", "Production and Operations Management", "BBA", "2nd Year", "1st Semester", "BBAR-203.pdf"),
                    ("BBAR-204", "Business Research Methods", "BBA", "2nd Year", "1st Semester", "BBAR-204.pdf"),
                    ("BBAR-205", "Entrepreneurship Development", "BBA", "2nd Year", "1st Semester", "BBAR-205.pdf"),
                    
                    # BBA 2nd Year 2nd Semester
                    ("BBAR-206", "International Business", "BBA", "2nd Year", "2nd Semester", "BBAR-206.pdf"),
                    ("BBAR-207", "Strategic Management", "BBA", "2nd Year", "2nd Semester", "BBAR-207.pdf"),
                    ("BBAR-208", "Business Ethics and Corporate Governance", "BBA", "2nd Year", "2nd Semester", "BBAR-208.pdf"),
                    ("BBAR-209", "Project Management", "BBA", "2nd Year", "2nd Semester", "BBAR-209.pdf"),
                    ("BBAR-210", "E-Commerce", "BBA", "2nd Year", "2nd Semester", "BBAR-210.pdf"),
                    
                    # BBA 3rd Year 1st Semester
                    ("BBAR-301", "Consumer Behaviour", "BBA", "3rd Year", "1st Semester", "BBAR-301.pdf"),
                    ("BBAR-302", "Investment Management", "BBA", "3rd Year", "1st Semester", "BBAR-302.pdf"),
                    ("BBAR-303", "Supply Chain Management", "BBA", "3rd Year", "1st Semester", "BBAR-303.pdf"),
                    ("BBAR-304", "Digital Marketing", "BBA", "3rd Year", "1st Semester", "BBAR-304.pdf"),
                    ("BBAR-305", "Business Analytics", "BBA", "3rd Year", "1st Semester", "BBAR-305.pdf"),
                    
                    # BBA 3rd Year 2nd Semester
                    ("BBAR-306", "International Marketing", "BBA", "3rd Year", "2nd Semester", "BBAR-306.pdf"),
                    ("BBAR-307", "Risk Management", "BBA", "3rd Year", "2nd Semester", "BBAR-307.pdf"),
                    ("BBAR-308", "Quality Management", "BBA", "3rd Year", "2nd Semester", "BBAR-308.pdf"),
                    ("BBAR-309", "Business Process Reengineering", "BBA", "3rd Year", "2nd Semester", "BBAR-309.pdf"),
                    ("BBAR-310", "Leadership and Team Management", "BBA", "3rd Year", "2nd Semester", "BBAR-310.pdf")
                ]
                
                for course_code, course_name, program, year, semester, pdf_filename in default_courses:
                    cursor.execute('''
                        INSERT INTO courses (course_code, course_name, program, year, semester, pdf_filename)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (course_code, course_name, program, year, semester, pdf_filename))
                
                print("✅ Default courses created")
                
                # Add yearly courses for different programs and academic years
                yearly_courses = [
                    # MBA Yearly Courses - 1st Year
                    ("MMPC-101", "Management Functions and Behaviour", "MBA", "1st Year", "Yearly", "MMPC-101.pdf"),
                    ("MMPC-102", "Human Resource Management", "MBA", "1st Year", "Yearly", "MMPC-102.pdf"),
                    ("MMPC-103", "Economics for Managers", "MBA", "1st Year", "Yearly", "MMPC-103.pdf"),
                    ("MMPC-104", "Strategic Management", "MBA", "1st Year", "Yearly", "MMPC-104.pdf"),
                    ("MMPC-105", "Financial Management", "MBA", "1st Year", "Yearly", "MMPC-105.pdf"),
                    
                    # MBA Yearly Courses - 2nd Year
                    ("MMPC-201", "Advanced Management Functions", "MBA", "2nd Year", "Yearly", "MMPC-201.pdf"),
                    ("MMPC-202", "Advanced Human Resource Management", "MBA", "2nd Year", "Yearly", "MMPC-202.pdf"),
                    ("MMPC-203", "Advanced Economics for Managers", "MBA", "2nd Year", "Yearly", "MMPC-203.pdf"),
                    ("MMPC-204", "Advanced Strategic Management", "MBA", "2nd Year", "Yearly", "MMPC-204.pdf"),
                    ("MMPC-205", "Advanced Financial Management", "MBA", "2nd Year", "Yearly", "MMPC-205.pdf"),
                    
                    # MBA Yearly Courses - 3rd Year
                    ("MMPC-301", "Executive Management Functions", "MBA", "3rd Year", "Yearly", "MMPC-301.pdf"),
                    ("MMPC-302", "Executive Human Resource Management", "MBA", "3rd Year", "Yearly", "MMPC-302.pdf"),
                    ("MMPC-303", "Executive Economics for Managers", "MBA", "3rd Year", "Yearly", "MMPC-303.pdf"),
                    ("MMPC-304", "Executive Strategic Management", "MBA", "3rd Year", "Yearly", "MMPC-304.pdf"),
                    ("MMPC-305", "Executive Financial Management", "MBA", "3rd Year", "Yearly", "MMPC-305.pdf"),
                    
                    # MBA Yearly Courses - 4th Year
                    ("MMPC-401", "Senior Management Functions", "MBA", "4th Year", "Yearly", "MMPC-401.pdf"),
                    ("MMPC-402", "Senior Human Resource Management", "MBA", "4th Year", "Yearly", "MMPC-402.pdf"),
                    ("MMPC-403", "Senior Economics for Managers", "MBA", "4th Year", "Yearly", "MMPC-403.pdf"),
                    ("MMPC-404", "Senior Strategic Management", "MBA", "4th Year", "Yearly", "MMPC-404.pdf"),
                    ("MMPC-405", "Senior Financial Management", "MBA", "4th Year", "Yearly", "MMPC-405.pdf"),
                    
                    # MCA Yearly Courses - 1st Year
                    ("MCS-101", "Problem Solving and Programming", "MCA", "1st Year", "Yearly", "MCS-101.pdf"),
                    ("MCS-102", "Computer Organization", "MCA", "1st Year", "Yearly", "MCS-102.pdf"),
                    ("MCS-103", "Discrete Mathematics", "MCA", "1st Year", "Yearly", "MCS-103.pdf"),
                    ("MCS-104", "Systems Analysis and Design", "MCA", "1st Year", "Yearly", "MCS-104.pdf"),
                    
                    # MCA Yearly Courses - 2nd Year
                    ("MCS-201", "Advanced Problem Solving and Programming", "MCA", "2nd Year", "Yearly", "MCS-201.pdf"),
                    ("MCS-202", "Advanced Computer Organization", "MCA", "2nd Year", "Yearly", "MCS-202.pdf"),
                    ("MCS-203", "Advanced Discrete Mathematics", "MCA", "2nd Year", "Yearly", "MCS-203.pdf"),
                    ("MCS-204", "Advanced Systems Analysis and Design", "MCA", "2nd Year", "Yearly", "MCS-204.pdf"),
                    
                    # MCA Yearly Courses - 3rd Year
                    ("MCS-301", "Expert Problem Solving and Programming", "MCA", "3rd Year", "Yearly", "MCS-301.pdf"),
                    ("MCS-302", "Expert Computer Organization", "MCA", "3rd Year", "Yearly", "MCS-302.pdf"),
                    ("MCS-303", "Expert Discrete Mathematics", "MCA", "3rd Year", "Yearly", "MCS-303.pdf"),
                    ("MCS-304", "Expert Systems Analysis and Design", "MCA", "3rd Year", "Yearly", "MCS-304.pdf"),
                    
                    # MCA Yearly Courses - 4th Year
                    ("MCS-401", "Master Problem Solving and Programming", "MCA", "4th Year", "Yearly", "MCS-401.pdf"),
                    ("MCS-402", "Master Computer Organization", "MCA", "4th Year", "Yearly", "MCS-402.pdf"),
                    ("MCS-403", "Master Discrete Mathematics", "MCA", "4th Year", "Yearly", "MCS-403.pdf"),
                    ("MCS-404", "Master Systems Analysis and Design", "MCA", "4th Year", "Yearly", "MCS-404.pdf"),
                    
                    # BCA Yearly Courses - 1st Year
                    ("BCS-101", "Computer Basics and PC Software", "BCA", "1st Year", "Yearly", "BCS-101.pdf"),
                    ("BCS-102", "Basic Mathematics", "BCA", "1st Year", "Yearly", "BCS-102.pdf"),
                    ("BCS-103", "Programming Methodology Using C", "BCA", "1st Year", "Yearly", "BCS-103.pdf"),
                    ("BCS-104", "Computer System Architecture", "BCA", "1st Year", "Yearly", "BCS-104.pdf"),
                    
                    # BCA Yearly Courses - 2nd Year
                    ("BCS-201", "Advanced Computer Basics and PC Software", "BCA", "2nd Year", "Yearly", "BCS-201.pdf"),
                    ("BCS-202", "Advanced Basic Mathematics", "BCA", "2nd Year", "Yearly", "BCS-202.pdf"),
                    ("BCS-203", "Advanced Programming Methodology Using C", "BCA", "2nd Year", "Yearly", "BCS-203.pdf"),
                    ("BCS-204", "Advanced Computer System Architecture", "BCA", "2nd Year", "Yearly", "BCS-204.pdf"),
                    
                    # BCA Yearly Courses - 3rd Year
                    ("BCS-301", "Expert Computer Basics and PC Software", "BCA", "3rd Year", "Yearly", "BCS-301.pdf"),
                    ("BCS-302", "Expert Basic Mathematics", "BCA", "3rd Year", "Yearly", "BCS-302.pdf"),
                    ("BCS-303", "Expert Programming Methodology Using C", "BCA", "3rd Year", "Yearly", "BCS-303.pdf"),
                    ("BCS-304", "Expert Computer System Architecture", "BCA", "3rd Year", "Yearly", "BCS-304.pdf"),
                    
                    # BCA Yearly Courses - 4th Year
                    ("BCS-401", "Master Computer Basics and PC Software", "BCA", "4th Year", "Yearly", "BCS-401.pdf"),
                    ("BCS-402", "Master Basic Mathematics", "BCA", "4th Year", "Yearly", "BCS-402.pdf"),
                    ("BCS-403", "Master Programming Methodology Using C", "BCA", "4th Year", "Yearly", "BCS-403.pdf"),
                    ("BCS-404", "Master Computer System Architecture", "BCA", "4th Year", "Yearly", "BCS-404.pdf"),
                    
                    # BBA Yearly Courses - 1st Year
                    ("BBAR-101", "Business Communication", "BBA", "1st Year", "Yearly", "BBAR-101.pdf"),
                    ("BBAR-102", "Principles of Management", "BBA", "1st Year", "Yearly", "BBAR-102.pdf"),
                    ("BBAR-103", "Business Mathematics", "BBA", "1st Year", "Yearly", "BBAR-103.pdf"),
                    ("BBAR-104", "Financial Accounting", "BBA", "1st Year", "Yearly", "BBAR-104.pdf"),
                    
                    # BBA Yearly Courses - 2nd Year
                    ("BBAR-201", "Advanced Business Communication", "BBA", "2nd Year", "Yearly", "BBAR-201.pdf"),
                    ("BBAR-202", "Advanced Principles of Management", "BBA", "2nd Year", "Yearly", "BBAR-202.pdf"),
                    ("BBAR-203", "Advanced Business Mathematics", "BBA", "2nd Year", "Yearly", "BBAR-203.pdf"),
                    ("BBAR-204", "Advanced Financial Accounting", "BBA", "2nd Year", "Yearly", "BBAR-204.pdf"),
                    
                    # BBA Yearly Courses - 3rd Year
                    ("BBAR-301", "Expert Business Communication", "BBA", "3rd Year", "Yearly", "BBAR-301.pdf"),
                    ("BBAR-302", "Expert Principles of Management", "BBA", "3rd Year", "Yearly", "BBAR-302.pdf"),
                    ("BBAR-303", "Expert Business Mathematics", "BBA", "3rd Year", "Yearly", "BBAR-303.pdf"),
                    ("BBAR-304", "Expert Financial Accounting", "BBA", "3rd Year", "Yearly", "BBAR-304.pdf"),
                    
                    # BBA Yearly Courses - 4th Year
                    ("BBAR-401", "Master Business Communication", "BBA", "4th Year", "Yearly", "BBAR-401.pdf"),
                    ("BBAR-402", "Master Principles of Management", "BBA", "4th Year", "Yearly", "BBAR-402.pdf"),
                    ("BBAR-403", "Master Business Mathematics", "BBA", "4th Year", "Yearly", "BBAR-403.pdf"),
                    ("BBAR-404", "Master Financial Accounting", "BBA", "4th Year", "Yearly", "BBAR-404.pdf"),
                ]
                
                for course_code, course_name, program, year, semester, pdf_filename in yearly_courses:
                    cursor.execute('''
                        INSERT INTO courses (course_code, course_name, program, year, semester, pdf_filename)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (course_code, course_name, program, year, semester, pdf_filename))
                
                print("✅ Yearly courses created")
                
                # Add semester-only courses (no year required)
                semester_only_courses = [
                    # MBA Semester Courses (No Year Required)
                    ("MMPC-S01", "General Management Principles", "MBA", "", "1st Semester", "MMPC-S01.pdf"),
                    ("MMPC-S02", "Business Fundamentals", "MBA", "", "1st Semester", "MMPC-S02.pdf"),
                    ("MMPC-S03", "Introduction to Business", "MBA", "", "1st Semester", "MMPC-S03.pdf"),
                    
                    ("MMPC-S04", "Advanced Business Concepts", "MBA", "", "2nd Semester", "MMPC-S04.pdf"),
                    ("MMPC-S05", "Business Strategy", "MBA", "", "2nd Semester", "MMPC-S05.pdf"),
                    ("MMPC-S06", "Leadership Skills", "MBA", "", "2nd Semester", "MMPC-S06.pdf"),
                    
                    ("MMPC-S07", "Strategic Management", "MBA", "", "3rd Semester", "MMPC-S07.pdf"),
                    ("MMPC-S08", "Financial Analysis", "MBA", "", "3rd Semester", "MMPC-S08.pdf"),
                    ("MMPC-S09", "Marketing Strategy", "MBA", "", "3rd Semester", "MMPC-S09.pdf"),
                    
                    ("MMPC-S10", "Executive Management", "MBA", "", "4th Semester", "MMPC-S10.pdf"),
                    ("MMPC-S11", "Business Innovation", "MBA", "", "4th Semester", "MMPC-S11.pdf"),
                    ("MMPC-S12", "Global Business", "MBA", "", "4th Semester", "MMPC-S12.pdf"),
                    
                    # MCA Semester Courses (No Year Required)
                    ("MCS-S01", "Programming Fundamentals", "MCA", "", "1st Semester", "MCS-S01.pdf"),
                    ("MCS-S02", "Computer Basics", "MCA", "", "1st Semester", "MCS-S02.pdf"),
                    ("MCS-S03", "Mathematics for Computing", "MCA", "", "1st Semester", "MCS-S03.pdf"),
                    
                    ("MCS-S04", "Data Structures", "MCA", "", "2nd Semester", "MCS-S04.pdf"),
                    ("MCS-S05", "Database Systems", "MCA", "", "2nd Semester", "MCS-S05.pdf"),
                    ("MCS-S06", "Object-Oriented Programming", "MCA", "", "2nd Semester", "MCS-S06.pdf"),
                    
                    ("MCS-S07", "Software Engineering", "MCA", "", "3rd Semester", "MCS-S07.pdf"),
                    ("MCS-S08", "Computer Networks", "MCA", "", "3rd Semester", "MCS-S08.pdf"),
                    ("MCS-S09", "Web Technologies", "MCA", "", "3rd Semester", "MCS-S09.pdf"),
                    
                    ("MCS-S10", "Advanced Programming", "MCA", "", "4th Semester", "MCS-S10.pdf"),
                    ("MCS-S11", "System Design", "MCA", "", "4th Semester", "MCS-S11.pdf"),
                    ("MCS-S12", "Project Management", "MCA", "", "4th Semester", "MCS-S12.pdf"),
                    
                    # BCA Semester Courses (No Year Required)
                    ("BCS-S01", "Computer Applications", "BCA", "", "1st Semester", "BCS-S01.pdf"),
                    ("BCS-S02", "Programming Logic", "BCA", "", "1st Semester", "BCS-S02.pdf"),
                    ("BCS-S03", "Basic Computing", "BCA", "", "1st Semester", "BCS-S03.pdf"),
                    
                    ("BCS-S04", "Database Management", "BCA", "", "2nd Semester", "BCS-S04.pdf"),
                    ("BCS-S05", "Web Development", "BCA", "", "2nd Semester", "BCS-S05.pdf"),
                    ("BCS-S06", "Software Applications", "BCA", "", "2nd Semester", "BCS-S06.pdf"),
                    
                    ("BCS-S07", "System Programming", "BCA", "", "3rd Semester", "BCS-S07.pdf"),
                    ("BCS-S08", "Network Programming", "BCA", "", "3rd Semester", "BCS-S08.pdf"),
                    ("BCS-S09", "Mobile Applications", "BCA", "", "3rd Semester", "BCS-S09.pdf"),
                    
                    ("BCS-S10", "Advanced Applications", "BCA", "", "4th Semester", "BCS-S10.pdf"),
                    ("BCS-S11", "Enterprise Systems", "BCA", "", "4th Semester", "BCS-S11.pdf"),
                    ("BCS-S12", "Final Project", "BCA", "", "4th Semester", "BCS-S12.pdf"),
                    
                    # BBA Semester Courses (No Year Required)
                    ("BBAR-S01", "Business Basics", "BBA", "", "1st Semester", "BBAR-S01.pdf"),
                    ("BBAR-S02", "Management Principles", "BBA", "", "1st Semester", "BBAR-S02.pdf"),
                    ("BBAR-S03", "Business Communication", "BBA", "", "1st Semester", "BBAR-S03.pdf"),
                    
                    ("BBAR-S04", "Financial Management", "BBA", "", "2nd Semester", "BBAR-S04.pdf"),
                    ("BBAR-S05", "Marketing Management", "BBA", "", "2nd Semester", "BBAR-S05.pdf"),
                    ("BBAR-S06", "Human Resource Management", "BBA", "", "2nd Semester", "BBAR-S06.pdf"),
                    
                    ("BBAR-S07", "Operations Management", "BBA", "", "3rd Semester", "BBAR-S07.pdf"),
                    ("BBAR-S08", "Strategic Planning", "BBA", "", "3rd Semester", "BBAR-S08.pdf"),
                    ("BBAR-S09", "Business Analytics", "BBA", "", "3rd Semester", "BBAR-S09.pdf"),
                    
                    ("BBAR-S10", "Leadership Development", "BBA", "", "4th Semester", "BBAR-S10.pdf"),
                    ("BBAR-S11", "Entrepreneurship", "BBA", "", "4th Semester", "BBAR-S11.pdf"),
                    ("BBAR-S12", "Business Ethics", "BBA", "", "4th Semester", "BBAR-S12.pdf"),
                ]
                
                for course_code, course_name, program, year, semester, pdf_filename in semester_only_courses:
                    cursor.execute('''
                        INSERT INTO courses (course_code, course_name, program, year, semester, pdf_filename)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (course_code, course_name, program, year, semester, pdf_filename))
                
                print("✅ Semester-only courses created")
            
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
