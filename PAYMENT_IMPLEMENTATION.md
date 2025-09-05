# IGNOU Assignment Portal - Payment Implementation

This document describes the payment functionality implemented in the IGNOU Assignment Portal.

## Overview

The payment system integrates with Cashfree payment gateway to allow users to pay for assignment downloads. Users must register/login, fill out the assignment form, and make a payment before they can download their assignments.

## Features

- **User Authentication**: Registration and login system
- **Payment Integration**: Cashfree payment gateway integration
- **Assignment Generation**: PDF generation with subject-specific content
- **Secure Downloads**: Payment verification before PDF access
- **Session Management**: Secure user sessions with token-based authentication

## Payment Flow

1. **User Registration/Login**: Users must create an account or login
2. **Form Filling**: Users fill out the assignment form with their details
3. **Payment Initiation**: System calculates amount (₹1 per subject) and initiates payment
4. **Payment Processing**: Users are redirected to Cashfree payment gateway
5. **Payment Verification**: System verifies payment status with Cashfree
6. **PDF Download**: Users can download their assignments after successful payment

## File Structure

```
├── app.py                 # Main Flask application with payment routes
├── database.py            # Database operations and user management
├── index.html             # Main assignment form with payment integration
├── login.html             # User login page
├── register.html          # User registration page
├── welcome.html           # Landing page for unauthenticated users
├── requirements.txt       # Python dependencies
├── test_payment.py        # Test script for payment functionality
└── PAYMENT_IMPLEMENTATION.md  # This documentation
```

## API Endpoints

### Authentication
- `POST /api/register` - User registration
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/profile` - Get user profile

### Payment
- `POST /initiate-payment` - Initiate payment (requires authentication)
- `GET /payment-success` - Payment success callback
- `POST /payment-callback` - Cashfree webhook callback

### Testing
- `GET /test` - Server health check
- `GET /test-cashfree-credentials` - Test Cashfree API credentials

## Environment Variables

Set these environment variables for production:

```bash
CASHFREE_APP_ID=your_cashfree_app_id
CASHFREE_SECRET_KEY=your_cashfree_secret_key
```

## Database Schema

### Users Table
- `id` - Primary key
- `name` - User's full name
- `email` - User's email (unique)
- `mobile` - User's mobile number
- `password_hash` - Hashed password
- `created_at` - Account creation timestamp
- `last_login` - Last login timestamp
- `is_active` - Account status

### User Sessions Table
- `id` - Primary key
- `user_id` - Foreign key to users table
- `session_token` - Unique session token
- `created_at` - Session creation timestamp
- `expires_at` - Session expiration timestamp

### User Assignments Table
- `id` - Primary key
- `user_id` - Foreign key to users table
- `subjects` - Comma-separated list of subjects
- `transaction_id` - Payment transaction ID
- `amount` - Payment amount
- `status` - Assignment status
- `created_at` - Request creation timestamp

## Payment Integration Details

### Cashfree Configuration
- **Mode**: Production
- **API Version**: 2023-08-01
- **Base URL**: https://api.cashfree.com/pg/orders
- **Payment URL**: https://payments.cashfree.com/order/#/{session_id}

### Payment Process
1. User submits assignment form
2. System validates form data
3. System creates order with Cashfree
4. User is redirected to Cashfree payment page
5. After payment, user is redirected to success page
6. System verifies payment with Cashfree API
7. User can download assignments

## Security Features

- **Password Hashing**: SHA-256 hashing for passwords
- **Session Management**: Token-based sessions with expiration
- **Payment Verification**: Server-side payment verification
- **Input Validation**: Form data validation and sanitization
- **CORS Protection**: Cross-origin request protection

## Testing

### Manual Testing
1. Start the server: `python app.py`
2. Open browser and go to `http://localhost:5000`
3. Register a new account
4. Fill out the assignment form
5. Test payment flow (use test credentials)

### Automated Testing
Run the test script:
```bash
python test_payment.py
```

## Deployment Considerations

### Environment Setup
1. Set production Cashfree credentials
2. Configure database (SQLite for development, PostgreSQL for production)
3. Set up proper logging
4. Configure HTTPS for production

### Security Checklist
- [ ] Change default secret key
- [ ] Use HTTPS in production
- [ ] Set up proper CORS policies
- [ ] Implement rate limiting
- [ ] Set up monitoring and logging
- [ ] Regular security updates

## Troubleshooting

### Common Issues

1. **Payment Initiation Fails**
   - Check Cashfree credentials
   - Verify API endpoint URLs
   - Check network connectivity

2. **Payment Verification Fails**
   - Verify webhook URL configuration
   - Check order ID format
   - Ensure proper error handling

3. **PDF Generation Issues**
   - Check PDF library dependencies
   - Verify file permissions
   - Check memory usage for large PDFs

### Debug Endpoints
- `/test` - Server health
- `/test-cashfree-credentials` - Test Cashfree API
- `/debug-payment-error` - Payment debugging info

## Future Enhancements

- [ ] Multiple payment gateways
- [ ] Subscription-based access
- [ ] Admin dashboard
- [ ] Email notifications
- [ ] Mobile app integration
- [ ] Advanced analytics

## Support

For technical support or questions about the payment implementation, please refer to:
- Cashfree Documentation: https://docs.cashfree.com/
- Flask Documentation: https://flask.palletsprojects.com/
- Project Repository: [Your Repository URL]

---

**Note**: This implementation is based on the working folder structure and maintains compatibility with the existing PDF generation system while adding secure payment functionality.
