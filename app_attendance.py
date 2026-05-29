import os
import sqlite3
import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static')
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'attendance.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS divisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        max_capacity INTEGER DEFAULT 30
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        usn TEXT UNIQUE NOT NULL,
        mobile_number TEXT,
        email TEXT,
        branch TEXT,
        semester INTEGER,
        division_id INTEGER,
        photo_path TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(division_id) REFERENCES divisions(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL,
        room_number TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        day_of_week TEXT NOT NULL,
        division_id INTEGER NOT NULL,
        FOREIGN KEY(division_id) REFERENCES divisions(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS co_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL,
        outcome_code TEXT NOT NULL,
        description TEXT NOT NULL,
        target_percentage INTEGER DEFAULT 100,
        current_completion INTEGER DEFAULT 0
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS po_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        outcome_code TEXT NOT NULL,
        description TEXT NOT NULL,
        target_percentage INTEGER DEFAULT 100,
        current_completion INTEGER DEFAULT 0
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS portion_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL,
        topic TEXT NOT NULL,
        status TEXT DEFAULT 'pending'
    )
    ''')
    
    # 2. Seed default data if users is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        print("Seeding default system data...")
        
        # Seed Divisions
        cursor.execute("INSERT OR IGNORE INTO divisions (name, max_capacity) VALUES ('Division A', 30)")
        cursor.execute("INSERT OR IGNORE INTO divisions (name, max_capacity) VALUES ('Division B', 30)")
        cursor.execute("INSERT OR IGNORE INTO divisions (name, max_capacity) VALUES ('Division C', 30)")
        
        # Seed Admin
        admin_pass = generate_password_hash("admin123")
        cursor.execute("INSERT INTO users (email, password_hash, role) VALUES ('admin@attendance.com', ?, 'admin')", (admin_pass,))
        
        # Seed Faculty
        faculty_pass = generate_password_hash("faculty123")
        cursor.execute("INSERT INTO users (email, password_hash, role) VALUES ('faculty@attendance.com', ?, 'faculty')", (faculty_pass,))
        
        # Seed Student
        student_pass = generate_password_hash("student123")
        cursor.execute("INSERT INTO users (email, password_hash, role) VALUES ('student@attendance.com', ?, 'student')", (student_pass,))
        student_user_id = cursor.lastrowid
        
        # Get division ID
        cursor.execute("SELECT id FROM divisions WHERE name='Division A'")
        div_a_id = cursor.fetchone()[0]
        
        # Insert Student profile
        cursor.execute('''
        INSERT INTO students (user_id, name, usn, mobile_number, email, branch, semester, division_id)
        VALUES (?, 'John Doe', '1MS21CS001', '8765432109', 'student@attendance.com', 'CSE', 6, ?)
        ''', (student_user_id, div_a_id))
        
        # Add a couple other mockup students to show CRUD and attendance easily
        cursor.execute('''
        INSERT INTO students (name, usn, mobile_number, email, branch, semester, division_id) VALUES
        ('Emma Watson', '1MS21CS002', '9988776655', 'emma@attendance.com', 'CSE', 6, ?),
        ('Liam Neeson', '1MS21CS003', '9988776644', 'liam@attendance.com', 'CSE', 6, ?),
        ('Olivia Wilde', '1MS21CS004', '9988776633', 'olivia@attendance.com', 'CSE', 6, ?)
        ''', (div_a_id, div_a_id, div_a_id))
        
        # Seed Timetable
        cursor.execute('''
        INSERT INTO timetable (course_name, room_number, start_time, end_time, duration_minutes, day_of_week, division_id) VALUES
        ('Data Structures', 'LHC-201', '09:00', '10:00', 60, 'Monday', ?),
        ('Operating Systems', 'LHC-202', '10:15', '11:15', 60, 'Monday', ?),
        ('Artificial Intelligence', 'LHC-201', '09:00', '10:00', 60, 'Tuesday', ?),
        ('Database Systems', 'CS-LAB-1', '14:00', '16:00', 120, 'Wednesday', ?)
        ''', (div_a_id, div_a_id, div_a_id, div_a_id))
        
        # Seed CO/PO
        cursor.execute('''
        INSERT INTO co_mappings (course_name, outcome_code, description, target_percentage, current_completion) VALUES
        ('Data Structures', 'CO1', 'Understand and apply linear and non-linear data structures.', 100, 80),
        ('Data Structures', 'CO2', 'Evaluate algorithms complexity using big-O notations.', 100, 55),
        ('Operating Systems', 'CO1', 'Explain key OS tasks: scheduling, virtual memory, filesystems.', 100, 75),
        ('Artificial Intelligence', 'CO1', 'Formulate heuristic search algorithms for game playing.', 100, 40)
        ''')
        
        cursor.execute('''
        INSERT INTO po_mappings (outcome_code, description, target_percentage, current_completion) VALUES
        ('PO1', 'Engineering Knowledge: Apply core scientific and math tools to design solutions.', 100, 65),
        ('PO2', 'Problem Analysis: Model and analyze complex computing problems.', 100, 50)
        ''')
        
        # Seed Portions
        cursor.execute('''
        INSERT INTO portion_tracking (course_name, topic, status) VALUES
        ('Data Structures', 'Arrays & Linked Lists', 'completed'),
        ('Data Structures', 'Stacks & Queues', 'completed'),
        ('Data Structures', 'Trees & Graphs', 'pending'),
        ('Operating Systems', 'Processes & Threads', 'completed'),
        ('Operating Systems', 'CPU Scheduling Algorithms', 'completed'),
        ('Operating Systems', 'Memory Management & Paging', 'pending')
        ''')
        
        # Seed some attendance logs for past few days
        today = datetime.date.today()
        for i in range(1, 6):
            log_date = (today - datetime.timedelta(days=i)).isoformat()
            cursor.execute("INSERT INTO attendance_logs (student_id, date, status, type, timestamp) VALUES (1, ?, 'Present', 'manual', ?)", (log_date, log_date + " 09:05:22"))
            cursor.execute("INSERT INTO attendance_logs (student_id, date, status, type, timestamp) VALUES (2, ?, 'Present', 'manual', ?)", (log_date, log_date + " 09:06:11"))
            cursor.execute("INSERT INTO attendance_logs (student_id, date, status, type, timestamp) VALUES (3, ?, 'Absent', 'manual', ?)", (log_date, log_date + " --"))
            cursor.execute("INSERT INTO attendance_logs (student_id, date, status, type, timestamp) VALUES (4, ?, 'Present', 'camera', ?)", (log_date, log_date + " 09:02:18"))
            
        conn.commit()
    conn.close()

# Initialize the DB on load
init_db()

# --- API ENDPOINTS ---

# Root Route: Serve the SPA page
@app.route('/')
def index():
    # We will serve templates/attendance.html
    return send_from_directory('templates', 'attendance.html')

# Auth Endpoint
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    
    if user and check_password_hash(user['password_hash'], password):
        user_id = user['id']
        role = user['role']
        
        # Check if student and fetch USN
        student_usn = ""
        student_id = None
        student_div = ""
        if role == 'student':
            student_row = conn.execute('SELECT s.id, s.usn, d.name as div_name FROM students s LEFT JOIN divisions d ON s.division_id = d.id WHERE s.user_id = ?', (user_id,)).fetchone()
            if student_row:
                student_usn = student_row['usn']
                student_id = student_row['id']
                student_div = student_row['div_name']
                
        conn.close()
        return jsonify({
            'token': f'mock-token-for-{email}',
            'user': {
                'id': user_id,
                'email': email,
                'role': role,
                'usn': student_usn,
                'student_id': student_id,
                'division': student_div
            }
        })
    
    conn.close()
    return jsonify({'error': 'Invalid credentials'}), 401

# Students CRUD Endpoints
@app.route('/api/students', methods=['GET'])
def get_students():
    search = request.args.get('search', '')
    division = request.args.get('division', '')
    semester = request.args.get('semester', '')
    
    conn = get_db_connection()
    query = '''
        SELECT s.*, d.name as division_name 
        FROM students s 
        LEFT JOIN divisions d ON s.division_id = d.id
        WHERE 1=1
    '''
    params = []
    
    if search:
        query += " AND (s.name LIKE ? OR s.usn LIKE ? OR s.email LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
        
    if division:
        query += " AND d.name = ?"
        params.append(division)
        
    if semester:
        query += " AND s.semester = ?"
        params.append(int(semester))
        
    rows = conn.execute(query, params).fetchall()
    students_list = [dict(r) for r in rows]
    conn.close()
    return jsonify(students_list)

@app.route('/api/students', methods=['POST'])
def add_student():
    data = request.json
    name = data.get('name')
    usn = data.get('usn')
    mobile = data.get('mobile_number', '')
    email = data.get('email', '')
    branch = data.get('branch', 'CSE')
    semester = data.get('semester', 6)
    division_name = data.get('division', 'Division A')
    
    if not name or not usn:
        return jsonify({'error': 'Name and USN are required'}), 400
        
    conn = get_db_connection()
    
    # Resolve division_id
    div_row = conn.execute('SELECT id, max_capacity FROM divisions WHERE name = ?', (division_name,)).fetchone()
    if not div_row:
        conn.close()
        return jsonify({'error': f'Division {division_name} not found'}), 404
        
    division_id = div_row['id']
    max_cap = div_row['max_capacity']
    
    # Check division capacity guard
    count_row = conn.execute('SELECT COUNT(*) FROM students WHERE division_id = ?', (division_id,)).fetchone()
    current_count = count_row[0]
    if current_count >= max_cap:
        conn.close()
        return jsonify({'error': f'Division {division_name} is full (capacity limit of {max_cap} reached)'}), 400
        
    # Check unique USN
    existing = conn.execute('SELECT id FROM students WHERE usn = ?', (usn,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': f'Student with USN {usn} already exists'}), 400
        
    try:
        # Create a user record for the student so they can log in
        salt_pass = generate_password_hash("student123")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password_hash, role) VALUES (?, ?, 'student')", (email or f"{usn.lower()}@attendance.com", salt_pass))
        user_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO students (user_id, name, usn, mobile_number, email, branch, semester, division_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, usn, mobile, email, branch, int(semester), division_id))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({'success': True, 'id': new_id, 'message': 'Student registered successfully.'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    data = request.json
    name = data.get('name')
    usn = data.get('usn')
    mobile = data.get('mobile_number', '')
    email = data.get('email', '')
    branch = data.get('branch', 'CSE')
    semester = data.get('semester', 6)
    division_name = data.get('division', 'Division A')
    
    if not name or not usn:
        return jsonify({'error': 'Name and USN are required'}), 400
        
    conn = get_db_connection()
    
    # Resolve division_id
    div_row = conn.execute('SELECT id FROM divisions WHERE name = ?', (division_name,)).fetchone()
    if not div_row:
        conn.close()
        return jsonify({'error': f'Division {division_name} not found'}), 404
    division_id = div_row['id']
    
    # Check if another student has the same USN
    existing = conn.execute('SELECT id FROM students WHERE usn = ? AND id != ?', (usn, student_id)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': f'Another student with USN {usn} already exists'}), 400
        
    try:
        conn.execute('''
            UPDATE students 
            SET name = ?, usn = ?, mobile_number = ?, email = ?, branch = ?, semester = ?, division_id = ?
            WHERE id = ?
        ''', (name, usn, mobile, email, branch, int(semester), division_id, student_id))
        
        # Also update user email if user_id matches
        student = conn.execute('SELECT user_id FROM students WHERE id = ?', (student_id,)).fetchone()
        if student and student['user_id']:
            conn.execute('UPDATE users SET email = ? WHERE id = ?', (email, student['user_id']))
            
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Student updated successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    conn = get_db_connection()
    try:
        student = conn.execute('SELECT user_id FROM students WHERE id = ?', (student_id,)).fetchone()
        if student:
            user_id = student['user_id']
            if user_id:
                conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Student deleted successfully'})
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# Divisions Endpoints
@app.route('/api/divisions', methods=['GET'])
def get_divisions():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT d.id, d.name, d.max_capacity, COUNT(s.id) as student_count 
        FROM divisions d 
        LEFT JOIN students s ON d.id = s.division_id 
        GROUP BY d.id
    ''').fetchall()
    div_list = [dict(r) for r in rows]
    conn.close()
    return jsonify(div_list)

# Attendance Logging Endpoints
@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    data = request.json
    student_id = data.get('student_id')
    status = data.get('status', 'Present')
    mark_type = data.get('type', 'manual')
    date_str = data.get('date', datetime.date.today().isoformat())
    
    if not student_id:
        return jsonify({'error': 'student_id is required'}), 400
        
    conn = get_db_connection()
    
    # Check if student exists
    student = conn.execute('SELECT name FROM students WHERE id = ?', (student_id,)).fetchone()
    if not student:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == 'Present' else '--'
    
    try:
        # Delete existing log for this student on this date
        conn.execute('DELETE FROM attendance_logs WHERE student_id = ? AND date = ?', (student_id, date_str))
        
        # Insert new log
        conn.execute('''
            INSERT INTO attendance_logs (student_id, date, status, type, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (student_id, date_str, status, mark_type, timestamp))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Attendance marked as {status} for {student["name"]}'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance/bulk', methods=['POST'])
def mark_bulk_attendance():
    data = request.json
    records = data.get('records', []) # list of dicts: {student_id: X, status: 'Present'/'Absent'}
    date_str = data.get('date', datetime.date.today().isoformat())
    
    if not records:
        return jsonify({'error': 'No records provided'}), 400
        
    conn = get_db_connection()
    try:
        for rec in records:
            s_id = rec.get('student_id')
            status = rec.get('status', 'Present')
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == 'Present' else '--'
            
            # Delete old log for this student on this date
            conn.execute('DELETE FROM attendance_logs WHERE student_id = ? AND date = ?', (s_id, date_str))
            # Insert new log
            conn.execute('''
                INSERT INTO attendance_logs (student_id, date, status, type, timestamp)
                VALUES (?, ?, ?, 'manual', ?)
            ''', (s_id, date_str, status, timestamp))
            
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Bulk attendance logs saved for {len(records)} students.'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance/stats', methods=['GET'])
def get_stats():
    conn = get_db_connection()
    today_str = datetime.date.today().isoformat()
    
    # 1. KPI Stats
    total_students = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    
    present_today = conn.execute(
        "SELECT COUNT(*) FROM attendance_logs WHERE date = ? AND status = 'Present'", (today_str,)
    ).fetchone()[0]
    
    absent_today = conn.execute(
        "SELECT COUNT(*) FROM attendance_logs WHERE date = ? AND status = 'Absent'", (today_str,)
    ).fetchone()[0]
    
    # Unmarked students are total_students - (present + absent)
    unmarked_today = max(0, total_students - (present_today + absent_today))
    
    # 2. Cumulative Rates
    total_logs_count = conn.execute('SELECT COUNT(*) FROM attendance_logs').fetchone()[0]
    total_present_count = conn.execute("SELECT COUNT(*) FROM attendance_logs WHERE status = 'Present'").fetchone()[0]
    
    attendance_rate = 100
    if total_logs_count > 0:
        attendance_rate = round((total_present_count / total_logs_count) * 100, 1)
        
    # 3. Weekly Trends (Last 7 days)
    trends = []
    today = datetime.date.today()
    for i in range(6, -1, -1):
        day_date = today - datetime.timedelta(days=i)
        day_str = day_date.isoformat()
        day_name = day_date.strftime("%a")
        
        # Count present/absent for this date
        p_count = conn.execute("SELECT COUNT(*) FROM attendance_logs WHERE date = ? AND status = 'Present'", (day_str,)).fetchone()[0]
        a_count = conn.execute("SELECT COUNT(*) FROM attendance_logs WHERE date = ? AND status = 'Absent'", (day_str,)).fetchone()[0]
        
        trends.append({
            'date': day_str,
            'label': day_name,
            'present': p_count,
            'absent': a_count
        })
        
    # 4. Recent activity logs
    logs_row = conn.execute('''
        SELECT a.timestamp, a.status, a.type, s.name, s.usn 
        FROM attendance_logs a
        JOIN students s ON a.student_id = s.id
        ORDER BY a.id DESC LIMIT 10
    ''').fetchall()
    recent_activity = [dict(r) for r in logs_row]
    
    conn.close()
    return jsonify({
        'total_students': total_students,
        'present_today': present_today,
        'absent_today': absent_today,
        'unmarked_today': unmarked_today,
        'attendance_rate': attendance_rate,
        'trends': trends,
        'recent_activity': recent_activity
    })

# Timetable Scheduler Endpoints
@app.route('/api/timetable', methods=['GET'])
def get_timetable():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT t.*, d.name as division_name 
        FROM timetable t
        JOIN divisions d ON t.division_id = d.id
        ORDER BY t.day_of_week, t.start_time
    ''').fetchall()
    timetable_list = [dict(r) for r in rows]
    conn.close()
    return jsonify(timetable_list)

@app.route('/api/timetable', methods=['POST'])
def add_timetable_slot():
    data = request.json
    course_name = data.get('course_name')
    room_number = data.get('room_number')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    day_of_week = data.get('day_of_week')
    division_name = data.get('division', 'Division A')
    
    if not course_name or not room_number or not start_time or not end_time or not day_of_week:
        return jsonify({'error': 'All slot parameters are required'}), 400
        
    # Calculate duration
    try:
        t1 = datetime.datetime.strptime(start_time, "%H:%M")
        t2 = datetime.datetime.strptime(end_time, "%H:%M")
        duration = int((t2 - t1).total_seconds() / 60)
        if duration <= 0:
            return jsonify({'error': 'End time must be after start time'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid time format. Use HH:MM'}), 400
        
    conn = get_db_connection()
    div_row = conn.execute('SELECT id FROM divisions WHERE name = ?', (division_name,)).fetchone()
    if not div_row:
        conn.close()
        return jsonify({'error': f'Division {division_name} not found'}), 404
    division_id = div_row['id']
    
    try:
        conn.execute('''
            INSERT INTO timetable (course_name, room_number, start_time, end_time, duration_minutes, day_of_week, division_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (course_name, room_number, start_time, end_time, duration, day_of_week, division_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Class scheduled successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/timetable/<int:slot_id>', methods=['DELETE'])
def delete_timetable_slot(slot_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM timetable WHERE id = ?', (slot_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Scheduled class deleted'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# CO/PO portions tracking
@app.route('/api/copo/portions', methods=['GET'])
def get_portions():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM portion_tracking').fetchall()
    portions = [dict(r) for r in rows]
    conn.close()
    return jsonify(portions)

@app.route('/api/copo/portions', methods=['POST'])
def add_or_update_portion():
    data = request.json
    course_name = data.get('course_name')
    topic = data.get('topic')
    status = data.get('status', 'pending')
    portion_id = data.get('id')
    
    if not course_name or not topic:
        return jsonify({'error': 'Course name and topic are required'}), 400
        
    conn = get_db_connection()
    try:
        if portion_id:
            conn.execute('UPDATE portion_tracking SET course_name = ?, topic = ?, status = ? WHERE id = ?', (course_name, topic, status, portion_id))
        else:
            conn.execute('INSERT INTO portion_tracking (course_name, topic, status) VALUES (?, ?, ?)', (course_name, topic, status))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Portion details updated'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/copo/portions/<int:pid>', methods=['DELETE'])
def delete_portion(pid):
    conn = get_db_connection()
    conn.execute('DELETE FROM portion_tracking WHERE id = ?', (pid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Portion deleted'})

@app.route('/api/copo/outcomes', methods=['GET'])
def get_outcomes():
    conn = get_db_connection()
    co_rows = conn.execute('SELECT * FROM co_mappings').fetchall()
    po_rows = conn.execute('SELECT * FROM po_mappings').fetchall()
    conn.close()
    return jsonify({
        'co': [dict(r) for r in co_rows],
        'po': [dict(r) for r in po_rows]
    })

@app.route('/api/copo/outcomes/update', methods=['POST'])
def update_outcomes():
    data = request.json
    outcome_type = data.get('type') # 'co' or 'po'
    outcome_id = data.get('id')
    value = data.get('current_completion')
    
    if outcome_type not in ['co', 'po'] or not outcome_id:
        return jsonify({'error': 'Invalid parameters'}), 400
        
    conn = get_db_connection()
    table = 'co_mappings' if outcome_type == 'co' else 'po_mappings'
    try:
        conn.execute(f'UPDATE {table} SET current_completion = ? WHERE id = ?', (int(value), int(outcome_id)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Outcome completion updated'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/copo/outcomes', methods=['POST'])
def add_outcome():
    data = request.json
    outcome_type = data.get('type') # 'co' or 'po'
    outcome_code = data.get('outcome_code')
    description = data.get('description')
    course_name = data.get('course_name', '') # optional, only for CO
    target_percentage = data.get('target_percentage', 100)
    
    if not outcome_code or not description:
        return jsonify({'error': 'Outcome code and description are required'}), 400
        
    conn = get_db_connection()
    try:
        if outcome_type == 'co':
            if not course_name:
                conn.close()
                return jsonify({'error': 'Course name is required for Course Outcomes'}), 400
            conn.execute('''
                INSERT INTO co_mappings (course_name, outcome_code, description, target_percentage, current_completion)
                VALUES (?, ?, ?, ?, 0)
            ''', (course_name, outcome_code, description, int(target_percentage)))
        else:
            conn.execute('''
                INSERT INTO po_mappings (outcome_code, description, target_percentage, current_completion)
                VALUES (?, ?, ?, 0)
            ''', (outcome_code, description, int(target_percentage)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'{outcome_type.upper()} mapping created successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/copo/outcomes/<string:otype>/<int:oid>', methods=['DELETE'])
def delete_outcome(otype, oid):
    if otype not in ['co', 'po']:
        return jsonify({'error': 'Invalid outcome type'}), 400
    conn = get_db_connection()
    table = 'co_mappings' if otype == 'co' else 'po_mappings'
    try:
        conn.execute(f'DELETE FROM {table} WHERE id = ?', (oid,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Outcome mapped record removed'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# Reports / Consolidated Audits
@app.route('/api/reports/monthly', methods=['GET'])
def get_monthly_report():
    conn = get_db_connection()
    
    # Create consolidated matrix of student logs
    # Rows: Student Name, USN, Division, Present Count, Absent Count, Attendance Rate %
    rows = conn.execute('''
        SELECT 
            s.id, s.name, s.usn, d.name as division,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent_count
        FROM students s
        LEFT JOIN divisions d ON s.division_id = d.id
        LEFT JOIN attendance_logs a ON s.id = a.student_id
        GROUP BY s.id
    ''').fetchall()
    
    report_data = []
    for r in rows:
        present = r['present_count'] or 0
        absent = r['absent_count'] or 0
        total = present + absent
        rate = 100
        if total > 0:
            rate = round((present / total) * 100, 1)
            
        report_data.append({
            'name': r['name'],
            'usn': r['usn'],
            'division': r['division'],
            'present': present,
            'absent': absent,
            'total_classes': total,
            'attendance_rate': rate
        })
        
    conn.close()
    return jsonify(report_data)

# Run standard Flask loop
if __name__ == '__main__':
    # Make sure templates folder exists
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        
    app.run(debug=True, host='0.0.0.0', port=5000)
