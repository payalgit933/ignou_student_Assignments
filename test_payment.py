#!/usr/bin/env python3
"""
Test script for IGNOU Assignment Portal Payment System
This script tests the payment flow without making actual payments
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5000"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

def test_server_health():
    """Test if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/test")
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server is not running: {e}")
        return False

def test_user_registration():
    """Test user registration"""
    try:
        data = {
            "name": "Test User",
            "email": TEST_EMAIL,
            "mobile": "9999999999",
            "password": TEST_PASSWORD
        }
        
        response = requests.post(f"{BASE_URL}/api/register", json=data)
        result = response.json()
        
        if result.get("success"):
            print("✅ User registration successful")
            return True
        else:
            print(f"⚠️  User registration: {result.get('error', 'Unknown error')}")
            return True  # User might already exist
    except Exception as e:
        print(f"❌ User registration failed: {e}")
        return False

def test_user_login():
    """Test user login"""
    try:
        data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response = requests.post(f"{BASE_URL}/api/login", json=data)
        result = response.json()
        
        if result.get("success"):
            print("✅ User login successful")
            return result.get("session_token")
        else:
            print(f"❌ User login failed: {result.get('error', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"❌ User login failed: {e}")
        return None

def test_payment_initiation(session_token):
    """Test payment initiation (without actual payment)"""
    try:
        headers = {
            "Cookie": f"session={session_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "subjects": ["Mathematics", "Computer Science"],
            "studentName": "Test Student",
            "enrollmentNumber": "TEST123456",
            "emailId": "test@example.com",
            "mobileNumber": "9999999999"
        }
        
        response = requests.post(f"{BASE_URL}/initiate-payment", json=data, headers=headers)
        result = response.json()
        
        if result.get("success"):
            print("✅ Payment initiation successful")
            print(f"   Transaction ID: {result.get('transactionId')}")
            print(f"   Amount: ₹{result.get('amount')}")
            print(f"   Payment URL: {result.get('paymentUrl')}")
            return True
        else:
            print(f"❌ Payment initiation failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Payment initiation failed: {e}")
        return False

def test_cashfree_credentials():
    """Test Cashfree credentials"""
    try:
        response = requests.get(f"{BASE_URL}/test-cashfree-credentials")
        result = response.json()
        
        if result.get("success"):
            print("✅ Cashfree credentials test successful")
            return True
        else:
            print(f"⚠️  Cashfree credentials test: {result.get('error', 'Unknown error')}")
            print("   This is expected if credentials are not set in production")
            return True
    except Exception as e:
        print(f"❌ Cashfree credentials test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing IGNOU Assignment Portal Payment System")
    print("=" * 50)
    
    # Test server health
    if not test_server_health():
        print("\n❌ Server is not running. Please start the server first:")
        print("   python app.py")
        return
    
    print()
    
    # Test user registration
    test_user_registration()
    print()
    
    # Test user login
    session_token = test_user_login()
    if not session_token:
        print("❌ Cannot proceed without valid session")
        return
    print()
    
    # Test Cashfree credentials
    test_cashfree_credentials()
    print()
    
    # Test payment initiation
    test_payment_initiation(session_token)
    print()
    
    print("🎉 Test completed!")
    print("\nNote: This test only verifies the API endpoints.")
    print("For full testing, you need to:")
    print("1. Set up Cashfree credentials in environment variables")
    print("2. Test the complete flow through the web interface")
    print("3. Make actual payments in test mode")

if __name__ == "__main__":
    main()
