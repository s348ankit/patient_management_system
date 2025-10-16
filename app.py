from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for
import pandas as pd
import sqlite3
import os
from datetime import datetime
import uuid
import hashlib

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure key in production
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY, name TEXT, mobile_number TEXT UNIQUE, age INTEGER, address TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id TEXT PRIMARY KEY, patient_id TEXT, reason TEXT, booking_date TEXT, appointment_date TEXT, 
        booking_type TEXT, confirmed INTEGER, checkin_status TEXT, checkin_time TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS diagnoses (
        appointment_id TEXT PRIMARY KEY, chief_complaints TEXT, symptoms TEXT, mind TEXT, psychology TEXT, 
        diagnosis TEXT, medicines TEXT, tests TEXT, next_visit TEXT, diagnosis_saved INTEGER, 
        medicines_prescribed INTEGER,
        FOREIGN KEY (appointment_id) REFERENCES appointments (id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS billing (
        appointment_id TEXT PRIMARY KEY, consultation_charge REAL, medicine_charge REAL, courier_charge REAL, 
        delivery_type TEXT, delivered_to TEXT, courier_channel TEXT, courier_tracking TEXT, 
        amount_paid REAL, payment_date TEXT, payment_id TEXT, discount REAL, 
        medicines_prepared INTEGER, medicines_handed_over INTEGER, couriered INTEGER, checkout_done INTEGER,
        FOREIGN KEY (appointment_id) REFERENCES appointments (id)
    )''')
    conn.commit()
    conn.close()

    # Initialize users.csv for login credentials
    users = [
        {'username': 'receptionist', 'password': hashlib.sha256('rec123'.encode()).hexdigest(), 'role': 'receptionist'},
        {'username': 'doctor', 'password': hashlib.sha256('doc123'.encode()).hexdigest(), 'role': 'doctor'},
        {'username': 'pharmacist', 'password': hashlib.sha256('pharm123'.encode()).hexdigest(), 'role': 'pharmacist'}
    ]
    pd.DataFrame(users).to_csv(f'{UPLOAD_FOLDER}/users.csv', index=False)

init_db()

# Helper functions
def save_to_csv(table_name, data):
    df = pd.DataFrame(data)
    df.to_csv(f'{UPLOAD_FOLDER}/{table_name}.csv', index=False)

def send_whatsapp_message(mobile, message):
    print(f"Sending WhatsApp to {mobile}: {message}")

# Routes
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for(f"{session['role']}_dashboard"))
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        users = pd.read_csv(f'{UPLOAD_FOLDER}/users.csv')
        user = users[(users['username'] == username) & (users['password'] == password)]
        if not user.empty:
            session['username'] = username
            session['role'] = user.iloc[0]['role']
            return redirect(url_for(f"{session['role']}_dashboard"))
        error = "Invalid credentials"
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clinic Management - Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-r from-blue-500 to-purple-600 min-h-screen flex items-center justify-center">
    <div class="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h1 class="text-3xl font-bold text-center text-gray-800 mb-6">Clinic Management System</h1>
        {% if error %}
        <p class="text-red-500 text-center">{{ error }}</p>
        {% endif %}
        <form method="post" class="space-y-4">
            <input type="text" name="username" placeholder="Username" class="w-full p-2 border rounded">
            <input type="password" name="password" placeholder="Password" class="w-full p-2 border rounded">
            <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">Login</button>
        </form>
    </div>
</body>
</html>
    """, error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/receptionist_dashboard', methods=['GET', 'POST'])
def receptionist_dashboard():
    if 'role' not in session or session['role'] != 'receptionist':
        return redirect(url_for('login'))
    if request.method == 'POST' and 'booking' in request.form:
        data = {
            'name': request.form['patient_name'],
            'mobile_number': request.form['mobile_number'],
            'age': request.form['age'],
            'address': request.form['address'],
            'reason': request.form['reason'],
            'appointment_date': request.form['appointment_date'],
            'booking_type': request.form['booking_type']
        }
        conn = sqlite3.connect('clinic.db')
        c = conn.cursor()
        # Check for existing patient by mobile number
        c.execute('SELECT patient_id FROM patients WHERE mobile_number = ?', (data['mobile_number'],))
        patient = c.fetchone()
        if patient:
            patient_id = patient[0]
            c.execute('UPDATE patients SET name = ?, age = ?, address = ? WHERE patient_id = ?',
                      (data['name'], data['age'], data['address'], patient_id))
        else:
            patient_id = str(uuid.uuid4())
            c.execute('INSERT INTO patients (patient_id, name, mobile_number, age, address) VALUES (?, ?, ?, ?, ?)',
                      (patient_id, data['name'], data['mobile_number'], data['age'], data['address']))
        # Book appointment
        appointment_id = str(uuid.uuid4())
        booking_date = datetime.now().strftime('%Y-%m-%d')
        today = datetime.now().date()
        appt_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d').date()
        if appt_date == today and data['booking_type'] == 'Online Direct':
            conn.close()
            return render_template_string("""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Receptionist Dashboard</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-gray-100 font-sans">
                <div class="min-h-screen bg-gradient-to-r from-green-400 to-blue-500 p-4">
                    <div class="container mx-auto bg-white rounded-lg shadow-lg p-6">
                        <p class="text-red-500 text-center">Same-day online bookings not allowed</p>
                        <a href="/receptionist_dashboard" class="text-blue-600">Back to Dashboard</a>
                    </div>
                </div>
            </body>
            </html>
            """)
        c.execute('''INSERT INTO appointments (id, patient_id, reason, booking_date, appointment_date, booking_type, confirmed, checkin_status, checkin_time)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (appointment_id, patient_id, data['reason'], booking_date, data['appointment_date'], data['booking_type'], 0, '', ''))
        conn.commit()
        conn.close()
        send_whatsapp_message(data['mobile_number'], f"Appointment booked for {data['appointment_date']}")
        if data['booking_type'] != 'Manual In-Clinic':
            send_whatsapp_message(data['mobile_number'], "Appointment confirmation pending from clinic")
        save_to_csv('patients', pd.read_sql_query("SELECT * FROM patients", sqlite3.connect('clinic.db')).to_dict('records'))
        save_to_csv('appointments', pd.read_sql_query("SELECT * FROM appointments", sqlite3.connect('clinic.db')).to_dict('records'))
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('''SELECT a.*, p.name, p.mobile_number, p.age, p.address, d.chief_complaints, d.symptoms, d.mind, d.psychology, 
                 d.diagnosis, d.medicines, d.tests, d.next_visit, d.diagnosis_saved, d.medicines_prescribed, 
                 b.consultation_charge, b.medicine_charge, b.courier_charge, b.delivery_type, b.delivered_to, 
                 b.courier_channel, b.courier_tracking, b.amount_paid, b.payment_date, b.payment_id, b.discount, 
                 b.medicines_prepared, b.medicines_handed_over, b.couriered, b.checkout_done
                 FROM appointments a
                 JOIN patients p ON a.patient_id = p.patient_id
                 LEFT JOIN diagnoses d ON a.id = d.appointment_id
                 LEFT JOIN billing b ON a.id = b.appointment_id''')
    appointments = c.fetchall()
    conn.close()
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Receptionist Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans">
    <div class="min-h-screen bg-gradient-to-r from-green-400 to-blue-500 p-4">
        <div class="container mx-auto bg-white rounded-lg shadow-lg p-6">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-3xl font-bold text-gray-800">Receptionist Dashboard</h1>
                <a href="/logout" class="bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700">Logout</a>
            </div>
            <!-- Search Bar -->
            <div class="mb-6">
                <input type="text" id="searchInput" placeholder="Search by Patient Name, Mobile, or Date" class="w-full p-2 border rounded" onkeyup="searchAppointments()">
            </div>
            <!-- Appointment Booking -->
            <div class="mb-8">
                <h2 class="text-2xl font-semibold text-gray-700 mb-4">Book Appointment</h2>
                <form method="post" class="space-y-4">
                    <input type="hidden" name="booking" value="1">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <input type="text" name="patient_name" placeholder="Patient Name" class="p-2 border rounded">
                        <input type="text" name="mobile_number" placeholder="Mobile Number" class="p-2 border rounded">
                        <input type="number" name="age" placeholder="Age" class="p-2 border rounded">
                        <input type="text" name="address" placeholder="Address" class="p-2 border rounded">
                        <select name="reason" class="p-2 border rounded">
                            <option value="Consultation">Consultation</option>
                            <option value="Collecting Medicine">Collecting Medicine</option>
                            <option value="Other">Other</option>
                        </select>
                        <input type="date" name="appointment_date" class="p-2 border rounded">
                        <select name="booking_type" class="p-2 border rounded">
                            <option value="Online Direct">Online Direct</option>
                            <option value="Online Manual">Online Manual</option>
                            <option value="Manual In-Clinic">Manual In-Clinic</option>
                        </select>
                    </div>
                    <button type="submit" class="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700">Book Appointment</button>
                </form>
            </div>
            <!-- Appointment List -->
            <div class="mb-8">
                <h2 class="text-2xl font-semibold text-gray-700 mb-4">Appointments</h2>
                <div id="appointmentList" class="overflow-x-auto">
                    <table class="table-auto w-full border-collapse border border-gray-300">
                        <thead>
                            <tr>
                                <th class="border p-2">Patient</th>
                                <th class="border p-2">Mobile</th>
                                <th class="border p-2">Date</th>
                                <th class="border p-2">Reason</th>
                                <th class="border p-2">Diagnosis</th>
                                <th class="border p-2">Medicines</th>
                                <th class="border p-2">Billing</th>
                                <th class="border p-2">Status</th>
                                <th class="border p-2">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="appointmentTableBody">
                            {% for appt in appointments %}
                            <tr>
                                <td class="border p-2">{{ appt[9] }}</td>
                                <td class="border p-2">{{ appt[10] }}</td>
                                <td class="border p-2">{{ appt[4] }}</td>
                                <td class="border p-2">{{ appt[2] }}</td>
                                <td class="border p-2">
                                    {% if appt[14] %}
                                    Complaints: {{ appt[14] }}<br>
                                    Symptoms: {{ appt[15] }}<br>
                                    Mind: {{ appt[16] }}<br>
                                    Psychology: {{ appt[17] }}<br>
                                    Diagnosis: {{ appt[18] }}<br>
                                    Tests: {{ appt[20] }}<br>
                                    Next Visit: {{ appt[21] }}
                                    {% else %}
                                    Not Diagnosed
                                    {% endif %}
                                </td>
                                <td class="border p-2">{{ appt[19] if appt[19] else 'None' }}</td>
                                <td class="border p-2">
                                    {% if appt[23] is not none %}
                                    Consultation: ${{ appt[23]|default(0, true) }}<br>
                                    Medicine: ${{ appt[24]|default(0, true) }}<br>
                                    Courier: ${{ appt[25]|default(0, true) }}<br>
                                    Delivery: {{ appt[26]|default('In-Person', true) }}<br>
                                    Delivered To: {{ appt[27]|default('N/A', true) }}<br>
                                    Courier Channel: {{ appt[28]|default('N/A', true) }}<br>
                                    Tracking: {{ appt[29]|default('N/A', true) }}<br>
                                    Paid: ${{ appt[30]|default(0, true) }}<br>
                                    Discount: ${{ appt[31]|default(0, true) }}
                                    {% else %}
                                    Not Billed
                                    {% endif %}
                                </td>
                                <td class="border p-2">
                                    {% if appt[7] %}✅ Check-In: {{ appt[7] }} @ {{ appt[8] }}{% endif %}
                                    {% if appt[22] %}📝 Diagnosis Saved{% endif %}
                                    {% if appt[23] %}💊 Medicines Prescribed{% endif %}
                                    {% if appt[32] %}📦 Medicines Prepared{% endif %}
                                    {% if appt[33] %}🚚 Handed Over{% endif %}
                                    {% if appt[34] %}📬 Couriered{% endif %}
                                    {% if appt[35] %}✔️ Checked Out{% endif %}
                                </td>
                                <td class="border p-2">
                                    {% if not appt[7] %}
                                    <button onclick="checkIn('{{ appt[0] }}', 'Scheduled')" class="bg-blue-500 text-white px-2 py-1 rounded">Check-In</button>
                                    {% endif %}
                                    <button onclick="showBillingForm('{{ appt[0] }}')" class="bg-purple-500 text-white px-2 py-1 rounded">Billing</button>
                                    {% if appt[32] and not appt[33] %}
                                    <button onclick="handOverMedicine('{{ appt[0] }}')" class="bg-green-500 text-white px-2 py-1 rounded">Hand Over Medicine</button>
                                    {% endif %}
                                    {% if appt[32] and not appt[34] and appt[26] == 'Courier' %}
                                    <button onclick="courierDone('{{ appt[0] }}')" class="bg-purple-600 text-white px-2 py-1 rounded">Courier Done</button>
                                    {% endif %}
                                    {% if appt[33] or appt[34] %}
                                    <button onclick="completeCheckout('{{ appt[0] }}')" class="bg-red-600 text-white px-2 py-1 rounded">Complete Checkout</button>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            <!-- Billing Form -->
            <div class="mb-8">
                <h2 class="text-2xl font-semibold text-gray-700 mb-4">Billing & Handover</h2>
                <div id="billingForm" class="space-y-4 hidden">
                    <input type="hidden" id="billingAppointmentId">
                    <input type="number" id="consultationCharge" placeholder="Consultation Charge" class="p-2 border rounded">
                    <input type="number" id="medicineCharge" placeholder="Medicine Charge" class="p-2 border rounded">
                    <input type="number" id="courierCharge" placeholder="Courier Charge" class="p-2 border rounded">
                    <select id="deliveryType" class="p-2 border rounded">
                        <option value="In-Person">In-Person</option>
                        <option value="Courier">Courier</option>
                    </select>
                    <input type="text" id="deliveredTo" placeholder="Delivered To (for In-Person)" class="p-2 border rounded">
                    <select id="courierChannel" class="p-2 border rounded">
                        <option value="Rapido">Rapido</option>
                        <option value="Porter">Porter</option>
                        <option value="India Post">India Post</option>
                        <option value="DTDC">DTDC</option>
                        <option value="BlueDart">BlueDart</option>
                        <option value="Others">Others</option>
                    </select>
                    <input type="text" id="courierTracking" placeholder="Courier Tracking ID" class="p-2 border rounded">
                    <input type="number" id="amountPaid" placeholder="Amount Paid" class="p-2 border rounded">
                    <input type="date" id="paymentDate" placeholder="Payment Date" class="p-2 border rounded">
                    <input type="text" id="paymentId" placeholder="Payment ID" class="p-2 border rounded">
                    <input type="number" id="discount" placeholder="Discount (if any)" class="p-2 border rounded">
                    <button onclick="saveBilling()" class="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700">Save Billing</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        async function checkIn(id, status) {
            await fetch(`/check_in/${id}/${status}`, { method: 'POST' });
            alert(`Checked in as ${status}`);
            location.reload();
        }
        async function showBillingForm(id) {
            const response = await fetch(`/billing/${id}`);
            const data = await response.json();
            document.getElementById('billingAppointmentId').value = id;
            document.getElementById('consultationCharge').value = data.consultation_charge || 0;
            document.getElementById('medicineCharge').value = data.medicine_charge || 0;
            document.getElementById('courierCharge').value = data.courier_charge || 0;
            document.getElementById('deliveryType').value = data.delivery_type || 'In-Person';
            document.getElementById('deliveredTo').value = data.delivered_to || '';
            document.getElementById('courierChannel').value = data.courier_channel || 'Rapido';
            document.getElementById('courierTracking').value = data.courier_tracking || '';
            document.getElementById('amountPaid').value = data.amount_paid || 0;
            document.getElementById('paymentDate').value = data.payment_date || '';
            document.getElementById('paymentId').value = data.payment_id || '';
            document.getElementById('discount').value = data.discount || 0;
            document.getElementById('billingForm').classList.remove('hidden');
        }
        async function saveBilling() {
            const id = document.getElementById('billingAppointmentId').value;
            const data = {
                consultation_charge: parseFloat(document.getElementById('consultationCharge').value) || 0,
                medicine_charge: parseFloat(document.getElementById('medicineCharge').value) || 0,
                courier_charge: parseFloat(document.getElementById('courierCharge').value) || 0,
                delivery_type: document.getElementById('deliveryType').value,
                delivered_to: document.getElementById('deliveredTo').value,
                courier_channel: document.getElementById('courierChannel').value,
                courier_tracking: document.getElementById('courierTracking').value,
                amount_paid: parseFloat(document.getElementById('amountPaid').value) || 0,
                payment_date: document.getElementById('paymentDate').value,
                payment_id: document.getElementById('paymentId').value,
                discount: parseFloat(document.getElementById('discount').value) || 0
            };
            await fetch(`/billing_prepare/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            alert('Billing saved');
            location.reload();
        }
        async function handOverMedicine(id) {
            await fetch(`/hand_over_medicine/${id}`, { method: 'POST' });
            alert('Medicine handed over');
            location.reload();
        }
        async function courierDone(id) {
            await fetch(`/courier_done/${id}`, { method: 'POST' });
            alert('Courier done');
            location.reload();
        }
        async function completeCheckout(id) {
            await fetch(`/complete_checkout/${id}`, { method: 'POST' });
            alert('Checkout completed');
            location.reload();
        }
        function searchAppointments() {
            const input = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.getElementById('appointmentTableBody').getElementsByTagName('tr');
            for (let row of rows) {
                const patient = row.cells[0].textContent.toLowerCase();
                const mobile = row.cells[1].textContent.toLowerCase();
                const date = row.cells[2].textContent.toLowerCase();
                row.style.display = (patient.includes(input) || mobile.includes(input) || date.includes(input)) ? '' : 'none';
            }
        }
    </script>
</body>
</html>
    """, appointments=appointments)

@app.route('/doctor_dashboard', methods=['GET'])
def doctor_dashboard():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('''SELECT a.*, p.name, p.mobile_number, p.age, p.address, d.chief_complaints, d.symptoms, d.mind, d.psychology, 
                 d.diagnosis, d.medicines, d.tests, d.next_visit, d.diagnosis_saved, d.medicines_prescribed, 
                 b.consultation_charge, b.medicine_charge, b.courier_charge, b.delivery_type, b.delivered_to, 
                 b.courier_channel, b.courier_tracking, b.amount_paid, b.payment_date, b.payment_id, b.discount, 
                 b.medicines_prepared, b.medicines_handed_over, b.couriered, b.checkout_done
                 FROM appointments a
                 JOIN patients p ON a.patient_id = p.patient_id
                 LEFT JOIN diagnoses d ON a.id = d.appointment_id
                 LEFT JOIN billing b ON a.id = b.appointment_id''')
    appointments = c.fetchall()
    conn.close()
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Doctor Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans">
    <div class="min-h-screen bg-gradient-to-r from-purple-400 to-pink-500 p-4">
        <div class="container mx-auto bg-white rounded-lg shadow-lg p-6">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-3xl font-bold text-gray-800">Doctor Dashboard</h1>
                <a href="/logout" class="bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700">Logout</a>
            </div>
            <!-- Search Bar -->
            <div class="mb-6">
                <input type="text" id="searchInput" placeholder="Search by Patient Name, Mobile, or Date" class="w-full p-2 border rounded" onkeyup="searchAppointments()">
            </div>
            <!-- Appointment List -->
            <div class="mb-8">
                <h2 class="text-2xl font-semibold text-gray-700 mb-4">Appointments</h2>
                <div id="appointmentList" class="overflow-x-auto">
                    <table class="table-auto w-full border-collapse border border-gray-300">
                        <thead>
                            <tr>
                                <th class="border p-2">Patient</th>
                                <th class="border p-2">Mobile</th>
                                <th class="border p-2">Date</th>
                                <th class="border p-2">Reason</th>
                                <th class="border p-2">Diagnosis</th>
                                <th class="border p-2">Medicines</th>
                                <th class="border p-2">Billing</th>
                                <th class="border p-2">Status</th>
                                <th class="border p-2">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="appointmentTableBody">
                            {% for appt in appointments %}
                            <tr>
                                <td class="border p-2">{{ appt[9] }}</td>
                                <td class="border p-2">{{ appt[10] }}</td>
                                <td class="border p-2">{{ appt[4] }}</td>
                                <td class="border p-2">{{ appt[2] }}</td>
                                <td class="border p-2">
                                    {% if appt[14] %}
                                    Complaints: {{ appt[14] }}<br>
                                    Symptoms: {{ appt[15] }}<br>
                                    Mind: {{ appt[16] }}<br>
                                    Psychology: {{ appt[17] }}<br>
                                    Diagnosis: {{ appt[18] }}<br>
                                    Tests: {{ appt[20] }}<br>
                                    Next Visit: {{ appt[21] }}
                                    {% else %}
                                    Not Diagnosed
                                    {% endif %}
                                </td>
                                <td class="border p-2">{{ appt[19] if appt[19] else 'None' }}</td>
                                <td class="border p-2">
                                    {% if appt[23] is not none %}
                                    Consultation: ${{ appt[23]|default(0, true) }}<br>
                                    Medicine: ${{ appt[24]|default(0, true) }}<br>
                                    Courier: ${{ appt[25]|default(0, true) }}<br>
                                    Delivery: {{ appt[26]|default('In-Person', true) }}<br>
                                    Delivered To: {{ appt[27]|default('N/A', true) }}<br>
                                    Courier Channel: {{ appt[28]|default('N/A', true) }}<br>
                                    Tracking: {{ appt[29]|default('N/A', true) }}<br>
                                    Paid: ${{ appt[30]|default(0, true) }}<br>
                                    Discount: ${{ appt[31]|default(0, true) }}
                                    {% else %}
                                    Not Billed
                                    {% endif %}
                                </td>
                                <td class="border p-2">
                                    {% if appt[7] %}✅ Check-In: {{ appt[7] }} @ {{ appt[8] }}{% endif %}
                                    {% if appt[22] %}📝 Diagnosis Saved{% endif %}
                                    {% if appt[23] %}💊 Medicines Prescribed{% endif %}
                                    {% if appt[32] %}📦 Medicines Prepared{% endif %}
                                    {% if appt[33] %}🚚 Handed Over{% endif %}
                                    {% if appt[34] %}📬 Couriered{% endif %}
                                    {% if appt[35] %}✔️ Checked Out{% endif %}
                                </td>
                                <td class="border p-2">
                                    <button onclick="showDoctorForm('{{ appt[0] }}')" class="bg-green-500 text-white px-2 py-1 rounded">View/Edit Diagnosis</button>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            <!-- Doctor Form -->
            <div class="mb-8">
                <h2 class="text-2xl font-semibold text-gray-700 mb-4">Diagnosis & Prescription</h2>
                <div id="doctorForm" class="space-y-4 hidden">
                    <input type="hidden" id="appointmentId">
                    <textarea id="chiefComplaints" placeholder="Chief Complaints" class="p-2 border rounded w-full h-24"></textarea>
                    <textarea id="symptoms" placeholder="Symptoms Observed" class="p-2 border rounded w-full h-24"></textarea>
                    <textarea id="mind" placeholder="Mind" class="p-2 border rounded w-full h-24"></textarea>
                    <textarea id="psychology" placeholder="Psychology" class="p-2 border rounded w-full h-24"></textarea>
                    <textarea id="diagnosis" placeholder="Diagnosis" class="p-2 border rounded w-full h-24"></textarea>
                    <textarea id="medicines" placeholder="Medicines Prescribed" class="p-2 border rounded w-full h-24"></textarea>
                    <textarea id="tests" placeholder="Tests Prescribed" class="p-2 border rounded w-full h-24"></textarea>
                    <input type="date" id="nextVisit" placeholder="Next Visit" class="p-2 border rounded">
                    <button onclick="saveDiagnosis()" class="bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700">Save</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        async function showDoctorForm(id) {
            const response = await fetch(`/diagnosis/${id}`);
            const data = await response.json();
            document.getElementById('appointmentId').value = id;
            document.getElementById('chiefComplaints').value = data.chief_complaints || '';
            document.getElementById('symptoms').value = data.symptoms || '';
            document.getElementById('mind').value = data.mind || '';
            document.getElementById('psychology').value = data.psychology || '';
            document.getElementById('diagnosis').value = data.diagnosis || '';
            document.getElementById('medicines').value = data.medicines || '';
            document.getElementById('tests').value = data.tests || '';
            document.getElementById('nextVisit').value = data.next_visit || '';
            document.getElementById('doctorForm').classList.remove('hidden');
        }
        async function saveDiagnosis() {
            const id = document.getElementById('appointmentId').value;
            const data = {
                chief_complaints: document.getElementById('chiefComplaints').value,
                symptoms: document.getElementById('symptoms').value,
                mind: document.getElementById('mind').value,
                psychology: document.getElementById('psychology').value,
                diagnosis: document.getElementById('diagnosis').value,
                medicines: document.getElementById('medicines').value,
                tests: document.getElementById('tests').value,
                next_visit: document.getElementById('nextVisit').value
            };
            await fetch(`/save_diagnosis/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            alert('Diagnosis and prescription saved');
            location.reload();
        }
        function searchAppointments() {
            const input = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.getElementById('appointmentTableBody').getElementsByTagName('tr');
            for (let row of rows) {
                const patient = row.cells[0].textContent.toLowerCase();
                const mobile = row.cells[1].textContent.toLowerCase();
                const date = row.cells[2].textContent.toLowerCase();
                row.style.display = (patient.includes(input) || mobile.includes(input) || date.includes(input)) ? '' : 'none';
            }
        }
    </script>
</body>
</html>
    """, appointments=appointments)

@app.route('/pharmacist_dashboard', methods=['GET'])
def pharmacist_dashboard():
    if 'role' not in session or session['role'] != 'pharmacist':
        return redirect(url_for('login'))
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('''SELECT a.*, p.name, p.mobile_number, p.age, p.address, d.chief_complaints, d.symptoms, d.mind, d.psychology, 
                 d.diagnosis, d.medicines, d.tests, d.next_visit, d.diagnosis_saved, d.medicines_prescribed, 
                 b.consultation_charge, b.medicine_charge, b.courier_charge, b.delivery_type, b.delivered_to, 
                 b.courier_channel, b.courier_tracking, b.amount_paid, b.payment_date, b.payment_id, b.discount, 
                 b.medicines_prepared, b.medicines_handed_over, b.couriered, b.checkout_done
                 FROM appointments a
                 JOIN patients p ON a.patient_id = p.patient_id
                 LEFT JOIN diagnoses d ON a.id = d.appointment_id
                 LEFT JOIN billing b ON a.id = b.appointment_id
                 WHERE d.medicines_prescribed = 1''')
    appointments = c.fetchall()
    conn.close()
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pharmacist Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans">
    <div class="min-h-screen bg-gradient-to-r from-teal-400 to-blue-500 p-4">
        <div class="container mx-auto bg-white rounded-lg shadow-lg p-6">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-3xl font-bold text-gray-800">Pharmacist Dashboard</h1>
                <a href="/logout" class="bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700">Logout</a>
            </div>
            <!-- Search Bar -->
            <div class="mb-6">
                <input type="text" id="searchInput" placeholder="Search by Patient Name or Mobile" class="w-full p-2 border rounded" onkeyup="searchAppointments()">
            </div>
            <!-- Medicine Preparation -->
            <div class="mb-8">
                <h2 class="text-2xl font-semibold text-gray-700 mb-4">Medicine Preparation</h2>
                <div class="overflow-x-auto">
                    <table class="table-auto w-full border-collapse border border-gray-300">
                        <thead>
                            <tr>
                                <th class="border p-2">Patient</th>
                                <th class="border p-2">Mobile</th>
                                <th class="border p-2">Date</th>
                                <th class="border p-2">Medicines</th>
                                <th class="border p-2">Diagnosis</th>
                                <th class="border p-2">Billing</th>
                                <th class="border p-2">Status</th>
                                <th class="border p-2">Action</th>
                            </tr>
                        </thead>
                        <tbody id="appointmentTableBody">
                            {% for appt in appointments %}
                            <tr>
                                <td class="border p-2">{{ appt[9] }}</td>
                                <td class="border p-2">{{ appt[10] }}</td>
                                <td class="border p-2">{{ appt[4] }}</td>
                                <td class="border p-2">{{ appt[19] if appt[19] else 'None' }}</td>
                                <td class="border p-2">
                                    {% if appt[14] %}
                                    Complaints: {{ appt[14] }}<br>
                                    Symptoms: {{ appt[15] }}<br>
                                    Mind: {{ appt[16] }}<br>
                                    Psychology: {{ appt[17] }}<br>
                                    Diagnosis: {{ appt[18] }}<br>
                                    Tests: {{ appt[20] }}<br>
                                    Next Visit: {{ appt[21] }}
                                    {% else %}
                                    Not Diagnosed
                                    {% endif %}
                                </td>
                                <td class="border p-2">
                                    {% if appt[23] is not none %}
                                    Consultation: ${{ appt[23]|default(0, true) }}<br>
                                    Medicine: ${{ appt[24]|default(0, true) }}<br>
                                    Courier: ${{ appt[25]|default(0, true) }}<br>
                                    Delivery: {{ appt[26]|default('In-Person', true) }}<br>
                                    Delivered To: {{ appt[27]|default('N/A', true) }}<br>
                                    Courier Channel: {{ appt[28]|default('N/A', true) }}<br>
                                    Tracking: {{ appt[29]|default('N/A', true) }}<br>
                                    Paid: ${{ appt[30]|default(0, true) }}<br>
                                    Discount: ${{ appt[31]|default(0, true) }}
                                    {% else %}
                                    Not Billed
                                    {% endif %}
                                </td>
                                <td class="border p-2">
                                    {% if appt[7] %}✅ Check-In: {{ appt[7] }} @ {{ appt[8] }}{% endif %}
                                    {% if appt[22] %}📝 Diagnosis Saved{% endif %}
                                    {% if appt[23] %}💊 Medicines Prescribed{% endif %}
                                    {% if appt[32] %}📦 Medicines Prepared{% endif %}
                                    {% if appt[33] %}🚚 Handed Over{% endif %}
                                    {% if appt[34] %}📬 Couriered{% endif %}
                                    {% if appt[35] %}✔️ Checked Out{% endif %}
                                </td>
                                <td class="border p-2">
                                    {% if not appt[32] %}
                                    <button onclick="prepareMedicine('{{ appt[0] }}')" class="bg-blue-500 text-white px-2 py-1 rounded">Prepare Medicine</button>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <script>
        async function prepareMedicine(id) {
            await fetch(`/prepare_medicine/${id}`, { method: 'POST' });
            alert('Medicines prepared');
            location.reload();
        }
        function searchAppointments() {
            const input = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.getElementById('appointmentTableBody').getElementsByTagName('tr');
            for (let row of rows) {
                const patient = row.cells[0].textContent.toLowerCase();
                const mobile = row.cells[1].textContent.toLowerCase();
                row.style.display = (patient.includes(input) || mobile.includes(input)) ? '' : 'none';
            }
        }
    </script>
</body>
</html>
    """, appointments=appointments)

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    if 'role' not in session or session['role'] != 'receptionist':
        return jsonify({'message': 'Unauthorized'}), 403
    data = request.json
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    # Check for existing patient
    c.execute('SELECT patient_id FROM patients WHERE mobile_number = ?', (data['mobile_number'],))
    patient = c.fetchone()
    if patient:
        patient_id = patient[0]
        c.execute('UPDATE patients SET name = ?, age = ?, address = ? WHERE patient_id = ?',
                  (data['name'], data['age'], data['address'], patient_id))
    else:
        patient_id = str(uuid.uuid4())
        c.execute('INSERT INTO patients (patient_id, name, mobile_number, age, address) VALUES (?, ?, ?, ?, ?)',
                  (patient_id, data['name'], data['mobile_number'], data['age'], data['address']))
    # Book appointment
    appointment_id = str(uuid.uuid4())
    booking_date = datetime.now().strftime('%Y-%m-%d')
    today = datetime.now().date()
    appt_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d').date()
    if appt_date == today and data['booking_type'] == 'Online Direct':
        conn.close()
        return jsonify({'message': 'Same-day online bookings not allowed'}), 400
    c.execute('''INSERT INTO appointments (id, patient_id, reason, booking_date, appointment_date, booking_type, confirmed, checkin_status, checkin_time)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (appointment_id, patient_id, data['reason'], booking_date, data['appointment_date'], data['booking_type'], 0, '', ''))
    c.execute('INSERT OR IGNORE INTO billing (appointment_id, consultation_charge, medicine_charge, courier_charge, delivery_type, medicines_prepared) VALUES (?, 0, 0, 0, ?, 0)',
              (appointment_id, 'In-Person'))
    conn.commit()
    conn.close()
    send_whatsapp_message(data['mobile_number'], f"Appointment booked for {data['appointment_date']}")
    if data['booking_type'] != 'Manual In-Clinic':
        send_whatsapp_message(data['mobile_number'], "Appointment confirmation pending from clinic")
    save_to_csv('patients', pd.read_sql_query("SELECT * FROM patients", sqlite3.connect('clinic.db')).to_dict('records'))
    save_to_csv('appointments', pd.read_sql_query("SELECT * FROM appointments", sqlite3.connect('clinic.db')).to_dict('records'))
    save_to_csv('billing', pd.read_sql_query("SELECT * FROM billing", sqlite3.connect('clinic.db')).to_dict('records'))
    return jsonify({'message': 'Appointment booked'})

@app.route('/check_in/<id>/<status>', methods=['POST'])
def check_in(id, status):
    if 'role' not in session or session['role'] != 'receptionist':
        return jsonify({'message': 'Unauthorized'}), 403
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    # Only update check-in status and time, no new entries
    c.execute('UPDATE appointments SET checkin_status = ?, checkin_time = ? WHERE id = ?',
              (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), id))
    c.execute('SELECT patient_id FROM appointments WHERE id = ?', (id,))
    patient_id = c.fetchone()
    if not patient_id:
        conn.close()
        return jsonify({'message': 'Appointment not found'}), 404
    conn.commit()
    conn.close()
    save_to_csv('appointments', pd.read_sql_query("SELECT * FROM appointments", sqlite3.connect('clinic.db')).to_dict('records'))
    return jsonify({'message': 'Checked in'})

@app.route('/diagnosis/<id>', methods=['GET'])
def get_diagnosis(id):
    if 'role' not in session or session['role'] != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('SELECT * FROM diagnoses WHERE appointment_id = ?', (id,))
    diagnosis = c.fetchone()
    conn.close()
    return jsonify({
        'chief_complaints': diagnosis[1] if diagnosis else '',
        'symptoms': diagnosis[2] if diagnosis else '',
        'mind': diagnosis[3] if diagnosis else '',
        'psychology': diagnosis[4] if diagnosis else '',
        'diagnosis': diagnosis[5] if diagnosis else '',
        'medicines': diagnosis[6] if diagnosis else '',
        'tests': diagnosis[7] if diagnosis else '',
        'next_visit': diagnosis[8] if diagnosis else '',
        'diagnosis_saved': diagnosis[9] if diagnosis else 0,
        'medicines_prescribed': diagnosis[10] if diagnosis else 0
    })

@app.route('/save_diagnosis/<id>', methods=['POST'])
def save_diagnosis(id):
    if 'role' not in session or session['role'] != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    data = request.json
    medicines_prescribed = 1 if data['medicines'].strip() else 0
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO diagnoses (appointment_id, chief_complaints, symptoms, mind, psychology, diagnosis, medicines, tests, next_visit, diagnosis_saved, medicines_prescribed)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (id, data['chief_complaints'], data['symptoms'], data['mind'], data['psychology'], data['diagnosis'], data['medicines'], data['tests'], data['next_visit'], 1, medicines_prescribed))
    c.execute('INSERT OR IGNORE INTO billing (appointment_id, consultation_charge, medicine_charge, courier_charge, delivery_type, medicines_prepared) VALUES (?, 0, 0, 0, ?, 0)',
              (id, 'In-Person'))
    conn.commit()
    if medicines_prescribed:
        c.execute('SELECT p.mobile_number FROM appointments a JOIN patients p ON a.patient_id = p.patient_id WHERE a.id = ?', (id,))
        mobile = c.fetchone()[0]
        send_whatsapp_message(mobile, "Medicines prescribed")
    conn.close()
    save_to_csv('diagnoses', pd.read_sql_query("SELECT * FROM diagnoses", sqlite3.connect('clinic.db')).to_dict('records'))
    save_to_csv('billing', pd.read_sql_query("SELECT * FROM billing", sqlite3.connect('clinic.db')).to_dict('records'))
    return jsonify({'message': 'Diagnosis and prescription saved'})

@app.route('/prepare_medicine/<id>', methods=['POST'])
def prepare_medicine(id):
    if 'role' not in session or session['role'] != 'pharmacist':
        return jsonify({'message': 'Unauthorized'}), 403
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO billing (appointment_id, consultation_charge, medicine_charge, courier_charge, delivery_type, medicines_prepared) VALUES (?, 0, 0, 0, ?, 0)',
              (id, 'In-Person'))
    c.execute('UPDATE billing SET medicines_prepared = 1 WHERE appointment_id = ?', (id,))
    c.execute('SELECT p.mobile_number FROM appointments a JOIN patients p ON a.patient_id = p.patient_id WHERE a.id = ?', (id,))
    mobile = c.fetchone()[0]
    conn.commit()
    conn.close()
    send_whatsapp_message(mobile, "Medicines prepared")
    save_to_csv('billing', pd.read_sql_query("SELECT * FROM billing", sqlite3.connect('clinic.db')).to_dict('records'))
    return jsonify({'message': 'Medicines prepared'})

@app.route('/billing/<id>', methods=['GET'])
def get_billing(id):
    if 'role' not in session or session['role'] != 'receptionist':
        return jsonify({'message': 'Unauthorized'}), 403
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('SELECT * FROM billing WHERE appointment_id = ?', (id,))
    billing = c.fetchone()
    conn.close()
    return jsonify({
        'consultation_charge': float(billing[1]) if billing and billing[1] is not None else 0.0,
        'medicine_charge': float(billing[2]) if billing and billing[2] is not None else 0.0,
        'courier_charge': float(billing[3]) if billing and billing[3] is not None else 0.0,
        'delivery_type': billing[4] if billing and billing[4] is not None else 'In-Person',
        'delivered_to': billing[5] if billing and billing[5] is not None else '',
        'courier_channel': billing[6] if billing and billing[6] is not None else '',
        'courier_tracking': billing[7] if billing and billing[7] is not None else '',
        'amount_paid': float(billing[8]) if billing and billing[8] is not None else 0.0,
        'payment_date': billing[9] if billing and billing[9] is not None else '',
        'payment_id': billing[10] if billing and billing[10] is not None else '',
        'discount': float(billing[11]) if billing and billing[11] is not None else 0.0,
        'medicines_prepared': billing[12] if billing and billing[12] is not None else 0,
        'medicines_handed_over': billing[13] if billing and billing[13] is not None else 0,
        'couriered': billing[14] if billing and billing[14] is not None else 0,
        'checkout_done': billing[15] if billing and billing[15] is not None else 0
    })

@app.route('/billing_prepare/<id>', methods=['POST'])
def billing_prepare(id):
    if 'role' not in session or session['role'] != 'receptionist':
        return jsonify({'message': 'Unauthorized'}), 403
    data = request.json
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO billing (appointment_id, consultation_charge, medicine_charge, courier_charge, delivery_type, medicines_prepared) VALUES (?, 0, 0, 0, ?, 0)',
              (id, 'In-Person'))
    c.execute('''UPDATE billing SET 
                 consultation_charge = ?, medicine_charge = ?, courier_charge = ?, 
                 delivery_type = ?, delivered_to = ?, courier_channel = ?, courier_tracking = ?, 
                 amount_paid = ?, payment_date = ?, payment_id = ?, discount = ?
                 WHERE appointment_id = ?''',
                 (float(data['consultation_charge']) if data['consultation_charge'] else 0.0,
                  float(data['medicine_charge']) if data['medicine_charge'] else 0.0,
                  float(data['courier_charge']) if data['courier_charge'] else 0.0,
                  data['delivery_type'] or 'In-Person',
                  data['delivered_to'] or '',
                  data['courier_channel'] or '',
                  data['courier_tracking'] or '',
                  float(data['amount_paid']) if data['amount_paid'] else 0.0,
                  data['payment_date'] or '',
                  data['payment_id'] or '',
                  float(data['discount']) if data['discount'] else 0.0,
                  id))
    conn.commit()
    conn.close()
    save_to_csv('billing', pd.read_sql_query("SELECT * FROM billing", sqlite3.connect('clinic.db')).to_dict('records'))
    return jsonify({'message': 'Billing saved'})

@app.route('/hand_over_medicine/<id>', methods=['POST'])
def hand_over_medicine(id):
    if 'role' not in session or session['role'] != 'receptionist':
        return jsonify({'message': 'Unauthorized'}), 403
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('SELECT medicines_prepared FROM billing WHERE appointment_id = ?', (id,))
    prepared = c.fetchone()
    if not prepared or not prepared[0]:
        conn.close()
        return jsonify({'message': 'Medicines not prepared yet'}), 400
    c.execute('UPDATE billing SET medicines_handed_over = 1 WHERE appointment_id = ?', (id,))
    c.execute('SELECT p.mobile_number FROM appointments a JOIN patients p ON a.patient_id = p.patient_id WHERE a.id = ?', (id,))
    mobile = c.fetchone()[0]
    conn.commit()
    conn.close()
    send_whatsapp_message(mobile, "Medicines handed over")
    save_to_csv('billing', pd.read_sql_query("SELECT * FROM billing", sqlite3.connect('clinic.db')).to_dict('records'))
    return jsonify({'message': 'Medicine handed over'})

@app.route('/courier_done/<id>', methods=['POST'])
def courier_done(id):
    if 'role' not in session or session['role'] != 'receptionist':
        return jsonify({'message': 'Unauthorized'}), 403
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('SELECT medicines_prepared, delivery_type FROM billing WHERE appointment_id = ?', (id,))
    billing = c.fetchone()
    if not billing or not billing[0]:
        conn.close()
        return jsonify({'message': 'Medicines not prepared yet'}), 400
    if billing[1] != 'Courier':
        conn.close()
        return jsonify({'message': 'Delivery type is not Courier'}), 400
    c.execute('UPDATE billing SET couriered = 1 WHERE appointment_id = ?', (id,))
    c.execute('SELECT p.mobile_number FROM appointments a JOIN patients p ON a.patient_id = p.patient_id WHERE a.id = ?', (id,))
    mobile = c.fetchone()[0]
    conn.commit()
    conn.close()
    send_whatsapp_message(mobile, "Medicines couriered")
    save_to_csv('billing', pd.read_sql_query("SELECT * FROM billing", sqlite3.connect('clinic.db')).to_dict('records'))
    return jsonify({'message': 'Courier done'})

@app.route('/complete_checkout/<id>', methods=['POST'])
def complete_checkout(id):
    if 'role' not in session or session['role'] != 'receptionist':
        return jsonify({'message': 'Unauthorized'}), 403
    conn = sqlite3.connect('clinic.db')
    c = conn.cursor()
    c.execute('SELECT medicines_prepared, medicines_handed_over, couriered, consultation_charge, medicine_charge, courier_charge, amount_paid, discount FROM billing WHERE appointment_id = ?', (id,))
    billing = c.fetchone()
    if not billing or (not billing[1] and not billing[2]):
        conn.close()
        return jsonify({'message': 'Medicines not handed over or couriered'}), 400
    c.execute('UPDATE billing SET checkout_done = 1 WHERE appointment_id = ?', (id,))
    total_due = (billing[3] or 0) + (billing[4] or 0) + (billing[5] or 0) - (billing[7] or 0)
    if billing[6] < total_due:
        print(f"Credit due for appointment {id}: {total_due - billing[6]}")
    c.execute('SELECT p.mobile_number FROM appointments a JOIN patients p ON a.patient_id = p.patient_id WHERE a.id = ?', (id,))
    mobile = c.fetchone()[0]
    conn.commit()
    conn.close()
    send_whatsapp_message(mobile, "Checkout completed")
    save_to_csv('billing', pd.read_sql_query("SELECT * FROM billing", sqlite3.connect('clinic.db')).to_dict('records'))
    return jsonify({'message': 'Checkout completed'})

if __name__ == '__main__':
    app.run(debug=True)