# app.py

import base64
import hashlib
import json
import os
import time
from flask import Flask, request, jsonify, redirect, send_from_directory, session
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

# Debug: Print credentials status (remove in production)
print(f"🔍 Cashfree Config Check:")
print(f"   APP_ID: {'✅ Set' if CASHFREE_APP_ID != 'your_production_app_id' else '❌ Using placeholder'}")
print(f"   SECRET_KEY: {'✅ Set' if CASHFREE_SECRET_KEY != 'your_production_secret_key' else '❌ Using placeholder'}")
print(f"   BASE_URL: {CASHFREE_BASE_URL}")

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

# Test payment route for debugging
@app.route("/test-payment")
def test_payment():
    return jsonify({
        "message": "Payment system is accessible",
        "status": "success",
        "payment_sessions_count": len(getattr(app, 'payment_sessions', {}))
    })

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
        account_url = "https://api.cashfree.com/pg/merchants/me"
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
                "return_url": "https://ignou-assignment-portal.onrender.com/payment-success",
                "notify_url": "https://ignou-assignment-portal.onrender.com/payment-callback"
            }
        }
        
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json"
        }
        
        print(f"🧪 Testing Cashfree credentials...")
        print(f"🧪 APP_ID: {CASHFREE_APP_ID}")
        print(f"🧪 SECRET_KEY: {CASHFREE_SECRET_KEY[:10]}...{CASHFREE_SECRET_KEY[-10:]}")
        print(f"🧪 API_URL: {CASHFREE_BASE_URL}")
        print(f"🧪 Test payload: {test_payload}")
        
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

# Route to initiate payment for assignments (now protected)
@app.route("/initiate-payment", methods=["POST"])
@require_auth
def initiate_payment():
    try:
        data = request.json
        subjects = data.get("subjects", [])
        student_name = data.get("studentName", "")
        enrollment = data.get("enrollmentNumber", "")

        if not subjects or not student_name or not enrollment:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        amount_rupees = max(len(subjects), 1)  # Minimum ₹1, ₹1 per subject

        # ✅ Create unique orderId
        order_id = f"ORD{int(time.time())}"
        
        # Validate required data
        customer_email = data.get("emailId", "test@example.com")
        customer_phone = data.get("mobileNumber", "9999999999")
        
        # Ensure valid email format
        if not customer_email or "@" not in customer_email:
            customer_email = "heypayal12345@gmail.com"
        
        # Ensure valid phone format (10 digits minimum)
        if not customer_phone or len(customer_phone.replace("+", "").replace("-", "").replace(" ", "")) < 10:
            customer_phone = "9334273197"
        
        print(f"🔍 Payment data validation:")
        print(f"   Student: {student_name}")
        print(f"   Email: {customer_email}")
        print(f"   Phone: {customer_phone}")
        print(f"   Amount: ₹{amount_rupees}")
        print(f"   Order ID: {order_id}")

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

        print(f"🔍 Cashfree API Request:")
        print(f"URL: {CASHFREE_BASE_URL}")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
        
        response = requests.post(CASHFREE_BASE_URL, headers=headers, json=payload)
        
        print(f"📡 Cashfree API Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")

        if response.status_code != 200:
            return jsonify({"success": False, "error": f"Cashfree API error: {response.text}"}), 400

        try:
            res_data = response.json()
            print(f"📊 Parsed Response Data: {res_data}")
            
            # Check for payment_session_id to construct payment URL
            if "payment_session_id" in res_data:
                payment_session_id = res_data["payment_session_id"]
                print(f"✅ Found payment_session_id: {payment_session_id}")
                
                # Construct the payment URL using the session ID
                payment_url = f"https://payments.cashfree.com/order/#/{payment_session_id}"
                print(f"✅ Constructed payment URL: {payment_url}")
                
                # Add warning about potential account issues
                print(f"⚠️  If payment page shows error, check Cashfree dashboard for:")
                print(f"   - KYC completion status")
                print(f"   - Business verification")
                print(f"   - Bank account verification")
                print(f"   - Account activation status")
                
            else:
                print(f"❌ No payment_session_id found in response. Available keys: {list(res_data.keys())}")
                return jsonify({
                    "success": False, 
                    "error": f"Payment session ID not found in response. Available fields: {list(res_data.keys())}. Response: {res_data}"
                }), 400
            
            return jsonify({
                "success": True,
                "paymentUrl": payment_url,
                "paymentSessionId": payment_session_id,
                "transactionId": order_id,
                "amount": amount_rupees,
                "subjects": subjects
            })
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
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
        print(f"🔍 Payment success request - Order ID: {order_id}")
        
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
        
        print(f"📡 Cashfree order status response: {response.status_code}")
        print(f"📡 Response: {response.text}")
        
        if response.status_code != 200:
            return f"Payment verification failed. API error: {response.text}"
        
        order_data = response.json()
        order_status = order_data.get("order_status", "UNKNOWN")
        
        print(f"📊 Order status: {order_status}")
        
        if order_status != "PAID":
            return f"Payment verification failed. Order status: {order_status}. Please contact support."
        
        # Payment is verified as successful
        print(f"✅ Payment verified as successful for order: {order_id}")
        
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
                    <p class="text-gray-600 mb-6">Your payment of ₹{order_data.get('order_amount', 'N/A')} has been processed successfully.</p>
                    
                    <div class="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
                        <h2 class="text-xl font-semibold text-blue-800 mb-4">Payment Details</h2>
                        <div class="text-left space-y-2">
                            <p><strong>Order ID:</strong> {order_id}</p>
                            <p><strong>Status:</strong> ✅ PAID</p>
                            <p><strong>Amount:</strong> ₹{order_data.get('order_amount', 'N/A')}</p>
                            <p><strong>Payment Method:</strong> QR Code</p>
                            <p><strong>Transaction Time:</strong> {order_data.get('created_at', 'N/A')}</p>
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
                // Store payment data for PDF generation
                window.paymentData = {{
                    orderId: "{order_id}",
                    amount: {order_data.get('order_amount', 1)},
                    status: "{order_data.get('order_status', 'PAID')}",
                    subjects: ["Mathematics", "Computer Science"] // Default subjects - you can customize this
                }};
                
                function downloadAllSubjects() {{
                    const subjects = window.paymentData.subjects;
                    alert('Downloading all subjects as ZIP...');
                    
                    // Download each subject individually
                    subjects.forEach((subject, index) => {{
                        setTimeout(() => {{
                            downloadSingleSubject(subject);
                        }}, index * 1000); // Delay each download by 1 second
                    }});
                }}
                
                function downloadIndividualSubjects() {{
                    const container = document.getElementById('individualButtons');
                    container.classList.remove('hidden');
                    
                    const subjects = window.paymentData.subjects;
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
                    try {{
                        // Create a simple PDF with assignment details
                        const {{ jsPDF }} = window.jspdf;
                        const doc = new jsPDF();
                        
                        // Add content to PDF
                        doc.setFontSize(20);
                        doc.text('IGNOU Assignment', 20, 30);
                        
                        doc.setFontSize(16);
                        doc.text(`Subject: ${{subject}}`, 20, 50);
                        doc.text(`Order ID: ${{window.paymentData.orderId}}`, 20, 70);
                        doc.text(`Amount Paid: ₹${{window.paymentData.amount}}`, 20, 90);
                        doc.text(`Status: ${{window.paymentData.status}}`, 20, 110);
                        doc.text(`Date: ${{new Date().toLocaleDateString()}}`, 20, 130);
                        
                        // Add some assignment content
                        doc.setFontSize(12);
                        doc.text('Assignment Questions:', 20, 160);
                        doc.text('1. Explain the basic concepts of the subject.', 20, 180);
                        doc.text('2. Discuss the practical applications.', 20, 200);
                        doc.text('3. Provide examples and case studies.', 20, 220);
                        
                        // Save the PDF
                        const fileName = `Assignment_${{subject}}_${{window.paymentData.orderId}}.pdf`;
                        doc.save(fileName);
                        
                        console.log(`PDF downloaded: ${{fileName}}`);
                        
                    }} catch (error) {{
                        console.error('PDF generation failed:', error);
                        alert('PDF generation failed. Please try again.');
                    }}
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

@app.route("/payment-callback", methods=["POST"])
def payment_callback():
    try:
        # Cashfree sends webhook data
        data = request.json
        print(f"📡 Cashfree webhook received: {data}")
        
        # Extract order information
        order_id = data.get("order_id")
        order_status = data.get("order_status")
        
        if order_status == "PAID":
            print(f"✅ Payment confirmed via webhook for order: {order_id}")
            return jsonify({"status": "success", "message": "Payment received. Allow PDF download."})
        else:
            print(f"❌ Payment not completed. Status: {order_status}")
            return jsonify({"status": "failed", "message": "Payment not completed"})
            
    except Exception as e:
        print(f"❌ Webhook processing error: {str(e)}")
        return jsonify({"status": "error", "message": "Webhook processing failed"}), 500

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
            "api_version": "2022-09-01"
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

if __name__ == "__main__":
    app.run(port=5000, debug=True)
