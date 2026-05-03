from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import time, random, string
from datetime import datetime

app = Flask(__name__)
app.secret_key = "afit_secret_key_2024"

# ── In-Memory Storage ──────────────────────────────────────
stats = {"total_bookings": 0, "completed_trips": 0}

tricycles = [{"id": i+1, "label": f"AFIT-KK-{i+1:02}", "status": "free", "passenger": None, "route": None, "ticket_code": None, "start_time": 0} for i in range(6)]
bookings = []

# ── Helpers ────────────────────────────────────────────────
def gen_ticket():
    part1 = ''.join(random.choices(string.ascii_uppercase, k=3))
    part2 = ''.join(random.choices(string.digits, k=4))
    return f"TKT-{part1}-{part2}"

def gen_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def calc_avg_wait():
    queued = len([b for b in bookings if b['status'] == 'queued'])
    free   = len([t for t in tricycles if t['status'] == 'free'])
    if free > 0:
        return max(2, round((queued / max(free, 1)) * 8))
    return round(queued * 8)

def process_simulation():
    current_time = time.time()
    for t in tricycles:
        if t['status'] == 'busy' and (current_time - t['start_time']) >= 60:
            stats["completed_trips"] += 1
            # Mark booking as completed
            for b in bookings:
                if b.get('ticket_code') == t['ticket_code']:
                    b['status'] = 'completed'
                    break
            t.update({"status": "free", "passenger": None, "route": None, "ticket_code": None, "start_time": 0})

    # Dispatch queued passengers to free tricycles
    queued    = [b for b in bookings if b['status'] == 'queued']
    free_list = [t for t in tricycles if t['status'] == 'free']
    for i in range(min(len(queued), len(free_list))):
        person = queued[i]
        keke   = free_list[i]
        keke.update({
            "status": "busy",
            "passenger": person['name'],
            "route": f"{person['pickup']} → {person['destination']}",
            "ticket_code": person['ticket_code'],
            "start_time": current_time
        })
        person['status'] = 'assigned'
        person['tricycle'] = keke['label']

# ── Pages ──────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/driver')
def driver_page():
    return render_template('driver.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# ── Auth ───────────────────────────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    data   = request.json
    name   = data.get('name', '').strip()
    matric = data.get('matric', '').strip().upper()
    faculty = data.get('faculty', '').strip()

    if not name or not matric:
        return jsonify({"status": "error", "message": "Name and matric required."}), 400
    if not matric.startswith('U'):
        return jsonify({"status": "error", "message": "Invalid matric. Must start with U."}), 400

    session['user']    = name
    session['matric']  = matric
    session['faculty'] = faculty
    return jsonify({"status": "success", "name": name, "matric": matric})

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ── Booking ────────────────────────────────────────────────
@app.route('/api/book', methods=['POST'])
def book():
    if 'user' not in session:
        return jsonify({"error": "Not logged in."}), 401

    data        = request.json
    pickup      = data.get('pickup', '').strip()
    destination = data.get('destination', '').strip()
    name        = session['user']
    matric      = session['matric']

    if not pickup or not destination:
        return jsonify({"error": "Select pickup and destination."}), 400
    if pickup == destination:
        return jsonify({"error": "Pickup and destination cannot be the same."}), 400

    # Check existing active booking
    existing = next((b for b in bookings if b['matric'] == matric and b['status'] in ('queued', 'assigned')), None)
    if existing:
        return jsonify({"error": "You already have an active booking."}), 400

    ticket_code = gen_ticket()
    booking_id  = gen_id()
    new_booking = {
        "booking_id":   booking_id,
        "ticket​​​​​​​​​​​​​​​​
