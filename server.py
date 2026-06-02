from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)

data = {}
stats = {}
session_started_at = datetime.now()
active_student = None
logged_students = {}


def empty_stats():
    return {
        "engaged": 0,
        "neutral": 0,
        "disengaged": 0,
        "detected": 0,
        "total": 0,
        "confidence_sum": 0.0,
    }


def outcome_for(score):
    if score >= 75:
        return "Highly Attentive"
    if score >= 50:
        return "Moderately Attentive"
    return "Needs Attention"


def student_report(student_id, details):
    student_stats = stats.get(student_id, empty_stats())
    total = max(student_stats["total"], 1)
    attention_score = round(
        (
            (student_stats["engaged"] * 100)
            + (student_stats["neutral"] * 50)
            + (student_stats["disengaged"] * 0)
        ) / total,
        1,
    )
    average_confidence = round(student_stats["confidence_sum"] / total, 1)

    if student_stats["total"] == 0:
        attention_score = 0
        average_confidence = 0
        final_outcome = "Waiting for Detection"
    else:
        final_outcome = outcome_for(attention_score)

    login_details = logged_students.get(student_id, {})

    return {
        "Student Name": details.get("name", student_id),
        "Roll Number": student_id,
        "Current Status": details.get("status", "disengaged").title(),
        "Current Confidence": f"{float(details.get('confidence', 0)):.1f}%",
        "Detected Frames": student_stats["detected"],
        "Total Checks": student_stats["total"],
        "Engaged Checks": student_stats["engaged"],
        "Neutral Checks": student_stats["neutral"],
        "Disengaged Checks": student_stats["disengaged"],
        "Average Confidence": f"{average_confidence:.1f}%",
        "Attention Score": f"{attention_score:.1f}%",
        "Final Outcome": final_outcome,
        "Last Updated": details.get("updated_at", "-"),
        "Login Status": login_details.get("login_status", "Not Logged In"),
        "Logged In At": login_details.get("logged_in_at", "-"),
        "Logged Out At": login_details.get("logged_out_at", "-"),
    }


@app.route("/update", methods=["POST"])
def update():
    req = request.get_json(force=True) or {}
    student_id = req.get("id", "Student1")
    status = req.get("status", "disengaged")
    confidence = float(req.get("confidence", 0))
    face_detected = bool(req.get("face_detected", status != "disengaged"))
    name = req.get("name", student_id)

    data[student_id] = {
        "name": name,
        "status": status,
        "confidence": confidence,
        "face_detected": face_detected,
        "updated_at": datetime.now().strftime("%H:%M:%S"),
    }

    student_stats = stats.setdefault(student_id, empty_stats())
    student_stats[status] = student_stats.get(status, 0) + 1
    student_stats["total"] += 1
    student_stats["confidence_sum"] += confidence
    if face_detected:
        student_stats["detected"] += 1

    return jsonify({"message": "updated", "student": student_id})


@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(data)


@app.route("/summary", methods=["GET"])
def summary():
    counts = {"engaged": 0, "neutral": 0, "disengaged": 0}
    detected_students = 0

    for details in data.values():
        status = details.get("status", "disengaged")
        if details.get("face_detected", False):
            detected_students += 1
        counts[status] = counts.get(status, 0) + 1

    report_ids = sorted(set(data.keys()) | set(logged_students.keys()))
    reports = []
    for student_id in report_ids:
        details = data.get(student_id, {
            "name": logged_students.get(student_id, {}).get("name", student_id),
            "status": "waiting",
            "confidence": 0,
            "face_detected": False,
            "updated_at": "-",
        })
        reports.append(student_report(student_id, details))

    class_score = 0
    scored_reports = [report for report in reports if report["Total Checks"] > 0]
    if scored_reports:
        class_score = round(
            sum(float(report["Attention Score"].replace("%", "")) for report in scored_reports)
            / len(scored_reports),
            1,
        )

    return jsonify({
        "session_started_at": session_started_at.strftime("%Y-%m-%d %H:%M:%S"),
        "total_students": len(set(data.keys()) | set(logged_students.keys())),
        "detected_students": detected_students,
        "counts": counts,
        "students": data,
        "reports": reports,
        "class_attention_score": class_score,
        "class_outcome": outcome_for(class_score),
        "active_student": active_student,
        "logged_students": logged_students,
    })


@app.route("/reset", methods=["POST"])
def reset():
    global data, stats, session_started_at, logged_students, active_student
    data = {}
    stats = {}
    logged_students = {}
    active_student = None
    session_started_at = datetime.now()
    return jsonify({"message": "class session reset"})


@app.route("/active-student", methods=["GET", "POST", "DELETE"])
def active_student_state():
    global active_student, logged_students

    if request.method == "GET":
        return jsonify({
            "active": active_student is not None,
            "student": active_student,
        })

    if request.method == "DELETE":
        req = request.get_json(silent=True) or {}
        roll_no = req.get("roll_no")
        if roll_no:
            if roll_no in logged_students:
                logged_students[roll_no]["login_status"] = "Logged Out"
                logged_students[roll_no]["logged_out_at"] = datetime.now().strftime("%H:%M:%S")
            if active_student and active_student.get("roll_no") == roll_no:
                active_student = None
        else:
            active_student = None
        return jsonify({"message": "student session cleared"})

    req = request.get_json(force=True) or {}
    roll_no = req.get("roll_no")
    name = req.get("name", roll_no)
    if not roll_no:
        return jsonify({"error": "roll_no is required"}), 400

    active_student = {
        "roll_no": roll_no,
        "name": name,
        "logged_in_at": datetime.now().strftime("%H:%M:%S"),
        "logged_out_at": "-",
        "login_status": "Logged In",
    }
    logged_students[roll_no] = active_student
    return jsonify({"message": "student session activated", "student": active_student})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
