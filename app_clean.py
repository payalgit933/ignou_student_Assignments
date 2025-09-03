import base64
import hashlib
import json
import os
import time
from flask import Flask, request, jsonify, redirect, send_from_directory
from flask_cors import CORS
import requests

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this-in-production')
CORS(app)  # Enable CORS for all routes

# Cashfree Configuration
CASHFREE_APP_ID = os.getenv('CASHFREE_APP_ID', 'your-app-id')
CASHFREE_SECRET_KEY = os.getenv('CASHFREE_SECRET_KEY', 'your-secret-key')
CASHFREE_BASE_URL = "https://api.cashfree.com/pg/orders"

# Route to serve the main form
@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

# Route to serve static files (images, etc.)
@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory('.', filename)

# Test route
@app.route("/test")
def test():
    return jsonify({"message": "Server is running!", "timestamp": time.time()})

# Test Cashfree credentials
@app.route("/test-cashfree-credentials")
def test_cashfree_credentials():
    try:
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2022-09-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "order_id": f"TEST{int(time.time())}",
            "order_amount": 1.00,
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
        
        response = requests.post(CASHFREE_BASE_URL, headers=headers, json=payload)
        
        return jsonify({
            "success": True,
            "message": "Cashfree credentials test completed",
            "status_code": response.status_code,
            "response": response.text,
            "credentials": {
                "api_url": CASHFREE_BASE_URL,
                "app_id": CASHFREE_APP_ID,
                "secret_key_length": len(CASHFREE_SECRET_KEY)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "credentials": {
                "api_url": CASHFREE_BASE_URL,
                "app_id": CASHFREE_APP_ID,
                "secret_key_length": len(CASHFREE_SECRET_KEY)
            }
        })

# Route to initiate payment for assignments
@app.route("/initiate-payment", methods=["POST"])
def initiate_payment():
    try:
        data = request.json
        subjects = data.get("subjects", [])
        student_name = data.get("studentName", "")
        enrollment = data.get("enrollmentNumber", "")
        
        if not subjects or not student_name or not enrollment:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        amount_rupees = len(subjects)  # ₹1 per subject
        
        # Create unique orderId
        order_id = f"ORD{int(time.time())}"
        
        payload = {
            "order_id": order_id,
            "order_amount": amount_rupees,
            "order_currency": "INR",
            "customer_details": {
                "customer_id": f"CUST{int(time.time())}",
                "customer_name": student_name,
                "customer_email": data.get("emailId", "test@example.com"),
                "customer_phone": data.get("mobileNumber", "9999999999")
            },
            "order_meta": {
                "return_url": "https://your-render-app-url.onrender.com/payment-success?order_id={order_id}",
                "notify_url": "https://your-render-app-url.onrender.com/payment-callback"
            }
        }
        
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2022-09-01",
            "Content-Type": "application/json"
        }
        
        print(f"🚀 Initiating payment for order: {order_id}")
        print(f"📊 Order amount: ₹{amount_rupees}")
        print(f"📚 Subjects: {subjects}")
        print(f"👤 Student: {student_name}")
        print(f"🔑 Using App ID: {CASHFREE_APP_ID}")
        print(f"🔑 Secret Key length: {len(CASHFREE_SECRET_KEY)}")
        print(f"🌐 API URL: {CASHFREE_BASE_URL}")
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
                payment_url = f"https://payments.cashfree.com/order/#/{payment_session_id}"
                print(f"✅ Payment session created: {payment_session_id}")
                print(f"🔗 Payment URL: {payment_url}")
                
                return jsonify({
                    "success": True,
                    "paymentUrl": payment_url,
                    "paymentSessionId": payment_session_id,
                    "transactionId": order_id,
                    "amount": amount_rupees,
                    "subjects": subjects
                })
            else:
                print(f"❌ No payment_session_id found in response")
                return jsonify({"success": False, "error": "Payment session creation failed"}), 400
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            return jsonify({"success": False, "error": f"Invalid response format: {response.text}"}), 400
            
    except Exception as e:
        print(f"❌ Payment initiation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Payment success route
@app.route("/payment-success", methods=["GET", "POST"])
def payment_success():
    try:
        order_id = request.args.get('order_id')
        
        if not order_id:
            return "Payment verification failed: No order ID provided"
        
        print(f"🔍 Verifying payment for order: {order_id}")
        
        # Verify payment with Cashfree API
        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2022-09-01",
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
                    
                    <div class="bg-gray-50 rounded-lg p-6 mb-8">
                        <h2 class="text-xl font-semibold text-gray-800 mb-4">Payment Details</h2>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
                            <div>
                                <span class="font-semibold">Order ID:</span>
                                <span class="ml-2">{order_id}</span>
                            </div>
                            <div>
                                <span class="font-semibold">Amount:</span>
                                <span class="ml-2">₹{order_data.get('order_amount', 'N/A')}</span>
                            </div>
                            <div>
                                <span class="font-semibold">Status:</span>
                                <span class="ml-2 text-green-600 font-semibold">{order_data.get('order_status', 'N/A')}</span>
                            </div>
                            <div>
                                <span class="font-semibold">Date:</span>
                                <span class="ml-2">{order_data.get('created_at', 'N/A')}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="space-y-4">
                        <button onclick="downloadAllSubjects()" class="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition-colors w-full">
                            📥 Download All Subjects
                        </button>
                        
                        <button onclick="downloadIndividualSubjects()" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors w-full">
                            📚 Download Individual Subjects
                        </button>
                        
                        <div id="individualButtons" class="hidden mt-4">
                            <!-- Individual subject buttons will be generated here -->
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                // Store payment data for PDF generation
                window.paymentData = {{
                    orderId: "{order_id}",
                    amount: {order_data.get('order_amount', 1)},
                    status: "{order_data.get('order_status', 'PAID')}",
                    subjects: ["Mathematics", "Computer Science", "Physics", "Chemistry", "Economics", "Biology"] // All available subjects
                }};
                
                // Store form data for PDF generation (if available)
                window.formData = {{
                    studentName: "Student Name",
                    enrollmentNumber: "{order_id}",
                    programSelection: "BCA",
                    courseCode: "BCS-053",
                    studyCenterCode: "1234",
                    studyCenterAddress: "Delhi Study Center",
                    examType: "Yearly",
                    yearSelection: "2025",
                    mediumSelection: "English",
                    mobileNumber: "9999999999",
                    emailId: "test@example.com"
                }};
                
                // Include your original PDF generation functions
                const {{ jsPDF }} = window.jspdf;
                const {{ PDFDocument }} = window.PDFLib;
                
                // Subject to PDF mapping for automatic attachment
                const subjectPDFMapping = {{
                    'Mathematics': 'https://raw.githubusercontent.com/payalgit933/ignou_student_Assignments/main/pdfs/BCS-53-EM-2025-26.pdf',
                    'Computer Science': 'https://raw.githubusercontent.com/payalgit933/ignou_student_Assignments/main/pdfs/BCS-54-EM-2025-26.pdf',
                    'Economics': 'https://raw.githubusercontent.com/payalgit933/ignou_student_Assignments/main/pdfs/BCS-53-EM-2025-26.pdf',
                    'Physics': 'https://raw.githubusercontent.com/payalgit933/ignou_student_Assignments/main/pdfs/BCS-53-EM-2025-26.pdf',
                    'Chemistry': 'https://raw.githubusercontent.com/payalgit933/ignou_student_Assignments/main/pdfs/BCS-53-EM-2025-26.pdf',
                    'Biology': 'https://raw.githubusercontent.com/payalgit933/ignou_student_Assignments/main/pdfs/BCS-53-EM-2025-26.pdf'
                }};
                
                // Function to merge PDFs (your original function)
                async function mergePDFs(generatedPDFBytes, subjectName) {{
                    try {{
                        console.log('Starting PDF merge process...');
                        
                        const mergedPdf = await PDFDocument.create();
                        const generatedPdf = await PDFDocument.load(generatedPDFBytes);
                        const generatedPages = await mergedPdf.copyPages(generatedPdf, generatedPdf.getPageIndices());
                        generatedPages.forEach(page => mergedPdf.addPage(page));
                        
                        const pdfToAttach = subjectPDFMapping[subjectName] || 'https://raw.githubusercontent.com/payalgit933/ignou_student_Assignments/main/pdfs/BCS-53-EM-2025-26.pdf';
                        console.log(`Attaching PDF: ${{pdfToAttach}} for subject: ${{subjectName}}`);
                        
                        try {{
                            const response = await fetch(pdfToAttach);
                            if (!response.ok) {{
                                throw new Error(`Failed to fetch ${{pdfToAttach}}: ${{response.status}}`);
                            }}
                            
                            const subjectPDFBytes = await response.arrayBuffer();
                            const subjectPdf = await PDFDocument.load(subjectPDFBytes);
                            const subjectPages = await mergedPdf.copyPages(subjectPdf, subjectPdf.getPageIndices());
                            subjectPages.forEach(page => mergedPdf.addPage(page));
                            
                            console.log(`Successfully merged ${{subjectPages.length}} pages from ${{pdfToAttach}}`);
                        }} catch (error) {{
                            console.warn(`Could not attach ${{pdfToAttach}}:`, error.message);
                        }}
                        
                        const mergedPdfBytes = await mergedPdf.save();
                        return mergedPdfBytes;
                        
                    }} catch (error) {{
                        console.error('PDF merging failed:', error);
                        return generatedPDFBytes;
                    }}
                }}
                
                // Your original PDF generation function
                async function generatePDF(templateData, returnBlob = false) {{
                    const doc = new jsPDF({{ unit: "pt", format: "a4" }});
                    const pageWidth = doc.internal.pageSize.getWidth();
                    const pageHeight = doc.internal.pageSize.getHeight();
                    const margin = 50;
                    const lineHeight = 24;
                    const maxWidth = pageWidth - margin * 2;

                    // Outer border
                    doc.setLineWidth(1);
                    doc.rect(margin / 2, margin / 2, pageWidth - margin, pageHeight - margin);

                    // IGNOU Logos
                    try {{
                        doc.addImage("https://raw.githubusercontent.com/payalgit933/ignou-logo/main/image2.jpg", "JPEG", margin - 15, margin + 15, 100, 40);
                        doc.addImage("https://raw.githubusercontent.com/payalgit933/ignou-logo/main/image4.jpg", "JPEG", pageWidth - margin - 75, margin + 15, 80, 35);
                    }} catch (e) {{
                        console.warn("IGNOU logo loading failed:", e);
                    }}

                    // Header
                    doc.setFont("helvetica", "bold");
                    doc.setFontSize(14);
                    doc.text("INDIRA GANDHI NATIONAL OPEN UNIVERSITY", pageWidth / 2, margin + 35, {{ align: "center" }});

                    doc.setFontSize(11);
                    doc.setTextColor(200, 0, 0);
                    doc.text(`Regional Centre ${{templateData.center || "Delhi"}}`, pageWidth / 2, margin + 55, {{ align: "center" }});
                    doc.setTextColor(0, 0, 0);

                    // Title
                    doc.setFontSize(14);
                    doc.text("Format for Assignment Submission", pageWidth / 2, margin + 95, {{ align: "center" }});
                    doc.line(pageWidth / 2 - 120, margin + 98, pageWidth / 2 + 120, margin + 98);

                    // Exam info
                    doc.setFontSize(11);
                    doc.setFont("helvetica", "italic");
                    doc.setTextColor(100, 100, 100);
                    doc.text(`For Term End Exam June/Dec - _______ Year - ${{templateData.year || "_______"}}`, pageWidth / 2, margin + 115, {{ align: "center" }});
                    doc.text("(Please read the instructions given below carefully before submitting assignments)", pageWidth / 2, margin + 135, {{ align: "center" }});
                    
                    doc.setTextColor(0, 0, 0);
                    doc.setFont("helvetica", "normal");

                    let y = margin + 200;

                    // Row helper function
                    function addRow(num, label, value) {{
                        const leftX = margin + 10;
                        const labelWidth = 240;
                        const valueWidth = maxWidth - 260;
                        
                        doc.setFont("helvetica", "bold");
                        const labelText = `${{num}}. ${{label}} : `;
                        const wrappedLabel = doc.splitTextToSize(labelText, labelWidth);
                        doc.text(wrappedLabel, leftX, y);
                        
                        doc.setFont("helvetica", "normal");
                        const wrappedValue = doc.splitTextToSize(value || "__________", valueWidth);
                        
                        if (wrappedValue.length > 0) {{
                            doc.text(wrappedValue[0], leftX + 250, y);
                        }}
                        
                        for (let i = 1; i < wrappedValue.length; i++) {{
                            doc.text(wrappedValue[i], leftX + 250, y + (i * lineHeight));
                        }}
                        
                        const lines = Math.max(wrappedLabel.length, wrappedValue.length);
                        y += lineHeight * lines + 6;
                    }}

                    // Add all the form data rows
                    addRow(1, "Name of the Student", templateData.name);
                    addRow(2, "Enrollment Number", templateData.enrollment);
                    addRow(3, "Programme Code", templateData.program);
                    addRow(4, "Course Code", templateData.course);
                    addRow(5, "Course Code", templateData.courseCode);
                    addRow(6, "Name of the Study Centre With complete address", templateData.centerAddress);
                    addRow(7, "Study Centre Code", templateData.centerCode);
                    addRow(8, "Mobile Number", templateData.mobile);
                    addRow(9, "Details if this same assignment has been submitted anywhere else also", templateData.assignmentAnyWhereElse);
                    addRow(10, "Email ID", templateData.email);
                    addRow(11, "Above information cross checked and correct?", templateData.crossChecked);

                    // Footer
                    const footerY = 780;
                    const signLabelY = footerY - 40;
                    
                    doc.setFont("helvetica", "bold");
                    doc.text("Date of Submission:", margin, signLabelY);
                    doc.setFont("helvetica", "normal");
                    doc.text(templateData.date || "__________", margin + 130, signLabelY);

                    // Signature
                    if (templateData.sign) {{
                        try {{
                            doc.addImage(templateData.sign, "PNG", pageWidth - margin - 120, signLabelY - 50, 100, 40);
                        }} catch (e) {{
                            console.warn("Signature image failed:", e);
                        }}
                    }}
                    
                    doc.setFont("helvetica", "bold");
                    doc.text("Signature of the Student", pageWidth - margin - 120, signLabelY);

                    // PAGE 2: Student Photo
                    if (templateData.photo) {{
                        doc.addPage();
                        doc.setLineWidth(1);
                        doc.rect(margin / 2, margin / 2, pageWidth - margin, pageHeight - margin);
                        
                        try {{
                            let imageFormat = "JPEG";
                            if (templateData.photo.startsWith("data:image/png")) {{
                                imageFormat = "PNG";
                            }}
                            
                            const photoWidth = 400;
                            const photoHeight = 300;
                            const x = (pageWidth - photoWidth) / 2;
                            const y = (pageHeight - photoHeight) / 2;
                            
                            doc.addImage(templateData.photo, imageFormat, x, y, photoWidth, photoHeight);
                        }} catch (e) {{
                            console.warn("Photo addImage failed", e);
                        }}
                    }}

                    // Save file with merging
                    const enrollment = templateData.enrollment || "Student";
                    const subject = templateData.course || "General";
                    const fileName = `${{enrollment}}_${{subject}}.pdf`;
                    
                    const pdfBytes = doc.output('arraybuffer');
                    
                    try {{
                        const mergedPDFBytes = await mergePDFs(pdfBytes, subject);
                        const blob = new Blob([mergedPDFBytes], {{ type: 'application/pdf' }});
                        
                        if (returnBlob) {{
                            return blob;
                        }}
                        
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = fileName;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        URL.revokeObjectURL(url);
                        
                    }} catch (error) {{
                        console.error('PDF merging failed, downloading original:', error);
                        
                        if (returnBlob) {{
                            return new Blob([doc.output('arraybuffer')], {{ type: 'application/pdf' }});
                        }}
                        
                        doc.save(fileName);
                    }}
                }}
                
                function downloadAllSubjects() {{
                    const subjects = window.paymentData.subjects;
                    alert('Downloading all subjects as ZIP...');
                    
                    // Download each subject individually with your original format
                    subjects.forEach((subject, index) => {{
                        setTimeout(() => {{
                            downloadSingleSubject(subject);
                        }}, index * 1000);
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
                        // Use your original PDF generation with the subject
                        const templateData = {{
                            name: window.formData?.studentName || "Student Name",
                            enrollment: window.paymentData.orderId,
                            program: window.formData?.programSelection || "BCA",
                            courseCode: window.formData?.courseCode || "BCS-053",
                            course: subject,
                            centerCode: window.formData?.studyCenterCode || "1234",
                            centerAddress: window.formData?.studyCenterAddress || "Delhi Study Center",
                            center: "Delhi",
                            mobile: window.formData?.mobileNumber || "9999999999",
                            email: window.formData?.emailId || "test@example.com",
                            assignmentAnyWhereElse: "No",
                            crossChecked: "Yes",
                            date: new Date().toLocaleDateString('en-GB'),
                            year: window.formData?.yearSelection || "2025",
                            photo: null,
                            sign: null
                        }};
                        
                        generatePDF(templateData, false);
                        
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
        print(f"❌ Error processing payment success: {e}")
        return f"Error processing payment success: {str(e)}"

# Payment callback route for Cashfree webhooks
@app.route("/payment-callback", methods=["POST"])
def payment_callback():
    try:
        data = request.json
        print(f"📞 Payment callback received: {data}")
        
        order_status = data.get("order_status", "UNKNOWN")
        order_id = data.get("order_id", "UNKNOWN")
        
        print(f"📊 Order {order_id} status: {order_status}")
        
        if order_status == "PAID":
            print(f"✅ Payment confirmed for order: {order_id}")
            # Here you would typically update your database
            return jsonify({"status": "success", "message": "Payment confirmed"})
        else:
            print(f"❌ Payment failed for order: {order_id}")
            return jsonify({"status": "failed", "message": "Payment not completed"})
            
    except Exception as e:
        print(f"❌ Payment callback error: {e}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
