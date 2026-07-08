from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import time, random, string
from datetime import datetime

app = Flask(__name__)
app.secret_key = "afit_secret_key_2024"

# --- Simple staff passwords. Change these before deploying. ---
ADMIN_PASSWORD = "Tym@2004"
DRIVER_PASSWORD = "Afitdriver"

# --- Timing constants (seconds) ---
ARRIVE_SECONDS = 30   # time for the assigned tricycle to reach the pickup point
TRIP_SECONDS = 60     # time for the actual journey once passenger boards

stats = {"total_bookings": 0, "completed_trips": 0}

tricycles = [{"id": i+1, "label": f"AFIT-KK-{i+1:02}", "status": "free", "passenger": None, "route": None, "ticket_code": None, "phase_start": 0} for i in range(6)]
bookings = []

def gen_ticket():
    part1 = ''.join(random.choices(string.ascii_uppercase, k=3))
    part2 = ''.join(random.choices(string.digits, k=4))
    return f"TKT-{part1}-{part2}"

def gen_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def calc_avg_wait():
    queued = len([b for b in bookings if b['status'] == 'queued'])
    free = len([t for t in tricycles if t['status'] == 'free'])
    if free > 0:
        return max(2, round((queued / max(free, 1)) * 8))
    return round(queued * 8)

def process_simulation():
    current_time = time.time()

    for t in tricycles:
        # Phase 1: tricycle was en route to pickup the passenger -> now arrives
        if t['status'] == 'enroute' and (current_time - t['phase_start']) >= ARRIVE_SECONDS:
            t['status'] = 'busy'
            t['phase_start'] = current_time
            for b in bookings:
                if b.get('ticket_code') == t['ticket_code']:
                    b['status'] = 'onboard'
                    break

        # Phase 2: journey is underway -> now completes
        elif t['status'] == 'busy' and (current_time - t['phase_start']) >= TRIP_SECONDS:
            stats["completed_trips"] += 1
            for b in bookings:
                if b.get('ticket_code') == t['ticket_code']:
                    b['status'] = 'completed'
                    break
            t.update({"status": "free", "passenger": None, "route": None, "ticket_code": None, "phase_start": 0})

    queued = [b for b in bookings if b['status'] == 'queued']
    free_list = [t for t in tricycles if t['status'] == 'free']
    for i in range(min(len(queued), len(free_list))):
        person = queued[i]
        keke = free_list[i]
        keke.update({
            "status": "enroute",
            "passenger": person['name'],
            "route": f"{person['pickup']} -> {person['destination']}",
            "ticket_code": person['ticket_code'],
            "phase_start": current_time
        })
        person['status'] = 'enroute'
        person['tricycle'] = keke['label']

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    name = data.get('name', '').strip()
    matric = data.get('matric', '').strip().upper()
    faculty = data.get('faculty', '').strip()

    if not name or not matric:
        return jsonify({"status": "error", "message": "Name and matric required."}), 400
    if not matric.startswith('U'):
        return jsonify({"status": "error", "message": "Invalid matric. Must start with U."}), 400

    session['user'] = name
    session['matric'] = matric
    session['faculty'] = faculty
    return jsonify({"status": "success", "name": name, "matric": matric})

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ---------------- Driver ----------------

@app.route('/driver')
def driver_page():
    if not session.get('is_driver'):
        return redirect(url_for('driver_login'))
    return render_template('driver.html')

@app.route('/driver/login', methods=['GET', 'POST'])
def driver_login():
    if request.method == 'GET':
        return render_template('driver_login.html')
    data = request.json or {}
    password = data.get('password', '').strip()
    if password == DRIVER_PASSWORD:
        session['is_driver'] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Incorrect password."}), 401

@app.route('/driver/logout')
def driver_logout():
    session.pop('is_driver', None)
    return redirect(url_for('driver_login'))

# ---------------- Admin ----------------

@app.route('/admin')
def admin_page():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    return render_template('admin.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin_login.html')
    data = request.json or {}
    password = data.get('password', '').strip()
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Incorrect password."}), 401

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

# ---------------- Booking API ----------------

@app.route('/api/book', methods=['POST'])
def book():
    if 'user' not in session:
        return jsonify({"error": "Not logged in."}), 401

    data = request.json
    pickup = data.get('pickup', '').strip()
    destination = data.get('destination', '').strip()
    name = session['user']
    matric = session['matric']

    if not pickup or not destination:
        return jsonify({"error": "Select pickup and destination."}), 400
    if pickup == destination:
        return jsonify({"error": "Pickup and destination cannot be the same."}), 400

    existing = next((b for b in bookings if b['matric'] == matric and b['status'] in ('queued', 'enroute', 'onboard')), None)
    if existing:
        return jsonify({"error": "You already have an active booking."}), 400

    ticket_code = gen_ticket()
    booking_id = gen_id()
    new_booking = {
        "booking_id": booking_id,
        "ticket_code": ticket_code,
        "name": name,
        "matric": matric,
        "pickup": pickup,
        "destination": destination,
        "status": "queued",
        "tricycle": None,
        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    bookings.append(new_booking)
    stats["total_bookings"] += 1
    process_simulation()
    return jsonify({"booking_id": booking_id, "ticket_code": ticket_code, "status": "queued"})

@app.route('/api/cancel', methods=['POST'])
def cancel():
    if 'user' not in session:
        return jsonify({"error": "Not logged in."}), 401
    matric = session['matric']
    for b in bookings:
        if b['matric'] == matric and b['status'] == 'queued':
            b['status'] = 'cancelled'
            break
    return jsonify({"status": "cancelled"})

@app.route('/api/state')
def get_state():
    if 'user' not in session:
        return jsonify({"error": "Not logged in."}), 401

    process_simulation()
    matric = session['matric']
    queue = [b for b in bookings if b['status'] == 'queued']

    personal = next((b for b in bookings if b['matric'] == matric and b['status'] in ('queued', 'enroute', 'onboard')), None)
    personal_data = None
    if personal:
        p = dict(personal)
        if p['status'] == 'queued':
            p['position'] = queue.index(personal) + 1
            p['est_wait'] = calc_avg_wait()
        personal_data = p

    return jsonify({
        "fleet": tricycles,
        "queue": queue,
        "personal_booking": personal_data,
        "avg_wait": calc_avg_wait(),
        "user": {
            "name": session.get('user', ''),
            "matric": session.get('matric', '')
        }
    })

@app.route('/status')
def status():
    process_simulation()
    queue = [b for b in bookings if b['status'] == 'queued']
    return jsonify({
        "queue": queue,
        "tricycles": tricycles,
        "avg_wait": calc_avg_wait()
    })

@app.route('/verify/<ticket_code>')
def verify_ticket(ticket_code):
    booking = next((b for b in bookings if b['ticket_code'] == ticket_code.upper()), None)
    if not booking:
        return jsonify({"error": "Invalid ticket."}), 404
    return jsonify(booking)

@app.route('/api/stats')
def get_stats():
    process_simulation()
    today = datetime.now().strftime('%Y-%m-%d')
    active_trips = len([t for t in tricycles if t['status'] in ('busy', 'enroute')])

    route_counts = {}
    for b in bookings:
        if b.get('created_at', '').startswith(today):
            route = f"{b['pickup']} -> {b['destination']}"
            route_counts[route] = route_counts.get(route, 0) + 1
    top_routes = [{"route": r, "trips": c} for r, c in sorted(route_counts.items(), key=lambda x: -x[1])[:5]]
    recent = sorted(bookings, key=lambda x: x.get('created_at', ''), reverse=True)[:20]

    return jsonify({
        "total_bookings": stats["total_bookings"],
        "completed_trips": stats["completed_trips"],
        "currently_queued": len([b for b in bookings if b['status'] == 'queued']),
        "active_trips": active_trips,
        "free_tricycles": 6 - active_trips,
        "avg_wait": calc_avg_wait(),
        "top_routes": top_routes,
        "recent_bookings": recent,
        "tricycles": tricycles
    })

@app.route('/api/history')
def history():
    if 'user' not in session:
        return jsonify([])
    matric = session['matric']
    user_bookings = [b for b in bookings if b['matric'] == matric]
    return jsonify(sorted(user_bookings, key=lambda x: x.get('created_at', ''), reverse=True)[:10])

if __name__ == '__main__':
    print("AFIT Smart-Keke is running!")
    app.run(host='0.0.0.0', port=5000, debug=False)
