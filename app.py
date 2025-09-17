# app.py

import base64
import hashlib
import json
import os
import time
from flask import Flask, request, jsonify, redirect, send_from_directory, session, send_file
import sqlite3
from flask_cors import CORS
import requests
from database import db

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this!
CORS(app)  # Enable CORS for all routes

# 🔑 Production credentials from environment variables
CASHFREE_APP_ID = os.getenv('CASHFREE_APP_ID', 'your_production_app_id')
CASHFREE_SECRET_KEY = os.getenv('CASHFREE_SECRET_KEY', 'your_production_secret_key')
CASHFREE_BASE_URL = "https://api.cashfree.com/pg/orders"  # Production URL

# Configuration loaded from environment variables

# PhonePe sandbox URL
PHONEPE_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox/pg/v1/pay"



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
    
    # Check if this is a payment success redirect
    payment_success = request.args.get('payment_success') == 'true'
    payment_data = session.get('payment_data', {}) if payment_success else {}
    
    # User is authenticated, serve the form with payment data
    if payment_success and payment_data:
        # For payment success, we need to pass data to the template
        # Read the file and replace template variables manually
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace template variables with proper JavaScript
        content = content.replace('{% if payment_success and payment_data %}', 'if (true) {')
        content = content.replace('{% endif %}', '}')
        content = content.replace('{{ payment_data | tojson }}', str(payment_data).replace("'", '"'))
        
        return content
    else:
        # For normal access, also process template variables to avoid syntax errors
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace template variables with JavaScript that won't execute
        content = content.replace('{% if payment_success and payment_data %}', 'if (false) {')
        content = content.replace('{% endif %}', '}')
        content = content.replace('{{ payment_data | tojson }}', '{}')
        
        return content

# Public landing page for unauthenticated users
@app.route("/welcome")
def welcome():
    return send_from_directory('.', 'welcome.html')

# Ensure uploads directory structure exists
os.makedirs(os.path.join('uploads', 'english'), exist_ok=True)
os.makedirs(os.path.join('uploads', 'hindi'), exist_ok=True)

# Route to serve static files (PDFs, images, etc.) including nested paths
@app.route('/pdfs/<path:filename>')
def serve_pdf(filename):
    return send_from_directory('pdfs', filename)

# Route to serve uploaded files (English/Hindi)
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory('uploads', filename)

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

# Public API: list active study centers for the student form
@app.route("/api/study-centers")
def public_study_centers():
    try:
        result = db.get_study_centers(limit=1000, offset=0)
        if not result.get("success"):
            return jsonify(result), 500
        centers = [c for c in result.get("centers", []) if c.get("is_active")]
        return jsonify({"success": True, "centers": centers})
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

# Test payment route for debugging
@app.route("/test-payment")
def test_payment():
    return jsonify({
        "message": "Payment system is accessible",
        "status": "success",
        "payment_sessions_count": len(getattr(app, 'payment_sessions', {}))
    })

# Test Cashfree credentials route
@app.route("/test-cashfree-credentials")
def test_cashfree_credentials():
    try:
        # Test with minimal payload
        test_payload = {
            "order_id": f"TEST{int(time.time())}",
            "order_amount": 1,  # ₹1
            "order_currency": "INR",
            "customer_details": {
                "customer_id": f"TESTUSER{int(time.time())}",
                "customer_name": "Test User",
                "customer_email": "test@example.com",
                "customer_phone": "9999999999"
            },
            "order_meta": {
                "return_url": "https://your-render-app-url.onrender.com/payment-success",
                "notify_url": "https://your-render-app-url.onrender.com/payment-callback"
            }
        }
        
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json"
        }
        
        # Testing Cashfree credentials
        
        # Make test request
        response = requests.post(CASHFREE_BASE_URL, headers=headers, json=test_payload)
        
        return jsonify({
            "success": True,
            "message": "Cashfree credentials test completed",
            "status_code": response.status_code,
            "response": response.text[:500] if response.text else "No response text",
            "credentials": {
                "app_id": CASHFREE_APP_ID,
                "secret_key_length": len(CASHFREE_SECRET_KEY),
                "api_url": CASHFREE_BASE_URL
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "credentials": {
                "app_id": CASHFREE_APP_ID,
                "secret_key_length": len(CASHFREE_SECRET_KEY),
                "api_url": CASHFREE_BASE_URL
            }
        }), 500

# Check Cashfree account configuration
@app.route("/check-cashfree-config")
def check_cashfree_config():
    try:
        # Check account configuration
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json"
        }
        
        # Try to get account info
        account_url = f"https://api.cashfree.com/pg/merchants/{CASHFREE_APP_ID}"
        response = requests.get(account_url, headers=headers)
        
        return jsonify({
            "success": True,
            "message": "Cashfree account configuration check",
            "status_code": response.status_code,
            "account_info": response.json() if response.status_code == 200 else response.text,
            "credentials": {
                "app_id": CASHFREE_APP_ID,
                "secret_key_length": len(CASHFREE_SECRET_KEY),
                "api_url": CASHFREE_BASE_URL
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "credentials": {
                "app_id": CASHFREE_APP_ID,
                "secret_key_length": len(CASHFREE_SECRET_KEY),
                "api_url": CASHFREE_BASE_URL
            }
        }), 500


# Route to initiate payment for assignments (now protected)
@app.route("/initiate-payment", methods=["POST"])
@require_auth
def initiate_payment():
    try:
        data = request.json
        courses = data.get("courses", []) or data.get("subjects", [])
        student_name = data.get("studentName", "")
        enrollment = data.get("enrollmentNumber", "")
        programme_code = data.get("programSelection", "")
        course_code = data.get("courseCode", "")
        study_center_code = data.get("studyCenterCode", "")
        study_center_name = data.get("studyCenterAddress", "")
        medium_selection = data.get("mediumSelection", "")
        exam_type = data.get("examType", "")
        semester_number = data.get("semesterNumber", "")
        year_selection = data.get("yearSelection", "")
        mobile_number = data.get("mobileNumber", "")
        email_id = data.get("emailId", "")

        if not courses or not student_name or not enrollment:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        amount_rupees = max(len(courses), 1)  # Minimum ₹1, ₹1 per course

        # ✅ Create unique orderId
        order_id = f"ORD{int(time.time())}"
        
        # Validate required data
        customer_email = email_id if email_id else "test@example.com"
        customer_phone = mobile_number if mobile_number else "9999999999"
        
        # Ensure valid email format
        if not customer_email or "@" not in customer_email:
            customer_email = "heypayal12345@gmail.com"
        
        # Ensure valid phone format (10 digits minimum)
        if not customer_phone or len(customer_phone.replace("+", "").replace("-", "").replace(" ", "")) < 10:
            customer_phone = "9334273197"
        
        # Payment data validated

        payload = {
            "order_id": order_id,
            "order_amount": amount_rupees,
            "order_currency": "INR",
            "customer_details": {
                "customer_id": f"CUST{int(time.time())}",
                "customer_name": student_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone
            },
            "order_meta": {
                "return_url": "https://ignou-assignment-portal.onrender.com/payment-success?order_id={order_id}",
                "notify_url": "https://ignou-assignment-portal.onrender.com/payment-callback"
            }
        }

        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json"
        }
        
        response = requests.post(CASHFREE_BASE_URL, headers=headers, json=payload)

        if response.status_code != 200:
            return jsonify({"success": False, "error": f"Cashfree API error: {response.text}"}), 400

        try:
            res_data = response.json()
            
            # Check for payment_session_id to construct payment URL
            if "payment_session_id" in res_data:
                payment_session_id = res_data["payment_session_id"]
                payment_url = f"https://payments.cashfree.com/order/#/{payment_session_id}"
            else:
                return jsonify({
                    "success": False, 
                    "error": f"Payment session ID not found in response. Available fields: {list(res_data.keys())}. Response: {res_data}"
                }), 400
            
            # Save payment request details to session
            session['payment_request'] = {
                "studentName": student_name,
                "enrollmentNumber": enrollment,
                "emailId": customer_email,
                "mobileNumber": customer_phone,
                "programmeCode": programme_code,
                "courseCode": course_code,
                "studyCenterCode": study_center_code,
                "studyCenterName": study_center_name,
                "mediumSelection": medium_selection,
                "examType": exam_type,
                "semesterNumber": semester_number,
                "yearSelection": year_selection,
                "submittedElsewhere": data.get("submittedElsewhere", ""),
                "submissionDetails": data.get("submissionDetails", ""),
                "confirmation": data.get("confirmation", ""),
                "courses": courses,
                "amount": amount_rupees,
                "order_id": order_id
            }
            
            return jsonify({
                "success": True,
                "paymentUrl": payment_url,
                "paymentSessionId": payment_session_id,
                "transactionId": order_id,
                "amount": amount_rupees,
                "courses": courses
            })
            
        except json.JSONDecodeError as e:
            return jsonify({
                "success": False, 
                "error": f"Invalid JSON response from Cashfree: {response.text}"
            }), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Route to handle successful payment redirect
@app.route("/payment-success", methods=["GET", "POST"])
def payment_success():
    try:
        # Get order ID from query parameters (Cashfree sends this)
        order_id = request.args.get("order_id")
        
        if not order_id:
            return "Payment verification failed. Order ID not found."
        
        # Verify payment with Cashfree API
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json"
        }
        
        # Get order status from Cashfree
        order_url = f"https://api.cashfree.com/pg/orders/{order_id}"
        response = requests.get(order_url, headers=headers)
        
        if response.status_code != 200:
            return f"Payment verification failed. API error: {response.text}"
        
        order_data = response.json()
        order_status = order_data.get("order_status", "UNKNOWN")
        
        if order_status != "PAID":
            return f"Payment verification failed. Order status: {order_status}. Please contact support."
        
        # Store payment data in session for use in index.html
        session['payment_success'] = True
        payment_request = session.get("payment_request", {})
        session['payment_data'] = {
            "order_id": order_id,
            "amount": order_data.get("order_amount", 1),
            "status": order_data.get("order_status", "PAID"),
            "created_at": order_data.get("created_at", ""),
            # Student Information
            "studentName": payment_request.get("studentName", "Not Provided"),
            "enrollmentNumber": payment_request.get("enrollmentNumber", "Not Provided"),
            "emailId": payment_request.get("emailId", "Not Provided"),
            "mobileNumber": payment_request.get("mobileNumber", "Not Provided"),
            # Program and Course Information
            "programmeCode": payment_request.get("programmeCode", "Not Provided"),
            "courseCode": payment_request.get("courseCode", "Not Provided"),
            # Study Center Information
            "studyCenterCode": payment_request.get("studyCenterCode", "Not Provided"),
            "studyCenterName": payment_request.get("studyCenterName", "Not Provided"),
            # Academic Information
            "mediumSelection": payment_request.get("mediumSelection", "Not Provided"),
            "examType": payment_request.get("examType", "Not Provided"),
            "semesterNumber": payment_request.get("semesterNumber", "Not Provided"),
            "yearSelection": payment_request.get("yearSelection", "Not Provided"),
            # Assignment Information
            "submittedElsewhere": payment_request.get("submittedElsewhere", "Not Provided"),
            "submissionDetails": payment_request.get("submissionDetails", "Not Provided"),
            "confirmation": payment_request.get("confirmation", "Not Provided"),
            # Selected Courses
            "courses": payment_request.get("courses", []) or payment_request.get("subjects", []),
            # File uploads (these will be added by the frontend)
            "idCardPhoto": None,
            "signaturePhoto": None
        }
        
        # Redirect to index.html with payment success flag
        return redirect(f"/?payment_success=true&order_id={order_id}")
        
    except Exception as e:
        return f"Error processing payment success: {str(e)}"

# Route to check payment status
@app.route("/check-payment/<transaction_id>")
def check_payment(transaction_id):
    if not hasattr(app, 'payment_sessions'):
        return jsonify({"success": False, "error": "No payment sessions"}), 404
    
    payment_session = app.payment_sessions.get(transaction_id)
    if not payment_session:
        return jsonify({"success": False, "error": "Payment session not found"}), 404
    
    return jsonify({
        "success": True,
        "payment": payment_session
    })

@app.route("/payment-callback", methods=["POST"])
def payment_callback():
    try:
        # Cashfree sends webhook data
        data = request.json
        
        # Extract order information
        order_id = data.get("order_id")
        order_status = data.get("order_status")
        
        if order_status == "PAID":
            return jsonify({"status": "success", "message": "Payment received. Allow PDF download."})
        else:
            return jsonify({"status": "failed", "message": "Payment not completed"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": "Webhook processing failed"}), 500

@app.route("/payment-status", methods=["POST"])
def payment_status():
    # This is the redirect page after payment
    return "Payment completed. You can now download your PDF."

@app.route("/payment-status/<transaction_id>", methods=["GET"])
def get_payment_status(transaction_id):
    # Get payment data from session if available
    payment_request = session.get('payment_request', {})
    payment_data = session.get('payment_data', {})
    
    return jsonify({
        "success": True,
        "status": "PAYMENT_SUCCESS",
        "amount": payment_data.get("amount", 1),
        "courses": payment_request.get("courses", []) or payment_request.get("subjects", []),
        "userData": {
            "studentName": payment_request.get("studentName", "Not Provided"),
            "enrollmentNumber": payment_request.get("enrollmentNumber", "Not Provided"),
            "emailId": payment_request.get("emailId", "Not Provided"),
            "mobileNumber": payment_request.get("mobileNumber", "Not Provided"),
            "programmeCode": payment_request.get("programmeCode", "Not Provided"),
            "courseCode": payment_request.get("courseCode", "Not Provided"),
            "studyCenterCode": payment_request.get("studyCenterCode", "Not Provided"),
            "studyCenterName": payment_request.get("studyCenterName", "Not Provided"),
            "mediumSelection": payment_request.get("mediumSelection", "Not Provided"),
            "examType": payment_request.get("examType", "Not Provided"),
            "semesterNumber": payment_request.get("semesterNumber", "Not Provided"),
            "yearSelection": payment_request.get("yearSelection", "Not Provided")
        }
    })

# Debug route to check form data
@app.route("/debug-form-data", methods=["POST"])
def debug_form_data():
    """Debug route to check what form data is being received"""
    try:
        data = request.json
        return jsonify({
            "success": True,
            "received_data": data,
            "field_count": len(data) if data else 0,
            "expected_fields": [
                "studentName", "enrollmentNumber", "programSelection", "courseCode",
                "studyCenterCode", "studyCenterAddress", "mediumSelection", "examType",
                "semesterNumber", "yearSelection", "subjects", "mobileNumber", "emailId"
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Debug route to check payment error
@app.route("/debug-payment-error")
def debug_payment_error():
    """Debug route to identify payment gateway issues"""
    debug_info = {
        "credentials_status": {
            "app_id_configured": CASHFREE_APP_ID != 'your_production_app_id',
            "secret_key_configured": CASHFREE_SECRET_KEY != 'your_production_secret_key',
            "app_id_preview": CASHFREE_APP_ID[:8] + "..." if CASHFREE_APP_ID != 'your_production_app_id' else "❌ NOT SET",
            "secret_key_preview": CASHFREE_SECRET_KEY[:8] + "..." if CASHFREE_SECRET_KEY != 'your_production_secret_key' else "❌ NOT SET"
        },
        "api_config": {
            "base_url": CASHFREE_BASE_URL,
            "environment": "PRODUCTION",
            "api_version": "2023-08-01"
        },
        "common_issues": [
            "1. Credentials not set in environment variables",
            "2. Using sandbox credentials in production",
            "3. Invalid order amount (must be >= 1.00)",
            "4. Invalid customer details",
            "5. Network connectivity issues"
        ]
    }
    return jsonify(debug_info)

# Test production authentication
@app.route("/test-production-auth")
def test_production_auth():
    """Test authentication with production Cashfree API"""
    try:
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json"
        }
        
        # Try to get account info (this will fail if auth is wrong)
        account_url = "https://api.cashfree.com/pg/merchants/me"
        response = requests.get(account_url, headers=headers, timeout=10)
        
        return jsonify({
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "error": response.text if response.status_code != 200 else "Authentication successful",
            "url": account_url,
            "credentials": {
                "app_id_preview": CASHFREE_APP_ID[:8] + "..." if CASHFREE_APP_ID != 'your_production_app_id' else "❌ NOT SET",
                "secret_key_preview": CASHFREE_SECRET_KEY[:8] + "..." if CASHFREE_SECRET_KEY != 'your_production_secret_key' else "❌ NOT SET"
            }
        })
        
    except Exception as e:
        return jsonify({
            "status_code": "ERROR",
            "success": False,
            "error": str(e),
            "credentials": {
                "app_id_preview": CASHFREE_APP_ID[:8] + "..." if CASHFREE_APP_ID != 'your_production_app_id' else "❌ NOT SET",
                "secret_key_preview": CASHFREE_SECRET_KEY[:8] + "..." if CASHFREE_SECRET_KEY != 'your_production_secret_key' else "❌ NOT SET"
            }
        })

# Secure PDF route - only accessible after payment
@app.route("/get-pdf/<course_code>")
def get_pdf(course_code):
    """Secure route to serve PDFs only to paid users"""
    try:
        # Check if user has paid
        payment_data = session.get('payment_data')
        if not payment_data or payment_data.get("status") != "PAID":
            return jsonify({"success": False, "error": "Unauthorized access. Payment required."}), 403
        
        # Map course code to PDF file
        pdf_mapping = {
            "MMPC-001": "pdfs/MBA/MMPC-001.pdf",
            "MMPC-002": "pdfs/MBA/MMPC-002.pdf",
            "MMPC-003": "pdfs/MBA/MMPC-003.pdf",
            "MMPC-004": "pdfs/MBA/MMPC-004.pdf",
            "MMPC-005": "pdfs/MBA/MMPC-005.pdf",
            "MMPC-006": "pdfs/MBA/MMPC-006.pdf",
            "MMPC-007": "pdfs/MBA/MMPC-007.pdf",
            "MMPC-008": "pdfs/MBA/MMPC-008.pdf",
            "MMPC-009": "pdfs/MBA/MMPC-009.pdf",
            "MMPC-010": "pdfs/MBA/MMPC-010.pdf",
            # BBA course codes
            "BBAR-101": "pdfs/BBA/BBAR-101.pdf",
            "BBAR-102": "pdfs/BBA/BBAR-102.pdf",
            "BBAR-103": "pdfs/BBA/BBAR-103.pdf",
            "BBAR-104": "pdfs/BBA/BBAR-104.pdf",
            "BBAR-105": "pdfs/BBA/BBAR-105.pdf",
            "BBAR-106": "pdfs/BBA/BBAR-106.pdf",
            # MCA course codes
            "MCS-011": "pdfs/MCA/MCS-011.pdf",
            "MCS-012": "pdfs/MCA/MCS-012.pdf",
            "MCS-013": "pdfs/MCA/MCS-013.pdf",
            "MCS-014": "pdfs/MCA/MCS-014.pdf",
            "MCS-015": "pdfs/MCA/MCS-015.pdf",
            "MCS-021": "pdfs/MCA/MCS-021.pdf",
            "MCS-022": "pdfs/MCA/MCS-022.pdf",
            "MCS-023": "pdfs/MCA/MCS-023.pdf",
            "MCS-024": "pdfs/MCA/MCS-024.pdf",
            "MCS-025": "pdfs/MCA/MCS-025.pdf",
            # BCA course codes
            "BCS-011": "pdfs/BCA/BCS-011.pdf",
            "BCS-012": "pdfs/BCA/BCS-012.pdf",
            "BCS-013": "pdfs/BCA/BCS-013.pdf",
            "BCS-014": "pdfs/BCA/BCS-014.pdf",
            "BCS-015": "pdfs/BCA/BCS-015.pdf",
            "BCS-021": "pdfs/BCA/BCS-021.pdf",
            "BCS-022": "pdfs/BCA/BCS-022.pdf",
            "BCS-023": "pdfs/BCA/BCS-023.pdf",
            "BCS-024": "pdfs/BCA/BCS-024.pdf",
            "BCS-025": "pdfs/BCA/BCS-025.pdf",
            # B.Tech course codes
            "BT-101": "pdfs/B.Tech/BT-101.pdf",
            "BT-102": "pdfs/B.Tech/BT-102.pdf",
            "BT-103": "pdfs/B.Tech/BT-103.pdf",
            "BT-104": "pdfs/B.Tech/BT-104.pdf",
            "BT-105": "pdfs/B.Tech/BT-105.pdf",
            "BT-106": "pdfs/B.Tech/BT-106.pdf",
            "BT-201": "pdfs/B.Tech/BT-201.pdf",
            "BT-202": "pdfs/B.Tech/BT-202.pdf",
            "BT-203": "pdfs/B.Tech/BT-203.pdf",
            "BT-204": "pdfs/B.Tech/BT-204.pdf",
            # M.Tech course codes
            "MT-501": "pdfs/M.Tech/MT-501.pdf",
            "MT-502": "pdfs/M.Tech/MT-502.pdf",
            "MT-503": "pdfs/M.Tech/MT-503.pdf",
            "MT-504": "pdfs/M.Tech/MT-504.pdf",
            "MT-505": "pdfs/M.Tech/MT-505.pdf",
            "MT-506": "pdfs/M.Tech/MT-506.pdf",
            "MT-507": "pdfs/M.Tech/MT-507.pdf",
            "MT-508": "pdfs/M.Tech/MT-508.pdf",
            "MT-509": "pdfs/M.Tech/MT-509.pdf",
            "MT-510": "pdfs/M.Tech/MT-510.pdf"
        }

        pdf_file = pdf_mapping.get(course_code)
        if not pdf_file:
            return jsonify({"success": False, "error": f"Course code {course_code} not found"}), 404
        
        if not os.path.exists(pdf_file):
            return jsonify({"success": False, "error": f"PDF file not found for course {course_code}"}), 404

        return send_file(pdf_file, as_attachment=False, mimetype='application/pdf')
        
    except Exception as e:
        return jsonify({"success": False, "error": "Internal server error"}), 500

# Admin routes
@app.route("/admin/login")
def admin_login_page():
    return send_from_directory('.', 'admin_login.html')

@app.route("/admin/dashboard")
def admin_dashboard_page():
    return send_from_directory('.', 'admin_dashboard.html')

# Admin authentication API
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"success": False, "error": "Username and password are required"}), 400
        
        result = db.login_admin(username, password)
        
        if result["success"]:
            session['admin_token'] = result['session_token']
            session['admin_data'] = result['admin']
            return jsonify(result)
        else:
            return jsonify(result), 401
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    try:
        admin_token = session.get('admin_token')
        if admin_token:
            db.logout_admin(admin_token)
            session.pop('admin_token', None)
            session.pop('admin_data', None)
        return jsonify({"success": True, "message": "Admin logged out successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/verify")
def verify_admin_session():
    try:
        admin_token = session.get('admin_token')
        if not admin_token:
            return jsonify({"success": False, "error": "No admin session"}), 401
        
        result = db.verify_admin_session(admin_token)
        if result["success"]:
            return jsonify(result)
        else:
            session.pop('admin_token', None)
            session.pop('admin_data', None)
            return jsonify({"success": False, "error": "Session expired"}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Admin protected route decorator
def require_admin_auth(f):
    def decorated_function(*args, **kwargs):
        admin_token = session.get('admin_token')
        if not admin_token:
            return jsonify({"success": False, "error": "Admin authentication required"}), 401
        
        result = db.verify_admin_session(admin_token)
        if not result["success"]:
            session.pop('admin_token', None)
            session.pop('admin_data', None)
            return jsonify({"success": False, "error": "Admin session expired"}), 401
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Admin dashboard statistics
@app.route("/api/admin/statistics")
@require_admin_auth
def admin_statistics():
    try:
        # Get user count
        user_result = db.get_all_users(limit=1, offset=0)
        total_users = user_result.get("total_count", 0) if user_result["success"] else 0
        
        # Get assignment statistics
        assignment_stats = db.get_assignment_statistics()
        
        if assignment_stats["success"]:
            stats = assignment_stats["statistics"]
            stats["total_users"] = total_users
            return jsonify({"success": True, "statistics": stats})
        else:
            return jsonify(assignment_stats), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Admin user management
@app.route("/api/admin/users")
@require_admin_auth
def admin_get_users():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = (page - 1) * limit
        
        result = db.get_all_users(limit=limit, offset=offset)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/users/<int:user_id>/status", methods=["PUT"])
@require_admin_auth
def admin_update_user_status(user_id):
    try:
        data = request.json
        is_active = data.get("is_active")
        
        if is_active is None:
            return jsonify({"success": False, "error": "is_active field is required"}), 400
        
        result = db.update_user_status(user_id, is_active)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Admin assignment management
@app.route("/api/admin/assignments")
@require_admin_auth
def admin_get_assignments():
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ua.id, u.name, u.email, ua.courses, ua.amount, ua.status, ua.created_at
            FROM user_assignments ua
            JOIN users u ON ua.user_id = u.id
            ORDER BY ua.created_at DESC
            LIMIT 100
        ''')
        
        assignments = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "assignments": [{
                "id": assignment[0],
                "user_name": assignment[1],
                "user_email": assignment[2],
                "courses": assignment[3],
                "amount": assignment[4],
                "status": assignment[5],
                "created_at": assignment[6]
            } for assignment in assignments]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Admin course management
@app.route("/api/admin/courses")
@require_admin_auth
def admin_get_courses():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = (page - 1) * limit
        
        result = db.get_all_courses(limit=limit, offset=offset)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/courses", methods=["POST"])
@require_admin_auth
def admin_add_course():
    try:
        data = request.json
        course_code = data.get("course_code")
        course_name = data.get("course_name")
        program = data.get("program")
        year = data.get("year") or ""
        semester = data.get("semester") or ""
        pdf_filename = data.get("pdf_filename")
        pdf_filename_en = data.get("pdf_filename_en")
        pdf_filename_hi = data.get("pdf_filename_hi")
        credits = data.get("credits")
        
        if not all([course_code, course_name, program]):
            return jsonify({"success": False, "error": "course_code, course_name and program are required"}), 400
        # Require exactly one of year OR semester to be provided (non-empty)
        if (year == "" and semester == "") or (year != "" and semester != ""):
            return jsonify({"success": False, "error": "Provide either year or semester (not both)"}), 400
        
        result = db.add_course(
            course_code, course_name, program, year, semester, 
            pdf_filename, pdf_filename_en, pdf_filename_hi, credits
        )
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/courses/<int:course_id>", methods=["PUT"])
@require_admin_auth
def admin_update_course(course_id):
    try:
        data = request.json
        
        result = db.update_course(
            course_id,
            course_code=data.get("course_code"),
            course_name=data.get("course_name"),
            program=data.get("program"),
            year=data.get("year"),
            semester=data.get("semester"),
            pdf_filename=data.get("pdf_filename"),
            pdf_filename_en=data.get("pdf_filename_en"),
            pdf_filename_hi=data.get("pdf_filename_hi"),
            credits=data.get("credits"),
            is_active=data.get("is_active")
        )
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/courses/<int:course_id>", methods=["DELETE"])
@require_admin_auth
def admin_delete_course(course_id):
    try:
        result = db.delete_course(course_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Admin programs management
@app.route("/api/admin/programs")
@require_admin_auth
def admin_get_programs():
    try:
        result = db.get_all_programs()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/programs", methods=["POST"])
@require_admin_auth
def admin_add_program():
    try:
        data = request.json
        program_code = data.get("program_code")
        program_name = data.get("program_name")
        description = data.get("description")
        
        if not all([program_code, program_name]):
            return jsonify({"success": False, "error": "Program code and name are required"}), 400
        
        result = db.add_program(program_code, program_name, description)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Resolve PDF filename(s) for a given course code and medium
@app.route("/api/course-material/<course_code>")
def resolve_course_material(course_code):
    try:
        medium = request.args.get('medium', '').lower()  # 'english' or 'hindi'
        # Support duplicates: fetch all rows for this code and pick best match
        multi = getattr(db, 'get_courses_by_code_all', None)
        courses_list = []
        if callable(multi):
            res_all = db.get_courses_by_code_all(course_code)
            if res_all.get('success'):
                courses_list = res_all.get('courses', [])
        if not courses_list:
            single = db.get_course_by_code(course_code)
            if not single.get('success'):
                return jsonify(single), 404
            courses_list = [single['course']]

        # Choose course row based on medium-specific availability
        chosen = None
        if medium == 'hindi':
            chosen = next((c for c in courses_list if c.get('pdf_filename_hi')), None)
        elif medium == 'english':
            chosen = next((c for c in courses_list if c.get('pdf_filename_en')), None)
        if not chosen:
            chosen = next((c for c in courses_list if c.get('pdf_filename')), courses_list[0])

        course = chosen
        # Priority: medium-specific > default
        filename_primary = None
        if medium == 'hindi' and course.get('pdf_filename_hi'):
            filename_primary = course['pdf_filename_hi']
        elif medium == 'english' and course.get('pdf_filename_en'):
            filename_primary = course['pdf_filename_en']
        # Fallback filename from default
        filename_fallback = course.get('pdf_filename')

        def ensure_pdf_ext(name: str) -> str:
            base = os.path.basename(name)
            return name if ('.' in base) else f"{name}.pdf"

        def try_resolve_paths(file_name: str) -> str:
            if not file_name:
                return None
            file_name = ensure_pdf_ext(file_name)
            program = course.get('program') or ''
            program_folder = program.upper().replace('.', '').replace(' ', '')
            candidates = []
            # uploads/<medium>/Program/filename and uploads/<medium>/filename when medium is specified
            if medium in ('english', 'hindi'):
                candidates.append((os.path.join('uploads', medium, program_folder, file_name), f"/uploads/{medium}/{program_folder}/{file_name}"))
                candidates.append((os.path.join('uploads', medium, file_name), f"/uploads/{medium}/{file_name}"))
            # legacy pdfs folder as additional fallback
            candidates.append((os.path.join('pdfs', program_folder, file_name), f"/pdfs/{program_folder}/{file_name}"))
            candidates.append((os.path.join('pdfs', file_name), f"/pdfs/{file_name}"))
            # if absolute/relative path provided directly
            if '/' in file_name or '\\' in file_name:
                candidates.append((os.path.join('pdfs', file_name), f"/pdfs/{file_name}"))
            for fs_path, web_path in candidates:
                if os.path.exists(fs_path):
                    return web_path
            return None

        # Always try to find a PDF - prioritize medium-specific, then fallback to default
        pdf_path = None
        
        # First try: medium-specific PDF if medium is selected
        if medium in ('english', 'hindi') and filename_primary:
            pdf_path = try_resolve_paths(filename_primary)
            print(f"DEBUG: Medium {medium} specific PDF search: {filename_primary} -> {pdf_path}")
        
        # Second try: default PDF if medium-specific not found
        if not pdf_path and filename_fallback:
            pdf_path = try_resolve_paths(filename_fallback)
            print(f"DEBUG: Fallback to default PDF: {filename_fallback} -> {pdf_path}")
        
        # Third try: any available PDF from the course (for backward compatibility)
        if not pdf_path:
            all_filenames = [f for f in [filename_primary, filename_fallback] if f]
            for filename in all_filenames:
                pdf_path = try_resolve_paths(filename)
                if pdf_path:
                    print(f"DEBUG: Found PDF with filename: {filename} -> {pdf_path}")
                    break
        
        if not pdf_path:
            return jsonify({
                "success": False, 
                "error": f"No PDF found for course {course_code}. Please ensure PDF files are uploaded in uploads/{medium}/ or pdfs/ directory."
            }), 404
        return jsonify({"success": True, "pdf_path": pdf_path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Admin uploads management
@app.route('/api/admin/uploads', methods=['POST'])
@require_admin_auth
def admin_upload_file():
    try:
        medium = (request.args.get('medium') or '').lower()
        if medium not in ('english', 'hindi'):
            return jsonify({"success": False, "error": "medium must be 'english' or 'hindi'"}), 400
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file part in the request"}), 400
        f = request.files['file']
        # Optional subfolder (e.g., program code)
        subfolder = (request.form.get('subfolder') or '').strip().replace('..', '').replace('\\', '/').strip('/')
        dest_dir = os.path.join('uploads', medium, subfolder) if subfolder else os.path.join('uploads', medium)
        os.makedirs(dest_dir, exist_ok=True)
        filename = f.filename
        if not filename:
            return jsonify({"success": False, "error": "Invalid filename"}), 400
        save_path = os.path.join(dest_dir, filename)
        f.save(save_path)
        public_path = f"/uploads/{medium}/{subfolder + '/' if subfolder else ''}{filename}"
        return jsonify({"success": True, "path": public_path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/admin/uploads', methods=['GET'])
@require_admin_auth
def admin_list_uploads():
    try:
        medium = (request.args.get('medium') or '').lower()
        if medium not in ('english', 'hindi'):
            return jsonify({"success": False, "error": "medium must be 'english' or 'hindi'"}), 400
        base_dir = os.path.join('uploads', medium)
        files = []
        for root, _, filenames in os.walk(base_dir):
            for name in filenames:
                rel = os.path.relpath(os.path.join(root, name), base_dir).replace('\\', '/')
                files.append({
                    'name': name,
                    'relative_path': rel,
                    'public_url': f"/uploads/{medium}/{rel}"
                })
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Admin study centers management
@app.route("/api/admin/study-centers")
@require_admin_auth
def admin_get_study_centers():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = (page - 1) * limit
        result = db.get_study_centers(limit=limit, offset=offset)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/study-centers", methods=["POST"])
@require_admin_auth
def admin_add_study_center():
    try:
        data = request.json
        center_code = data.get("center_code")
        name = data.get("name")
        address = data.get("address")
        city = data.get("city")
        state = data.get("state")
        pincode = data.get("pincode")
        phone = data.get("phone")
        email = data.get("email")
        if not all([center_code, name, address]):
            return jsonify({"success": False, "error": "center_code, name and address are required"}), 400
        result = db.add_study_center(center_code, name, address, city, state, pincode, phone, email)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/study-centers/<int:center_id>", methods=["PUT"])
@require_admin_auth
def admin_update_study_center(center_id):
    try:
        data = request.json
        result = db.update_study_center(
            center_id,
            center_code=data.get("center_code"),
            name=data.get("name"),
            address=data.get("address"),
            city=data.get("city"),
            state=data.get("state"),
            pincode=data.get("pincode"),
            phone=data.get("phone"),
            email=data.get("email"),
            is_active=data.get("is_active")
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/study-centers/<int:center_id>", methods=["DELETE"])
@require_admin_auth
def admin_delete_study_center(center_id):
    try:
        result = db.delete_study_center(center_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Public API for course filtering (for main form)
@app.route("/api/courses/filter")
def get_filtered_courses():
    try:
        program = request.args.get('program')
        year = request.args.get('year')
        semester = request.args.get('semester')
        
        result = db.get_courses_by_filter(program=program, year=year, semester=semester)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Admin filtered courses endpoint
@app.route("/api/admin/courses/filter")
@require_admin_auth
def admin_get_filtered_courses():
    try:
        program = request.args.get('program')
        year = request.args.get('year')
        semester = request.args.get('semester')
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        result = db.get_courses_by_filter(
            program=program, 
            year=year, 
            semester=semester, 
            is_active=None if include_inactive else True
        )
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Admin analytics
@app.route("/api/admin/analytics")
@require_admin_auth
def admin_analytics():
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        # Get user registration trends (last 30 days)
        cursor.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM users 
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        
        user_trends = cursor.fetchall()
        
        # Get revenue trends (last 30 days)
        cursor.execute('''
            SELECT DATE(created_at) as date, SUM(amount) as revenue
            FROM user_assignments 
            WHERE created_at >= datetime('now', '-30 days') AND status = 'completed'
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        
        revenue_trends = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            "success": True,
            "analytics": {
                "user_trends": [{"date": trend[0], "count": trend[1]} for trend in user_trends],
                "revenue_trends": [{"date": trend[0], "revenue": trend[1] or 0} for trend in revenue_trends]
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)