Python
from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'kalpitiya_pradeshiya_sabha_secret_key'

def init_db():
    conn = sqlite3.connect('vehicle_tracker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_no TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            driver_name TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fuel_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            date TEXT,
            odometer REAL,
            liters REAL,
            total_cost REAL,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            date TEXT,
            service_type TEXT,
            description TEXT,
            cost REAL,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('vehicle_tracker.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM vehicles')
    vehicles = cursor.fetchall()
    
    selected_vehicle_id = request.args.get('vehicle_id', '')
    report_type = request.args.get('report_type', 'all')
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    fuel_query = '''
        SELECT fuel_logs.*, vehicles.vehicle_no 
        FROM fuel_logs 
        JOIN vehicles ON fuel_logs.vehicle_id = vehicles.id
    '''
    maint_query = '''
        SELECT maintenance_logs.*, vehicles.vehicle_no 
        FROM maintenance_logs 
        JOIN vehicles ON maintenance_logs.vehicle_id = vehicles.id
    '''
    
    fuel_conditions = []
    maint_conditions = []
    params = []

    if selected_vehicle_id:
        fuel_conditions.append('fuel_logs.vehicle_id = ?')
        maint_conditions.append('maintenance_logs.vehicle_id = ?')
        params.append(selected_vehicle_id)

    if report_type == 'day' and selected_date:
        fuel_conditions.append('fuel_logs.date = ?')
        maint_conditions.append('maintenance_logs.date = ?')
        params.append(selected_date)
    elif report_type == 'month' and selected_date:
        year_month = selected_date[:7]
        fuel_conditions.append('strftime("%Y-%m", fuel_logs.date) = ?')
        maint_conditions.append('strftime("%Y-%m", maintenance_logs.date) = ?')
        params.append(year_month)
    elif report_type == 'year' and selected_date:
        year = selected_date[:4]
        fuel_conditions.append('strftime("%Y", fuel_logs.date) = ?')
        maint_conditions.append('strftime("%Y", maintenance_logs.date) = ?')
        params.append(year)

    if fuel_conditions:
        fuel_query += ' WHERE ' + ' AND '.join(fuel_conditions)
    if maint_conditions:
        maint_query += ' WHERE ' + ' AND '.join(maint_conditions)

    fuel_query += ' ORDER BY fuel_logs.date DESC'
    maint_query += ' ORDER BY maintenance_logs.date DESC'
    
    cursor.execute(fuel_query, params)
    fuel_logs = cursor.fetchall()

    cursor.execute(maint_query, params)
    maint_logs = cursor.fetchall()
    
    total_fuel_cost = sum(row['total_cost'] for row in fuel_logs)
    total_maint_cost = sum(row['cost'] for row in maint_logs)
    grand_total = total_fuel_cost + total_maint_cost

vehicle_summary = []
    for v in vehicles:
        v_id = v['id']
        cursor.execute('SELECT SUM(total_cost) FROM fuel_logs WHERE vehicle_id = ?', (v_id,))
        f_cost = cursor.fetchone()[0] or 0.0
        cursor.execute('SELECT SUM(cost) FROM maintenance_logs WHERE vehicle_id = ?', (v_id,))
        m_cost = cursor.fetchone()[0] or 0.0
        
        vehicle_summary.append({
            'vehicle_no': v['vehicle_no'],
            'vehicle_type': v['vehicle_type'],
            'driver_name': v['driver_name'],
            'fuel_cost': f_cost,
            'maint_cost': m_cost,
            'total_cost': f_cost + m_cost
        })

    conn.close()
    logged_in = session.get('logged_in', False)
    
    return render_template_string(HTML_TEMPLATE, 
                                  vehicles=vehicles, 
                                  fuel_logs=fuel_logs, 
                                  maint_logs=maint_logs,
                                  vehicle_summary=vehicle_summary,
                                  report_type=report_type,
                                  selected_date=selected_date,
                                  selected_vehicle_id=selected_vehicle_id,
                                  total_fuel_cost=total_fuel_cost,
                                  total_maint_cost=total_maint_cost,
                                  grand_total=grand_total,
                                  logged_in=logged_in)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = 'Invalid Username or Password!'
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/add_vehicle', methods=['POST'])
def add_vehicle():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('vehicle_tracker.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO vehicles (vehicle_no, vehicle_type, driver_name) VALUES (?, ?, ?)',
                   (request.form['vehicle_no'], request.form['vehicle_type'], request.form['driver_name']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_fuel', methods=['POST'])
def add_fuel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('vehicle_tracker.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO fuel_logs (vehicle_id, date, odometer, liters, total_cost) VALUES (?, ?, ?, ?, ?)',
                   (request.form['vehicle_id'], request.form['date'], request.form['odometer'], request.form['liters'], request.form['total_cost']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_maintenance', methods=['POST'])
def add_maintenance():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('vehicle_tracker.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO maintenance_logs (vehicle_id, date, service_type, description, cost) VALUES (?, ?, ?, ?, ?)',
                   (request.form['vehicle_id'], request.form['date'], request.form['service_type'], request.form['description'], request.form['cost']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit_fuel/<int:id>', methods=['GET', 'POST'])
def edit_fuel(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('vehicle_tracker.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if request.method == 'POST':
        cursor.execute('''
            UPDATE fuel_logs SET vehicle_id = ?, date = ?, odometer = ?, liters = ?, total_cost = ?
            WHERE id = ?
        ''', (request.form['vehicle_id'], request.form['date'], request.form['odometer'], request.form['liters'], request.form['total_cost'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    cursor.execute('SELECT * FROM fuel_logs WHERE id = ?', (id,))
    fuel = cursor.fetchone()
    cursor.execute('SELECT * FROM vehicles')
    vehicles = cursor.fetchall()
    conn.close()
    return render_template_string(EDIT_FUEL_TEMPLATE, fuel=fuel, vehicles=vehicles)

@app.route('/edit_maintenance/<int:id>', methods=['GET', 'POST'])
def edit_maintenance(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('vehicle_tracker.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if request.method == 'POST':
        cursor.execute('''
            UPDATE maintenance_logs SET vehicle_id = ?, date = ?, service_type = ?, description = ?, cost = ?
            WHERE id = ?
        ''', (request.form['vehicle_id'], request.form['date'], request.form['service_type'], request.form['description'], request.form['cost'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    cursor.execute('SELECT * FROM maintenance_logs WHERE id = ?', (id,))
    maint = cursor.fetchone()
    cursor.execute('SELECT * FROM vehicles')
    vehicles = cursor.fetchall()
    conn.close()
    return render_template_string(EDIT_MAINT_TEMPLATE, maint=maint, vehicles=vehicles)

@app.route('/delete/<table_name>/<int:id>')
def delete_record(table_name, id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('vehicle_tracker.db')
    cursor = conn.cursor()
    if table_name == 'fuel':
        cursor.execute('DELETE FROM fuel_logs WHERE id = ?', (id,))
    elif table_name == 'maintenance':
        cursor.execute('DELETE FROM maintenance_logs WHERE id = ?', (id,))
    elif table_name == 'vehicle':
        cursor.execute('DELETE FROM vehicles WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Kalpitiya Pradeshiya Sabha - Vehicle & Maintenance Management System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 15px; background: #f4f7f6; }
        h2 { color: #2c3e50; text-align: center; }
        .card { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow-x: auto; }
        input, select, textarea { padding: 8px; margin: 5px 0; width: 100%; max-width: 400px; display: block; border: 1px solid #ccc; border-radius: 4px; }
        button, .btn-print, .btn-login { background: #27ae60; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 4px; font-weight: bold; text-decoration: none; display: inline-block; }
        button:hover, .btn-print:hover, .btn-login:hover { background: #219653; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; min-width: 600px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; }
        th { background: #2c3e50; color: white; }
        .btn-del { background: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px; margin-right: 5px; }
        .btn-del:hover { background: #c0392b; }
        .btn-edit { background: #f39c12; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px; }
        .btn-edit:hover { background: #d68910; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; background: white; padding: 10px 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .summary-box { background: #e8f8f5; padding: 15px; border-left: 5px solid #27ae60; margin-bottom: 15px; border-radius: 4px; }
        @media print {
            form, .btn-del, .btn-edit, .no-print { display: none !important; }
            body { background: white; margin: 0; }
            .card { box-shadow: none; border: 1px solid #ddd; }
        }
    </style>
</head>
<body>
    <div class="top-bar no-print">
        <h3 style="margin: 0; color: #2c3e50;">Kalpitiya Pradeshiya Sabha</h3>
        <div>
            {% if logged_in %}
                <span style="color: #27ae60; font-weight: bold; margin-right: 15px;">👤 Admin Logged In</span>
                <a href="/logout" class="btn-del" style="padding: 8px 12px; background: #c0392b;">Logout</a>
            {% else %}
                <a href="/login" class="btn-login">Admin Login</a>
            {% endif %}
        </div>
    </div>

    <h2>Vehicle & Maintenance Management System</h2>

    <div class="card no-print">
        <h3>📊 Advanced Reports & Vehicle Filter</h3>
        <form method="GET" action="/">
            <label>Select Vehicle:</label>
            <select name="vehicle_id">
                <option value="">All Vehicles</option>
                {% for v in vehicles %}
                <option value="{{ v.id }}" {% if selected_vehicle_id|string == v.id|string %}selected{% endif %}>{{ v.vehicle_no }} ({{ v.vehicle_type }})</option>
                {% endfor %}
            </select>

            <label>Report Period Type:</label>
            <select name="report_type">
                <option value="all" {% if report_type == 'all' %}selected{% endif %}>All Records</option>
                <option value="day" {% if report_type == 'day' %}selected{% endif %}>Day Report (YYYY-MM-DD)</option>
                <option value="month" {% if report_type == 'month' %}selected{% endif %}>Month Report (YYYY-MM)</option>
                <option value="year" {% if report_type == 'year' %}selected{% endif %}>Year Report (YYYY)</option>
            </select>
            
            <label>Date / Month / Year Value:</label>
            <input type="text" name="date" value="{{ selected_date }}" placeholder="YYYY-MM-DD or YYYY-MM or YYYY">
            <button type="submit">Filter Report</button>
            <button type="button" class="btn-print" onclick="window.print()" style="background: #2980b9; margin-top: 5px;">Download / Print PDF</button>
        </form>
    </div>

    <div class="summary-box">
        <h3>📈 Cost Summary (Filtered)</h3>
        <p><b>Total Fuel Cost:</b> Rs. {{ "%.2f"|format(total_fuel_cost) }}</p>
        <p><b>Total Maintenance Cost:</b> Rs. {{ "%.2f"|format(total_maint_cost) }}</p>
        <p><b>Grand Total Cost:</b> <span style="color: #c0392b; font-size: 18px;"><b>Rs. {{ "%.2f"|format(grand_total) }}</b></span></p>
    </div>

    <div class="card">
        <h3>🚗 Vehicle-wise Overall Expense Summary</h3>
        <table>
            <tr>
                <th>Vehicle No</th>
                <th>Type</th>
                <th>Driver</th>
                <th>Fuel Cost (Rs.)</th>
                <th>Maintenance Cost (Rs.)</th>
                <th>Total Cost (Rs.)</th>
            </tr>
            {% for vs in vehicle_summary %}
            <tr>
                <td>{{ vs.vehicle_no }}</td>
                <td>{{ vs.vehicle_type }}</td>
                <td>{{ vs.driver_name }}</td>
                <td>Rs. {{ "%.2f"|format(vs.fuel_cost) }}</td>
                <td>Rs. {{ "%.2f"|format(vs.maint_cost) }}</td>
                <td><b>Rs. {{ "%.2f"|format(vs.total_cost) }}</b></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h3>1. Registered Vehicles</h3>
        <table>
            <tr>
                <th>Vehicle No</th>
                <th>Type</th>
                <th>Driver Name</th>
                {% if logged_in %}<th class="no-print">Action</th>{% endif %}
            </tr>
            {% for v in vehicles %}
            <tr>
                <td>{{ v.vehicle_no }}</td>
                <td>{{ v.vehicle_type }}</td>
                <td>{{ v.driver_name }}</td>
                {% if logged_in %}
                <td class="no-print"><a href="/delete/vehicle/{{ v.id }}" class="btn-del" onclick="return confirm('Are you sure you want to delete?')">Delete</a></td>
                {% endif %}
            </tr>
            {% endfor %}
        </table>

        {% if logged_in %}
        <h3 style="margin-top: 20px;" class="no-print">Add New Vehicle</h3>
        <form action="/add_vehicle" method="POST" class="no-print">
            <input type="text" name="vehicle_no" placeholder="Vehicle No (e.g., WP NC-1234)" required>
            <input type="text" name="vehicle_type" placeholder="Vehicle Type (Tractor/Cab/Bike)" required>
            <input type="text" name="driver_name" placeholder="Driver Name" required>
            <button type="submit">Add Vehicle</button>
        </form>
        {% endif %}
    </div>

    {% if logged_in %}
    <div class="card no-print">
        <h3>2. Add Fuel Log</h3>
        <form action="/add_fuel" method="POST">
            <select name="vehicle_id" required>
                <option value="">Select Vehicle</option>
                {% for v in vehicles %}
                <option value="{{ v.id }}">{{ v.vehicle_no }} ({{ v.vehicle_type }})</option>
                {% endfor %}
            </select>
            <input type="date" name="date" required>
            <input type="number" step="0.01" name="odometer" placeholder="Odometer (km)" required>
            <input type="number" step="0.01" name="liters" placeholder="Liters" required>
            <input type="number" step="0.01" name="total_cost" placeholder="Fuel Cost (Rs.)" required>
            <button type="submit">Add Fuel Log</button>
        </form>
    </div>

    <div class="card no-print">
        <h3>3. Add Maintenance Expense</h3>
        <form action="/add_maintenance" method="POST">
            <select name="vehicle_id" required>
                <option value="">Select Vehicle</option>
                {% for v in vehicles %}
                <option value="{{ v.id }}">{{ v.vehicle_no }} ({{ v.vehicle_type }})</option>
                {% endfor %}
            </select>
            <input type="date" name="date" required>
            <input type="text" name="service_type" placeholder="Service Type (e.g., Oil Change, Tyre Repair)" required>
            <textarea name="description" placeholder="Work Description" rows="2"></textarea>
            <input type="number" step="0.01" name="cost" placeholder="Maintenance Cost (Rs.)" required>
            <button type="submit">Add Maintenance Log</button>
        </form>
    </div>
    {% endif %}

    <div class="card">
        <h3>4. Fuel Logs List</h3>
        <table>
            <tr>
                <th>Date</th>
                <th>Vehicle No</th>
                <th>Odometer (km)</th>
                <th>Liters</th>
                <th>Cost (Rs.)</th>
                {% if logged_in %}<th class="no-print">Action</th>{% endif %}
            </tr>
            {% for log in fuel_logs %}
            <tr>
                <td>{{ log.date }}</td>
                <td>{{ log.vehicle_no }}</td>
                <td>{{ log.odometer }}</td>
                <td>{{ log.liters }}</td>
                <td>{{ log.total_cost }}</td>
                {% if logged_in %}
                <td class="no-print">
                    <a href="/edit_fuel/{{ log.id }}" class="btn-edit">Edit</a>
                    <a href="/delete/fuel/{{ log.id }}" class="btn-del" onclick="return confirm('Are you sure you want to delete?')">Delete</a>
                </td>
                {% endif %}
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h3>5. Maintenance Expenses List</h3>
        <table>
            <tr>
                <th>Date</th>
                <th>Vehicle No</th>
                <th>Service Type</th>
                <th>Description</th>
                <th>Cost (Rs.)</th>
                {% if logged_in %}<th class="no-print">Action</th>{% endif %}
            </tr>
            {% for m in maint_logs %}
            <tr>
                <td>{{ m.date }}</td>
                <td>{{ m.vehicle_no }}</td>
                <td>{{ m.service_type }}</td>
                <td>{{ m.description }}</td>
                <td>{{ m.cost }}</td>
                {% if logged_in %}
                <td class="no-print">
                    <a href="/edit_maintenance/{{ m.id }}" class="btn-edit">Edit</a>
                    <a href="/delete/maintenance/{{ m.id }}" class="btn-del" onclick="return confirm('Are you sure you want to delete?')">Delete</a>
                </td>
                {% endif %}
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; background: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); width: 100%; max-width: 350px; }
        h3 { text-align: center; color: #2c3e50; margin-bottom: 20px; }
        input { padding: 10px; margin: 10px 0; width: 100%; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { background: #27ae60; color: white; border: none; padding: 10px; width: 100%; cursor: pointer; border-radius: 4px; font-weight: bold; font-size: 16px; }
        button:hover { background: #219653; }
        .error { color: #e74c3c; font-size: 14px; text-align: center; margin-bottom: 10px; }
        a { display: block; text-align: center; margin-top: 15px; text-decoration: none; color: #2980b9; font-size: 14px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h3>Admin Login</h3>
        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username (admin)" required>
            <input type="password" name="password" placeholder="Password (admin123)" required>
            <button type="submit">Login</button>
        </form>
        <a href="/">← Back to Home</a>
    </div>
</body>
</html>
'''

EDIT_FUEL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Edit Fuel Log</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; background: #f4f7f6; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 500px; margin: auto; }
        input, select { padding: 8px; margin: 10px 0; width: 100%; border: 1px solid #ccc; border-radius: 4px; display: block; box-sizing: border-box; }
        button { background: #f39c12; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 4px; font-weight: bold; width: 100%; }
        button:hover { background: #d68910; }
        a { display: inline-block; margin-top: 10px; text-decoration: none; color: #2c3e50; }
    </style>
</head>
<body>
    <div class="card">
        <h3>Edit Fuel Log</h3>
        <form method="POST">
            <label>Vehicle:</label>
            <select name="vehicle_id" required>
                {% for v in vehicles %}
                <option value="{{ v.id }}" {% if v.id == fuel.vehicle_id %}selected{% endif %}>{{ v.vehicle_no }} ({{ v.vehicle_type }})</option>
                {% endfor %}
            </select>
            <label>Date:</label>
            <input type="date" name="date" value="{{ fuel.date }}" required>
            <label>Odometer (km):</label>
            <input type="number" step="0.01" name="odometer" value="{{ fuel.odometer }}" required>
            <label>Liters:</label>
            <input type="number" step="0.01" name="liters" value="{{ fuel.liters }}" required>
            <label>Fuel Cost (Rs.):</label>
            <input type="number" step="0.01" name="total_cost" value="{{ fuel.total_cost }}" required>
            <button type="submit">Update Fuel Log</button>
        </form>
        <a href="/">← Back to Home</a>
    </div>
</body>
</html>
'''

EDIT_MAINT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Edit Maintenance Log</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; background: #f4f7f6; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 500px; margin: auto; }
        input, select, textarea { padding: 8px; margin: 10px 0; width: 100%; border: 1px solid #ccc; border-radius: 4px; display: block; box-sizing: border-box; }
        button { background: #f39c12; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 4px; font-weight: bold; width: 100%; }
        button:hover { background: #d68910; }
        a { display: inline-block; margin-top: 10px; text-decoration: none; color: #2c3e50; }
    </style>
</head>
<body>
    <div class="card">
        <h3>Edit Maintenance Log</h3>
        <form method="POST">
            <label>Vehicle:</label>
            <select name="vehicle_id" required>
                {% for v in vehicles %}
                <option value="{{ v.id }}" {% if v.id == maint.vehicle_id %}selected{% endif %}>{{ v.vehicle_no }} ({{ v.vehicle_type }})</option>
                {% endfor %}
            </select>
            <label>Date:</label>
            <input type="date" name="date" value="{{ maint.date }}" required>
            <label>Service Type:</label>
            <input type="text" name="service_type" value="{{ maint.service_type }}" required>
            <label>Description:</label>
            <textarea name="description" rows="3">{{ maint.description }}</textarea>
            <label>Maintenance Cost (Rs.):</label>
            <input type="number" step="0.01" name="cost" value="{{ maint.cost }}" required>
            <button type="submit">Update Maintenance Log</button>
        </form>
        <a href="/">← Back to Home</a>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)