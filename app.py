from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-deployment"
DB_PATH = Path(__file__).with_name("database.db")

# Demo login: username = admin, password = admin123
# Change these before publishing the website.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_no TEXT NOT NULL UNIQUE,
                class_name TEXT NOT NULL,
                academic_year TEXT NOT NULL DEFAULT '2026-2027'
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS marks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
                max_marks REAL NOT NULL CHECK(max_marks > 0 AND marks_obtained <= max_marks),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE(student_id, subject)
            )
        """)

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped

def grade_for(percentage):
    if percentage >= 90: return "A+"
    if percentage >= 80: return "A"
    if percentage >= 70: return "B"
    if percentage >= 60: return "C"
    if percentage >= 50: return "D"
    if percentage >= 40: return "E"
    return "F"

def result_data(student):
    with get_db() as db:
        marks = db.execute(
            "SELECT subject, marks_obtained, max_marks FROM marks WHERE student_id=? ORDER BY subject",
            (student["id"],)
        ).fetchall()
    total = sum(m["marks_obtained"] for m in marks)
    maximum = sum(m["max_marks"] for m in marks)
    percentage = (total / maximum * 100) if maximum else 0
    return {
        "student": student, "marks": marks, "total": total, "maximum": maximum,
        "percentage": percentage, "grade": grade_for(percentage) if marks else "—",
        "status": "PASS" if marks and percentage >= 40 and all(m["marks_obtained"] >= 0.35*m["max_marks"] for m in marks) else ("—" if not marks else "NEEDS IMPROVEMENT")
    }

@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip()
        with get_db() as db:
            student = db.execute("SELECT * FROM students WHERE roll_no=?", (roll_no,)).fetchone()
        if student:
            result = result_data(student)
        else:
            flash("No student found with that roll number. Please check and try again.", "error")
    return render_template("index.html", result=result)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("Welcome to the admin dashboard!", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect username or password.", "error")
    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def dashboard():
    with get_db() as db:
        students = db.execute("SELECT * FROM students ORDER BY name").fetchall()
        student_count = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        marks_count = db.execute("SELECT COUNT(*) FROM marks").fetchone()[0]
    return render_template("admin.html", students=students, student_count=student_count, marks_count=marks_count)

@app.route("/admin/student/add", methods=["GET", "POST"])
@admin_required
def add_student():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        class_name = request.form.get("class_name", "").strip()
        academic_year = request.form.get("academic_year", "2026-2027").strip()
        if not all([name, roll_no, class_name, academic_year]):
            flash("Please fill in all fields.", "error")
        else:
            try:
                with get_db() as db:
                    db.execute("INSERT INTO students(name, roll_no, class_name, academic_year) VALUES(?,?,?,?)",
                               (name, roll_no, class_name, academic_year))
                flash("Student added successfully.", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("That roll number already exists. Use a unique roll number.", "error")
    return render_template("student_form.html", student=None)

@app.route("/admin/student/<int:student_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_student(student_id):
    with get_db() as db:
        student = db.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        values = (request.form.get("name","").strip(), request.form.get("roll_no","").strip(),
                  request.form.get("class_name","").strip(), request.form.get("academic_year","").strip(), student_id)
        try:
            with get_db() as db:
                db.execute("UPDATE students SET name=?, roll_no=?, class_name=?, academic_year=? WHERE id=?", values)
            flash("Student details updated.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Roll number already belongs to another student.", "error")
    return render_template("student_form.html", student=student)

@app.route("/admin/student/<int:student_id>/marks", methods=["GET", "POST"])
@admin_required
def manage_marks(student_id):
    with get_db() as db:
        student = db.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        existing = db.execute("SELECT * FROM marks WHERE student_id=? ORDER BY subject", (student_id,)).fetchall()
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        subjects = request.form.getlist("subject[]")
        obtained = request.form.getlist("obtained[]")
        maximum = request.form.getlist("maximum[]")
        clean_rows = []
        try:
            for subject, score, max_score in zip(subjects, obtained, maximum):
                subject = subject.strip()
                if not subject and not score and not max_score:
                    continue
                score, max_score = float(score), float(max_score)
                if not subject or max_score <= 0 or score < 0 or score > max_score:
                    raise ValueError
                clean_rows.append((subject, score, max_score))
            with get_db() as db:
                db.execute("DELETE FROM marks WHERE student_id=?", (student_id,))
                for subject, score, max_score in clean_rows:
                    db.execute("INSERT INTO marks(student_id,subject,marks_obtained,max_marks) VALUES(?,?,?,?)",
                               (student_id, subject, score, max_score))
            flash("Marks saved successfully.", "success")
            return redirect(url_for("dashboard"))
        except (ValueError, sqlite3.IntegrityError):
            flash("Check marks: subject names must be unique, and obtained marks must be between 0 and maximum marks.", "error")
    return render_template("marks_form.html", student=student, marks=existing)

@app.route("/admin/student/<int:student_id>/delete", methods=["POST"])
@admin_required
def delete_student(student_id):
    with get_db() as db:
        db.execute("DELETE FROM marks WHERE student_id=?", (student_id,))
        db.execute("DELETE FROM students WHERE id=?", (student_id,))
    flash("Student deleted.", "success")
    return redirect(url_for("dashboard"))

@app.route("/result/<roll_no>")
def result_by_roll(roll_no):
    with get_db() as db:
        student = db.execute("SELECT * FROM students WHERE roll_no=?", (roll_no,)).fetchone()
    if not student:
        return render_template("not_found.html", roll_no=roll_no), 404
    return render_template("result_page.html", result=result_data(student))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
