from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime

app = Flask(__name__)

# Security Key
ADMIN_KEY = os.environ.get("ADMIN_KEY", "afit2026")

# Mock data to keep the app running without a database file
tricycles = [
    {"label": "Keke 01", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 02", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 03", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 04", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 05", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 06", "status": "free", "passenger": None, "route": None, "ticket_code": None},
]
bookings = []

# --- Page Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/admin')
def admin():
    key = request.args.get('key')
    if key != ADMIN_KEY:
        return "Unauthorized", 401
    return render_template('admin.html')

# --- Data Routes (These fix the JSON error) ---

@app.route('/status')
def status():
    return jsonify({
        "tricycles": tricycles,
        "queue": [b for b in bookings if b['status'] == 'queued'],
        "avg_wait": "5"
    })

@app.route('/book', methods=['POST'])
def book():
    data = request.json
    booking_id = len(bookings) + 1
    ticket_code = f"AFIT-{1000 + booking_id}"
    new_booking = {
        "booking_id": booking_id, "name": data.get('name'),
        "matric": data.get('matric'), "pickup": data.get('pickup'),
        "destination": data.get('destination'), "status": "queued",
        "ticket_code": ticket_code, "created_at": datetime.now().isoformat()
    }
    bookings.append(new_booking)
    return jsonify(new_booking)

@app.route('/mybooking/<int:bid>')
def my_booking(bid):
    booking = next((b for b in bookings if b['booking_id'] == bid), None)
    return jsonify(booking) if booking else (jsonify({"error": "Not found"}), 404)

@app.route('/history/<matric>')
def history(matric):
    user_history = [b for b in bookings if b['matric'] == matric]
    return jsonify(user_history)

@app.route('/cancel/<int:bid>', methods=['POST'])
def cancel(bid):
    global bookings
    bookings = [b for b in bookings if b['booking_id'] != bid]
    return jsonify({"status": "cancelled"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
