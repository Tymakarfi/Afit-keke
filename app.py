from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import init_db, get_db
import sqlite3, threading, time, random, string
from datetime import datetime

app = Flask(**name**)
app.secret_key = “afit_secret_key_2024”

# ── Helpers ────────────────────────────────────────────────

def gen_id():
return ‘’.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def gen_ticket():
part1 = ‘’.join(random.choices(string.ascii_uppercase, k=3))
part2 = ‘’.join(random.choices(string.digits, k=4))
return f”TKT-{part1}-{part2}”

def calc_avg_wait():
db = get_db()
queue_len = db.execute(“SELECT count(*) FROM bookings WHERE status=‘queued’”).fetchone()[0]
free_count = db.execute(“SELECT count(*) FROM tricycles WHERE status=‘free’”).fetchone()[0]
db.close()
if free_count > 0:
return max(2, round((queue_len / max(free_count, 1)) * 8))
return round(queue_len * 8)

# ── Pages ──────────────────────────────────────────────────

@app.route(’/’)
def index():
if ‘user’ not in session:
return redirect(url_for(‘login_page’))
return render_template(‘index.html’)

@app.route(’/login’)
def login_page():
return render_template(‘login.html’)

@app.route(’/driver’)
def driver_page():
return render_template(‘driver.html’)

@app.route(’/admin’)
def admin_page():
return render_template(‘admin.html’)

# ── Auth ───────────────────────────────────────────────────

@app.route(’/login’, methods=[‘POST’])
def login():
data = request.json
name   = data.get(‘name’, ‘’).strip()
matric = data.get(‘matric’, ‘’).strip().upper()
faculty = data.get(‘faculty’, ‘’).strip()

```
if not name or not matric:
    return jsonify({"status": "error", "message": "Name and matric required."}), 400
if not matric.startswith('U'):
    return jsonify({"status": "error", "message": "Invalid matric. Must start with U."}), 400

db = get_db()
db.execute("INSERT OR REPLACE INTO users (name, matric, faculty) VALUES (?, ?, ?)",
           (name, matric, faculty))
db.commit()
db.close()

session['user'] = name
session['matric'] = matric
session['faculty'] = faculty
return jsonify({"status": "success", "name": name, "matric": matric})
```

@app.route(’/api/logout’)
def logout():
session.clear()
return redirect(url_for(‘login_page’))

# ── Booking ────────────────────────────────────────────────

@app.route(’/api/book’, methods=[‘POST’])
def book():
if ‘user’ not in session:
return jsonify({“error”: “Not logged in.”}), 401

```
data        = request.json
pickup      = data.get('pickup', '').strip()
destination = data.get('destination', '').strip()
name        = session['user']
matric      = session['matric']

if not pickup or not destination:
    return jsonify({"error": "Select pickup and destination."}), 400
if pickup == destination:
    return jsonify({"error": "Pickup and destination cannot be the same."}), 400

db = get_db()
existing = db.execute(
    "SELECT booking_id FROM bookings WHERE matric=? AND status IN ('queued','assigned')",
    (matric,)).fetchone()
if existing:
    db.close()
    return jsonify({"error": "You already have an active booking."}), 400

booking_id  = gen_id()
ticket_code = gen_ticket()
db.execute(
    "INSERT INTO bookings (booking_id, ticket_code, name, matric, pickup, destination) VALUES (?,?,?,?,?,?)",
    (booking_id, ticket_code, name, matric, pickup, destination))
db.commit()
db.close()
return jsonify({"booking_id": booking_id, "ticket_code": ticket_code, "status": "queued"})
```

# ── Cancel ─────────────────────────────────────────────────

@app.route(’/api/cancel’, methods=[‘POST’])
def cancel():
if ‘user’ not in session:
return jsonify({“error”: “Not logged in.”}), 401
matric = session[‘matric’]
db = get_db()
db.execute(“UPDATE bookings SET status=‘cancelled’ WHERE matric=? AND status=‘queued’”, (matric,))
db.commit()
db.close()
return jsonify({“status”: “cancelled”})

# ── State (main dashboard) ──────────────────────────────────

@app.route(’/api/state’)
def get_state():
if ‘user’ not in session:
return jsonify({“error”: “Not logged in.”}), 401

```
matric = session['matric']
db     = get_db()

# Fleet
tricycles = db.execute("SELECT label, status, passenger, route FROM tricycles ORDER BY id").fetchall()
fleet     = [dict(t) for t in tricycles]

# Queue
queue = db.execute(
    "SELECT booking_id, ticket_code, name, pickup, destination, created_at FROM bookings WHERE status='queued' ORDER BY created_at ASC"
).fetchall()

# Personal booking
personal = db.execute(
    "SELECT booking_id, ticket_code, pickup, destination, status, tricycle FROM bookings WHERE matric=? AND status IN ('queued','assigned') ORDER BY created_at DESC LIMIT 1",
    (matric,)).fetchone()

personal_data = None
if personal:
    p = dict(personal)
    if p['status'] == 'queued':
        pos = db.execute(
            "SELECT count(*) FROM bookings WHERE status='queued' AND created_at <= (SELECT created_at FROM bookings WHERE booking_id=?)",
            (p['booking_id'],)).fetchone()[0]
        p['position'] = pos
        p['est_wait'] = calc_avg_wait()
    elif p['status'] == 'assigned':
        p['keke_label'] = p['tricycle']
        p['route'] = f"{p['pickup']} → {p['destination']}"
    personal_data = p

db.close()
return jsonify({
    "fleet": fleet,
    "queue": [dict(q) for q in queue],
    "personal_booking": personal_data,
    "avg_wait": calc_avg_wait()
})
```

# ── Status (driver/public) ──────────────────────────────────

@app.route(’/status’)
def status():
db = get_db()
queue     = db.execute(“SELECT booking_id, ticket_code, name, pickup, destination FROM bookings WHERE status=‘queued’ ORDER BY created_at ASC”).fetchall()
tricycles = db.execute(“SELECT label, status, passenger, current_booking_id, route FROM tricycles ORDER BY id”).fetchall()

```
tricycle_list = [dict(t) for t in tricycles]
for t in tricycle_list:
    if t['current_booking_id']:
        bk = db.execute("SELECT ticket_code FROM bookings WHERE booking_id=?", (t['current_booking_id'],)).fetchone()
        if bk:
            t['ticket_code'] = bk['ticket_code']
db.close()
return jsonify({
    "queue": [dict(q) for q in queue],
    "tricycles": tricycle_list,
    "avg_wait": calc_avg_wait()
})
```

# ── Verify ticket (driver) ──────────────────────────────────

@app.route(’/verify/<ticket_code>’)
def verify_ticket(ticket_code):
db  = get_db()
row = db.execute(
“SELECT booking_id, ticket_code, name, matric, pickup, destination, status, tricycle FROM bookings WHERE ticket_code=?”,
(ticket_code.upper(),)).fetchone()
db.close()
if not row:
return jsonify({“error”: “Invalid ticket.”}), 404
return jsonify(dict(row))

# ── Admin stats ─────────────────────────────────────────────

@app.route(’/api/stats’)
def get_stats():
db    = get_db()
today = datetime.now().strftime(’%Y-%m-%d’)

```
total_today     = db.execute("SELECT count(*) FROM bookings WHERE date(created_at)=?", (today,)).fetchone()[0]
completed_today = db.execute("SELECT count(*) FROM bookings WHERE date(created_at)=? AND status='completed'", (today,)).fetchone()[0]
queued_now      = db.execute("SELECT count(*) FROM bookings WHERE status='queued'").fetchone()[0]
active_now      = db.execute("SELECT count(*) FROM bookings WHERE status='assigned'").fetchone()[0]
free_tricycles  = db.execute("SELECT count(*) FROM tricycles WHERE status='free'").fetchone()[0]

top_routes = db.execute(
    "SELECT pickup || ' → ' || destination as route, count(*) as trips FROM bookings WHERE date(created_at)=? GROUP BY route ORDER BY trips DESC LIMIT 5",
    (today,)).fetchall()

recent = db.execute(
    "SELECT name, pickup, destination, status, ticket_code, created_at FROM bookings ORDER BY created_at DESC LIMIT 20"
).fetchall()

db.close()
return jsonify({
    "total_bookings":    total_today,
    "completed_trips":   completed_today,
    "currently_queued":  queued_now,
    "active_trips":      active_now,
    "free_tricycles":    free_tricycles,
    "avg_wait":          calc_avg_wait(),
    "top_routes":        [dict(r) for r in top_routes],
    "recent_bookings":   [dict(r) for r in recent]
})
```

# ── History ─────────────────────────────────────────────────

@app.route(’/api/history’)
def history():
if ‘user’ not in session:
return jsonify([])
db   = get_db()
rows = db.execute(
“SELECT ticket_code, pickup, destination, status, tricycle, created_at FROM bookings WHERE matric=? ORDER BY created_at DESC LIMIT 10”,
(session[‘matric’],)).fetchall()
db.close()
return jsonify([dict(r) for r in rows])

# ── Queue Processor ─────────────────────────────────────────

def process_queue():
while True:
time.sleep(2)
try:
db       = get_db()
free     = db.execute(“SELECT id, label FROM tricycles WHERE status=‘free’”).fetchall()
waiting  = db.execute(“SELECT id, booking_id, name, pickup, destination FROM bookings WHERE status=‘queued’ ORDER BY created_at ASC”).fetchall()

```
        for i in range(min(len(free), len(waiting))):
            t_id, t_label = free[i]['id'], free[i]['label']
            p             = waiting[i]
            now           = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            route         = f"{p['pickup']} → {p['destination']}"

            db.execute("UPDATE bookings SET status='assigned', tricycle=?, assigned_at=? WHERE id=?",
                       (t_label, now, p['id']))
            db.execute("UPDATE tricycles SET status='busy', passenger=?, current_booking_id=?, route=? WHERE id=?",
                       (p['name'], p['booking_id'], route, t_id))
            db.commit()

            def finish_trip(tid, bid):
                time.sleep(60)
                done = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                c = sqlite3.connect('tricycle.db')
                c.execute("UPDATE tricycles SET status='free', passenger=NULL, current_booking_id=NULL, route=NULL WHERE id=?", (tid,))
                c.execute("UPDATE bookings SET status='completed', completed_at=? WHERE booking_id=?", (done, bid))
                c.commit()
                c.close()

            threading.Thread(target=finish_trip, args=(t_id, p['booking_id']), daemon=True).start()

        db.close()
    except Exception as e:
        print("Queue error:", e)
```

# ── Start ───────────────────────────────────────────────────

init_db()
threading.Thread(target=process_queue, daemon=True).start()

if **name** == ‘**main**’:
print(“🛺 AFIT Smart-Keke running at http://localhost:5000”)
app.run(host=‘0.0.0.0’, port=5000, debug=False)
