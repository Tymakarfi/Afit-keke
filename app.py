import os
import sqlite3
import random
import string
import time
import threading
from flask import Flask, render_template, request, jsonify
import smtplib
from email.message import EmailMessage

app = Flask(__name__)

# --- CONFIGURATION (FULLY AUTOMATED) ---
# These pull from Render's "Environment" tab so you never have to edit code
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "your-default-email@gmail.com") 
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD") 
ADMIN_KEY = os.environ.get("ADMIN_KEY", "afit2026") 

# --- DATABASE SETUP (CLOUD-READY PATHS) ---
# This ensures the database file is found correctly on the server
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tricycle.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, matric_no TEXT, ticket_code TEXT, 
                  status TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- MOCK FLEET STATUS ---
TOTAL_TRICYCLES = 6
active_bookings = []

# --- BACKGROUND CLEANUP ---
def complete_trip(ticket_code):
    time.sleep(30)
    global active_bookings
    active_bookings = [b for b in active_bookings if b['ticket_code'] != ticket_code]
    print(f"✅ Trip {ticket_code} completed. Tricycle is now free.")

# --- HELPER FUNCTIONS ---
def generate_ticket():
    return "TKT-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def send_alert_email(ticket_code, user_name):
    if not SENDER_PASSWORD or not SENDER_EMAIL:
        print("⚠️ Email credentials missing in Environment Variables!")
        return
        
    msg = EmailMessage()
    msg.set_content(f"Hello {user_name},\n\nYour AFIT Smart-Keke is ready! \nTicket Code: {ticket_code}\n\nPlease proceed to the nearest park.")
    msg['Subject'] = f"Keke Assigned: {ticket_code}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = SENDER_EMAIL # Typically sends to the user; kept as self-send for your demo

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            print(f"📧 Alert email sent for {ticket_code}")
    except Exception as e:
        print(f"❌ Email error: {e}")

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/book', methods=['POST'])
def book():
    data = request.json
    name = data.get('name')
    matric = data.get('matric')
    
    ticket = generate_ticket()
    
    if len(active_bookings) < TOTAL_TRICYCLES:
        status = "Assigned"
        active_bookings.append({'ticket_code': ticket, 'name': name})
        threading.Thread(target=complete_trip, args=(ticket,)).start()
        threading.Thread(target=send_alert_email, args=(ticket, name)).start()
    else:
        status = f"Queued (Position: {len(active_bookings) - TOTAL_TRICYCLES + 1})"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO bookings (name, matric_no, ticket_code, status) VALUES (?, ?, ?, ?)", 
              (name, matric, ticket, status))
    conn.commit()
    conn.close()

    return jsonify({"status": status, "ticket": ticket})

@app.route('/admin')
def admin():
    key = request.args.get('key')
    if key != ADMIN_KEY:
        return "Unauthorized", 403
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM bookings ORDER BY id DESC")
    all_bookings = c.fetchall()
    conn.close()
    
    return render_template('admin.html', bookings=all_bookings, active_count=len(active_bookings))

# --- PRODUCTION LAUNCH ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)