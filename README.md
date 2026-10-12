# TruckLink: Integrated Logistics & Fleet Analytics Platform
### A Combined 100% Local Academic Project for **FSD**, **DBMS**, and **EDADV**

---

## 1. Project Overview & Subject Integration
**TruckLink** is an end-to-end freight booking and fleet analytics platform designed to satisfy all curriculum and laboratory evaluation criteria for three distinct subjects within a single unified codebase:

```
                          ┌────────────────────────────────┐
                          │   TruckLink Core Platform      │
                          └───────────────┬────────────────┘
                                          │
       ┌──────────────────────────────────┼──────────────────────────────────┐
       │                                  │                                  │
┌──────▼──────┐                   ┌───────▼───────┐                  ┌───────▼───────┐
│     FSD     │                   │     DBMS      │                  │     EDADV     │
│ Full Stack  │                   │ Database Sys  │                  │ Data Analysis │
├─────────────┤                   ├───────────────┤                  ├───────────────┤
│• Customer   │                   │• 3NF Schema   │                  │• Univariate   │
│  Booking UI │                   │• SQLite/MySQL │                  │  Distributions│
│• Driver App │                   │• 3 Triggers   │                  │• Boxplot Fare │
│• Admin Panel│                   │• 4 Views      │                  │  Outliers     │
│• REST APIs  │                   │• 7 Indexes    │                  │• Heatmap Corr │
│• 0% CDN     │                   │• ACID Locks   │                  │• Jupyter .ipynb│
└─────────────┘                   └───────────────┘                  └───────────────┘
```

---

## 2. Subject-by-Subject Breakdown

### A. DBMS (Database Management Systems)
- **Relational Integrity (3NF):** 6 interconnected tables (`users`, `trucks`, `bookings`, `payments`, `reviews`, `audit_logs`).
- **Triggers:**
  - `trg_booking_status_in_transit`: Automatically updates truck status to `'in_transit'` upon trip dispatch.
  - `trg_booking_status_delivered`: Automatically frees the truck back to `'available'` and updates its current location city upon delivery completion.
  - `trg_booking_audit_status`: Automatically writes historical audit records into `audit_logs` whenever booking statuses change.
- **Views (Complex Aggregations):**
  - `vw_fleet_status`: Aggregates active, available, and maintenance trucks by type.
  - `vw_driver_performance`: Calculates completed trips, earnings, and average rating per driver.
  - `vw_route_analytics`: Summarizes tonnage, frequency, and delays per corridor.
  - `vw_monthly_revenue`: Monthly gross revenue and booking counts.
- **Concurrency & Transactions:** ACID-compliant `BEGIN TRANSACTION ... COMMIT / ROLLBACK` during booking creation prevents double-booking race conditions.
- **Cross-Engine Support:**
  - `database/schema.sql`: Active SQLite script (Zero config, local file).
  - `database/schema_mysql.sql`: MySQL/MariaDB script with `STORED PROCEDURES` (`sp_calculate_fare`, `sp_confirm_and_lock_truck`) for university lab evaluations.

### B. FSD (Full Stack Development)
- **Zero-Internet Architecture:** 100% self-contained HTML5, CSS3, and JavaScript. No external CDN requests (`cdnjs`, `bootstrap`, `tailwind CDN`).
- **Frontend Portals (`frontend/`):**
  1. **Customer Portal:** City selection, cargo weight validation, real-time offline fare preview, truck vehicle picker, and booking history.
  2. **Driver Console:** View incoming assignments, one-click buttons to transition trips (`in_transit` -> `delivered`), directly triggering DBMS triggers.
  3. **Admin Dashboard:** High-level operational KPIs, interactive HTML5 Canvas charts, and fleet controls.
- **Backend REST API (`backend/server.py`):**
  - `GET /api/trucks`: Filter available trucks by city and tonnage capacity.
  - `POST /api/bookings`: Transactional creation of booking + simulated payment.
  - `PATCH /api/bookings/:id/status`: Updates trip lifecycle.
  - `GET /api/analytics/summary`: Feeds SQL view data directly to the UI.
  - `GET /api/users`: Switch roles instantly for grading demonstrations.

### C. EDADV (Exploratory Data Analysis & Data Visualization)
- **Local Dataset:** 350 realistic Indian freight transit records spanning 10 major logistics hubs (Mumbai, Delhi, Pune, Bengaluru, Chennai, Hyderabad, Ahmedabad, Kolkata, Jaipur, Surat).
- **Statistical EDA Script (`edadv_analytics/eda_analysis.py`):**
  - Data shape verification, missing value audits, summary statistics (`describe()`).
  - Correlation coefficient matrix ($r > 0.85$ between distance and fare).
- **High-Resolution Figures Generated (`edadv_analytics/charts/`):**
  1. `01_univariate_weight_distance.png`: Histogram & KDE curves for payload weights and route mileages.
  2. `02_outlier_boxplots_fare.png`: Box plots highlighting fare dispersion and price outliers across vehicle categories.
  3. `03_correlation_heatmap.png`: Multi-metric correlation heatmap.
  4. `04_distance_vs_fare_scatter.png`: Distance vs. Fare scatter plot with linear regression trend line.
  5. `05_top_revenue_routes.png`: Bar chart of top 10 most profitable national corridors.
  6. `06_monthly_booking_trends.png`: Monthly stacked order volume and delivery fulfillment.
- **Jupyter Notebook (`edadv_analytics/eda_report.ipynb`):** Complete interactive notebook ready to open in JupyterLab.

---

## 3. How to Run the Project (100% Offline)

### Method 1: One-Click Launch (Windows)
1. Double-click `start_server.bat` in the project root folder.
2. Your browser will automatically open `http://localhost:5000`.

### Method 2: Command Line Launch
1. **Start the local server:**
   ```bash
   python backend/server.py
   ```
2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

### Method 3: Re-running the EDADV Analytics Script
To re-analyze data and generate fresh charts:
```bash
python edadv_analytics/eda_analysis.py
# Or double-click run_eda.bat
```

To view the Jupyter Notebook:
```bash
jupyter lab edadv_analytics/eda_report.ipynb
```

---

## 4. Viva / Evaluation Cheat Sheet

| Question | Answer for Examiner |
| :--- | :--- |
| **How is 3NF achieved?** | All non-key attributes are fully dependent only on primary keys. Users are separated from Trucks, Payments are isolated from Bookings, and Reviews are separated from Trips to prevent transitive anomalies. |
| **Where are the DBMS Triggers?** | When a driver clicks "Start Trip" or "Mark Delivered", `trg_booking_status_in_transit` and `trg_booking_status_delivered` automatically synchronize truck availability without manual application code. |
| **Why is the project 100% local?** | All CSS and JS are bundled locally. SQLite requires no cloud server. All charts are rendered via Python Matplotlib/Seaborn and local HTML5 Canvas without external CDN dependencies. |
| **What insights were found during EDADV?** | Container carriers drive 52% of total freight revenue despite being 25% of fleet. Long-haul routes (> 1,200 KM) account for 85% of transit delays. |
