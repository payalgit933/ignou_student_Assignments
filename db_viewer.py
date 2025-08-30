#!/usr/bin/env python3
"""
Simple Database Viewer for IGNOU Assignment Portal
Run this script anytime to see your database contents
"""

import sqlite3
import os

def view_database():
    db_path = 'users.db'
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database file '{db_path}' not found!")
        return
    
    print(f"📁 Database Location: {os.path.abspath(db_path)}")
    print(f"📊 File Size: {os.path.getsize(db_path)} bytes")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"🗂️ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        print()
        
        # View each table
        for table_name in [table[0] for table in tables]:
            print(f"📋 TABLE: {table_name.upper()}")
            print("-" * 50)
            
            try:
                # Get table structure
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # Get all data
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                if rows:
                    print(f"Total Records: {len(rows)}")
                    print()
                    
                    # Show column names
                    col_names = [col[1] for col in columns]
                    print("Columns:", " | ".join(col_names))
                    print("-" * 80)
                    
                    # Show data
                    for i, row in enumerate(rows, 1):
                        print(f"Record #{i}:")
                        for j, value in enumerate(row):
                            col_name = col_names[j] if j < len(col_names) else f"Col{j}"
                            print(f"  {col_name}: {value}")
                        print("-" * 40)
                else:
                    print("No data found in this table")
                    
            except Exception as e:
                print(f"Error reading table {table_name}: {e}")
            
            print("\n" + "=" * 60 + "\n")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")

def quick_user_count():
    """Quick function to just count users"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE expires_at > datetime('now')")
        active_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_assignments")
        assignments = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"👥 Users: {user_count} | 🔐 Active Sessions: {active_sessions} | 📚 Assignments: {assignments}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("🔍 IGNOU ASSIGNMENT PORTAL - DATABASE VIEWER")
    print("=" * 60)
    
    # Show quick stats
    print("📊 Quick Stats:")
    quick_user_count()
    print()
    
    # Show full database
    view_database()
    
    print("\n💡 Tips:")
    print("- Use 'DB Browser for SQLite' for visual interface")
    print("- Run this script anytime: python db_viewer.py")
    print("- Database file: users.db in your project folder")
