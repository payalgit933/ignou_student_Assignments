# app.py

import base64
import hashlib
import json
import time
from flask import Flask, request, jsonify, redirect, send_from_directory, session
from flask_cors import CORS
import requests
from database import db

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this!
CORS(app)  # Enable CORS for all routes

# 🔑 Put your real creds here (keep them secret!)
MERCHANT_ID = "M23KH53VIZWI6"       # your merchant id
SALT_KEY = "4d87df48-54a4-4f61-9137-a7ccd7b80ea1"   # your API key (Salt Key)
SALT_INDEX = "1"                 # version (salt index)

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

# Test payment route for debugging
@app.route("/test-payment")
def test_payment():
    return jsonify({
        "message": "Payment system is accessible",
        "status": "success",
        "payment_sessions_count": len(getattr(app, 'payment_sessions', {}))
    })

# Test PhonePe credentials route
@app.route("/test-phonepe-credentials")
def test_phonepe_credentials():
    try:
        # Test with minimal payload
        test_payload = {
            "merchantId": MERCHANT_ID,
            "merchantTransactionId": f"test_{int(time.time())}",
            "amount": 100,  # ₹1 in paise
            "merchantUserId": f"test_user_{int(time.time())}",
            "redirectUrl": "https://ignou-assignment-portal.onrender.com/payment-success",
            "redirectMode": "POST",
            "callbackUrl": "https://ignou-assignment-portal.onrender.com/payment-callback",
            "paymentInstrument": {"type": "PAY_PAGE"}
        }
        
        # Base64 encode payload
        payload_str = json.dumps(test_payload)
        payload_base64 = base64.b64encode(payload_str.encode()).decode()
        
        # Generate checksum
        raw_string = payload_base64 + "/pg/v1/pay" + SALT_KEY
        checksum = hashlib.sha256(raw_string.encode()).hexdigest() + "###" + SALT_INDEX
        
        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": checksum,
            "accept": "application/json"
        }
        
        print(f"🧪 Testing PhonePe credentials...")
        print(f"🧪 MERCHANT_ID: {MERCHANT_ID}")
        print(f"🧪 SALT_KEY: {SALT_KEY[:10]}...{SALT_KEY[-10:]}")
        print(f"🧪 SALT_INDEX: {SALT_INDEX}")
        print(f"🧪 Test payload: {test_payload}")
        
        # Make test request
        response = requests.post(PHONEPE_URL, headers=headers, json={"request": payload_base64})
        
        return jsonify({
            "success": True,
            "message": "PhonePe credentials test completed",
            "status_code": response.status_code,
            "response": response.text[:500] if response.text else "No response text",
            "credentials": {
                "merchant_id": MERCHANT_ID,
                "salt_key_length": len(SALT_KEY),
                "salt_index": SALT_INDEX,
                "api_url": PHONEPE_URL
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "credentials": {
                "merchant_id": MERCHANT_ID,
                "salt_key_length": len(SALT_KEY),
                "salt_index": SALT_INDEX,
                "api_url": PHONEPE_URL
            }
        }), 500

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

# Route to initiate payment for assignments (now protected)
@app.route("/initiate-payment", methods=["POST"])
@require_auth
def initiate_payment():
    try:
        data = request.json
        print(f"🔍 Payment initiation request data: {data}")
        
        # Check if data is empty
        if not data:
            print("❌ No data received")
            return jsonify({"success": False, "error": "No data received"}), 400
        
        subjects = data.get("subjects", [])
        student_name = data.get("studentName", "")
        enrollment = data.get("enrollmentNumber", "")
        
        print(f"📚 Subjects: {subjects}")
        print(f"👤 Student: {student_name}")
        print(f"🆔 Enrollment: {enrollment}")
        
        # Check if subjects is empty or None
        if not subjects or len(subjects) == 0:
            print("❌ No subjects selected")
            return jsonify({"success": False, "error": "No subjects selected"}), 400
        
        # Check if required fields are present
        if not student_name or student_name.strip() == "":
            print("❌ Student name is missing")
            return jsonify({"success": False, "error": "Student name is required"}), 400
        
        if not enrollment or enrollment.strip() == "":
            print("❌ Enrollment number is missing")
            return jsonify({"success": False, "error": "Enrollment number is required"}), 400
        
        print("✅ All validation passed, proceeding with payment...")
        
        # Calculate amount based on number of subjects (₹1 per subject)
        amount_rupees = len(subjects)
        merchant_txn_id = f"txn_{int(time.time())}"
        
        # Store payment session data
        payment_session = {
            "merchant_txn_id": merchant_txn_id,
            "subjects": subjects,
            "student_name": student_name,
            "enrollment": enrollment,
            "amount": amount_rupees,
            "status": "pending",
            "timestamp": time.time()
        }
        
        if not hasattr(app, 'payment_sessions'):
            app.payment_sessions = {}
        app.payment_sessions[merchant_txn_id] = payment_session
        
        # Real PhonePe payment integration
        print(f"🚀 Initiating real PhonePe payment: {merchant_txn_id}")
        
        # Calculate amount in paise (PhonePe requirement)
        amount_paise = amount_rupees * 100
        
        # Get your Render URL - UPDATE THIS WITH YOUR ACTUAL RENDER URL
        render_url = "https://ignou-assignment-portal.onrender.com"  # ✅ Your actual Render URL
        
        payload = {
            "merchantId": MERCHANT_ID,
            "merchantTransactionId": merchant_txn_id,
            "amount": amount_paise,
            "merchantUserId": f"user_{int(time.time())}",
            "redirectUrl": f"{render_url}/payment-success",
            "redirectMode": "POST",
            "callbackUrl": f"{render_url}/payment-callback",
            "paymentInstrument": {"type": "PAY_PAGE"}
        }
        
        # Base64 encode payload
        payload_str = json.dumps(payload)
        payload_base64 = base64.b64encode(payload_str.encode()).decode()
        
        # Generate checksum
        raw_string = payload_base64 + "/pg/v1/pay" + SALT_KEY
        checksum = hashlib.sha256(raw_string.encode()).hexdigest() + "###" + SALT_INDEX
        
        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": checksum,
            "accept": "application/json"
        }
        
        print(f"📡 Calling PhonePe API with payload: {payload}")
        
        # Call PhonePe API
        print(f"📡 Making request to PhonePe API: {PHONEPE_URL}")
        print(f"📡 Request headers: {headers}")
        print(f"📡 Request payload: {{'request': payload_base64}}")
        
        try:
            response = requests.post(PHONEPE_URL, headers=headers, json={"request": payload_base64})
            print(f"📡 PhonePe API response status: {response.status_code}")
            print(f"📡 PhonePe API response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"❌ PhonePe API returned non-200 status: {response.status_code}")
                print(f"❌ Response text: {response.text}")
                return jsonify({"success": False, "error": f"PhonePe API error: {response.status_code}", "details": response.text}), 400
            
            res_data = response.json()
            print(f"📡 PhonePe API response: {res_data}")
            
            if "data" in res_data and "instrumentResponse" in res_data["data"]:
                redirect_url = res_data["data"]["instrumentResponse"]["redirectInfo"]["url"]
                print(f"✅ PhonePe payment initiated successfully. Redirect URL: {redirect_url}")
                
                return jsonify({
                    "success": True,
                    "paymentUrl": redirect_url,
                    "transactionId": merchant_txn_id,
                    "amount": amount_rupees,
                    "subjects": subjects
                })
            else:
                print(f"❌ PhonePe API error response: {res_data}")
                error_msg = res_data.get("message", "Unknown error")
                code = res_data.get("code", "UNKNOWN")
                return jsonify({"success": False, "error": f"Payment initiation failed: {error_msg}", "code": code, "details": res_data}), 400
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error calling PhonePe API: {str(e)}")
            return jsonify({"success": False, "error": f"Network error: {str(e)}"}), 500
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response from PhonePe: {str(e)}")
            print(f"❌ Raw response: {response.text}")
            return jsonify({"success": False, "error": "Invalid response from PhonePe"}), 500
        
    except Exception as e:
        print(f"❌ Payment initiation exception: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Route to handle successful payment redirect
@app.route("/payment-success", methods=["GET", "POST"])
def payment_success():
    try:
        # Handle both GET and POST requests
        if request.method == "GET":
            # For debugging - get transaction ID from query parameter
            merchant_txn_id = request.args.get("txn")
        else:
            # Real PhonePe response - get from form data
            data = request.form.to_dict()
            merchant_txn_id = data.get("merchantTransactionId")
            
            # Log the full PhonePe response for debugging
            print(f"📡 PhonePe response data: {data}")
        
        print(f"🔍 Payment success request - Transaction ID: {merchant_txn_id}")
        
        if not merchant_txn_id or not hasattr(app, 'payment_sessions'):
            return "Payment verification failed. Please contact support."
        
        payment_session = app.payment_sessions.get(merchant_txn_id)
        if not payment_session:
            return "Payment session not found. Please contact support."
        
        # Mark payment as successful
        payment_session["status"] = "completed"
        
        print(f"✅ Payment marked as successful for: {merchant_txn_id}")
        
        # Return success page with download options
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Successful</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-100 p-8">
            <div class="max-w-4xl mx-auto">
                <div class="bg-white rounded-lg shadow-lg p-8 text-center">
                    <div class="text-green-600 text-6xl mb-4">✅</div>
                    <h1 class="text-3xl font-bold text-gray-800 mb-4">Payment Successful!</h1>
                    <p class="text-gray-600 mb-6">Your payment of ₹{payment_session['amount']} has been processed successfully.</p>
                    
                    <div class="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
                        <h2 class="text-xl font-semibold text-blue-800 mb-4">Payment Details</h2>
                        <div class="text-left space-y-2">
                            <p><strong>Transaction ID:</strong> {merchant_txn_id}</p>
                            <p><strong>Student:</strong> {payment_session['student_name']}</p>
                            <p><strong>Enrollment:</strong> {payment_session['enrollment']}</p>
                            <p><strong>Amount:</strong> ₹{payment_session['amount']}</p>
                            <p><strong>Subjects:</strong> {', '.join(payment_session['subjects'])}</p>
                        </div>
                    </div>
                    
                    <div class="space-y-4">
                        <h3 class="text-xl font-semibold text-gray-800">Download Your Assignments</h3>
                        <p class="text-gray-600">You can now download your assignments for the selected subjects.</p>
                        
                        <div class="flex flex-wrap gap-4 justify-center mt-6">
                            <button onclick="downloadAllSubjects()" class="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition-colors">
                                📥 Download All Subjects (ZIP)
                            </button>
                            <button onclick="downloadIndividualSubjects()" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors">
                                📚 Download Individual Subjects
                            </button>
                        </div>
                        
                        <div id="individualButtons" class="hidden mt-6">
                            <!-- Individual subject buttons will be generated here -->
                        </div>
                    </div>
                    
                    <div class="mt-8 pt-6 border-t border-gray-200">
                        <a href="/" class="text-blue-600 hover:text-blue-800 underline">← Back to Form</a>
                    </div>
                </div>
            </div>
            
            <script>
                // Store payment session data for PDF generation
                window.paymentSession = {json.dumps(payment_session)};
                
                function downloadAllSubjects() {{
                    const subjects = {json.dumps(payment_session['subjects'])};
                    alert('Downloading all subjects as ZIP...');
                    // Implement ZIP download logic here
                }}
                
                function downloadIndividualSubjects() {{
                    const container = document.getElementById('individualButtons');
                    container.classList.remove('hidden');
                    
                    const subjects = {json.dumps(payment_session['subjects'])};
                    container.innerHTML = '';
                    
                    subjects.forEach(subject => {{
                        const button = document.createElement('button');
                        button.className = 'bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-lg transition-colors m-2';
                        button.textContent = `📖 ${{subject}}`;
                        button.onclick = () => downloadSingleSubject(subject);
                        container.appendChild(button);
                    }});
                }}
                
                function downloadSingleSubject(subject) {{
                    alert(`Downloading assignment for ${{subject}}...`);
                    // Implement individual PDF download logic here
                }}
            </script>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        print(f"❌ Error in payment success: {str(e)}")
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

@app.route("/create-payment", methods=["POST"])
def create_payment():
    data = request.json
    subject_count = data.get("subjectCount", 1)
    amount_rupees = subject_count * 1
    amount_paise = amount_rupees * 100   # PhonePe uses paise

    merchant_txn_id = f"txn_{int(time.time())}"

    payload = {
        "merchantId": MERCHANT_ID,
        "merchantTransactionId": merchant_txn_id,
        "amount": amount_paise,
        "merchantUserId": f"user_{int(time.time())}",
        "redirectUrl": "https://ignou-assignment-portal.onrender.com/payment-status",   # ✅ Updated for Render
        "redirectMode": "POST",
        "callbackUrl": "https://ignou-assignment-portal.onrender.com/payment-callback", # ✅ Updated for Render
        "paymentInstrument": {"type": "PAY_PAGE"}
    }

    # Base64 encode
    payload_str = json.dumps(payload)
    payload_base64 = base64.b64encode(payload_str.encode()).decode()

    # Generate checksum
    raw_string = payload_base64 + "/pg/v1/pay" + SALT_KEY
    checksum = hashlib.sha256(raw_string.encode()).hexdigest() + "###" + SALT_INDEX

    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": checksum,
        "accept": "application/json"
    }

    # Call PhonePe API
    response = requests.post(PHONEPE_URL, headers=headers, json={"request": payload_base64})
    res_data = response.json()

    if "data" in res_data and "instrumentResponse" in res_data["data"]:
        redirect_url = res_data["data"]["instrumentResponse"]["redirectInfo"]["url"]
        return jsonify({
            "success": True,
            "paymentUrl": redirect_url,
            "transactionId": merchant_txn_id
        })
    else:
        return jsonify({"success": False, "error": "Payment init failed", "details": res_data}), 400


@app.route("/payment-callback", methods=["POST"])
def payment_callback():
    data = request.json
    status = data.get("code")
    if status == "PAYMENT_SUCCESS":
        # ✅ mark order paid in DB here
        return jsonify({"status": "success", "message": "Payment received. Allow PDF download."})
    else:
        return jsonify({"status": "failed", "message": "Payment not completed"})


@app.route("/payment-status", methods=["POST"])
def payment_status():
    # This is the redirect page after payment
    return "Payment completed. You can now download your PDF."

@app.route("/payment-status/<transaction_id>", methods=["GET"])
def get_payment_status(transaction_id):
    # In a real app, you'd check the database for payment status
    # For now, we'll return a mock success response
    return jsonify({
        "success": True,
        "status": "PAYMENT_SUCCESS",
        "amount": 1,  # You might want to store this in the session
        "subjects": ["Mathematics", "Computer Science"],  # Store this in session too
        "userData": {
            "mobileNumber": "9999999999",
            "studentName": "Student",
            "enrollmentNumber": "Unknown"
        }
    })


if __name__ == "__main__":
    app.run(port=5000, debug=True)