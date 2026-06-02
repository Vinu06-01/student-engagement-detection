import base64
import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.models import load_model

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-deployment"

ADMIN_USER_ID = "admin"
ADMIN_PASSWORD = "admin123"
DB_PATH = Path("engagement.db")
MODEL_PATH = Path("models/engagement_model.h5")
CLASS_PATH = Path("models/class_names.json")

model = load_model(MODEL_PATH, compile=False)
class_names = json.loads(CLASS_PATH.read_text()) if CLASS_PATH.exists() else ["disengaged", "engaged", "neutral"]
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def now():
    return datetime.now().strftime("%H:%M:%S")


def today():
    return datetime.now().strftime("%Y-%m-%d")


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                roll_no TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                branch TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                roll_no TEXT PRIMARY KEY,
                login_status TEXT NOT NULL,
                logged_in_at TEXT NOT NULL,
                logged_out_at TEXT DEFAULT '-',
                current_status TEXT DEFAULT 'Waiting',
                confidence REAL DEFAULT 0,
                detected_frames INTEGER DEFAULT 0,
                total_checks INTEGER DEFAULT 0,
                engaged_checks INTEGER DEFAULT 0,
                neutral_checks INTEGER DEFAULT 0,
                disengaged_checks INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT '-',
                session_date TEXT NOT NULL
            )
        """)


def valid_roll_no(roll_no):
    return bool(re.fullmatch(r"[A-Za-z0-9]{10}", roll_no or ""))


def valid_phone(phone):
    return bool(re.fullmatch(r"\d{10}", phone or ""))


def valid_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""))


def login_required(role=None):
    return "role" in session and (role is None or session["role"] == role)


def score_from_row(row):
    total = row["total_checks"] or 0
    if total == 0:
        return 0
    return round(((row["engaged_checks"] * 100) + (row["neutral_checks"] * 50)) / total, 1)


def outcome_for(score):
    if score >= 75:
        return "Highly Attentive"
    if score >= 50:
        return "Moderately Attentive"
    if score > 0:
        return "Needs Attention"
    return "Waiting for Detection"


def decode_frame(image_data):
    encoded = image_data.split(",", 1)[1] if "," in image_data else image_data
    image_array = np.frombuffer(base64.b64decode(encoded), np.uint8)
    return cv2.imdecode(image_array, cv2.IMREAD_COLOR)


def crop_largest_face(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=6, minSize=(80, 80))
    if len(faces) == 0:
        return None

    frame_h, frame_w = frame.shape[:2]
    frame_area = frame_h * frame_w
    valid_faces = []
    for x, y, w, h in faces:
        area_ratio = (w * h) / frame_area
        aspect_ratio = w / max(h, 1)
        if w >= 90 and h >= 90 and area_ratio >= 0.018 and 0.68 <= aspect_ratio <= 1.35:
            valid_faces.append((x, y, w, h))
    if not valid_faces:
        return None

    x, y, w, h = max(valid_faces, key=lambda face: face[2] * face[3])
    pad_x = int(w * 0.18)
    pad_y = int(h * 0.18)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(frame_w, x + w + pad_x)
    y2 = min(frame_h, y + h + pad_y)
    return frame[y1:y2, x1:x2]


def predict_status(frame):
    face = crop_largest_face(frame)
    if face is None:
        return "disengaged", 0, False
    image = cv2.resize(face, (224, 224))
    image = preprocess_input(image.astype(np.float32))
    image = np.expand_dims(image, axis=0)
    prediction = model.predict(image, verbose=0)[0]
    index = int(np.argmax(prediction))
    return class_names[index], round(float(prediction[index] * 100), 1), True


def activate_student(roll_no):
    with db() as conn:
        conn.execute("""
            INSERT INTO sessions (roll_no, login_status, logged_in_at, logged_out_at, session_date)
            VALUES (?, 'Logged In', ?, '-', ?)
            ON CONFLICT(roll_no) DO UPDATE SET
                login_status='Logged In',
                logged_in_at=excluded.logged_in_at,
                logged_out_at='-'
        """, (roll_no, now(), today()))


def logout_student(roll_no):
    with db() as conn:
        conn.execute("UPDATE sessions SET login_status='Logged Out', logged_out_at=? WHERE roll_no=?", (now(), roll_no))


def update_prediction(roll_no, status, confidence, detected):
    column = f"{status}_checks"
    if column not in {"engaged_checks", "neutral_checks", "disengaged_checks"}:
        column = "disengaged_checks"
        status = "disengaged"
    with db() as conn:
        conn.execute(f"""
            UPDATE sessions
            SET current_status=?,
                confidence=?,
                detected_frames=detected_frames + ?,
                total_checks=total_checks + 1,
                {column}={column} + 1,
                last_updated=?
            WHERE roll_no=?
        """, (status.title(), confidence, 1 if detected else 0, now(), roll_no))


@app.route("/")
def index():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    if session.get("role") == "student":
        return redirect(url_for("student_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        role = request.form.get("role")
        if role == "admin":
            if request.form.get("user_id") == ADMIN_USER_ID and request.form.get("password") == ADMIN_PASSWORD:
                session.clear()
                session["role"] = "admin"
                return redirect(url_for("admin_dashboard"))
            error = "Invalid admin user ID or password."
        else:
            roll_no = request.form.get("roll_no", "").upper()
            password = request.form.get("password", "")
            with db() as conn:
                student = conn.execute("SELECT * FROM students WHERE roll_no=?", (roll_no,)).fetchone()
            if student and student["password_hash"] == hash_password(password):
                session.clear()
                session["role"] = "student"
                session["roll_no"] = roll_no
                activate_student(roll_no)
                return redirect(url_for("student_dashboard"))
            error = "Invalid roll number or password."
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    success = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").upper()
        branch = request.form.get("branch", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not all([name, roll_no, branch, phone, email, password, confirm]):
            error = "Please fill all details."
        elif not valid_roll_no(roll_no):
            error = "Roll number must be exactly 10 alphanumeric characters."
        elif not valid_phone(phone):
            error = "Phone number must be exactly 10 digits."
        elif not valid_email(email):
            error = "Enter a valid email ID."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            try:
                with db() as conn:
                    conn.execute("""
                        INSERT INTO students (roll_no, name, branch, phone, email, password_hash)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (roll_no, name, branch, phone, email, hash_password(password)))
                success = "Student account created. You can login now."
            except sqlite3.IntegrityError:
                error = "A student with this roll number already exists."
    return render_template("register.html", error=error, success=success)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = None
    success = None
    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").upper()
        phone = request.form.get("phone", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        with db() as conn:
            student = conn.execute("SELECT * FROM students WHERE roll_no=? AND phone=?", (roll_no, phone)).fetchone()
            if not student:
                error = "Roll number and phone number do not match."
            elif not password or password != confirm:
                error = "New passwords do not match."
            else:
                conn.execute("UPDATE students SET password_hash=? WHERE roll_no=?", (hash_password(password), roll_no))
                success = "Password reset successful. Login with your new password."
    return render_template("forgot.html", error=error, success=success)


@app.route("/student")
def student_dashboard():
    if not login_required("student"):
        return redirect(url_for("login"))
    with db() as conn:
        student = conn.execute("SELECT * FROM students WHERE roll_no=?", (session["roll_no"],)).fetchone()
    return render_template("student.html", student=student)


@app.route("/admin")
def admin_dashboard():
    if not login_required("admin"):
        return redirect(url_for("login"))
    return render_template("admin.html")


@app.route("/api/predict", methods=["POST"])
def api_predict():
    if not login_required("student"):
        return jsonify({"error": "not logged in"}), 401
    frame = decode_frame(request.get_json(force=True).get("image", ""))
    status, confidence, detected = predict_status(frame)
    update_prediction(session["roll_no"], status, confidence, detected)
    return jsonify({"status": status.title(), "confidence": confidence, "face_detected": detected})


@app.route("/api/student-status")
def api_student_status():
    if not login_required("student"):
        return jsonify({"error": "not logged in"}), 401
    with db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE roll_no=?", (session["roll_no"],)).fetchone()
    score = score_from_row(row) if row else 0
    return jsonify({
        "current_status": row["current_status"] if row else "Waiting",
        "confidence": row["confidence"] if row else 0,
        "attention_score": score,
        "final_outcome": outcome_for(score),
        "last_updated": row["last_updated"] if row else "-",
    })


@app.route("/api/admin-data")
def api_admin_data():
    if not login_required("admin"):
        return jsonify({"error": "not logged in"}), 401
    with db() as conn:
        rows = conn.execute("""
            SELECT s.name, s.roll_no, s.branch, s.phone, s.email,
                   COALESCE(se.login_status, 'Not Logged In') AS login_status,
                   COALESCE(se.current_status, 'Waiting') AS current_status,
                   COALESCE(se.confidence, 0) AS confidence,
                   COALESCE(se.detected_frames, 0) AS detected_frames,
                   COALESCE(se.total_checks, 0) AS total_checks,
                   COALESCE(se.engaged_checks, 0) AS engaged_checks,
                   COALESCE(se.neutral_checks, 0) AS neutral_checks,
                   COALESCE(se.disengaged_checks, 0) AS disengaged_checks,
                   COALESCE(se.last_updated, '-') AS last_updated,
                   COALESCE(se.logged_in_at, '-') AS logged_in_at,
                   COALESCE(se.logged_out_at, '-') AS logged_out_at
            FROM students s
            LEFT JOIN sessions se ON s.roll_no = se.roll_no
            ORDER BY s.roll_no
        """).fetchall()
    students = []
    counts = {"engaged": 0, "neutral": 0, "disengaged": 0}
    for row in rows:
        score = score_from_row(row)
        status_key = row["current_status"].lower()
        if status_key in counts:
            counts[status_key] += 1
        students.append({
            "student_name": row["name"],
            "roll_number": row["roll_no"],
            "branch": row["branch"],
            "phone": row["phone"],
            "email": row["email"],
            "login_status": row["login_status"],
            "current_status": row["current_status"],
            "confidence": f"{float(row['confidence']):.1f}%",
            "detected_frames": row["detected_frames"],
            "total_checks": row["total_checks"],
            "engaged_checks": row["engaged_checks"],
            "neutral_checks": row["neutral_checks"],
            "disengaged_checks": row["disengaged_checks"],
            "attention_score": f"{score:.1f}%",
            "final_outcome": outcome_for(score),
            "last_updated": row["last_updated"],
            "logged_in_at": row["logged_in_at"],
            "logged_out_at": row["logged_out_at"],
        })
    scored = [student for student in students if student["total_checks"] > 0]
    class_score = round(sum(float(s["attention_score"].replace("%", "")) for s in scored) / len(scored), 1) if scored else 0
    return jsonify({
        "students": students,
        "counts": counts,
        "total_students": len(students),
        "class_score": class_score,
        "class_outcome": outcome_for(class_score),
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    if not login_required("admin"):
        return jsonify({"error": "not logged in"}), 401
    with db() as conn:
        conn.execute("DELETE FROM sessions")
    return jsonify({"message": "class session reset"})


@app.route("/logout")
def logout():
    if session.get("role") == "student":
        logout_student(session["roll_no"])
    session.clear()
    return redirect(url_for("login"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
