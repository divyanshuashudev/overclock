"""
Student Attendance & Performance Insights Dashboard (Problem Statement SW-12)

This file (`app.py`) builds the visual webpage that users interact with.

All login and data work is kept separate in `logic.py`:
    - Login & roles  -> Supabase
    - Student data   -> Google Sheets (one shareable link per class)

If `logic.py` or the Supabase secrets are missing, the app still runs with the
built-in DEMO data (the demo data is never removed).
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# The school's fixed minimum attendance rule: any student below 75% will be flagged
MIN_ATTENDANCE_THRESHOLD: float = 75.0

# The default passing score (40 out of 100); teachers can change this number on the screen
DEFAULT_PASS_MARK: float = 40.0

# The 5 column names every sheet / uploaded file must have
EXPECTED_COLUMNS: List[str] = ["student_id", "name", "subject", "attendance", "marks"]

# Extra column added automatically when data comes from Google Sheets (which class a row belongs to)
OPTIONAL_COLUMNS: List[str] = ["class_name"]

# ------------------------------------------------------------------------------
# Section 1: Sample (demo) Data & Backup System
# ------------------------------------------------------------------------------

def _build_mock_records() -> pd.DataFrame:
    """Create a small set of fake student records so the dashboard can be tested right away."""
    data = [
        {"student_id": "STU001", "name": "Aarav Demo", "subject": "Mathematics", "attendance": 88.5, "marks": 82.0},
        {"student_id": "STU001", "name": "Aarav Demo", "subject": "Physics", "attendance": 91.0, "marks": 78.5},
        {"student_id": "STU001", "name": "Aarav Demo", "subject": "Computer Science", "attendance": 94.0, "marks": 91.0},
        {"student_id": "STU002", "name": "Diya Sample", "subject": "Mathematics", "attendance": 68.0, "marks": 74.0},
        {"student_id": "STU002", "name": "Diya Sample", "subject": "Physics", "attendance": 79.0, "marks": 36.0},
        {"student_id": "STU002", "name": "Diya Sample", "subject": "Computer Science", "attendance": 85.0, "marks": 69.5},
        {"student_id": "STU003", "name": "Kabir Test", "subject": "Mathematics", "attendance": 62.5, "marks": 32.0},
        {"student_id": "STU003", "name": "Kabir Test", "subject": "Physics", "attendance": 71.0, "marks": 38.5},
        {"student_id": "STU003", "name": "Kabir Test", "subject": "Computer Science", "attendance": 76.0, "marks": 54.0},
        {"student_id": "STU004", "name": "Meera Synth", "subject": "Mathematics", "attendance": 81.0, "marks": 65.0},
        {"student_id": "STU004", "name": "Meera Synth", "subject": "Physics", "attendance": 72.5, "marks": 61.0},
        {"student_id": "STU004", "name": "Meera Synth", "subject": "Computer Science", "attendance": 89.0, "marks": 84.0},
        {"student_id": "STU005", "name": "Rohan Mock", "subject": "Mathematics", "attendance": 95.0, "marks": 35.0},
        {"student_id": "STU005", "name": "Rohan Mock", "subject": "Physics", "attendance": 82.0, "marks": 71.0},
        {"student_id": "STU005", "name": "Rohan Mock", "subject": "Computer Science", "attendance": 64.0, "marks": 29.0},
    ]
    return pd.DataFrame(data, columns=EXPECTED_COLUMNS)


class _MockLogicModule:
    """A pretend backend so this app still works without Supabase / Google Sheets (demo data)."""

    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
        if not email or not password:
            return None
        role = "student" if "student" in email.lower() else "faculty"
        return {
            "user_id": "demo-user-001",
            "email": email.strip(),
            "student_id": "STU002" if role == "student" else None,
        }

    @staticmethod
    def get_user_role(user_id: str) -> str:
        return "student" if "student" in str(user_id).lower() else "faculty"

    @staticmethod
    def fetch_all_records() -> pd.DataFrame:
        # The first time we need data, save our pretend student table into the browser's temporary memory
        if "mock_records_df" not in st.session_state:
            st.session_state["mock_records_df"] = _build_mock_records()
        return st.session_state["mock_records_df"].copy()

    @staticmethod
    def save_records(df: pd.DataFrame) -> Tuple[bool, str]:
        if df.empty:
            return False, "Cannot save an empty DataFrame."
        st.session_state["mock_records_df"] = df.copy()
        return True, f"Saved {len(df)} record(s) to local demo store."


# The demo backend always exists, even when the real backend is connected.
_mock_backend = _MockLogicModule()

# Try to connect to the real `logic.py` (Supabase + Google Sheets) if it exists and is configured
try:
    import logic as _imported_logic

    required_hooks = ("authenticate_user", "get_user_role", "fetch_all_records", "save_records")
    hooks_ok = all(hasattr(_imported_logic, hook) for hook in required_hooks)
    # `is_configured()` is True only when the Supabase secrets are present
    configured = _imported_logic.is_configured() if hasattr(_imported_logic, "is_configured") else True

    if hooks_ok and configured:
        logic = _imported_logic
        USING_MOCK_LOGIC = False
    else:
        logic = _mock_backend
        USING_MOCK_LOGIC = True
except Exception:
    # `logic.py` is missing, or a library (like supabase) is not installed -> demo mode
    logic = _mock_backend
    USING_MOCK_LOGIC = True

# ------------------------------------------------------------------------------
# Section 2: Webpage Setup & Login Memory Helpers
# ------------------------------------------------------------------------------

st.set_page_config(
    page_title="Student Attendance & Performance Insights Dashboard",
    page_icon="📊",
    layout="wide",
)


def _using_demo_data() -> bool:
    """True when the app should use the built-in demo data (no Supabase, or Demo Mode was clicked)."""
    return USING_MOCK_LOGIC or bool(st.session_state.get("demo_mode"))


def _backend():
    """Pick which backend to use right now: demo data or the real Supabase + Google Sheets one."""
    return _mock_backend if _using_demo_data() else logic


def init_session_state() -> None:
    """Set up empty memory slots in the browser to remember who is logged in."""
    defaults: Dict[str, Any] = {
        "user": None,
        "role": None,
        "student_id": None,
        "demo_mode": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout_user() -> None:
    """Erase the current user's login memory and send them back to the login page."""
    # End the real Supabase session too (not needed for demo mode)
    if not _using_demo_data() and hasattr(logic, "sign_out"):
        logic.sign_out()

    st.session_state["user"] = None
    st.session_state["role"] = None
    st.session_state["student_id"] = None
    st.session_state["demo_mode"] = False
    st.session_state["sheet_errors"] = []
    st.rerun()


def activate_demo_mode(role: str = "faculty", student_id: Optional[str] = None) -> None:
    """Let someone preview the dashboard right away with the built-in demo data."""
    st.session_state["user"] = {
        "user_id": f"demo-{role}",
        "email": f"demo.{role}@institution.edu",
    }
    st.session_state["role"] = role
    st.session_state["student_id"] = student_id
    st.session_state["demo_mode"] = True
    st.rerun()


# ------------------------------------------------------------------------------
# Section 3: Table Cleanup & At-Risk Warning Rules
# ------------------------------------------------------------------------------

def _clean_column_name(col: Any) -> str:
    """Turn headers like 'Student ID' or 'student-id' into 'student_id'."""
    return re.sub(r"[\s\-]+", "_", str(col).strip().lower())


def _to_number(series: pd.Series) -> pd.Series:
    """Convert text like '85', '85%' or ' 72.5 ' to numbers. Anything unreadable becomes blank (NaN)."""
    text = series.astype(str).str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(text, errors="coerce")


def normalize_records_df(df: pd.DataFrame) -> pd.DataFrame:
    """Clean up a table (from Google Sheets, an upload or the demo) so columns and numbers are consistent."""
    if df is None or df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    cleaned = df.copy()
    cleaned.columns = [_clean_column_name(col) for col in cleaned.columns]

    # Every required column must be present; if any is missing, return an empty table
    for col in EXPECTED_COLUMNS:
        if col not in cleaned.columns:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)

    # Keep the 5 required columns (plus `class_name` when it exists)
    keep = EXPECTED_COLUMNS + [col for col in OPTIONAL_COLUMNS if col in cleaned.columns]
    cleaned = cleaned[keep].copy()

    # Rows without a student ID are useless (e.g. empty rows at the bottom of a sheet) -> drop them
    cleaned = cleaned.dropna(subset=["student_id"])

    # Student IDs: trim spaces, remove a trailing ".0" (Excel quirk) and use CAPITAL letters,
    # so "stu001", " STU001 " and "STU001" all match the same student.
    cleaned["student_id"] = (
        cleaned["student_id"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.upper()
    )
    cleaned = cleaned[cleaned["student_id"] != ""].copy()

    cleaned["name"] = cleaned["name"].fillna("").astype(str).str.strip()
    cleaned["subject"] = cleaned["subject"].fillna("").astype(str).str.strip()
    if "class_name" in cleaned.columns:
        cleaned["class_name"] = cleaned["class_name"].fillna("").astype(str).str.strip()

    # Numbers: unreadable or impossible values become blank (NaN) instead of 0,
    # so a typo in a sheet does not silently make a student look like a failure.
    cleaned["attendance"] = _to_number(cleaned["attendance"])
    cleaned["marks"] = _to_number(cleaned["marks"])
    cleaned["attendance"] = cleaned["attendance"].where(cleaned["attendance"].between(0, 100)).astype(float)
    cleaned["marks"] = cleaned["marks"].where(cleaned["marks"] >= 0).astype(float)

    return cleaned.reset_index(drop=True)


def compute_flag_reason(attendance: float, marks: float, pass_mark: float) -> str:
    """Decide whether a student is 'On Track' or needs attention in a subject."""
    low_attendance = (not pd.isna(attendance)) and attendance < MIN_ATTENDANCE_THRESHOLD
    low_marks = (not pd.isna(marks)) and marks < pass_mark

    if low_attendance and low_marks:
        return "Both"
    if low_attendance:
        return "Low Attendance"
    if low_marks:
        return "Low Marks"
    # Nothing is low, but a value is blank/invalid -> ask the teacher to check the sheet
    if pd.isna(attendance) or pd.isna(marks):
        return "Missing Data"
    return "On Track"


def highlight_flagged_rows(row: pd.Series) -> List[str]:
    """Color a table row light red whenever the student is flagged."""
    if row.get("Flag Reason", "On Track") != "On Track":
        return ["background-color: #FADBD8; color: #78281F"] * len(row)
    return [""] * len(row)


def load_records() -> pd.DataFrame:
    """Get the records from the right place (demo data or Google Sheets) and clean them."""
    backend = _backend()
    if backend is _mock_backend:
        st.session_state["sheet_errors"] = []
        return normalize_records_df(backend.fetch_all_records())
    with st.spinner("Loading class sheets from Google Sheets..."):
        return normalize_records_df(backend.fetch_all_records())


def render_refresh_button(container) -> None:
    """Show a 'Refresh data now' button (only for live Google Sheets data)."""
    if _using_demo_data():
        return
    if container.button("🔄 Refresh data now", width="stretch"):
        if hasattr(logic, "refresh_data"):
            logic.refresh_data()
        st.rerun()
    container.caption("Edits in Google Sheets appear automatically within about a minute.")


# ------------------------------------------------------------------------------
# Section 4: Login Screen (Shown before a user signs in)
# ------------------------------------------------------------------------------

def render_login_screen() -> None:
    """Draw the Login page, including the email/password box and quick Demo Mode buttons."""
    st.title("📊 Student Attendance & Performance Insights Dashboard")
    st.caption("SW-12 | Sign in to access the Faculty Analytics Dashboard or Student Portal.")

    if USING_MOCK_LOGIC:
        st.info(
            "Running with built-in demo data (Supabase / `logic.py` not connected). "
            "Use **Demo Mode** or any credentials to preview."
        )

    st.sidebar.header("Developer Preview")
    if st.sidebar.button("Demo Mode (Bypass Login)", width="stretch"):
        activate_demo_mode(role="faculty")

    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        with st.form("login_form"):
            st.subheader("Sign In")
            email = st.text_input("Email", placeholder="faculty@university.edu")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Log In", type="primary", width="stretch")

        if submitted:
            auth_result = logic.authenticate_user(email.strip(), password)
            if not auth_result:
                # Show the specific reason (e.g. "account not set up") if the backend gave one
                st.error(st.session_state.get("auth_error") or "Invalid email or password. Please try again.")
            else:
                user_id = auth_result.get("user_id") or auth_result.get("id") or email.strip()
                role = auth_result.get("role") or logic.get_user_role(user_id)

                st.session_state["user"] = auth_result
                st.session_state["role"] = role
                st.session_state["student_id"] = auth_result.get("student_id")
                st.session_state["demo_mode"] = False
                st.rerun()

        st.divider()
        st.caption("Demo previews use built-in sample data only (no Google Sheets).")
        demo_col1, demo_col2 = st.columns(2)
        if demo_col1.button("Preview as Faculty (Demo)", width="stretch"):
            activate_demo_mode(role="faculty")
        if demo_col2.button("Preview as Student (Demo)", width="stretch"):
            activate_demo_mode(role="student", student_id="STU002")


# ------------------------------------------------------------------------------
# Section 5: Student Portal (Read-only view showing only one student's own data)
# ------------------------------------------------------------------------------

def render_student_portal() -> None:
    """Draw the restricted Student Portal so a student only sees their own grades and attendance."""
    user = st.session_state.get("user") or {}
    student_id = st.session_state.get("student_id")

    st.sidebar.header("Student Account")
    st.sidebar.write(f"**Email:** `{user.get('email', 'student@university.edu')}`")
    st.sidebar.info("Role: Student (Read-Only)")
    if st.sidebar.button("Logout", width="stretch"):
        logout_user()
    st.sidebar.divider()
    render_refresh_button(st.sidebar)

    st.title("🎓 Student Performance Portal")
    st.caption("Read-only view of your attendance and subject marks.")

    # SAFETY: a student account must always be linked to a Student ID.
    # (Never fall back to "the first student in the table" - that would show someone else's data.)
    if not student_id:
        st.error("Your account is not linked to a Student ID. Please contact the administrator.")
        return
    target_id = str(student_id).strip().upper()

    df = load_records()

    if st.session_state.get("sheet_errors"):
        st.warning("Some class sheets could not be loaded, so your data may be incomplete.")

    if df.empty:
        st.info("No records found yet. Please check again later.")
        return

    # Keep ONLY the rows that belong to this student (matching on student_id)
    student_df = df[df["student_id"] == target_id].copy()
    if student_df.empty:
        st.info(f"No records found for Student ID `{target_id}`. Please contact your class teacher.")
        return

    student_name = str(student_df["name"].iloc[0])
    st.subheader(f"Welcome, {student_name} (`{target_id}`)")
    avg_attendance = float(student_df["attendance"].mean())
    avg_marks = float(student_df["marks"].mean())

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Overall Attendance (%)", f"{avg_attendance:.1f}%")
    kpi2.metric("Average Marks", f"{avg_marks:.1f}")
    kpi3.metric("Subjects Enrolled", f"{len(student_df)}")

    student_df["Flag Reason"] = student_df.apply(
        lambda r: compute_flag_reason(float(r["attendance"]), float(r["marks"]), DEFAULT_PASS_MARK),
        axis=1,
    )

    at_risk_df = student_df[student_df["Flag Reason"] != "On Track"]
    if not at_risk_df.empty:
        for _, row in at_risk_df.iterrows():
            st.warning(
                f"**{row['subject']}** — {row['Flag Reason']} "
                f"(Attendance: {row['attendance']:.1f}%, Marks: {row['marks']:.1f})"
            )
    else:
        st.success("All subjects meet the 75% attendance and 40 pass mark thresholds.")

    st.divider()

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**Attendance (%) by Subject**")
        st.bar_chart(student_df.set_index("subject")["attendance"])
    with chart_col2:
        st.markdown("**Marks by Subject**")
        st.bar_chart(student_df.set_index("subject")["marks"])

    st.subheader("Subject Breakdown")
    display_df = student_df[["subject", "attendance", "marks", "Flag Reason"]].rename(
        columns={"subject": "Subject", "attendance": "Attendance (%)", "marks": "Marks"}
    )
    styled_df = display_df.style.apply(highlight_flagged_rows, axis=1).format(
        {"Attendance (%)": "{:.1f}%", "Marks": "{:.1f}"}, na_rep="—"
    )
    st.dataframe(styled_df, width="stretch", hide_index=True)


# ------------------------------------------------------------------------------
# Section 6: Faculty Dashboard (Full teacher view with classes, filters, and charts)
# ------------------------------------------------------------------------------

def render_upload_section() -> None:
    """DEMO ONLY: upload a CSV/Excel file into the temporary demo store (kept from the original app)."""
    st.sidebar.header("Data Upload (Demo)")
    uploaded_file = st.sidebar.file_uploader(
        "Upload Student Records (.csv or .xlsx)",
        type=["csv", "xlsx"],
        help="Expected columns: student_id, name, subject, attendance, marks",
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file, engine="openpyxl")

            st.sidebar.caption("Preview (first 5 rows):")
            st.sidebar.dataframe(uploaded_df.head(), width="stretch", hide_index=True)

            if st.sidebar.button("Save to Demo Store", type="primary", width="stretch"):
                normalized_upload = normalize_records_df(uploaded_df)
                if normalized_upload.empty:
                    st.sidebar.error(f"Invalid schema. Required columns: {', '.join(EXPECTED_COLUMNS)}.")
                else:
                    ok, message = _mock_backend.save_records(normalized_upload)
                    if ok:
                        st.sidebar.success(message)
                        st.rerun()
                    else:
                        st.sidebar.error(message)
        except Exception as exc:
            st.sidebar.error(f"Failed to read uploaded file: {exc}")


def render_class_manager() -> None:
    """LIVE MODE: let faculty add / remove the Google Sheet link of each class."""
    st.sidebar.header("Class Sheets (Google Sheets)")
    render_refresh_button(st.sidebar)

    # Show the result of the last add/remove (the page reruns after each change)
    flash = st.session_state.pop("class_flash", None)
    if flash:
        (st.sidebar.success if flash[0] else st.sidebar.error)(flash[1])

    with st.sidebar.expander("Manage classes"):
        try:
            classes = logic.list_classes()
        except Exception as exc:
            classes = []
            st.error(f"Could not load classes: {exc}")

        if classes:
            st.markdown("**Registered classes**")
            for item in classes:
                st.write(f"• {item['class_name']}")
        else:
            st.info("No classes yet. Add your first class below.")

        with st.form("add_class_form", clear_on_submit=True):
            st.markdown("**Add a class**")
            new_name = st.text_input("Class name", placeholder="e.g. CSE-A 1st Year")
            new_link = st.text_input(
                "Google Sheet share link",
                placeholder="https://docs.google.com/spreadsheets/d/...",
                help="Share -> General access -> Anyone with the link (Viewer). "
                "Row 1 must be: student id, name, subject, attendance, marks.",
            )
            add_clicked = st.form_submit_button("Add class", width="stretch")

        if add_clicked:
            st.session_state["class_flash"] = logic.add_class(new_name, new_link)
            st.rerun()

        if classes:
            options = {item["class_name"]: item["id"] for item in classes}
            to_remove = st.selectbox("Remove a class", options=list(options.keys()))
            if st.button("Remove selected class", width="stretch"):
                st.session_state["class_flash"] = logic.remove_class(options[to_remove])
                st.rerun()


def render_faculty_dashboard() -> None:
    """Draw the full Faculty Dashboard with class sheets, threshold controls, KPIs, and 3 tabs."""
    user = st.session_state.get("user") or {}

    st.sidebar.header("Faculty Account")
    st.sidebar.write(f"**Email:** `{user.get('email', 'faculty@university.edu')}`")
    st.sidebar.success("Role: Faculty")
    if st.sidebar.button("Logout", width="stretch"):
        logout_user()
    st.sidebar.divider()

    # Demo mode keeps the original CSV/Excel upload; live mode uses Google Sheets instead
    if _using_demo_data():
        render_upload_section()
    else:
        render_class_manager()
    st.sidebar.divider()

    st.sidebar.header("Thresholds & Filters")
    pass_mark = float(
        st.sidebar.number_input(
            "Pass Mark Threshold",
            min_value=0.0,
            max_value=100.0,
            value=DEFAULT_PASS_MARK,
            step=1.0,
        )
    )
    st.sidebar.info(f"Minimum Attendance Threshold: **{MIN_ATTENDANCE_THRESHOLD:.0f}%** (Fixed)")

    st.title("📊 Student Attendance & Performance Insights Dashboard")
    st.caption("SW-12 | Faculty Analytics & At-Risk Student Monitoring")

    df = load_records()

    # Tell faculty exactly which class sheet failed and why (e.g. link not shared, column missing)
    for problem in st.session_state.get("sheet_errors", []):
        st.warning(f"⚠️ {problem}")

    if df.empty:
        if _using_demo_data():
            st.info("No records found. Upload a CSV or Excel file to begin.")
        else:
            st.info("No student data yet. Add a class under **Class Sheets → Manage classes** in the sidebar.")
        return

    # Filter 1 (live mode): choose a class
    if "class_name" in df.columns:
        class_options = ["All Classes"] + sorted(df["class_name"].dropna().unique().tolist())
        selected_class = st.sidebar.selectbox("Filter by Class", options=class_options)
        if selected_class != "All Classes":
            df = df[df["class_name"] == selected_class].copy()

    # Filter 2: choose a subject
    subjects = ["All Subjects"] + sorted(df["subject"].dropna().unique().tolist())
    selected_subject = st.sidebar.selectbox("Filter by Subject", options=subjects)
    filtered_df = df if selected_subject == "All Subjects" else df[df["subject"] == selected_subject].copy()

    if filtered_df.empty:
        st.info("No records found for this selection.")
        return

    filtered_df = filtered_df.copy()
    filtered_df["Flag Reason"] = filtered_df.apply(
        lambda r: compute_flag_reason(float(r["attendance"]), float(r["marks"]), pass_mark),
        axis=1,
    )

    at_risk_df = filtered_df[filtered_df["Flag Reason"] != "On Track"].copy()

    total_students = int(filtered_df["student_id"].nunique())
    avg_attendance = float(filtered_df["attendance"].mean())
    avg_marks = float(filtered_df["marks"].mean())
    flagged_students_count = int(at_risk_df["student_id"].nunique()) if not at_risk_df.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Students", f"{total_students}")
    col2.metric("Average Attendance (%)", f"{avg_attendance:.1f}%")
    col3.metric("Average Marks", f"{avg_marks:.1f}")
    col4.metric("Flagged At-Risk Students", f"{flagged_students_count}")

    st.divider()

    tab1, tab2, tab3 = st.tabs(
        [
            "🚨 At-Risk Alerts",
            "📚 Subject-Wise Insights",
            "🎓 Student-Wise Insights",
        ]
    )

    # Tab 1: Priority list of students who need attention
    with tab1:
        st.subheader("At-Risk Alerts (Priority View)")
        if at_risk_df.empty:
            st.success("No at-risk students found under the current thresholds.")
        else:
            alert_columns = ["student_id", "name", "subject", "attendance", "marks", "Flag Reason"]
            rename_map = {
                "student_id": "Student ID",
                "name": "Name",
                "subject": "Subject",
                "attendance": "Attendance (%)",
                "marks": "Marks",
            }
            if "class_name" in at_risk_df.columns:
                alert_columns.insert(2, "class_name")
                rename_map["class_name"] = "Class"

            alerts_display = at_risk_df[alert_columns].rename(columns=rename_map)
            styled_alerts = alerts_display.style.apply(highlight_flagged_rows, axis=1).format(
                {"Attendance (%)": "{:.1f}%", "Marks": "{:.1f}"}, na_rep="—"
            )
            st.dataframe(styled_alerts, width="stretch", hide_index=True)

    # Tab 2: Compare average attendance and marks across different subjects
    with tab2:
        st.subheader("Subject-Wise Insights")
        subject_summary = (
            filtered_df.groupby("subject", as_index=False)
            .agg(
                students=("student_id", "nunique"),
                avg_attendance=("attendance", "mean"),
                avg_marks=("marks", "mean"),
            )
            .sort_values("subject")
        )
        subject_summary["avg_attendance"] = subject_summary["avg_attendance"].round(2)
        subject_summary["avg_marks"] = subject_summary["avg_marks"].round(2)

        chart_left, chart_right = st.columns(2)
        with chart_left:
            st.markdown("**Average Attendance (%) by Subject**")
            st.bar_chart(subject_summary.set_index("subject")["avg_attendance"])
        with chart_right:
            st.markdown("**Average Marks by Subject**")
            st.bar_chart(subject_summary.set_index("subject")["avg_marks"])

        st.markdown("**Subject Summary Table**")
        summary_display = subject_summary.rename(
            columns={
                "subject": "Subject",
                "students": "Students",
                "avg_attendance": "Avg Attendance (%)",
                "avg_marks": "Avg Marks",
            }
        )
        st.dataframe(summary_display, width="stretch", hide_index=True)

    # Tab 3: Inspect one individual student in detail
    with tab3:
        st.subheader("Student-Wise Insights")

        student_options_df = (
            filtered_df[["student_id", "name"]].drop_duplicates().sort_values("student_id")
        )
        student_labels = [
            f"{row['student_id']} — {row['name']}" for _, row in student_options_df.iterrows()
        ]

        chosen_label = st.selectbox("Select Student", options=student_labels)
        chosen_id = chosen_label.split(" — ")[0].strip()

        single_student_df = filtered_df[filtered_df["student_id"] == chosen_id].copy()
        s_att = float(single_student_df["attendance"].mean())
        s_marks = float(single_student_df["marks"].mean())

        sk1, sk2 = st.columns(2)
        sk1.metric("Overall Attendance (%)", f"{s_att:.1f}%")
        sk2.metric("Overall Average Marks", f"{s_marks:.1f}")

        st.markdown(f"**Subject-Wise Attendance & Marks — {chosen_label}**")
        chart_df = single_student_df.set_index("subject")[["attendance", "marks"]].rename(
            columns={"attendance": "Attendance (%)", "marks": "Marks"}
        )
        st.bar_chart(chart_df)

        st.markdown("**Detailed Subject Breakdown**")
        breakdown_df = single_student_df[["subject", "attendance", "marks", "Flag Reason"]].rename(
            columns={
                "subject": "Subject",
                "attendance": "Attendance (%)",
                "marks": "Marks",
            }
        )
        styled_breakdown = breakdown_df.style.apply(highlight_flagged_rows, axis=1).format(
            {"Attendance (%)": "{:.1f}%", "Marks": "{:.1f}"}, na_rep="—"
        )
        st.dataframe(styled_breakdown, width="stretch", hide_index=True)


# ------------------------------------------------------------------------------
# Section 7: Application Starting Point
# ------------------------------------------------------------------------------

def main() -> None:
    """Decide which screen to show: Login, Student Portal, or Faculty Dashboard."""
    init_session_state()

    if st.session_state.get("user") is None:
        render_login_screen()
        return

    if st.session_state.get("role") == "student":
        render_student_portal()
    else:
        render_faculty_dashboard()


if __name__ == "__main__":
    main()
