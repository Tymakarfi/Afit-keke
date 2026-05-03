from flask import Flask, render_template, request, jsonify
import os
import time
from datetime import datetime

app = Flask(__name__)

# Security configuration
ADMIN_KEY = os.environ.get("ADMIN_KEY", "afit2026")

# Discrete Event Simulation Data
tricycles = [{"label": f"Keke {i+1:02}", "status": "free", "passenger": None, "ticket_code": None, "start_time": 0} for i in range(6)]
bookings = []

def process_simulation():
    """Handles the timing and queue logic"""
    current_time = time.time()
    
    # 1. AUTO-COMPLETE: Clear trips after 60 seconds
    for t in tricycles:
        if t['status'] == 'busy' and (current_time - t['start_time']) >= 60:
            for b in bookings:
                if b['ticket_code'] == t['ticket_code']:
                    b['status'] = 'completed'
            t.update({"status": "free", "passenger": None, "ticket_code": None, "start_time": 0})

    # 2. DISPATCH: Move people from queue to free Kekes
    queued = [b for b in bookings if b['status'] == 'queued']
    free_kekes = [t for t in tricycles if t['status'] == 'free']
    
    for i in range(min(len(queued), len(free_kekes))):
        person = queued[i]
        keke = free_kekes[i]
        keke.update({
            "status": "busy",
            "passenger": person['name'],
            "ticket_code": person['ticket_code'],
            "start_time": current_time
        })
        person.update({"status": "assigned", "tricycle": keke['label']})

@app.route('/')
def index(): return render_template('index.html')

@app.route('/admin')
def admin(): return render_template('admin.html')

@app.route('/status')
def status():
    process_simulation()
    queued_list = [b for b in bookings if b['status'] == 'queued']
    return jsonify({
        "tricycles": tricycles,
        "queue_count": len(queued_list),
        "avg_wait": len(queued_list) * 8
    })

@app.route('/book', methods=['POST'])
def book():
    data = request.json
    ticket_code = f"AFIT-{1000 + len(bookings) + 1}"
    new_booking = {
        "booking_id": len(bookings) + 1,
        "name": data.get('name'),
        "matric": data.get('matric'),
        "pickup": data.get('pickup'),
        "destination": data.get('destination'),
        "status": "queued",
        "ticket_code": ticket_code,
        "created_at": datetime.now().isoformat(),
        "tricycle": None
    }
    bookings.append(new_booking)
    return jsonify(new_booking)

@app.route('/mybooking/<int:bid>')
def my_booking(bid):
    process_simulation()
    booking = next((b for b in bookings if b['booking_id'] == bid), None)
    if booking:
        if booking['status'] == 'queued':
            queued_items = [b for b in bookings if b['status'] == 'queued']
            booking['queue_position'] = queued_items.index(booking) + 1
        return jsonify(booking)
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/all_data')
def admin_all_data():
    if request.args.get('key') != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"bookings": bookings, "tricycles": tricycles})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
