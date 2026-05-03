from flask import Flask, render_template, request, jsonify
import os
import time
from datetime import datetime

app = Flask(__name__)

# Security key for your admin dashboard
ADMIN_KEY = os.environ.get("ADMIN_KEY", "afit2026")

# Simulation Data
# 6 tricycles as per the AFIT fleet project
tricycles = [{"label": f"Keke {i+1:02}", "status": "free", "passenger": None, "ticket_code": None, "start_time": 0} for i in range(6)]
bookings = []

def process_simulation():
    """The core Discrete Event Simulation logic"""
    current_time = time.time()
    
    # 1. AUTO-COMPLETE: Check if any 60-second trips are finished
    for t in tricycles:
        if t['status'] == 'busy' and (current_time - t['start_time']) >= 60:
            # Find the booking and mark it finished
            for b in bookings:
                if b['ticket_code'] == t['ticket_code']:
                    b['status'] = 'completed'
            
            # Reset the Keke to free status
            t.update({"status": "free", "passenger": None, "ticket_code": None, "start_time": 0})

    # 2. DISPATCH: Move students from the Queue to a Keke
    queued = [b for b in bookings if b['status'] == 'queued']
    free_kekes = [t for t in tricycles if t['status'] == 'free']
    
    # Match the next person in line to the next available Keke
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

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/status')
def status():
    process_simulation() # Refresh the simulation state
    queued_list = [b for b in bookings if b['status'] == 'queued']
    return jsonify({
        "tricycles": tricycles,
        "queue_count": len(queued_list),
        "avg_wait": len(queued_list) * 8 # 8 mins per person in queue
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
    process_simulation() # Ensure state is current
    booking = next((b for b in bookings if b['booking_id'] == bid), None)
    if booking:
        # Calculate queue position
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
