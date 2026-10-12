-- ====================================================================
-- TRUCKLINK: Database Management System (DBMS) Schema
-- Fully Normalized (3NF) Relational Database Definition
-- Compatible with SQLite3, and exportable to MySQL/PostgreSQL
-- ====================================================================

PRAGMA foreign_keys = ON;

-- 1. DROP EXISTING OBJECTS (FOR CLEAN INITIALIZATION)
DROP VIEW IF EXISTS vw_monthly_revenue;
DROP VIEW IF EXISTS vw_route_analytics;
DROP VIEW IF EXISTS vw_driver_performance;
DROP VIEW IF EXISTS vw_fleet_status;

DROP TRIGGER IF EXISTS trg_booking_audit_status;
DROP TRIGGER IF EXISTS trg_booking_status_delivered;
DROP TRIGGER IF EXISTS trg_booking_status_in_transit;

DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS trucks;
DROP TABLE IF EXISTS users;

-- 2. RELATIONAL TABLES

-- Users Table: Customer, Driver, and Admin Accounts
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    role TEXT CHECK(role IN ('customer', 'driver', 'admin')) NOT NULL,
    password_hash TEXT NOT NULL,
    city TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Trucks Table: Fleet Vehicles & Driver Assignment
CREATE TABLE trucks (
    truck_id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER,
    license_plate TEXT UNIQUE NOT NULL,
    truck_type TEXT CHECK(truck_type IN (
        'Mini Truck (1-2T)',
        'Medium Duty (5-8T)',
        'Heavy Freight (15-20T)',
        'Container Carrier (25-30T)'
    )) NOT NULL,
    capacity_tons REAL NOT NULL,
    base_rate_per_km REAL NOT NULL,
    status TEXT CHECK(status IN ('available', 'in_transit', 'maintenance')) DEFAULT 'available',
    current_city TEXT NOT NULL,
    FOREIGN KEY (driver_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- Bookings Table: Freight Orders and Trips
CREATE TABLE bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    truck_id INTEGER,
    pickup_city TEXT NOT NULL,
    drop_city TEXT NOT NULL,
    distance_km REAL NOT NULL,
    cargo_type TEXT NOT NULL,
    cargo_weight_tons REAL NOT NULL,
    fare_amount REAL NOT NULL,
    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    scheduled_date DATE NOT NULL,
    delivery_date DATETIME,
    status TEXT CHECK(status IN ('pending', 'confirmed', 'in_transit', 'delivered', 'cancelled')) DEFAULT 'pending',
    delay_hours REAL DEFAULT 0.0,
    FOREIGN KEY (customer_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (truck_id) REFERENCES trucks(truck_id) ON DELETE SET NULL
);

-- Payments Table: Transaction Ledgers
CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER UNIQUE NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT CHECK(payment_method IN ('UPI', 'Net Banking', 'Cash on Delivery', 'Credit Card')) NOT NULL,
    payment_status TEXT CHECK(payment_status IN ('paid', 'pending', 'refunded')) DEFAULT 'paid',
    transaction_ref TEXT UNIQUE NOT NULL,
    payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);

-- Reviews Table: Quality of Service & Driver Ratings
CREATE TABLE reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER UNIQUE NOT NULL,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5) NOT NULL,
    feedback TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);

-- Audit Logs Table: Automated change tracking
CREATE TABLE audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. AUTOMATED DATABASE TRIGGERS

-- Trigger 1: When booking becomes 'in_transit', set Truck status to 'in_transit'
CREATE TRIGGER trg_booking_status_in_transit
AFTER UPDATE OF status ON bookings
WHEN NEW.status = 'in_transit' AND NEW.truck_id IS NOT NULL
BEGIN
    UPDATE trucks
    SET status = 'in_transit'
    WHERE truck_id = NEW.truck_id;
END;

-- Trigger 2: When booking is 'delivered', set Truck status to 'available' & update its city
CREATE TRIGGER trg_booking_status_delivered
AFTER UPDATE OF status ON bookings
WHEN NEW.status = 'delivered' AND NEW.truck_id IS NOT NULL
BEGIN
    UPDATE trucks
    SET status = 'available',
        current_city = NEW.drop_city
    WHERE truck_id = NEW.truck_id;
END;

-- Trigger 3: Audit logger for any status change in bookings
CREATE TRIGGER trg_booking_audit_status
AFTER UPDATE OF status ON bookings
WHEN OLD.status <> NEW.status
BEGIN
    INSERT INTO audit_logs (table_name, record_id, action, old_value, new_value)
    VALUES ('bookings', NEW.booking_id, 'STATUS_UPDATE', OLD.status, NEW.status);
END;

-- 4. REPORTING & ANALYTICS VIEWS

-- View 1: Fleet Utilization Overview
CREATE VIEW vw_fleet_status AS
SELECT 
    truck_type,
    COUNT(truck_id) AS total_trucks,
    SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) AS available_count,
    SUM(CASE WHEN status = 'in_transit' THEN 1 ELSE 0 END) AS in_transit_count,
    SUM(CASE WHEN status = 'maintenance' THEN 1 ELSE 0 END) AS maintenance_count,
    ROUND(AVG(capacity_tons), 2) AS avg_capacity_tons
FROM trucks
GROUP BY truck_type;

-- View 2: Driver Performance & Earnings
CREATE VIEW vw_driver_performance AS
SELECT 
    u.user_id AS driver_id,
    u.name AS driver_name,
    u.phone AS driver_phone,
    t.license_plate,
    t.truck_type,
    COUNT(b.booking_id) AS total_trips,
    SUM(CASE WHEN b.status = 'delivered' THEN 1 ELSE 0 END) AS completed_trips,
    ROUND(COALESCE(SUM(CASE WHEN b.status = 'delivered' THEN b.fare_amount ELSE 0 END), 0), 2) AS total_earnings,
    ROUND(COALESCE(AVG(r.rating), 0), 1) AS avg_rating
FROM users u
JOIN trucks t ON u.user_id = t.driver_id
LEFT JOIN bookings b ON t.truck_id = b.truck_id
LEFT JOIN reviews r ON b.booking_id = r.booking_id
WHERE u.role = 'driver'
GROUP BY u.user_id, u.name, u.phone, t.license_plate, t.truck_type;

-- View 3: Route Analytics (Corridors, Volume, Delay)
CREATE VIEW vw_route_analytics AS
SELECT 
    pickup_city || ' -> ' || drop_city AS route_name,
    pickup_city,
    drop_city,
    COUNT(booking_id) AS booking_count,
    ROUND(AVG(distance_km), 1) AS avg_distance_km,
    ROUND(SUM(cargo_weight_tons), 2) AS total_tonnage,
    ROUND(SUM(fare_amount), 2) AS total_revenue,
    ROUND(AVG(delay_hours), 1) AS avg_delay_hours
FROM bookings
GROUP BY pickup_city, drop_city;

-- View 4: Monthly Revenue Aggregation
CREATE VIEW vw_monthly_revenue AS
SELECT 
    strftime('%Y-%m', booking_date) AS month,
    COUNT(booking_id) AS total_bookings,
    SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered_bookings,
    ROUND(SUM(fare_amount), 2) AS gross_revenue
FROM bookings
GROUP BY strftime('%Y-%m', booking_date)
ORDER BY month ASC;

-- 5. PERFORMANCE B-TREE INDEXES
CREATE INDEX idx_bookings_customer ON bookings(customer_id);
CREATE INDEX idx_bookings_truck ON bookings(truck_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_route ON bookings(pickup_city, drop_city);
CREATE INDEX idx_trucks_status ON trucks(status);
CREATE INDEX idx_trucks_city ON trucks(current_city);
CREATE INDEX idx_payments_booking ON payments(booking_id);
