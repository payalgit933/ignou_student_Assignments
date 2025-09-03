# app.py

import json
import time
from flask import Flask, request, jsonify, redirect, send_from_directory, session
from flask_cors import CORS
from database import db

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this!
CORS(app)  # Enable CORS for all routes



# Route to serve the main HTML page
@app.route("/")
def index():
    # Check if user is authenticated
    user_token = session.get('user_token')
    if not user_token:
        return redirect('/welcome')
    
    # Verify session is still valid
    result = db.verify_session(user_token)
    if not result["success"]:
        session.clear()
        return redirect('/welcome')
    
    # User is authenticated, serve the form
    return send_from_directory('.', 'index.html')

# Public landing page for unauthenticated users
@app.route("/welcome")
def welcome():
    return send_from_directory('.', 'welcome.html')

# Route to serve static files (PDFs, images, etc.)
@app.route('/pdfs/<filename>')
def serve_pdf(filename):
    return send_from_directory('.', filename)

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory('.', filename)

# Test route to verify server is working
@app.route("/test")
def test():
    return jsonify({
        "message": "Flask server is running!",
        "status": "success",
        "timestamp": time.time()
    })

# Authentication routes
@app.route("/api/register", methods=["POST"])
def register():
    try:
        data = request.json
        name = data.get("name")
        email = data.get("email")
        mobile = data.get("mobile")
        password = data.get("password")
        
        if not all([name, email, mobile, password]):
            return jsonify({"success": False, "error": "All fields are required"}), 400
        
        if len(password) < 6:
            return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
        
        result = db.register_user(name, email, mobile, password)
        
        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password are required"}), 400
        
        result = db.login_user(email, password)
        
        if result["success"]:
            session['user_token'] = result['session_token']
            session['user_data'] = result['user']
            return jsonify(result)
        else:
            return jsonify(result), 401
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/logout", methods=["POST"])
def logout():
    try:
        user_token = session.get('user_token')
        if user_token:
            db.logout_user(user_token)
            session.clear()
        return jsonify({"success": True, "message": "Logged out successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/profile")
def get_profile():
    try:
        user_token = session.get('user_token')
        if not user_token:
            return jsonify({"success": False, "error": "Not authenticated"}), 401
        
        result = db.verify_session(user_token)
        if result["success"]:
            return jsonify(result)
        else:
            session.clear()
            return jsonify({"success": False, "error": "Session expired"}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Protected route decorator
def require_auth(f):
    def decorated_function(*args, **kwargs):
        user_token = session.get('user_token')
        if not user_token:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        
        result = db.verify_session(user_token)
        if not result["success"]:
            session.clear()
            return jsonify({"success": False, "error": "Session expired"}), 401
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Route to serve login page
@app.route("/login")
def login_page():
    return send_from_directory('.', 'login.html')

# Route to serve register page
@app.route("/register")
def register_page():
    return send_from_directory('.', 'register.html')

# Logout route
@app.route("/logout")
def logout_page():
    try:
        user_token = session.get('user_token')
        if user_token:
            db.logout_user(user_token)
            session.clear()
        return redirect('/login')
    except Exception as e:
        return redirect('/login')

# User dashboard route
@app.route("/dashboard")
@require_auth
def dashboard():
    try:
        user_token = session.get('user_token')
        result = db.verify_session(user_token)
        if result["success"]:
            user_data = result["user"]
            return jsonify({
                "success": True,
                "user": user_data,
                "message": "Welcome to your dashboard"
            })
        else:
            return jsonify({"success": False, "error": "Session expired"}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)