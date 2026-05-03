from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3, time, random, string
from datetime import datetime
from functools import wraps

app = Flask(**name**)
app.secret_key = “afit_secret_key_2024”

TRIP_DURATION = 60

def get_db():
conn = sqlite3.connect(‘tricycle.db’)
conn.row_factory = sqlite3.Row
return conn

def init_db():
conn = get_db()
conn.execute(’’‘CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL,
matric TEXT UNIQUE NOT NULL,
faculty TEXT,
created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)’’’)
conn.execute(’’‘CREATE TABLE IF NOT EXISTS bookings (
id INTEGER PRIMARY KEY AUTOINCREMENT,
booking_id TEXT UNIQUE,
ticket_code TEXT UNIQUE,
name TEXT,
matric TEXT,
pickup TEXT,
destination TEXT,
status TEXT DEFAULT ‘queued’,
tricycle TEXT,
created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
assigned_at DATETIME,
completed_at DATETIME
)’’’)
conn.execute(’’‘CREATE TABLE IF NOT EXISTS tricycles (
id INTEGER PRIMARY KEY AUTOINCREMENT,
label TEXT UNIQUE,
status TEXT DEFAULT ‘free’,
passenger TEXT,
current_booking_id TEXT,
ticket_code TEXT,
route TEXT,
start_time REAL DEFAULT 0
)’’’)
check = conn.execute(“SELECT count(*) FROM tricycles”).fetchone()[0]
if check == 0:
for i in range(1, 7):
conn.execute(“INSERT INTO tricycles (label) VALUES (?)”, (f”AFIT-KK-{i:02}”,))
conn.commit()
conn.close()

def gen_ticket():
part1 = ‘’.join(random.choices(string.ascii_uppercase, k=3))
part2 = ‘’.join(random.choices(string.digits, k=4))
return “TKT-” + part1 + “-” + part2

def gen_id():
return ‘’.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def login_required(f):
@wraps(f)
def decorated(*args, **kwargs):
if ‘user’ not in session:
return jsonify({“error”: “Not logged in.”}), 401
return f(*args, **kwargs)
return decorated

def process_simulation(conn):
current_time = time.time()
expired = conn.execute(
“SELECT * FROM tricycles WHERE status=‘busy’ AND start_time > 0 AND (? - start_time) >= ?”,
(current_time, TRIP_DURATION)
).fetchall()
for t in expired:
conn.execute(
“UPDATE bookings SET status=‘completed’, completed_at=? WHERE ticket_code=?”,
(datetime.now(), t[‘ticket_code’])
)
conn.execute(
“UPDATE tricycles SET status=‘free’, passenger=NULL, route=NULL, ticket_code=NULL, current_booking_id=NULL, start_time=0 WHERE label=?”,
(t[‘label’],)
)
conn.commit()
queued = conn.execute(
“SELECT * FROM bookings WHERE status=‘queued’ ORDER BY created_at ASC”
).fetchall()
free_list = conn.execute(
“SELECT * FROM tricycles WHERE status=‘free’”
).fetchall()
for i in range(min(len(queued), len(free_list))):
person = queued[i]
keke = free_list[i]
route = person[‘pickup’] + ’ -> ’ + person[‘destination’]
conn.execute(
“UPDATE tricycles SET status=‘busy’, passenger=?, route=?, ticket_code=?, current_booking_id=?, start_time=? WHERE label=?”,
(person[‘name’], route, person[‘ticket_code’], person[‘booking_id’], current_time, keke[‘label’])
)
conn.execute(
“UPDATE bookings SET status=‘assigned’, tricycle=?, assigned_at=? WHERE booking_id=?”,
(keke[‘label’], datetime.now(), person[‘booking_id’])
)
conn.commit()

def calc_avg_wait(conn):
queued = conn.execute(“SELECT count(*) FROM bookings WHERE status=‘queued’”).fetchone()[0]
free = conn.execute(“SELECT count(*) FROM tricycles WHERE status=‘free’”).fetchone()[0]
if free > 0:
return max(1, round((queued / max(free, 1)) * 8))
return max(1, round(queued * 8))

@app.route(’/’)
def index():
if ‘user’ not in session:
return redirect(url_for(‘login_page’))
return render_template(‘index.html’)

@app.route(’/login’)
def login_page():
if ‘user’ in session:
return redirect(url_for(‘index’))
return render_template(‘login.html’)

@app.route(’/driver’)
def driver_page():
return render_template(‘driver.html’)

@app.route(’/admin’)
def admin_page():
return render_template(‘admin.html’)

@app.route(’/login’, methods=[‘POST’])
def login():
data = request.json or {}
name = data.get(‘name’, ‘’).strip()
matric = data.get(‘matric’, ‘’).strip().upper()
faculty = data.get(‘faculty’, ‘’).strip()
if not name or not matric:
return jsonify({“status”: “error”, “message”: “Name and matric number are required.”}), 400
if not matric.startswith(‘U’):
return jsonify({“status”: “error”, “message”: “Invalid matric. Must start with U (e.g. U22CS1082).”}), 400
conn = get_db()
conn.execute(
“INSERT INTO users (name, matric, faculty) VALUES (?, ?, ?) ON CONFLICT(matric) DO UPDATE SET name=excluded.name, faculty=excluded.faculty”,
(name, matric, faculty)
)
conn.commit()
conn.close()
session[‘user’] = name
session[‘matric’] = matric
session[‘faculty’] = faculty
return jsonify({“status”: “success”, “name”: name, “matric”: matric})

@app.route(’/api/logout’)
def logout():
session.clear()
return redirect(url_for(‘login_page’))

@app.route(’/api/book’, methods=[‘POST’])
@login_required
def book():
data = request.json or {}
pickup = data.get(‘pickup’, ‘’).strip()
destination = data.get(‘destination’, ‘’).strip()
name = session[‘user’]
matric = session[‘matric’]
if not pickup or not destination:
return jsonify({“error”: “Please select pickup and destination.”}), 400
if pickup == destination:
return jsonify({“error”: “Pickup and destination cannot be the same.”}), 400
conn = get_db()
existing = conn.execute(
“SELECT * FROM bookings WHERE matric=? AND status IN (‘queued’,‘assigned’)”,
(matric,)
).fetchone()
if existing:
conn.close()
return jsonify({“error”: “You already have an active booking.”}), 400
ticket_code = gen_ticket()
booking_id = gen_id()
conn.execute(
“INSERT INTO bookings (booking_id, ticket_code, name, matric, pickup, destination, status) VALUES (?, ?, ?, ?, ?, ?, ‘queued’)”,
(booking_id, ticket_code, name, matric, pickup, destination)
)
conn.commit()
process_simulation(conn)
booking = conn.execute(
“SELECT * FROM bookings WHERE booking_id=?”, (booking_id,)
).fetchone()
conn.close()
return jsonify({
“booking_id”: booking[‘booking_id’],
“ticket_code”: booking[‘ticket_code’],
“status”: booking[‘status’],
“pickup”: booking[‘pickup’],
“destination”: booking[‘destination’],
“tricycle”: booking[‘tricycle’]
})

@app.route(’/api/cancel’, methods=[‘POST’])
@login_required
def cancel():
matric = session[‘matric’]
conn = get_db()
booking = conn.execute(
“SELECT * FROM bookings WHERE matric=? AND status=‘queued’”, (matric,)
).fetchone()
if not booking:
conn.close()
return jsonify({“error”: “No queued booking to cancel.”}), 400
conn.execute(
“UPDATE bookings SET status=‘cancelled’ WHERE booking_id=?”, (booking[‘booking_id’],)
)
conn.commit()
conn.close()
return jsonify({“success”: True})

@app.route(’/api/state’)
@login_required
def get_state():
matric = session[‘matric’]
conn = get_db()
process_simulation(conn)
tricycle_rows = conn.execute(“SELECT * FROM tricycles ORDER BY label”).fetchall()
fleet = [{“label”: t[‘label’], “status”: t[‘status’], “passenger”: t[‘passenger’],
“route”: t[‘route’], “ticket_code”: t[‘ticket_code’]} for t in tricycle_rows]
booking = conn.execute(
“SELECT * FROM bookings WHERE matric=? AND status IN (‘queued’,‘assigned’) ORDER BY created_at DESC LIMIT 1”,
(matric,)
).fetchone()
personal = None
if booking:
if booking[‘status’] == ‘queued’:
position = conn.execute(
“SELECT count(*) FROM bookings WHERE status=‘queued’ AND created_at <= ?”,
(booking[‘created_at’],)
).fetchone()[0]
personal = {“status”: “queued”, “position”: position, “ticket”: dict(booking)}
elif booking[‘status’] == ‘assigned’:
personal = {
“status”: “assigned”,
“keke_label”: booking[‘tricycle’],
“route”: booking[‘pickup’] + ’ -> ’ + booking[‘destination’],
“ticket”: dict(booking)
}
avg_wait = calc_avg_wait(conn)
conn.close()
return jsonify({“fleet”: fleet, “personal_booking”: personal, “avg_wait”: avg_wait})

@app.route(’/api/stats’)
def get_stats():
conn = get_db()
process_simulation(conn)
total = conn.execute(“SELECT count(*) FROM bookings”).fetchone()[0]
completed = conn.execute(“SELECT count(*) FROM bookings WHERE status=‘completed’”).fetchone()[0]
queued = conn.execute(“SELECT count(*) FROM bookings WHERE status=‘queued’”).fetchone()[0]
active = conn.execute(“SELECT count(*) FROM tricycles WHERE status=‘busy’”).fetchone()[0]
free = conn.execute(“SELECT count(*) FROM tricycles WHERE status=‘free’”).fetchone()[0]
avg_wait = calc_avg_wait(conn)
tricycle_rows = conn.execute(“SELECT * FROM tricycles ORDER BY label”).fetchall()
tricycles_out = [{“label”: t[‘label’], “status”: t[‘status’], “passenger”: t[‘passenger’],
“route”: t[‘route’], “ticket_code”: t[‘ticket_code’]} for t in tricycle_rows]
conn.close()
return jsonify({
“total_bookings”: total,
“completed_trips”: completed,
“currently_queued”: queued,
“active_trips”: active,
“free_tricycles”: free,
“avg_wait”: avg_wait,
“tricycles”: tricycles_out
})

@app.route(’/status’)
def get_status():
conn = get_db()
process_simulation(conn)
rows = conn.execute(“SELECT * FROM tricycles ORDER BY label”).fetchall()
conn.close()
tricycles_out = [{“label”: t[‘label’], “status”: t[‘status’], “passenger”: t[‘passenger’],
“route”: t[‘route’], “ticket_code”: t[‘ticket_code’]} for t in rows]
return jsonify({“tricycles”: tricycles_out})

@app.route(’/verify/<ticket_code>’)
def verify_ticket(ticket_code):
conn = get_db()
booking = conn.execute(
“SELECT * FROM bookings WHERE ticket_code=?”, (ticket_code.upper(),)
).fetchone()
conn.close()
if not booking:
return jsonify({“error”: “Ticket not found.”}), 404
return jsonify({
“ticket_code”: booking[‘ticket_code’],
“name”: booking[‘name’],
“matric”: booking[‘matric’],
“pickup”: booking[‘pickup’],
“destination”: booking[‘destination’],
“status”: booking[‘status’],
“tricycle”: booking[‘tricycle’]
})

init_db()

if __name__ == ‘__main__’:
app.run(debug=True)
