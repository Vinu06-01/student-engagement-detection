import time
import hashlib
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

API_URL = "http://127.0.0.1:5000/summary"
RESET_URL = "http://127.0.0.1:5000/reset"
ACTIVE_STUDENT_URL = "http://127.0.0.1:5000/active-student"
USER_STORE = Path("student_users.json")
ADMIN_USER_ID = "admin"
ADMIN_PASSWORD = "admin123"

st.set_page_config(
    page_title="AI Student Engagement Dashboard",
    page_icon="AI",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #0f172a;
        --muted: #64748b;
        --panel: rgba(255, 255, 255, 0.96);
        --line: rgba(15, 23, 42, 0.12);
        --soft: #f8fafc;
        --brand: #2563eb;
        --brand-dark: #1d4ed8;
        --green: #16a34a;
        --yellow: #d6a100;
        --red: #dc2626;
    }

    .stApp {
        background:
            radial-gradient(circle at 15% 12%, rgba(37, 99, 235, 0.14), transparent 28%),
            radial-gradient(circle at 86% 8%, rgba(20, 184, 166, 0.12), transparent 26%),
            linear-gradient(135deg, #f8fafc 0%, #eef6ff 52%, #f7fff9 100%);
        color: var(--ink);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1280px;
    }

    .hero {
        padding: 28px 32px;
        border: 1px solid var(--line);
        border-radius: 14px;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.98), rgba(239,246,255,0.92));
        box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
        margin-bottom: 22px;
    }

    .hero h1 {
        font-size: 38px;
        line-height: 1.1;
        margin: 0 0 10px;
        letter-spacing: 0;
        color: var(--ink);
    }

    .hero p {
        margin: 0;
        color: var(--muted);
        font-size: 17px;
        max-width: 980px;
    }

    .feature-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 18px 0 8px;
    }

    .feature-pill {
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 12px 14px;
        background: rgba(255,255,255,0.74);
        color: var(--ink);
        font-weight: 700;
    }

    .metric-card {
        padding: 20px;
        border-radius: 12px;
        border: 1px solid var(--line);
        background: var(--panel);
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.07);
        min-height: 124px;
    }

    .metric-label {
        color: var(--muted);
        font-size: 13px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .metric-value {
        color: var(--ink);
        font-size: 34px;
        font-weight: 900;
        margin-top: 8px;
    }

    .section-title {
        font-size: 21px;
        font-weight: 900;
        margin: 18px 0 8px;
        color: var(--ink);
    }

    .outcome-panel {
        padding: 22px;
        border-radius: 12px;
        border: 1px solid var(--line);
        background: rgba(255,255,255,0.84);
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
        margin-top: 18px;
    }

    .stButton > button {
        background: var(--brand) !important;
        color: #ffffff !important;
        border: 0 !important;
        border-radius: 10px !important;
        min-height: 44px !important;
        font-weight: 900 !important;
        box-shadow: 0 10px 22px rgba(37, 99, 235, 0.22) !important;
    }

    .stButton > button:hover {
        background: var(--brand-dark) !important;
        color: #ffffff !important;
        border: 0 !important;
    }

    .auth-card {
        max-width: 920px;
        margin: 18px auto 16px;
        padding: 28px 30px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background:
            linear-gradient(135deg, rgba(255,255,255,0.98), rgba(239,246,255,0.95));
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.09);
    }

    .auth-card h2 {
        margin: 0 0 8px;
        color: var(--ink);
        letter-spacing: 0;
        font-size: 30px;
    }

    .auth-card p {
        margin: 0;
        color: var(--muted);
        font-size: 15px;
    }

    .auth-shell {
        max-width: 920px;
        margin: 0 auto;
        padding: 22px;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.94);
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
    }

    .auth-note {
        padding: 12px 14px;
        border: 1px solid rgba(37, 99, 235, 0.18);
        border-radius: 10px;
        background: #eff6ff;
        color: #1e40af;
        font-weight: 700;
        margin-bottom: 14px;
    }

    .role-badge {
        display: inline-block;
        padding: 7px 11px;
        border-radius: 999px;
        background: #dbeafe;
        color: #1e40af;
        font-size: 12px;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 10px;
    }

    div[data-baseweb="input"] {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
    }

    div[data-baseweb="input"]:focus-within {
        border-color: var(--brand) !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.16) !important;
    }

    div[data-baseweb="input"] input {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        background: #ffffff !important;
        font-weight: 650 !important;
    }

    .stTextInput label,
    .stRadio label,
    .stSlider label {
        color: var(--ink) !important;
        font-weight: 800 !important;
    }

    .stRadio div[role="radiogroup"] label,
    .stRadio div[role="radiogroup"] label span,
    .stRadio div[role="radiogroup"] p {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        font-weight: 800 !important;
    }

    .stRadio div[role="radiogroup"] label[data-baseweb="radio"] {
        background: rgba(255, 255, 255, 0.74);
        border: 1px solid #dbeafe;
        border-radius: 999px;
        padding: 8px 12px;
        margin-right: 8px;
    }

    .stTabs [data-baseweb="tab-list"] {
        max-width: 920px;
        margin: 0 auto;
        gap: 8px;
        background: rgba(255,255,255,0.74);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 6px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 9px;
        padding: 10px 16px;
        color: var(--muted);
        font-weight: 900;
    }

    .stTabs [aria-selected="true"] {
        background: #ffffff;
        color: var(--brand);
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
    }

    [data-testid="stSidebar"] {
        background: #0f172a;
    }

    [data-testid="stSidebar"] * {
        color: #e2e8f0;
    }

    [data-testid="stSidebar"] .stButton > button {
        background: #2563eb !important;
    }

    @media (max-width: 900px) {
        .feature-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .hero h1 {
            font-size: 30px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_users():
    if not USER_STORE.exists():
        return {}
    try:
        return json.loads(USER_STORE.read_text())
    except json.JSONDecodeError:
        return {}


def save_users(users):
    USER_STORE.write_text(json.dumps(users, indent=2))


def valid_roll_no(roll_no):
    return bool(re.fullmatch(r"[A-Za-z0-9]{10}", roll_no or ""))


def valid_phone(phone):
    return bool(re.fullmatch(r"\d{10}", phone or ""))


def valid_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""))


def init_session():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("student_profile", None)


def activate_student_camera(student):
    try:
        requests.post(
            ACTIVE_STUDENT_URL,
            json={"roll_no": student["roll_no"], "name": student["name"]},
            timeout=2,
        )
    except requests.RequestException:
        pass


def deactivate_student_camera():
    try:
        payload = {}
        if st.session_state.user_id:
            payload["roll_no"] = st.session_state.user_id
        requests.delete(ACTIVE_STUDENT_URL, json=payload, timeout=2)
    except requests.RequestException:
        pass


def do_logout():
    if st.session_state.role == "student":
        deactivate_student_camera()
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.student_profile = None
    st.rerun()


def render_auth_page():
    st.markdown(
        """
        <div class="auth-card">
            <span class="role-badge">Secure Access</span>
            <h2>Login to Student Engagement System</h2>
            <p>Separate access for students and administrators with live attentiveness monitoring after login.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_tab, create_tab, forgot_tab = st.tabs([
        "Login",
        "Create Student User",
        "Forgot Student Password",
    ])

    with login_tab:
        left, right = st.columns([0.9, 1.1], vertical_alignment="center")
        with left:
            st.markdown(
                """
                <div class="auth-shell">
                    <span class="role-badge">Access Portal</span>
                    <h3 style="margin:0 0 8px;color:#0f172a;">Choose your workspace</h3>
                    <p style="margin:0;color:#64748b;">Students can view their registered profile and monitoring outcome. Admins manage the class session and dashboard.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            role = st.radio("Login as", ["Student", "Admin"], horizontal=True)
            if role == "Admin":
                st.markdown('<div class="auth-note">Admin credentials are fixed for this project demo.</div>', unsafe_allow_html=True)
                user_id = st.text_input("Admin User ID")
                password = st.text_input("Admin Password", type="password")
                if st.button("Login as Admin", use_container_width=True):
                    if user_id == ADMIN_USER_ID and password == ADMIN_PASSWORD:
                        st.session_state.logged_in = True
                        st.session_state.role = "admin"
                        st.session_state.user_id = ADMIN_USER_ID
                        st.success("Admin login successful.")
                        st.rerun()
                    else:
                        st.error("Invalid admin user ID or password.")
            else:
                st.markdown('<div class="auth-note">Use the roll number created during student registration.</div>', unsafe_allow_html=True)
                roll_no = st.text_input("Roll Number", key="student_login_roll").upper()
                password = st.text_input("Student Password", type="password", key="student_login_pass")
                if st.button("Login as Student", use_container_width=True):
                    users = load_users()
                    student = users.get(roll_no)
                    if student and student["password_hash"] == hash_password(password):
                        activate_student_camera(student)
                        st.session_state.logged_in = True
                        st.session_state.role = "student"
                        st.session_state.user_id = roll_no
                        st.session_state.student_profile = student
                        st.success("Student login successful.")
                        st.rerun()
                    else:
                        st.error("Invalid roll number or password.")

    with create_tab:
        st.markdown('<div class="auth-note">Create user option is available only for students.</div>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            name = st.text_input("Student Name")
            roll_no = st.text_input("Roll Number (10 alphanumeric characters)").upper()
            branch = st.text_input("Branch")
            phone = st.text_input("Phone Number (10 digits)")
        with col_b:
            email = st.text_input("Email ID")
            password = st.text_input("Create Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            st.caption("Roll number accepts letters and numbers, exactly 10 characters.")

        if st.button("Create Student Account", use_container_width=True):
            users = load_users()
            if not all([name, roll_no, branch, phone, email, password, confirm_password]):
                st.error("Please fill all student details.")
            elif not valid_roll_no(roll_no):
                st.error("Roll number must be exactly 10 alphanumeric characters.")
            elif not valid_phone(phone):
                st.error("Phone number must be exactly 10 digits.")
            elif not valid_email(email):
                st.error("Enter a valid email ID.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            elif roll_no in users:
                st.error("A student account with this roll number already exists.")
            else:
                users[roll_no] = {
                    "name": name.strip(),
                    "roll_no": roll_no,
                    "branch": branch.strip(),
                    "phone": phone,
                    "email": email.strip(),
                    "password_hash": hash_password(password),
                }
                save_users(users)
                st.success("Student account created. You can now login from the Login tab.")

    with forgot_tab:
        st.markdown('<div class="auth-note">Verify your roll number and registered phone number to reset the student password.</div>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            roll_no = st.text_input("Registered Roll Number", key="forgot_roll").upper()
            phone = st.text_input("Registered Phone Number", key="forgot_phone")
        with col_b:
            new_password = st.text_input("New Password", type="password", key="forgot_new")
            confirm_password = st.text_input("Confirm New Password", type="password", key="forgot_confirm")

        if st.button("Reset Student Password", use_container_width=True):
            users = load_users()
            student = users.get(roll_no)
            if not student or student.get("phone") != phone:
                st.error("Roll number and phone number do not match our records.")
            elif not new_password:
                st.error("Enter a new password.")
            elif new_password != confirm_password:
                st.error("New passwords do not match.")
            else:
                student["password_hash"] = hash_password(new_password)
                users[roll_no] = student
                save_users(users)
                st.success("Password reset successful. Login with your new password.")


def fetch_summary():
    try:
        response = requests.get(API_URL, timeout=2)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as exc:
        return {
            "total_students": 0,
            "detected_students": 0,
            "counts": {"engaged": 0, "neutral": 0, "disengaged": 0},
            "reports": [],
            "class_attention_score": 0,
            "class_outcome": "Waiting for Data",
        }, str(exc)


def metric_card(label, value):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def enrich_reports_with_student_details(reports):
    users = load_users()
    enriched = []
    for report in reports:
        row = dict(report)
        student = users.get(row.get("Roll Number"), {})
        row["Branch"] = student.get("branch", "-")
        row["Phone"] = student.get("phone", "-")
        row["Email"] = student.get("email", "-")
        enriched.append(row)
    return enriched


init_session()
if not st.session_state.logged_in:
    render_auth_page()
    st.stop()

if st.session_state.role == "admin":
    dashboard_badge = "Admin Dashboard"
    dashboard_title = "Classroom Engagement Command Center"
    dashboard_copy = (
        "Monitor live student engagement, reset class sessions, and review the final attentiveness outcome."
    )
    feature_items = [
        "Live Webcam Detection",
        "Class Session Control",
        "Attention Analytics",
        "After-Class Outcome",
    ]
else:
    dashboard_badge = "Student Dashboard"
    dashboard_title = "Student Engagement Profile"
    dashboard_copy = (
        "View your registered profile and the live attentiveness report generated during the class session."
    )
    feature_items = [
        "Student Profile",
        "Live Status",
        "Attention Score",
        "Final Outcome",
    ]

st.markdown(
    f"""
    <div class="hero">
        <span class="role-badge">{dashboard_badge}</span>
        <h1>{dashboard_title}</h1>
        <p>{dashboard_copy}</p>
        <div class="feature-strip">
            <div class="feature-pill">{feature_items[0]}</div>
            <div class="feature-pill">{feature_items[1]}</div>
            <div class="feature-pill">{feature_items[2]}</div>
            <div class="feature-pill">{feature_items[3]}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

refresh_seconds = st.sidebar.slider("Refresh interval", 1, 10, 2)
st.sidebar.success(f"Logged in as {st.session_state.role.title()}")
if st.session_state.role == "student" and st.session_state.student_profile:
    profile = st.session_state.student_profile
    st.sidebar.markdown("### Student Profile")
    st.sidebar.write(f"Name: {profile['name']}")
    st.sidebar.write(f"Roll No: {profile['roll_no']}")
    st.sidebar.write(f"Branch: {profile['branch']}")

if st.session_state.role == "admin" and st.sidebar.button("Start New Class / Reset Report", use_container_width=True):
    try:
        requests.post(RESET_URL, timeout=2)
        st.rerun()
    except requests.RequestException:
        st.sidebar.error("Server is not responding.")

st.sidebar.markdown("### How to Use")
st.sidebar.write("Run `python realtime_detection.py` during class. The dashboard updates automatically and builds the attentiveness report.")
if st.sidebar.button("Logout", use_container_width=True):
    do_logout()

summary, error = fetch_summary()
counts = summary.get("counts", {})
reports = summary.get("reports", [])
if st.session_state.role == "student":
    reports = [report for report in reports if report.get("Roll Number") == st.session_state.user_id]
else:
    reports = enrich_reports_with_student_details(reports)

if error:
    st.warning("Server is not responding yet. Start `server.py`, then run the detector.")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    metric_card("Detected", summary.get("detected_students", 0))
with col2:
    metric_card("Engaged", counts.get("engaged", 0))
with col3:
    metric_card("Neutral", counts.get("neutral", 0))
with col4:
    metric_card("Disengaged", counts.get("disengaged", 0))
with col5:
    metric_card("Class Score", f"{summary.get('class_attention_score', 0):.1f}%")

if st.session_state.role == "admin":
    st.markdown('<div class="section-title">All Logged-In Students Data</div>', unsafe_allow_html=True)
    if not reports:
        st.info("No student is logged in yet.")
    else:
        admin_columns = [
            "Student Name",
            "Roll Number",
            "Branch",
            "Phone",
            "Email",
            "Login Status",
            "Current Status",
            "Current Confidence",
            "Detected Frames",
            "Total Checks",
            "Engaged Checks",
            "Neutral Checks",
            "Disengaged Checks",
            "Attention Score",
            "Final Outcome",
            "Last Updated",
            "Logged In At",
            "Logged Out At",
        ]
        admin_df = pd.DataFrame(reports)[admin_columns]
        st.dataframe(
            admin_df,
            use_container_width=True,
            hide_index=True,
            height=min(520, 90 + (len(admin_df) * 38)),
        )

chart_col, live_col = st.columns([0.85, 1.15])
with chart_col:
    st.markdown('<div class="section-title">Live Status Distribution</div>', unsafe_allow_html=True)
    chart_values = [
        counts.get("engaged", 0),
        counts.get("neutral", 0),
        counts.get("disengaged", 0),
    ]
    chart_labels = ["Engaged", "Neutral", "Disengaged"]
    chart_colors = ["#16a34a", "#d6a100", "#dc2626"]

    if sum(chart_values) == 0:
        st.info("Waiting for live engagement data...")
    else:
        fig, ax = plt.subplots(figsize=(5.6, 5.6))
        fig.patch.set_alpha(0)
        ax.pie(
            chart_values,
            labels=chart_labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=chart_colors,
            wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 3},
            textprops={"color": "#172033", "fontsize": 11, "fontweight": "bold"},
        )
        ax.axis("equal")
        st.pyplot(fig, use_container_width=True)

if st.session_state.role == "student":
    with live_col:
        st.markdown('<div class="section-title">My Live Status</div>', unsafe_allow_html=True)
        if not reports:
            st.info("No student detected yet. Start `python realtime_detection.py`.")
        else:
            live_columns = [
                "Student Name",
                "Roll Number",
                "Current Status",
                "Current Confidence",
                "Attention Score",
                "Final Outcome",
                "Last Updated",
            ]
            live_df = pd.DataFrame(reports)[live_columns]
            st.dataframe(live_df, use_container_width=True, hide_index=True)

st.markdown(
    f"""
    <div class="outcome-panel">
        <div class="section-title" style="margin-top:0;">After-Class Attentiveness Outcome</div>
        <strong>Session started:</strong> {summary.get("session_started_at", "-")}<br>
        <strong>Class outcome:</strong> {summary.get("class_outcome", "Waiting for Data")}<br>
        <strong>Formula:</strong> Engaged = 100 points, Neutral = 50 points, Disengaged = 0 points across all continuous checks.
    </div>
    """,
    unsafe_allow_html=True,
)

if reports:
    report_df = pd.DataFrame(reports)
    st.dataframe(report_df, use_container_width=True, hide_index=True)

time.sleep(refresh_seconds)
st.rerun()
