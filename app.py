from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

# Security: Set your admin key here
ADMIN_KEY = os.environ.get("ADMIN_KEY", "afit2026")

# 1. HOME PAGE ROUTE
# This handles the main URL: https://afit-keke-1.onrender.com/
@app.route('/')
def index():
    return render_template('index.html')

# 2. LOGIN PAGE ROUTE
# This fixes the "GET /login 404" error seen in your logs
@app.route('/login')
def login():
    return render_template('login.html')

# 3. ADMIN DASHBOARD ROUTE
# Access via: https://afit-keke-1.onrender.com/admin?key=afit2026
@app.route('/admin')
def admin():
    key = request.args.get('key')
    if key != ADMIN_KEY:
        return "Unauthorized: Invalid Admin Key", 401
    return render_template('admin.html')

# 4. BOOKING DATA ROUTE
# This handles the booking form submission from index.html
@app.route('/book', methods=['POST'])
def book():
    try:
        data = request.json
        # Here you would typically save 'data' to a database
        return jsonify({"status": "success", "message": "Booking received!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# 5. DRIVER INTERFACE ROUTE (Optional)
@app.route('/driver')
def driver():
    return render_template('driver.html')

# RUN THE APP
if __name__ == '__main__':
    # '0.0.0.0' is required for Render to bind to the correct port
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
