from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime

app = Flask(__name__)

# --- Configuration ---
# You can change 'afit2026' here or in Render Environment Variables
ADMIN_KEY = os.environ.get("ADMIN_KEY", "afit2026")

# Mock database (Temporary memory)
tricycles = [
    {"label": "Keke 01", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 02", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 03", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 04", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 05", "status": "free", "passenger": None, "route": None, "ticket_code": None},
    {"label": "Keke 06", "status": "free", "passenger": None, "route": None, "ticket_code": None},
]
bookings = []

def dispatch_keke():
    """Operations Research Logic: Matches next passenger to first free Keke"""
    next_person = next((b for b in bookings if b['status'] == 'queued'), None)
    free_keke = next((t for t in tricycles if t['status'] == 'free'), None)
    
    if next_person and free_keke:
        free_keke['status'] = 'busy'
        free_keke['passenger'] = next_person['name']
        free_keke['route'] = f"{next_person['pickup']} -> {next_person['destination']}"
        free_keke['ticket_code'] = next_person['ticket_code']
        
        next_person['status'] = 'assigned'
        next_person['tricycle'] = free_keke['label']

# --- Page Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# --- Data Routes ---
@app.route('/status')
def status():
    dispatch_keke() 
    return jsonify({
        "tricycles": tricycles,
        "queue": [b for b in bookings if b['status'] == 'queued'],
        "avg_wait": "8"
    })

@app.route('/admin/all_data')
def admin_all_data():
    """Provides the full dataset to the admin dashboard"""
    key = request.args.get('key')
    if key != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({
        "bookings": bookings,
        "tricycles": tricycles
    })

@app.route('/book', methods=['POST'])
def book():
    data = request.json
    booking_id = len(bookings) + 1
    ticket_code = f"AFIT-{1000 + booking_id}"
    
    new_booking = {
        "booking_id": booking_id,
        "name": data.get('name'),
        "matric": data.get('matric'),
        "pickup": data.get('pickup'),
        "destination": data.get('destination'),
        "status": "queued",
        "ticket_code": ticket_code,
        "created_at": datetime.now().isoformat()
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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
