import sqlite3
import random
import os
import hashlib
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "trucklink.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

CITIES = ["Mumbai", "Pune", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Ahmedabad", "Kolkata", "Jaipur", "Surat"]

CITY_DISTANCES = {
    ("Mumbai", "Pune"): 150,
    ("Mumbai", "Ahmedabad"): 530,
    ("Mumbai", "Surat"): 280,
    ("Mumbai", "Bengaluru"): 980,
    ("Mumbai", "Delhi"): 1420,
    ("Delhi", "Jaipur"): 280,
    ("Delhi", "Ahmedabad"): 940,
    ("Delhi", "Kolkata"): 1530,
    ("Bengaluru", "Chennai"): 350,
    ("Bengaluru", "Hyderabad"): 570,
    ("Chennai", "Hyderabad"): 630,
    ("Pune", "Hyderabad"): 560,
    ("Ahmedabad", "Surat"): 260,
    ("Kolkata", "Delhi"): 1530,
}

def get_distance(c1, c2):
    if c1 == c2:
        return 45
    pair = (c1, c2)
    rev_pair = (c2, c1)
    if pair in CITY_DISTANCES:
        return CITY_DISTANCES[pair]
    if rev_pair in CITY_DISTANCES:
        return CITY_DISTANCES[rev_pair]
    return random.randint(350, 1200)

CARGO_TYPES = [
    "Industrial Machinery", "Automobile Parts", "Textiles & Garments",
    "FMCG & Packaged Foods", "Agricultural Produce", "Electronics",
    "Construction Materials", "Chemicals & Raw Goods"
]

TRUCK_SPECS = [
    {"type": "Mini Truck (1-2T)", "cap": 1.5, "rate": 22.0},
    {"type": "Medium Duty (5-8T)", "cap": 7.0, "rate": 38.0},
    {"type": "Heavy Freight (15-20T)", "cap": 18.0, "rate": 65.0},
    {"type": "Container Carrier (25-30T)", "cap": 28.0, "rate": 95.0}
]

def init_and_seed():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Execute schema.sql
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    print("[OK] Schema initialized successfully with tables, triggers, views, and indexes.")

    random.seed(42)

    # 2. Seed Users
    # Admin
    cursor.execute("""
        INSERT INTO users (name, email, phone, role, password_hash, city)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("Fleet Manager", "admin@trucklink.local", "9876543210", "admin", hash_pw("admin123"), "Mumbai"))

    # 15 Drivers
    driver_names = [
        "Rajesh Kumar", "Gurpreet Singh", "Suresh Patil", "Ramesh Verma",
        "Vikram Yadav", "Amit Sharma", "Manoj Tiwari", "Anil Chauhan",
        "Balwinder Singh", "Satish Reddy", "Prakash Rao", "Mohd. Rafiq",
        "Deepak Joshi", "Sanjay Nair", "Dharmendra Paul"
    ]
    driver_ids = []
    for i, name in enumerate(driver_names, 1):
        city = random.choice(CITIES)
        email = f"driver{i}@trucklink.local"
        phone = f"98{random.randint(10000000, 99999999)}"
        cursor.execute("""
            INSERT INTO users (name, email, phone, role, password_hash, city)
            VALUES (?, ?, ?, 'driver', ?, ?)
        """, (name, email, phone, hash_pw("driver123"), city))
        driver_ids.append(cursor.lastrowid)

    # 30 Customers
    customer_names = [
        "Tata Logistics", "Reliance Retail Hub", "Godrej Agro", "Mahindra Auto Spares",
        "Flipkart Fulfilment", "Amazon Hub Pune", "Adani Port Services", "Ambuja Cement Dist",
        "Apollo Tyres Wholesaler", "Raymond Fabrics", "ITC Consumer Goods", "Asian Paints Depot",
        "Havells Electric", "Parle Products", "Britannia Logistics", "UltraTech Supply",
        "Sun Pharma Goods", "L&T Heavy Engineering", "Kalyani Steel", "Maruti Transit Hub",
        "Anand Enterprise", "Kiran Traders", "Patel Brothers", "Sharma & Sons",
        "South Express Cargo", "Western Logistics", "Vanguard Electronics", "Apex FMCG",
        "Metro Industrial Spares", "National Grain Supply"
    ]
    customer_ids = []
    for i, name in enumerate(customer_names, 1):
        city = random.choice(CITIES)
        email = f"client{i}@logistics.local"
        phone = f"97{random.randint(10000000, 99999999)}"
        cursor.execute("""
            INSERT INTO users (name, email, phone, role, password_hash, city)
            VALUES (?, ?, ?, 'customer', ?, ?)
        """, (name, email, phone, hash_pw("customer123"), city))
        customer_ids.append(cursor.lastrowid)

    print(f"[OK] Inserted 1 Admin, {len(driver_ids)} Drivers, {len(customer_ids)} Customers.")

    # 3. Seed Trucks (Assigning to drivers)
    truck_ids = []
    state_codes = ["MH", "DL", "KA", "TN", "TS", "GJ", "WB", "RJ"]
    for i, d_id in enumerate(driver_ids):
        spec = TRUCK_SPECS[i % len(TRUCK_SPECS)]
        st = random.choice(state_codes)
        plate = f"{st}-{random.randint(10, 99):02d}-{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}-{random.randint(1000, 9999)}"
        city = random.choice(CITIES)
        cursor.execute("""
            INSERT INTO trucks (driver_id, license_plate, truck_type, capacity_tons, base_rate_per_km, status, current_city)
            VALUES (?, ?, ?, ?, ?, 'available', ?)
        """, (d_id, plate, spec["type"], spec["cap"], spec["rate"], city))
        truck_ids.append(cursor.lastrowid)

    # Add 5 additional fleet trucks without assigned drivers (depot spares)
    for i in range(1, 6):
        spec = random.choice(TRUCK_SPECS)
        plate = f"MH-12-FL-{random.randint(5000, 9999)}"
        city = random.choice(CITIES)
        cursor.execute("""
            INSERT INTO trucks (driver_id, license_plate, truck_type, capacity_tons, base_rate_per_km, status, current_city)
            VALUES (NULL, ?, ?, ?, ?, 'available', ?)
        """, (plate, spec["type"], spec["cap"], spec["rate"], city))
        truck_ids.append(cursor.lastrowid)

    print(f"[OK] Seeded {len(truck_ids)} Fleet Trucks.")

    # 4. Seed 350 Historical & Active Bookings
    # Span from 180 days ago to today
    base_time = datetime.now()
    booking_statuses = ["delivered"] * 280 + ["in_transit"] * 30 + ["confirmed"] * 20 + ["pending"] * 10 + ["cancelled"] * 10

    for i in range(350):
        cust_id = random.choice(customer_ids)
        truck_id = random.choice(truck_ids)
        pickup = random.choice(CITIES)
        drop = random.choice([c for c in CITIES if c != pickup])
        dist = get_distance(pickup, drop)
        
        # Determine cargo & weight
        cargo = random.choice(CARGO_TYPES)
        # Fetch truck capacity
        cursor.execute("SELECT capacity_tons, base_rate_per_km FROM trucks WHERE truck_id = ?", (truck_id,))
        cap, base_rate = cursor.fetchone()
        weight = round(random.uniform(0.4 * cap, cap), 1)

        # Fare formula: Base fare + (dist * rate) + (weight * 120)
        fare = round(1200 + (dist * base_rate) + (weight * 120), 2)

        # Dates
        days_ago = random.randint(1, 180)
        book_time = base_time - timedelta(days=days_ago, hours=random.randint(1, 12))
        sched_date = (book_time + timedelta(days=1)).strftime("%Y-%m-%d")
        
        status = booking_statuses[i]
        delay_hrs = 0.0
        deliv_time = None

        if status == "delivered":
            # Typical trip takes 1-3 days depending on distance
            trip_days = max(1, dist // 450)
            # 25% chance of delay
            if random.random() < 0.28:
                delay_hrs = round(random.uniform(1.5, 9.0), 1)
            deliv_time = book_time + timedelta(days=trip_days, hours=int(delay_hrs))
        elif status == "in_transit":
            # Active ongoing trip
            deliv_time = None
        elif status == "cancelled":
            delay_hrs = 0.0

        cursor.execute("""
            INSERT INTO bookings (
                customer_id, truck_id, pickup_city, drop_city, distance_km,
                cargo_type, cargo_weight_tons, fare_amount, booking_date,
                scheduled_date, delivery_date, status, delay_hours
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cust_id, truck_id, pickup, drop, dist, cargo, weight, fare,
            book_time.strftime("%Y-%m-%d %H:%M:%S"), sched_date,
            deliv_time.strftime("%Y-%m-%d %H:%M:%S") if deliv_time else None,
            status, delay_hrs
        ))
        b_id = cursor.lastrowid

        # If delivered or in_transit/confirmed, add payment
        if status in ["delivered", "in_transit", "confirmed"]:
            pay_method = random.choice(["UPI", "Net Banking", "Cash on Delivery", "Credit Card"])
            tx_ref = f"TXN-{random.randint(10000000, 99999999)}"
            cursor.execute("""
                INSERT INTO payments (booking_id, amount, payment_method, payment_status, transaction_ref, payment_date)
                VALUES (?, ?, ?, 'paid', ?, ?)
            """, (b_id, fare, pay_method, tx_ref, book_time.strftime("%Y-%m-%d %H:%M:%S")))

        # If delivered, 70% leave review
        if status == "delivered" and random.random() < 0.70:
            rating = 5 if delay_hrs == 0 else (4 if delay_hrs < 4 else random.choice([2, 3]))
            feedbacks = {
                5: "On-time delivery, driver was very professional and cargo safe.",
                4: "Good experience overall, took slightly longer at checkpoint.",
                3: "Average transit time, some minor delay due to road diversion.",
                2: "Delayed delivery by several hours, need better route tracking."
            }
            cursor.execute("""
                INSERT INTO reviews (booking_id, rating, feedback, created_at)
                VALUES (?, ?, ?, ?)
            """, (b_id, rating, feedbacks.get(rating, "Trip completed."), (deliv_time + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")))

    # Sync a few trucks to in_transit
    cursor.execute("""
        UPDATE trucks 
        SET status = 'in_transit' 
        WHERE truck_id IN (SELECT DISTINCT truck_id FROM bookings WHERE status = 'in_transit' AND truck_id IS NOT NULL)
    """)

    conn.commit()
    conn.close()
    print("[OK] Successfully seeded 350 bookings, payments, reviews, and synchronized fleet status!")

if __name__ == "__main__":
    init_and_seed()
