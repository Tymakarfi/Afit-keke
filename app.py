from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

# Use the key from Render's environment variables, or default to 'afit2026'
ADMIN_KEY = os.environ.get("ADMIN_KEY", "afit2026")

# 1. The Home Page Route (Fixes the 404 Error)
@app.route('/')
def index():
    return render_template('index.html')

# 2. The Booking Route (Handles the form submission)
@app.route('/book', methods=['POST'])
def book():
    data = request.json
    # Logic to save data to a database would go here
    return jsonify({"status": "success", "message": "Booking received!"})

# 3. The Admin Page Route
@app.route('/admin')
def admin():
    key = request.args.get('key')
    if key != ADMIN_KEY:
        return "Unauthorized", 401
    return render_template('admin.html')

# 4. Driver Dashboard Route (If you have a driver.html)
@app.route('/driver')
def driver():
    return render_template('driver.html')

if __name__ == '__main__':
    app.run(debug=True)
