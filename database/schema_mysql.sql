-- ====================================================================
-- TRUCKLINK: MySQL / MariaDB Relational Database Schema
-- Fully Normalized (3NF) Relational Database Definition
-- Includes Tables, Constraints, Stored Procedures, Triggers, Views & Indexes
-- ====================================================================

CREATE DATABASE IF NOT EXISTS trucklink_db;
USE trucklink_db;

-- 1. DROP EXISTING OBJECTS
DROP VIEW IF EXISTS vw_monthly_revenue;
DROP VIEW IF EXISTS vw_route_analytics;
DROP VIEW IF EXISTS vw_driver_performance;
DROP VIEW IF EXISTS vw_fleet_status;

DROP TRIGGER IF EXISTS trg_booking_status_delivered;
DROP TRIGGER IF EXISTS trg_booking_status_in_transit;
DROP TRIGGER IF EXISTS trg_booking_audit_status;

DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS trucks;
DROP TABLE IF EXISTS users;

-- 2. RELATIONAL TABLES

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    role ENUM('customer', 'driver', 'admin') NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    city VARCHAR(80) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE trucks (
    truck_id INT AUTO_INCREMENT PRIMARY KEY,
    driver_id INT NULL,
    license_plate VARCHAR(25) UNIQUE NOT NULL,
    truck_type ENUM(
        'Mini Truck (1-2T)',
        'Medium Duty (5-8T)',
        'Heavy Freight (15-20T)',
        'Container Carrier (25-30T)'
    ) NOT NULL,
    capacity_tons DECIMAL(5,2) NOT NULL,
    base_rate_per_km DECIMAL(6,2) NOT NULL,
    status ENUM('available', 'in_transit', 'maintenance') DEFAULT 'available',
    current_city VARCHAR(80) NOT NULL,
    FOREIGN KEY (driver_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    truck_id INT NULL,
    pickup_city VARCHAR(80) NOT NULL,
    drop_city VARCHAR(80) NOT NULL,
    distance_km DECIMAL(7,2) NOT NULL,
    cargo_type VARCHAR(100) NOT NULL,
    cargo_weight_tons DECIMAL(5,2) NOT NULL,
    fare_amount DECIMAL(10,2) NOT NULL,
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_date DATE NOT NULL,
    delivery_date TIMESTAMP NULL,
    status ENUM('pending', 'confirmed', 'in_transit', 'delivered', 'cancelled') DEFAULT 'pending',
    delay_hours DECIMAL(4,1) DEFAULT 0.0,
    FOREIGN KEY (customer_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (truck_id) REFERENCES trucks(truck_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT UNIQUE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method ENUM('UPI', 'Net Banking', 'Cash on Delivery', 'Credit Card') NOT NULL,
    payment_status ENUM('paid', 'pending', 'refunded') DEFAULT 'paid',
    transaction_ref VARCHAR(80) UNIQUE NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT UNIQUE NOT NULL,
    rating TINYINT CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INT NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_value VARCHAR(255),
    new_value VARCHAR(255),
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 3. STORED PROCEDURES (DBMS College Lab Requirement)

DELIMITER //

CREATE PROCEDURE sp_calculate_fare(
    IN p_distance DECIMAL(7,2),
    IN p_weight DECIMAL(5,2),
    IN p_truck_type VARCHAR(50),
    OUT p_total_fare DECIMAL(10,2)
)
BEGIN
    DECLARE v_rate DECIMAL(6,2);
    
    CASE p_truck_type
        WHEN 'Mini Truck (1-2T)' THEN SET v_rate = 22.0;
        WHEN 'Medium Duty (5-8T)' THEN SET v_rate = 38.0;
        WHEN 'Heavy Freight (15-20T)' THEN SET v_rate = 65.0;
        WHEN 'Container Carrier (25-30T)' THEN SET v_rate = 95.0;
        ELSE SET v_rate = 30.0;
    END CASE;
    
    SET p_total_fare = 1200 + (p_distance * v_rate) + (p_weight * 120);
END //

CREATE PROCEDURE sp_confirm_and_lock_truck(
    IN p_booking_id INT,
    IN p_truck_id INT,
    OUT p_status_msg VARCHAR(100)
)
BEGIN
    DECLARE v_truck_status VARCHAR(20);
    
    START TRANSACTION;
    
    SELECT status INTO v_truck_status FROM trucks WHERE truck_id = p_truck_id FOR UPDATE;
    
    IF v_truck_status = 'available' THEN
        UPDATE bookings SET truck_id = p_truck_id, status = 'confirmed' WHERE booking_id = p_booking_id;
        UPDATE trucks SET status = 'in_transit' WHERE truck_id = p_truck_id;
        COMMIT;
        SET p_status_msg = 'SUCCESS: Booking Confirmed and Truck Assigned';
    ELSE
        ROLLBACK;
        SET p_status_msg = 'ERROR: Truck is not available';
    END IF;
END //

-- 4. MYSQL TRIGGERS

CREATE TRIGGER trg_booking_status_in_transit
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF NEW.status = 'in_transit' AND NEW.truck_id IS NOT NULL THEN
        UPDATE trucks SET status = 'in_transit' WHERE truck_id = NEW.truck_id;
    END IF;
END //

CREATE TRIGGER trg_booking_status_delivered
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF NEW.status = 'delivered' AND NEW.truck_id IS NOT NULL THEN
        UPDATE trucks SET status = 'available', current_city = NEW.drop_city WHERE truck_id = NEW.truck_id;
    END IF;
END //

CREATE TRIGGER trg_booking_audit_status
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO audit_logs (table_name, record_id, action, old_value, new_value)
        VALUES ('bookings', NEW.booking_id, 'STATUS_UPDATE', OLD.status, NEW.status);
    END IF;
END //

DELIMITER ;

-- 5. VIEWS
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

CREATE VIEW vw_route_analytics AS
SELECT 
    CONCAT(pickup_city, ' -> ', drop_city) AS route_name,
    pickup_city,
    drop_city,
    COUNT(booking_id) AS booking_count,
    ROUND(AVG(distance_km), 1) AS avg_distance_km,
    ROUND(SUM(cargo_weight_tons), 2) AS total_tonnage,
    ROUND(SUM(fare_amount), 2) AS total_revenue,
    ROUND(AVG(delay_hours), 1) AS avg_delay_hours
FROM bookings
GROUP BY pickup_city, drop_city;

-- 6. INDEXES
CREATE INDEX idx_bookings_customer ON bookings(customer_id);
CREATE INDEX idx_bookings_truck ON bookings(truck_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_trucks_status ON trucks(status);
