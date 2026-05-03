import sqlite3

def get_db():
conn = sqlite3.connect(‘tricycle.db’)
conn.row_factory = sqlite3.Row
return conn

def init_db():
conn = get_db()

```
conn.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    matric TEXT UNIQUE NOT NULL,
    faculty TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)''')

conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id TEXT UNIQUE,
    ticket_code TEXT UNIQUE,
    name TEXT,
    matric TEXT,
    pickup TEXT,
    destination TEXT,
    status TEXT DEFAULT 'queued',
    tricycle TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_at DATETIME,
    completed_at DATETIME
)''')

conn.execute('''CREATE TABLE IF NOT EXISTS tricycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT UNIQUE,
    status TEXT DEFAULT 'free',
    passenger TEXT,
    current_booking_id TEXT,
    route TEXT
)''')

check = conn.execute("SELECT count(*) FROM tricycles").fetchone()[0]
if check == 0:
    for i in range(1, 7):
        conn.execute("INSERT INTO tricycles (label) VALUES (?)", (f"AFIT-KK-{i:02}",))

conn.commit()
conn.close()
```

if **name** == “**main**”:
init_db()
print(“Database initialized.”)
