# Cashfree Payment Gateway Integration Setup

## 🔑 Configuration Steps

### 1. Get Your Cashfree Credentials
1. Sign up at [Cashfree Dashboard](https://merchant.cashfree.com/)
2. Complete KYC and business verification
3. Get your credentials:
   - **App ID** (Client ID)
   - **Secret Key** (Client Secret)

### 2. Set Environment Variables
Create a `.env` file in your project root:

```bash
CASHFREE_APP_ID=your_actual_app_id_here
CASHFREE_SECRET_KEY=your_actual_secret_key_here
```

Or set them directly in your deployment environment (Render, Heroku, etc.)

### 3. Update URLs for Production
In `app.py`, update these URLs to match your domain:

```python
# Line 352-353: Update these URLs
"return_url": "https://your-actual-domain.com/payment-success?order_id={order_id}",
"notify_url": "https://your-actual-domain.com/payment-callback"
```

### 4. Test the Integration

#### Test Routes Available:
- `/test-cashfree-credentials` - Test your credentials
- `/check-cashfree-config` - Check account configuration
- `/test-payment` - Test payment system accessibility

#### Testing Steps:
1. Start your Flask app: `python app.py`
2. Visit `http://localhost:5000/test-cashfree-credentials`
3. Check if credentials are working
4. Fill the form and test payment flow

## 🚀 Payment Flow

1. **User fills form** → Selects subjects
2. **Clicks "Pay & Generate Assignment"** → Payment confirmation
3. **Redirected to Cashfree** → Payment page
4. **After payment** → Redirected to success page
5. **Download assignments** → PDF generation with your existing format

## 🔧 Key Features Preserved

✅ **Your existing PDF format** - No changes to layout or styling
✅ **Your download functionality** - Same PDF generation process
✅ **Your form structure** - All fields and validation preserved
✅ **Your authentication** - User login/logout system intact

## 🛠️ Troubleshooting

### Common Issues:

1. **"Payment session ID not found"**
   - Check your Cashfree credentials
   - Ensure account is verified and active

2. **"KYC not completed"**
   - Complete KYC in Cashfree dashboard
   - Verify business details

3. **"Invalid credentials"**
   - Double-check App ID and Secret Key
   - Ensure no extra spaces or characters

### Debug Endpoints:
- `/test-cashfree-credentials` - Test API connection
- `/check-cashfree-config` - Check account status

## 📱 Production Deployment

1. Set environment variables in your hosting platform
2. Update return URLs to your production domain
3. Test with small amounts first
4. Monitor Cashfree dashboard for transactions

## 💡 Notes

- Amount is ₹1 per subject selected
- Payment verification happens automatically
- PDF download is only available after successful payment
- All your existing functionality is preserved
