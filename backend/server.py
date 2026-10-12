import http.server
import socketserver
import json
import sqlite3
import os
import urllib.parse
from datetime import datetime

PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
DB_PATH = os.path.join(PROJECT_DIR, "database", "trucklink.db")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
CHARTS_DIR = os.path.join(PROJECT_DIR, "edadv_analytics", "charts")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

class TruckLinkHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local cross-origin development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status_code=200):
        response_bytes = json.dumps(data, default=str).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API ROUTES
        if path == "/api/health":
            self.send_json({"status": "online", "system": "TruckLink v1.0", "mode": "100% Local"})
            return

        elif path == "/api/users":
            conn = get_db()
            users = conn.execute("SELECT user_id, name, email, role, city FROM users ORDER BY role, name").fetchall()
            conn.close()
            self.send_json([dict(u) for u in users])
            return

        elif path == "/api/trucks":
            conn = get_db()
            city = query.get("city", [None])[0]
            weight = query.get("weight", [None])[0]
            
            sql = """
                SELECT t.truck_id, t.license_plate, t.truck_type, t.capacity_tons, 
                       t.base_rate_per_km, t.status, t.current_city, u.name AS driver_name
                FROM trucks t
                LEFT JOIN users u ON t.driver_id = u.user_id
                WHERE 1=1
            """
            params = []
            if city:
                sql += " AND t.current_city = ?"
                params.append(city)
            if weight:
                sql += " AND t.capacity_tons >= ?"
                params.append(float(weight))
            
            sql += " ORDER BY t.status, t.capacity_tons ASC"
            trucks = conn.execute(sql, params).fetchall()
            conn.close()
            self.send_json([dict(t) for t in trucks])
            return

        elif path == "/api/bookings":
            conn = get_db()
            role = query.get("role", [None])[0]
            user_id = query.get("user_id", [None])[0]

            sql = """
                SELECT b.*, u.name AS customer_name, t.license_plate, t.truck_type, 
                       d.name AS driver_name, r.rating, r.feedback
                FROM bookings b
                JOIN users u ON b.customer_id = u.user_id
                LEFT JOIN trucks t ON b.truck_id = t.truck_id
                LEFT JOIN users d ON t.driver_id = d.user_id
                LEFT JOIN reviews r ON b.booking_id = r.booking_id
                WHERE 1=1
            """
            params = []
            if role == "customer" and user_id:
                sql += " AND b.customer_id = ?"
                params.append(int(user_id))
            elif role == "driver" and user_id:
                sql += " AND t.driver_id = ?"
                params.append(int(user_id))
            
            sql += " ORDER BY b.booking_id DESC LIMIT 100"
            bookings = conn.execute(sql, params).fetchall()
            conn.close()
            self.send_json([dict(b) for b in bookings])
            return

        elif path == "/api/analytics/summary":
            conn = get_db()
            # Fetch summary stats directly from DBMS Views
            fleet = conn.execute("SELECT * FROM vw_fleet_status").fetchall()
            top_routes = conn.execute("SELECT * FROM vw_route_analytics ORDER BY total_revenue DESC LIMIT 8").fetchall()
            drivers = conn.execute("SELECT * FROM vw_driver_performance ORDER BY completed_trips DESC LIMIT 8").fetchall()
            monthly = conn.execute("SELECT * FROM vw_monthly_revenue").fetchall()
            
            # Key high-level metrics
            counts = conn.execute("""
                SELECT 
                    COUNT(booking_id) AS total_bookings,
                    SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered_count,
                    SUM(CASE WHEN status = 'in_transit' THEN 1 ELSE 0 END) AS in_transit_count,
                    ROUND(SUM(fare_amount), 2) AS total_revenue,
                    ROUND(AVG(fare_amount), 2) AS avg_fare
                FROM bookings
            """).fetchone()

            conn.close()
            self.send_json({
                "kpis": dict(counts) if counts else {},
                "fleet_status": [dict(r) for r in fleet],
                "top_routes": [dict(r) for r in top_routes],
                "top_drivers": [dict(r) for r in drivers],
                "monthly_trend": [dict(r) for r in monthly]
            })
            return

        elif path.startswith("/charts/"):
            # Serve generated analysis chart images
            chart_file = path.replace("/charts/", "")
            file_path = os.path.join(CHARTS_DIR, chart_file)
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                with open(file_path, 'rb') as f:
                    content = f.read()
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        # 2. STATIC FILES SERVING (Frontend)
        clean_path = path.lstrip("/")
        if clean_path == "" or clean_path == "index.html":
            file_path = os.path.join(FRONTEND_DIR, "index.html")
        else:
            file_path = os.path.join(FRONTEND_DIR, clean_path)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            content_type = "text/plain"
            if file_path.endswith(".html"):
                content_type = "text/html"
            elif file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".js"):
                content_type = "application/javascript"
            elif file_path.endswith(".png"):
                content_type = "image/png"
            elif file_path.endswith(".svg"):
                content_type = "image/svg+xml"

            self.send_response(200)
            self.send_header('Content-Type', f"{content_type}; charset=utf-8")
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body) if body else {}

        if parsed.path == "/api/bookings":
            conn = get_db()
            try:
                # Use a database transaction
                conn.execute("BEGIN TRANSACTION")
                
                # Verify truck availability
                truck_id = data.get("truck_id")
                if truck_id:
                    truck = conn.execute("SELECT status FROM trucks WHERE truck_id = ?", (truck_id,)).fetchone()
                    if truck and truck["status"] != "available":
                        conn.rollback()
                        conn.close()
                        self.send_json({"error": "Selected truck is not currently available"}, 400)
                        return

                # Calculate fare if not supplied: 1200 + (distance * 35) + (weight * 120)
                distance = float(data.get("distance_km", 100))
                weight = float(data.get("cargo_weight_tons", 2.0))
                fare = float(data.get("fare_amount", 1200 + (distance * 35) + (weight * 120)))

                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO bookings (
                        customer_id, truck_id, pickup_city, drop_city, distance_km,
                        cargo_type, cargo_weight_tons, fare_amount, scheduled_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed')
                """, (
                    data.get("customer_id", 2),
                    truck_id,
                    data.get("pickup_city", "Mumbai"),
                    data.get("drop_city", "Pune"),
                    distance,
                    data.get("cargo_type", "Standard Goods"),
                    weight,
                    fare,
                    data.get("scheduled_date", datetime.now().strftime("%Y-%m-%d"))
                ))
                new_booking_id = cur.lastrowid

                # Update truck status
                if truck_id:
                    cur.execute("UPDATE trucks SET status = 'in_transit' WHERE truck_id = ?", (truck_id,))

                # Record simulated payment
                cur.execute("""
                    INSERT INTO payments (booking_id, amount, payment_method, payment_status, transaction_ref)
                    VALUES (?, ?, ?, 'paid', ?)
                """, (
                    new_booking_id,
                    fare,
                    data.get("payment_method", "UPI"),
                    f"LOCAL-TXN-{int(datetime.now().timestamp())}"
                ))

                conn.commit()
                conn.close()
                self.send_json({
                    "message": "Booking confirmed successfully!",
                    "booking_id": new_booking_id,
                    "fare_amount": fare
                }, 201)
            except Exception as e:
                conn.rollback()
                conn.close()
                self.send_json({"error": str(e)}, 500)
            return

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/bookings/") and path.endswith("/status"):
            booking_id = int(path.split("/")[3])
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
            new_status = data.get("status")

            if new_status not in ['pending', 'confirmed', 'in_transit', 'delivered', 'cancelled']:
                self.send_json({"error": "Invalid status value"}, 400)
                return

            conn = get_db()
            try:
                # Update booking status (Triggers in SQLite will automatically handle truck status and audit logging!)
                conn.execute("UPDATE bookings SET status = ? WHERE booking_id = ?", (new_status, booking_id))
                conn.commit()
                conn.close()
                self.send_json({"message": f"Booking #{booking_id} updated to {new_status}"})
            except Exception as e:
                conn.close()
                self.send_json({"error": str(e)}, 500)
            return

        self.send_response(404)
        self.end_headers()

def run_server():
    server_address = ('', PORT)
    with socketserver.TCPServer(server_address, TruckLinkHandler) as httpd:
        print("="*60)
        print(" TRUCKLINK: 100% Local Server Running Successfully")
        print(f" URL: http://localhost:{PORT}")
        print("="*60)
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
