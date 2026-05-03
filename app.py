from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = "afit_secret_key"

# Persistent Stats for Admin Dashboard
stats = {
    "total_bookings": 0,
    "completed_trips": 0
}

# Fleet Configuration
tricycles = [{"label": f"Keke {i+1:02}", "status": "free", "passenger": None, "route": None, "start_time": 0} for i in range(6)]
bookings = []

def process_simulation():
    current_time = time.time()
    for t in tricycles:
        if t['status'] == 'busy' and (current_time - t['start_time']) >= 60:
            stats["completed_trips"] += 1
            t.update({"status": "free", "passenger": None, "route": None, "start_time": 0})
    
    # Dispatch Logic
    queued = [b for b in bookings if b['status'] == 'queued']
    free_kekes = [t for t in tricycles if t['status'] == 'free']
    for i in range(min(len(queued), len(free_kekes))):
        person = queued[i]
        keke = free_kekes[i]
        keke.update({
            "status": "busy",
            "passenger": person['name'],
            "route": f"{person['pickup']} -> {person['destination']}",
            "start_time": current_time
        })
        person['status'] = 'assigned'

@app.route('/')
def index():
    if 'user' not in session:
        return render_template('login.html')
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/login', methods=['POST'])
def login():
    session['user'] = request.json.get('name')
    return jsonify({"status": "success"})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/book', methods=['POST'])
def book():
    data = request.json
    stats["total_bookings"] += 1
    new_booking = {
        "booking_id": len(bookings) + 1,
        "name": session.get('user'),
        "pickup": data.get('pickup'),
        "destination": data.get('destination'),
        "status": "queued",
        "ticket_code": f"AFIT-{1000 + len(bookings) + 1}"
    }
    bookings.append(new_booking)
    return jsonify(new_booking)

@app.route('/api/stats')
def get_stats():
    process_simulation()
    active_trips = len([t for t in tricycles if t['status'] == 'busy'])
    return jsonify({
        "total_bookings": stats["total_bookings"],
        "completed_trips": stats["completed_trips"],
        "currently_queued": len([b for b in bookings if b['status'] == 'queued']),
        "active_trips": active_trips,
        "free_tricycles": 6 - active_trips,
        "tricycles": tricycles
    })

if __name__ == '__main__':
    app.run(debug=True)
