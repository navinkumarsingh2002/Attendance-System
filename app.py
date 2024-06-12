import sqlite3
import secrets
from flask import Flask, render_template, request, redirect, url_for,session,flash
from datetime import datetime, timedelta
import calendar
import jsonify


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


# Define SQLite database path
DB_PATH = 'database/attendance.db'

# Routes and other application logic...

# Database setup function
def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,
                        employee_name TEXT NOT NULL
                    )''')

    # Create Attendance table
    cursor.execute('''CREATE TABLE IF NOT EXISTS Attendance (
                        id INTEGER PRIMARY KEY,
                        employee_id INTEGER NOT NULL,
                        punch_in_time TEXT NOT NULL,
                        punch_out_time TEXT,
                        FOREIGN KEY(employee_id) REFERENCES Users(id)
                    )''')

    conn.commit()
    

    cursor.execute('''INSERT OR IGNORE INTO Users (username, password, role, employee_name) 
                      VALUES (?, ?, ?, ?)''', ('admin', 'admin123', 'admin', 'Admin1'))

    cursor.execute('''INSERT OR IGNORE INTO Users (username, password, role, employee_name) 
                      VALUES (?, ?, ?, ?)''', ('receptionist', 'receptionist123', 'receptionist', 'Receptionist Name'))

    cursor.execute('''INSERT OR IGNORE INTO Users (username, password, role, employee_name) 
                      VALUES (?, ?, ?, ?)''', ('employee', 'employee123', 'employee', 'Employee Name'))

    conn.commit()
    conn.close()

# Routes

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/dashboard', methods=['POST'])
def dashboard():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT * FROM Users WHERE username=? AND password=?''', (username, password))
        user = cursor.fetchone()
        
        if user:
            session['username'] = username
            session['role'] = user[3] 
            if session['role']=='admin':
                return render_template('admin_dashboard.html')
            elif session['role'] =='receptionist':
                return render_template('receptionist_dashboard.html')
            elif session['role'] =='employee':
                return render_template('employee_dashboard.html')
        else:
            return render_template('login.html', error='Invalid credentials')

@app.route('/admin')
def admin_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Fetch data or perform operations specific to admin
    conn.close()
    return render_template('admin_dashboard.html')


@app.route('/admin/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        employee_name = request.form['employee_name']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''INSERT INTO Users (username, password, role, employee_name) 
                          VALUES (?, ?, ?, ?)''', (username, password, role, employee_name))
        
        conn.commit()
        conn.close()

        
        return redirect(url_for('add_employee'))
    return render_template('add_employee.html')



@app.route('/admin/employee_list')
def employee_list():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch the list of employees from the database
    cursor.execute('''SELECT * FROM Users WHERE role != ?''', ('admin',))  # Exclude admin users from the list
    employees = cursor.fetchall()

    conn.close()

    return render_template('employee_list.html', employees=employees)


@app.route('/admin/insights')
def insights():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    # Fetch the list of employees to populate the dropdown menu
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''SELECT id, employee_name FROM Users WHERE role = 'employee' ''')
    employees = cursor.fetchall()
    conn.close()

    return render_template('view_insights.html', employees=employees)



@app.route('/admin/insights_data', methods=['POST'])
def insights_data():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    employee_id = request.form['employee_id']

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Calculate start and end dates for the current week
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Fetch weekly work done by the selected employee
    weekly_data = []
    for i in range(7):
        date = start_of_week + timedelta(days=i)
        cursor.execute('''SELECT COUNT(*) FROM Attendance WHERE employee_id=? AND punch_in_time BETWEEN ? AND ?''',
                       (employee_id, date.strftime('%Y-%m-%d 00:00:00'), date.strftime('%Y-%m-%d 23:59:59')))
        work_done = cursor.fetchone()[0]
        weekly_data.append(work_done)

    # Fetch monthly work done by the selected employee
    monthly_data = []
    for month in range(1, 13):
        num_days = calendar.monthrange(today.year, month)[1]
        start_date = datetime(today.year, month, 1)
        end_date = datetime(today.year, month, num_days)
        cursor.execute('''SELECT COUNT(*) FROM Attendance WHERE employee_id=? AND punch_in_time BETWEEN ? AND ?''',
                       (employee_id, start_date.strftime('%Y-%m-%d 00:00:00'), end_date.strftime('%Y-%m-%d 23:59:59')))
        work_done = cursor.fetchone()[0]
        monthly_data.append(work_done)

    conn.close()

    return jsonify({'weekly_data': weekly_data, 'monthly_data': monthly_data})



@app.route('/receptionist')
def receptionist_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('receptionist_dashboard.html')



# app.py
from flask import jsonify, flash

@app.route('/receptionist/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    if 'username' not in session or session['role'] != 'receptionist':
        return redirect(url_for('login'))

    if request.method == 'POST':
        employee_id = request.form['employee_id']
        punch_in_time = request.form['punch_in_time']
        punch_out_time = request.form['punch_out_time']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''INSERT INTO Attendance (employee_id, punch_in_time, punch_out_time) 
                          VALUES (?, ?, ?)''', (employee_id, punch_in_time, punch_out_time))

        conn.commit()
        conn.close()

        flash('Attendance marked successfully', 'success')
        return redirect(url_for('mark_attendance'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch the list of employees to populate the dropdown menu
    cursor.execute('''SELECT id, employee_name FROM Users WHERE role = 'employee' ''')
    employees = cursor.fetchall()

    conn.close()

    return render_template('mark_attendance.html', employees=employees)

 


@app.route('/receptionist/update_attendance', methods=['GET', 'POST'])
def update_attendance():
    pass


@app.route('/receptionist/view_attendance', methods=['GET', 'POST'])
def view_attendance():
    if 'username' not in session or session['role'] != 'receptionist':
        return redirect(url_for('login'))

    if request.method == 'POST':
        employee_name = request.form['employee_name']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''SELECT id FROM Users WHERE employee_name = ?''', (employee_name,))
        employee_id = cursor.fetchone()[0]

        cursor.execute('''SELECT punch_in_time, punch_out_time FROM Attendance 
                          WHERE employee_id = ? ORDER BY punch_in_time DESC''', (employee_id,))
        attendance_records = cursor.fetchall()

        conn.close()

        return render_template('view_attendance.html', employee_name=employee_name, attendance_records=attendance_records)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''SELECT employee_name FROM Users WHERE role = 'employee' ''')
    employees = cursor.fetchall()

    conn.close()

    return render_template('view_attendance.html', employees=employees)

    




@app.route('/employee')
def employee_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    
    return render_template('employee_dashboard.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    setup_database()
    app.run(debug=True)
