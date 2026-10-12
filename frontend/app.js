// ====================================================================
// TRUCKLINK: Offline Client-Side Application Logic
// 100% Localhost - Zero External Dependencies
// ====================================================================

const API_BASE = "http://localhost:5000/api";

let currentRole = "customer";
let currentUser = null;
let allUsers = [];

// Local Distance Matrix (Offline)
const DISTANCES = {
  "Mumbai-Pune": 150, "Pune-Mumbai": 150,
  "Mumbai-Ahmedabad": 530, "Ahmedabad-Mumbai": 530,
  "Mumbai-Surat": 280, "Surat-Mumbai": 280,
  "Mumbai-Bengaluru": 980, "Bengaluru-Mumbai": 980,
  "Mumbai-Delhi": 1420, "Delhi-Mumbai": 1420,
  "Delhi-Jaipur": 280, "Jaipur-Delhi": 280,
  "Delhi-Ahmedabad": 940, "Ahmedabad-Delhi": 940,
  "Delhi-Kolkata": 1530, "Kolkata-Delhi": 1530,
  "Bengaluru-Chennai": 350, "Chennai-Bengaluru": 350,
  "Bengaluru-Hyderabad": 570, "Hyderabad-Bengaluru": 570,
  "Chennai-Hyderabad": 630, "Hyderabad-Chennai": 630,
  "Pune-Hyderabad": 560, "Hyderabad-Pune": 560,
  "Ahmedabad-Surat": 260, "Surat-Ahmedabad": 260,
};

function getLocalDistance(c1, c2) {
  if (c1 === c2) return 50;
  const key = `${c1}-${c2}`;
  return DISTANCES[key] || 650;
}

// 1. INITIALIZATION
document.addEventListener("DOMContentLoaded", () => {
  // Set default scheduled date to tomorrow
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const dateInput = document.getElementById("scheduled-date");
  if (dateInput) {
    dateInput.value = tomorrow.toISOString().split("T")[0];
  }

  loadUsers();
  calculateFarePreview();
});

// 2. USER & ROLE MANAGEMENT
async function loadUsers() {
  try {
    const res = await fetch(`${API_BASE}/users`);
    allUsers = await res.json();
    populateUserDropdown();
  } catch (err) {
    console.error("Failed to fetch users:", err);
  }
}

function populateUserDropdown() {
  const select = document.getElementById("user-select");
  select.innerHTML = "";

  const filtered = allUsers.filter(u => u.role === currentRole);
  filtered.forEach(u => {
    const opt = document.createElement("option");
    opt.value = u.user_id;
    opt.textContent = `${u.name} (${u.city})`;
    select.appendChild(opt);
  });

  if (filtered.length > 0) {
    currentUser = filtered[0];
    select.value = currentUser.user_id;
  }
  refreshViewData();
}

function setRole(role) {
  currentRole = role;

  // Toggle active button
  document.querySelectorAll(".role-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(`btn-role-${role}`).classList.add("active");

  // Toggle visible view
  document.getElementById("view-customer").style.display = role === "customer" ? "block" : "none";
  document.getElementById("view-driver").style.display = role === "driver" ? "block" : "none";
  document.getElementById("view-admin").style.display = role === "admin" ? "block" : "none";

  populateUserDropdown();
}

function changeUser() {
  const select = document.getElementById("user-select");
  const uid = parseInt(select.value);
  currentUser = allUsers.find(u => u.user_id === uid);
  refreshViewData();
}

function refreshViewData() {
  if (currentRole === "customer") {
    loadAvailableTrucks();
    loadBookings();
  } else if (currentRole === "driver") {
    loadDriverTrips();
  } else if (currentRole === "admin") {
    loadAdminAnalytics();
  }
}

// 3. FARE ESTIMATION & TRUCK SELECTION
function calculateFarePreview() {
  const pickup = document.getElementById("pickup-city").value;
  const drop = document.getElementById("drop-city").value;
  const weight = parseFloat(document.getElementById("cargo-weight").value) || 1.0;

  const distance = getLocalDistance(pickup, drop);
  const baseRate = 38.0; // Medium rate estimate
  const surcharge = (distance * baseRate) + (weight * 120);
  const total = 1200 + surcharge;

  document.getElementById("preview-distance").textContent = `${distance} KM`;
  document.getElementById("preview-surcharge").textContent = `₹${surcharge.toLocaleString('en-IN', {maximumFractionDigits: 2})}`;
  document.getElementById("preview-fare").textContent = `₹${total.toLocaleString('en-IN', {maximumFractionDigits: 2})}`;
}

async function loadAvailableTrucks() {
  const weight = document.getElementById("cargo-weight").value;
  const truckSelect = document.getElementById("truck-select");

  try {
    const res = await fetch(`${API_BASE}/trucks?weight=${weight}`);
    const trucks = await res.json();
    truckSelect.innerHTML = "";

    const available = trucks.filter(t => t.status === "available");
    if (available.length === 0) {
      truckSelect.innerHTML = "<option value=''>No available trucks matching weight capacity</option>";
      return;
    }

    available.forEach(t => {
      const opt = document.createElement("option");
      opt.value = t.truck_id;
      opt.textContent = `${t.license_plate} - ${t.truck_type} (${t.capacity_tons}T cap) [Driver: ${t.driver_name || 'Fleet'}] - ${t.current_city}`;
      truckSelect.appendChild(opt);
    });
  } catch (err) {
    console.error("Error loading trucks:", err);
  }
}

// 4. BOOKING SUBMISSION (FSD + DBMS)
async function submitBooking(event) {
  event.preventDefault();

  const pickup = document.getElementById("pickup-city").value;
  const drop = document.getElementById("drop-city").value;
  const weight = parseFloat(document.getElementById("cargo-weight").value);
  const distance = getLocalDistance(pickup, drop);
  const truckId = parseInt(document.getElementById("truck-select").value);
  const cargoType = document.getElementById("cargo-type").value;
  const schedDate = document.getElementById("scheduled-date").value;
  const payMethod = document.getElementById("payment-method").value;

  if (!truckId) {
    alert("Please select an available truck.");
    return;
  }

  const payload = {
    customer_id: currentUser ? currentUser.user_id : 2,
    truck_id: truckId,
    pickup_city: pickup,
    drop_city: drop,
    distance_km: distance,
    cargo_type: cargoType,
    cargo_weight_tons: weight,
    scheduled_date: schedDate,
    payment_method: payMethod
  };

  try {
    const res = await fetch(`${API_BASE}/bookings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (res.ok) {
      alert(`Booking Confirmed! Tracking ID: #${result.booking_id}\nFare: ₹${result.fare_amount.toLocaleString('en-IN')}`);
      loadBookings();
      loadAvailableTrucks();
    } else {
      alert("Error: " + (result.error || "Could not complete booking"));
    }
  } catch (err) {
    alert("Server communication error. Ensure backend is running.");
  }
}

// 5. LOAD CUSTOMER BOOKINGS
async function loadBookings() {
  if (!currentUser) return;
  const tbody = document.getElementById("customer-bookings-table");
  tbody.innerHTML = "<tr><td colspan='5' style='text-align:center;'>Loading...</td></tr>";

  try {
    const res = await fetch(`${API_BASE}/bookings?role=customer&user_id=${currentUser.user_id}`);
    const bookings = await res.json();
    tbody.innerHTML = "";

    if (bookings.length === 0) {
      tbody.innerHTML = "<tr><td colspan='5' style='text-align:center;'>No bookings found. Place your first freight order!</td></tr>";
      return;
    }

    bookings.forEach(b => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>#${b.booking_id}</strong></td>
        <td>${b.pickup_city} &rarr; ${b.drop_city}<br><small style="color:var(--text-muted);">${b.distance_km} km</small></td>
        <td>${b.cargo_type}<br><small style="color:var(--text-muted);">${b.cargo_weight_tons} Tons</small></td>
        <td>₹${parseFloat(b.fare_amount).toLocaleString('en-IN')}</td>
        <td><span class="badge badge-${b.status}">${b.status.toUpperCase()}</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = "<tr><td colspan='5' style='text-align:center; color:red;'>Failed to load bookings</td></tr>";
  }
}

// 6. DRIVER VIEW & TRIGGER TESTING
async function loadDriverTrips() {
  if (!currentUser) return;
  document.getElementById("driver-portal-title").textContent = `Driver Console: ${currentUser.name}`;
  const tbody = document.getElementById("driver-trips-table");
  tbody.innerHTML = "<tr><td colspan='7' style='text-align:center;'>Loading assigned trips...</td></tr>";

  try {
    const res = await fetch(`${API_BASE}/bookings?role=driver&user_id=${currentUser.user_id}`);
    const trips = await res.json();
    tbody.innerHTML = "";

    if (trips.length === 0) {
      tbody.innerHTML = "<tr><td colspan='7' style='text-align:center;'>No trips currently assigned to this driver.</td></tr>";
      return;
    }

    // Set truck info banner
    if (trips.length > 0 && trips[0].license_plate) {
      document.getElementById("driver-assigned-truck").textContent = `Assigned Vehicle: ${trips[0].license_plate} (${trips[0].truck_type})`;
    }

    trips.forEach(t => {
      const tr = document.createElement("tr");
      let actionBtn = "";
      if (t.status === "confirmed" || t.status === "pending") {
        actionBtn = `<button class="btn btn-primary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="updateStatus(${t.booking_id}, 'in_transit')">Start Trip</button>`;
      } else if (t.status === "in_transit") {
        actionBtn = `<button class="btn btn-success" style="padding: 4px 10px; font-size: 0.75rem;" onclick="updateStatus(${t.booking_id}, 'delivered')">Mark Delivered</button>`;
      } else {
        actionBtn = `<span style="color: var(--text-muted); font-size: 0.75rem;">Completed</span>`;
      }

      tr.innerHTML = `
        <td><strong>#${t.booking_id}</strong></td>
        <td>${t.customer_name}</td>
        <td>${t.pickup_city} &rarr; ${t.drop_city} (${t.distance_km} KM)</td>
        <td>${t.cargo_type} (${t.cargo_weight_tons}T)</td>
        <td>₹${parseFloat(t.fare_amount).toLocaleString('en-IN')}</td>
        <td><span class="badge badge-${t.status}">${t.status.toUpperCase()}</span></td>
        <td>${actionBtn}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = "<tr><td colspan='7' style='text-align:center; color:red;'>Failed to load driver trips</td></tr>";
  }
}

async function updateStatus(bookingId, status) {
  try {
    const res = await fetch(`${API_BASE}/bookings/${bookingId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });
    const result = await res.json();
    alert(`Status updated to: ${status.toUpperCase()}!\nDBMS Triggers have synchronized truck availability.`);
    loadDriverTrips();
  } catch (err) {
    alert("Error updating status: " + err);
  }
}

// 7. ADMIN & EDADV ANALYTICS
async function loadAdminAnalytics() {
  try {
    const res = await fetch(`${API_BASE}/analytics/summary`);
    const data = await res.json();

    // KPIs
    document.getElementById("kpi-total-bookings").textContent = data.kpis.total_bookings || 0;
    document.getElementById("kpi-total-revenue").textContent = `₹${(data.kpis.total_revenue / 10000000).toFixed(2)} Cr`;
    document.getElementById("kpi-delivered").textContent = data.kpis.delivered_count || 0;
    document.getElementById("kpi-in-transit").textContent = data.kpis.in_transit_count || 0;

    // Render Pure Canvas Charts
    renderFleetCanvasChart(data.fleet_status);
    renderRoutesCanvasChart(data.top_routes);

    // Populate Driver Performance Table
    const dTable = document.getElementById("driver-performance-table");
    dTable.innerHTML = "";
    data.top_drivers.forEach(d => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${d.driver_name}</strong></td>
        <td>${d.driver_phone}</td>
        <td>${d.license_plate} (${d.truck_type})</td>
        <td>${d.total_trips}</td>
        <td><span class="badge badge-delivered">${d.completed_trips}</span></td>
        <td>₹${parseFloat(d.total_earnings).toLocaleString('en-IN')}</td>
        <td><strong>★ ${d.avg_rating} / 5</strong></td>
      `;
      dTable.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to load admin analytics:", err);
  }
}

// Pure HTML5 Canvas Rendering (No External Chart Library Needed)
function renderFleetCanvasChart(fleetData) {
  const canvas = document.getElementById("canvas-fleet-chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!fleetData || fleetData.length === 0) return;

  const barWidth = 70;
  const spacing = 45;
  const startX = 60;
  const baseY = 200;
  const maxVal = Math.max(...fleetData.map(d => d.total_trucks), 10);

  // Draw Axes
  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(40, 20);
  ctx.lineTo(40, baseY);
  ctx.lineTo(canvas.width - 20, baseY);
  ctx.stroke();

  fleetData.forEach((item, i) => {
    const x = startX + i * (barWidth + spacing);
    const barHeight = (item.total_trucks / maxVal) * 160;
    const y = baseY - barHeight;

    // Bar fill
    ctx.fillStyle = "#3b82f6";
    ctx.fillRect(x, y, barWidth, barHeight);

    // Value label
    ctx.fillStyle = "#0f172a";
    ctx.font = "bold 12px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${item.total_trucks} Trucks`, x + barWidth / 2, y - 6);

    // X Axis Label
    ctx.fillStyle = "#64748b";
    ctx.font = "10px sans-serif";
    const label = item.truck_type.split("(")[0].trim();
    ctx.fillText(label, x + barWidth / 2, baseY + 18);
  });
}

function renderRoutesCanvasChart(routeData) {
  const canvas = document.getElementById("canvas-routes-chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!routeData || routeData.length === 0) return;

  const top5 = routeData.slice(0, 5);
  const startY = 35;
  const barHeight = 24;
  const spacing = 16;
  const maxRev = Math.max(...top5.map(r => r.total_revenue), 100000);

  top5.forEach((r, i) => {
    const y = startY + i * (barHeight + spacing);
    const barWidth = (r.total_revenue / maxRev) * 320;

    // Route Name
    ctx.fillStyle = "#0f172a";
    ctx.font = "bold 11px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(r.route_name, 10, y + 16);

    // Bar
    ctx.fillStyle = "#10b981";
    ctx.fillRect(160, y, barWidth, barHeight);

    // Revenue text
    ctx.fillStyle = "#065f46";
    ctx.font = "bold 10px sans-serif";
    ctx.fillText(`₹${(r.total_revenue / 1000).toFixed(0)}k`, 170 + barWidth, y + 16);
  });
}

function triggerPythonEDA() {
  alert("To re-run the Python statistical analysis offline, open your terminal and run:\npython edadv_analytics/eda_analysis.py");
}
