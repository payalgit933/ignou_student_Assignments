# IGNOU Assignment Portal - Hostinger Deployment Guide

## 🚀 Pre-Deployment Checklist

### 1. **Database Setup** ⚠️ CRITICAL
The current `users.db` file will NOT work on Hostinger. You need to:

**Option A: Use Hostinger's MySQL Database (Recommended)**
1. Create a MySQL database in your Hostinger control panel
2. Update `database.py` to use MySQL instead of SQLite
3. Install `mysql-connector-python` or `PyMySQL`

**Option B: Use SQLite with proper file path**
1. Create a `data/` folder in your project
2. Update database path to use environment variable
3. Ensure the folder has write permissions

### 2. **Environment Variables**
Set these in your Hostinger control panel:
```
CASHFREE_APP_ID=your_production_app_id
CASHFREE_SECRET_KEY=your_production_secret_key
DATABASE_URL=your_database_connection_string (if using external DB)
```

### 3. **Missing Files**
You need to upload these PDF files to the `pdfs/MBA/` folder:
- MMPC-001.pdf
- MMPC-002.pdf

### 4. **File Structure for Hostinger**
```
your-domain.com/
├── app.py
├── database.py
├── requirements.txt
├── Procfile
├── index.html
├── login.html
├── register.html
├── welcome.html
├── admin_login.html
├── admin_dashboard.html
├── pdfs/
│   └── MBA/
│       ├── MMPC-001.pdf
│       ├── MMPC-002.pdf
│       ├── MMPC-003.pdf
│       ├── MMPC-004.pdf
│       ├── MMPC-005.pdf
│       ├── MMPC-006.pdf
│       └── MMPC-007.pdf
└── uploads/
    ├── english/
    │   └── MBA/
    └── hindi/
        └── MBA/
```

## 🔧 Quick Fixes Needed

### Fix 1: Update Database Configuration
```python
# In database.py, add this at the top:
import os

class Database:
    def __init__(self, db_name=None):
        if db_name is None:
            # Use environment variable or default
            db_name = os.environ.get('DATABASE_URL', 'users.db')
        self.db_name = db_name
        self.init_database()
```

### Fix 2: Create Missing PDF Files
You need to create these files in `pdfs/MBA/`:
- MMPC-001.pdf
- MMPC-002.pdf

### Fix 3: Update Requirements
Add to `requirements.txt`:
```
mysql-connector-python==8.0.33
```

## 📋 Deployment Steps

1. **Upload all files** to your Hostinger hosting directory
2. **Set environment variables** in Hostinger control panel
3. **Create database** (MySQL recommended)
4. **Update database configuration** in `database.py`
5. **Test the application** by visiting your domain

## ⚠️ Important Notes

- **Database**: SQLite files are not persistent on shared hosting
- **File Permissions**: Ensure `uploads/` folder has write permissions
- **SSL**: Enable SSL certificate for secure payments
- **Backup**: Regular database backups are essential

## 🆘 If Something Goes Wrong

1. Check Hostinger error logs
2. Verify all environment variables are set
3. Ensure database connection is working
4. Check file permissions on uploads folder
5. Test payment integration with Cashfree

## 📞 Support
If you need help with any of these steps, let me know!
