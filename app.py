from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'


# ---------------- Database Connection ----------------

def get_db_connection():
    conn = sqlite3.connect('courses.db')
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- Database Initialization ----------------

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration TEXT NOT NULL,
            company_name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course_id INTEGER,
            name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            year TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    conn.commit()
    conn.close()


# ---------------- Decorators for Access Control ----------------

def student_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'student_id' not in session:
            flash("Student access required. Please login.")
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Admin access required. Please login.")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------- Routes ----------------

@app.route('/')
def landing():
    return render_template('landing.html')


# ----- Student Routes -----

@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if len(password) < 8:
            flash("Password must be at least 8 characters long")
            return redirect(url_for('student_register'))

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO students (name, email, password) VALUES (?, ?, ?)",
                           (name, email, generate_password_hash(password)))
            conn.commit()
            flash("Registration successful. Please login.")
            return redirect(url_for('student_login'))
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return redirect(url_for('student_register'))
        finally:
            conn.close()

    return render_template('student/register.html')


@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE email = ?", (email,))
        student = cursor.fetchone()
        conn.close()

        if student and check_password_hash(student['password'], password):
            session['student_id'] = student['id']
            return redirect(url_for('student_home'))
        else:
            flash("Invalid email or password.")
            return redirect(url_for('student_login'))

    return render_template('student/login.html')


@app.route('/student/home')
@student_login_required
def student_home():
    conn = get_db_connection()
    courses = conn.execute("SELECT * FROM courses").fetchall()
    conn.close()

    return render_template('student/home.html', courses=courses)


@app.route('/student/enroll/<int:course_id>', methods=['GET', 'POST'])
@student_login_required
def enroll(course_id):
    conn = get_db_connection()
    course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        roll_number = request.form['roll_number']
        year = request.form['year']

        conn.execute(
            "INSERT INTO enrollments (student_id, course_id, name, roll_number, year) VALUES (?, ?, ?, ?, ?)",
            (session['student_id'], course_id, name, roll_number, year)
        )
        conn.commit()
        conn.close()
        flash("Enrolled successfully.")
        return redirect(url_for('student_home'))

    conn.close()
    return render_template('student/enroll.html', course=course)


@app.route('/student/profile')
@student_login_required
def student_profile():
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (session['student_id'],)).fetchone()
    enrollments = conn.execute('''
        SELECT courses.name AS course_name, courses.duration, courses.company_name,
               enrollments.name AS student_name, enrollments.roll_number, enrollments.year
        FROM enrollments
        JOIN courses ON enrollments.course_id = courses.id
        WHERE enrollments.student_id = ?
    ''', (session['student_id'],)).fetchall()
    conn.close()

    return render_template('student/profile.html', student=student, enrollments=enrollments)


# ----- Admin Routes -----

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        company_name = request.form['company_name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO admins (company_name, email, password) VALUES (?, ?, ?)",
                           (company_name, email, generate_password_hash(password)))
            conn.commit()
            flash("Admin registration successful. Please login.")
            return redirect(url_for('admin_login'))
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return redirect(url_for('admin_register'))
        finally:
            conn.close()

    return render_template('admin/register.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admins WHERE email = ?", (email,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin['password'], password):
            session['admin_id'] = admin['id']
            session['company_name'] = admin['company_name']
            return redirect(url_for('add_course'))
        else:
            flash("Invalid email or password.")
            return redirect(url_for('admin_login'))

    return render_template('admin/login.html')


@app.route('/admin/add_course', methods=['GET', 'POST'])
@admin_login_required
def add_course():
    if request.method == 'POST':
        name = request.form['name']
        duration = request.form['duration']
        company_name = session['company_name']

        conn = get_db_connection()
        conn.execute("INSERT INTO courses (name, duration, company_name) VALUES (?, ?, ?)",
                     (name, duration, company_name))
        conn.commit()
        conn.close()

        flash("Course added successfully.")
        return redirect(url_for('add_course'))

    return render_template('admin/add_course.html')


@app.route('/admin/course_stats', methods=['GET', 'POST'])
@admin_login_required
def course_stats():
    conn = get_db_connection()
    company_name = session.get('company_name')

    # Get filters from form
    selected_course = request.form.get('course') or None
    selected_year = request.form.get('year') or None

    # Build query dynamically based on filters
    query = '''
        SELECT courses.name, enrollments.year, COUNT(enrollments.id) AS enroll_count
        FROM courses
        LEFT JOIN enrollments ON courses.id = enrollments.course_id
        WHERE courses.company_name = ?
    '''
    params = [company_name]

    if selected_course:
        query += " AND courses.name = ?"
        params.append(selected_course)
    if selected_year:
        query += " AND enrollments.year = ?"
        params.append(selected_year)

    query += " GROUP BY courses.name, enrollments.year"

    data = conn.execute(query, params).fetchall()

    # For dropdowns
    all_courses = conn.execute("SELECT DISTINCT name FROM courses WHERE company_name = ?", (company_name,)).fetchall()
    all_years = conn.execute('''
        SELECT DISTINCT year FROM enrollments
        JOIN courses ON enrollments.course_id = courses.id
        WHERE courses.company_name = ?
    ''', (company_name,)).fetchall()

    conn.close()

    # Format for Chart.js
    labels = [f"{row['name']} ({row['year']})" for row in data]
    enroll_counts = [row['enroll_count'] for row in data]

    return render_template(
        'admin/course_stats.html',
        labels=labels,
        data=enroll_counts,
        all_courses=all_courses,
        all_years=all_years,
        selected_course=selected_course,
        selected_year=selected_year
    )
@app.route('/admin/manage_courses', methods=['GET', 'POST'])
@admin_login_required
def manage_courses():
    conn = get_db_connection()
    company_name = session['company_name']

    # Handle delete request
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        conn.execute("DELETE FROM courses WHERE id = ? AND company_name = ?", (course_id, company_name))
        conn.commit()
        flash("Course deleted successfully.")

    # Fetch all courses added by this company
    courses = conn.execute("SELECT * FROM courses WHERE company_name = ?", (company_name,)).fetchall()
    conn.close()

    return render_template('admin/manage_courses.html', courses=courses)



# ---------------- Logout ----------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))


# ---------------- Run the App ----------------

if __name__ == '__main__':
    init_db()
    app.run(debug=True)