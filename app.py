"""
Student Attendance & Performance Insights Dashboard (Problem Statement SW-12)
Pure Streamlit UI layer (`app.py`) with clean separation from backend `logic.py`.
"""

# Standard library typing imports for clean type annotations
from typing import Any, Dict, List, Optional, Tuple

# Third-party imports for tabular data manipulation and Streamlit UI rendering
import pandas as pd
import streamlit as st

# Fixed minimum attendance percentage required across all courses
MIN_ATTENDANCE_THRESHOLD: float = 75.0
# Default pass mark threshold (can be adjusted by faculty in the sidebar)
DEFAULT_PASS_MARK: float = 40.0
# Expected 5-column schema returned by logic.fetch_all_records() and uploaded files
EXPECTED_COLUMNS: List[str] = ["student_id", "name", "subject", "attendance", "marks"]


# ------------------------------------------------------------------------------
# Backend Hook Imports & Clean Mock Fallback (try/except ImportError)
# ------------------------------------------------------------------------------


def _build_mock_records() -> pd.DataFrame:
    """Return synthetic student records matching the expected 5-column schema."""
    # Sample rows covering on-track, low-attendance, low-marks, and dual-risk students
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
    # Convert the list of dicts into a Pandas DataFrame with strict column ordering
    return pd.DataFrame(data, columns=EXPECTED_COLUMNS)


class _MockLogicModule:
    """Fallback mock implementation used when logic.py is not yet created."""

    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
        # Reject empty credentials during mock login
        if not email or not password:
            return None
        # Route emails containing 'student' to student role, otherwise faculty
        role = "student" if "student" in email.lower() else "faculty"
        # Return a mock user dictionary mimicking a Supabase auth payload
        return {
            "user_id": "demo-user-001",
            "email": email.strip(),
            "student_id": "STU002" if role == "student" else None,
        }

    @staticmethod
    def get_user_role(user_id: str) -> str:
        # Derive role string from mock user_id when not explicitly provided
        return "student" if "student" in str(user_id).lower() else "faculty"

    @staticmethod
    def fetch_all_records() -> pd.DataFrame:
        # Seed session-scoped mock data once so uploaded edits persist across reruns
        if "mock_records_df" not in st.session_state:
            st.session_state["mock_records_df"] = _build_mock_records()
        # Return a copy so UI mutations never corrupt the cached mock DataFrame
        return st.session_state["mock_records_df"].copy()

    @staticmethod
    def save_records(df: pd.DataFrame) -> Tuple[bool, str]:
        # Guard against saving an empty DataFrame
        if df.empty:
            return False, "Cannot save an empty DataFrame."
        # Store the uploaded DataFrame in session state to simulate database persistence
        st.session_state["mock_records_df"] = df.copy()
        return True, f"Saved {len(df)} record(s) to local demo store."


# Attempt to import the real backend `logic.py` module and verify expected hooks
try:
    import logic as _imported_logic

    # Check that all four required backend functions exist on the imported module
    required_hooks = ("authenticate_user", "get_user_role", "fetch_all_records", "save_records")
    if all(hasattr(_imported_logic, hook) for hook in required_hooks):
        logic = _imported_logic
        USING_MOCK_LOGIC = False
    else:
        # Fall back to mock hooks if logic.py exists without the expected functions
        logic = _MockLogicModule()
        USING_MOCK_LOGIC = True
except ImportError:
    # Fall back to mock hooks if logic.py has not been created yet
    logic = _MockLogicModule()
    USING_MOCK_LOGIC = True


# ------------------------------------------------------------------------------
# Page Configuration & Session State HelpersBuild the complete Streamlit UI (`app.py`), backend helper module (`logic.py`), and `requirements.txt` for **SW-12: Student Attendance & Performance Insights Dashboard**, using **Supabase** for PostgreSQL database storage, authentication, and role-based authorization.



### 1. Project & Architecture Constraints

**Stack:** Python only (`streamlit`, `pandas`, `openpyxl`, `supabase`, `plotly`). Do not generate HTML/CSS/JS files.
**Deployment Target:** Streamlit Community Cloud.
**Folder Structure:**
`.streamlit/secrets.toml` (read via `st.secrets["SUPABASE_URL"]` and `st.secrets["SUPABASE_KEY"]`)
`logic.py` (all Supabase client initialization, auth calls, CSV/Excel parsing, database CRUD, and flagging calculations)
`app.py` (pure Streamlit UI rendering and session state management)
`requirements.txt`
**Data Rule:** Use synthetic/sample student records only; never hardcode real student PII.


### 2. Supabase Database & Auth Setup

Include a comment block at the top of `logic.py` with the exact SQL schema to run in the Supabase SQL Editor:

`profiles` table: `user_id` (UUID, references `auth.users(id)`), `email` (text), `role` (`'faculty'` or `'student'`), `student_roll_no` (text, nullable — links a student login to their records).
`student_records` table: `id` (bigint identity primary key), `student_roll_no` (text), `student_name` (text), `subject` (text), `attendance_pct` (numeric), `marks` (numeric), `uploaded_by` (UUID), `updated_at` (timestamptz), with a unique constraint on `(student_roll_no, subject)` so re-uploads upsert cleanly.


### 3. Authentication & Authorization Flow (`app.py` + `logic.py`)

Store `user`, `access_token`, `role`, and `student_roll_no` in `st.session_state`.
**Unauthenticated View:** Render a clean Login / Sign-Up tab interface using `st.form`:
**Login:** Email + Password (`supabase.auth.sign_in_with_password`). Fetch the user's `role` and `student_roll_no` from the `profiles` table immediately after login.
**Sign Up:** Email, Password, Role selector (`faculty` or `student`), and `student_roll_no` input (required if role is `student`). Insert into `auth.users` and `profiles`.
**Sidebar User Bar (Authenticated):** Show logged-in email, role badge, and a **Logout** button that clears `st.session_state` and calls `st.rerun()`.


### 4. Role-Based UI Requirements

#### A. Faculty View (`role == "faculty"`) — Full Dashboard

**Sidebar Data Upload & Thresholds:**
`st.file_uploader` accepting `.csv` and `.xlsx` files with expected columns: `student_roll_no`, `student_name`, `subject`, `attendance_pct`, `marks`.
Validate column names and numeric ranges (`0–100`) in `logic.py` before upserting to `student_records`. Display `st.success` or `st.error` feedback.
Include a **"Download Sample CSV"** `st.download_button` in the sidebar so evaluators can test uploads immediately.
`st.number_input` for **Pass Mark Threshold** (default `40.0`, range `0–100`) alongside the fixed **75.0% Attendance Threshold**.
`st.selectbox` filters for **Subject** ("All Subjects" + distinct subjects) and **Student**.
**Top Summary KPIs (`st.columns` + `st.metric`):**
Total Students, Average Attendance %, Average Marks, and Total Flagged At-Risk Students.
**Tabbed Analytics (`st.tabs`):**
**Tab 1 — Subject-Wise View:** Grouped bar charts (`plotly.express`) showing average attendance % (with a dashed threshold line at 75%) and average marks per subject (with a dashed line at the pass mark threshold), plus a subject summary dataframe.
**Tab 2 — Student-Wise View:** Selector for a specific student showing their KPI metrics, per-subject attendance & marks bar chart, and subject-level status table.
**Tab 3 — Flagged Students (Needs Attention):** Filtered `st.dataframe` listing every student-subject record where `attendance_pct < 75` OR `marks < pass_mark`, with a clear `Flag Reason` column (`"Low Attendance"`, `"Below Pass Mark"`, or `"Both"`) and red/amber row highlighting via Pandas Styler.


#### B. Student View (`role == "student"`) — Restricted Read-Only View

Query `student_records` filtered strictly by the logged-in user's `student_roll_no`.
Hide file uploaders and other students' records completely.
Display the student's personal overall attendance %, average marks, personal subject-wise charts, and warning banners (`st.warning` / `st.error`) for any subject where their attendance is `< 75%` or marks are `< 40`.


### 5. Code Quality Rules

Use `@st.cache_resource` for the Supabase client initialization and `@st.cache_data(ttl=60)` for read queries (calling `st.cache_data.clear()` right after a successful file upload).
Handle empty database states gracefully with `st.info("No records found. Upload a CSV or Excel file to begin.")` instead of crashing on empty DataFrames.
Output the complete, runnable code for `requirements.txt`, `logic.py`, and `app.py` with no placeholders or `TODO` comments.
write comment lines for every line (or group of lines of code)of code to tell what that part do.
# ------------------------------------------------------------------------------

# Configure the browser tab title, icon, and wide dashboard layout
st.set_page_config(
    page_title="Student Attendance & Performance Insights Dashboard",
    page_icon="📊",
    layout="wide",
)


def init_session_state() -> None:
    """Initialize required authentication and demo keys in st.session_state."""
    # Define default values for user identity, role, student link, and demo flag
    defaults: Dict[str, Any] = {
        "user": None,
        "role": None,
        "student_id": None,
        "demo_mode": False,
    }
    # Populate any missing keys without overwriting active session values
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout_user() -> None:
    """Clear user session state and return to the login screen."""
    # Reset all authentication fields in session state
    st.session_state["user"] = None
    st.session_state["role"] = None
    st.session_state["student_id"] = None
    st.session_state["demo_mode"] = False
    # Trigger an immediate rerun so Streamlit renders the login screen
    st.rerun()


def activate_demo_mode(role: str = "faculty", student_id: Optional[str] = None) -> None:
    """Bypass login in Demo Mode so evaluators can preview Faculty or Student views."""
    # Populate synthetic user metadata in session state for instant UI preview
    st.session_state["user"] = {
        "user_id": f"demo-{role}",
        "email": f"demo.{role}@institution.edu",
    }
    st.session_state["role"] = role
    st.session_state["student_id"] = student_id
    st.session_state["demo_mode"] = True
    # Rerun the app to enter the chosen role-based dashboard immediately
    st.rerun()


# ------------------------------------------------------------------------------
# Data Processing & Pandas Styler Helpers
# ------------------------------------------------------------------------------


def normalize_records_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the DataFrame conforms to the expected 5-column schema and types."""
    # Return an empty schema-aligned DataFrame if input is None or empty
    if df is None or df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    # Standardize column names to lowercase without surrounding whitespace
    cleaned = df.copy()
    cleaned.columns = [str(col).strip().lower() for col in cleaned.columns]
    # Abort normalization if any required column is missing
    for col in EXPECTED_COLUMNS:
        if col not in cleaned.columns:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)

    # Keep only the 5 expected columns and clean text/numeric types
    cleaned = cleaned[EXPECTED_COLUMNS].copy()
    cleaned["student_id"] = cleaned["student_id"].astype(str).str.strip()
    cleaned["name"] = cleaned["name"].astype(str).str.strip()
    cleaned["subject"] = cleaned["subject"].astype(str).str.strip()
    cleaned["attendance"] = pd.to_numeric(cleaned["attendance"], errors="coerce").fillna(0.0)
    cleaned["marks"] = pd.to_numeric(cleaned["marks"], errors="coerce").fillna(0.0)
    return cleaned


def compute_flag_reason(attendance: float, marks: float, pass_mark: float) -> str:
    """Determine the flag reason for a student-subject record."""
    # Check attendance against fixed 75% rule and marks against pass_mark
    low_attendance = attendance < MIN_ATTENDANCE_THRESHOLD
    low_marks = marks < pass_mark
    # Return the appropriate status label
    if low_attendance and low_marks:
        return "Both"
    if low_attendance:
        return "Low Attendance"
    if low_marks:
        return "Low Marks"
    return "On Track"


def highlight_flagged_rows(row: pd.Series) -> List[str]:
    """Apply a light red background to flagged rows using Pandas Styler."""
    # Highlight any row whose Flag Reason indicates an attendance or marks issue
    if row.get("Flag Reason", "On Track") != "On Track":
        return ["background-color: #FADBD8; color: #78281F"] * len(row)
    # Leave compliant rows unstyled
    return [""] * len(row)


# ------------------------------------------------------------------------------
# Authentication View
# ------------------------------------------------------------------------------


def render_login_screen() -> None:
    """Render the Login form and Demo Mode bypass option."""
    # Display application header and brief instruction
    st.title("📊 Student Attendance & Performance Insights Dashboard")
    st.caption("SW-12 | Sign in to access the Faculty Analytics Dashboard or Student Portal.")

    # Inform developers when running on the built-in mock fallback
    if USING_MOCK_LOGIC:
        st.info("Running with built-in demo data (`logic.py` hooks not detected). Use **Demo Mode** or any credentials to preview.")

    # Provide a sidebar Demo Mode button for one-click dashboard preview
    st.sidebar.header("Developer Preview")
    if st.sidebar.button("Demo Mode (Bypass Login)", use_container_width=True):
        activate_demo_mode(role="faculty")

    # Center the login form on the page using 3 columns
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        # Render the email/password login form
        with st.form("login_form"):
            st.subheader("Sign In")
            email = st.text_input("Email", placeholder="faculty@university.edu")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)

        # Authenticate via logic.py hooks when the form is submitted
        if submitted:
            auth_result = logic.authenticate_user(email.strip(), password)
            if not auth_result:
                st.error("Invalid email or password. Please try again.")
            else:
                # Resolve user ID and role, store in session state, and reload
                user_id = auth_result.get("user_id") or auth_result.get("id") or email.strip()
                role = auth_result.get("role") or logic.get_user_role(user_id)
                st.session_state["user"] = auth_result
                st.session_state["role"] = role
                st.session_state["student_id"] = auth_result.get("student_id")
                st.session_state["demo_mode"] = False
                st.rerun()

        # Offer quick Demo Mode role buttons below the login form
        st.divider()
        demo_col1, demo_col2 = st.columns(2)
        if demo_col1.button("Preview as Faculty (Demo)", use_container_width=True):
            activate_demo_mode(role="faculty")
        if demo_col2.button("Preview as Student (Demo)", use_container_width=True):
            activate_demo_mode(role="student", student_id="STU002")


# ------------------------------------------------------------------------------
# Student Portal View (Read-Only)
# ------------------------------------------------------------------------------


def render_student_portal() -> None:
    """Render the read-only Student Portal scoped to the logged-in student."""
    # Read authenticated student details from session state
    user = st.session_state.get("user") or {}
    student_id = st.session_state.get("student_id")

    # Render sidebar identity badge and Logout button
    st.sidebar.header("Student Account")
    st.sidebar.write(f"**Email:** `{user.get('email', 'student@university.edu')}`")
    st.sidebar.info("Role: Student (Read-Only)")
    if st.sidebar.button("Logout", use_container_width=True):
        logout_user()

    # Display Student Portal title
    st.title("🎓 Student Performance Portal")
    st.caption("Read-only view of your attendance and subject marks.")

    # Fetch records from backend and normalize schema
    raw_df = logic.fetch_all_records()
    df = normalize_records_df(raw_df)

    # Handle empty dataset gracefully
    if df.empty:
        st.info("No records found. Upload a CSV or Excel file to begin.")
        return

    # Filter strictly to the logged-in student's ID (defaulting to first record in demo)
    target_id = student_id or str(df["student_id"].iloc[0])
    student_df = df[df["student_id"] == target_id].copy()

    # Show friendly message if this student has no uploaded records yet
    if student_df.empty:
        st.info("No records found. Upload a CSV or Excel file to begin.")
        return

    # Greet the student and compute personal summary metrics
    student_name = str(student_df["name"].iloc[0])
    st.subheader(f"Welcome, {student_name} (`{target_id}`)")

    avg_attendance = float(student_df["attendance"].mean())
    avg_marks = float(student_df["marks"].mean())

    # Display personal KPI cards
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Overall Attendance (%)", f"{avg_attendance:.1f}%")
    kpi2.metric("Average Marks", f"{avg_marks:.1f}")
    kpi3.metric("Subjects Enrolled", f"{len(student_df)}")

    # Evaluate each subject against 75% attendance and 40 pass mark thresholds
    student_df["Flag Reason"] = student_df.apply(
        lambda r: compute_flag_reason(float(r["attendance"]), float(r["marks"]), DEFAULT_PASS_MARK),
        axis=1,
    )
    at_risk_df = student_df[student_df["Flag Reason"] != "On Track"]

    # Show status alerts for any subject needing attention, or a success banner
    if not at_risk_df.empty:
        for _, row in at_risk_df.iterrows():
            st.warning(
                f"**{row['subject']}** — {row['Flag Reason']} "
                f"(Attendance: {row['attendance']:.1f}%, Marks: {row['marks']:.1f})"
            )
    else:
        st.success("All subjects meet the 75% attendance and 40 pass mark thresholds.")

    st.divider()

    # Render side-by-side bar charts for the student's attendance and marks
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**Attendance (%) by Subject**")
        st.bar_chart(student_df.set_index("subject")["attendance"])
    with chart_col2:
        st.markdown("**Marks by Subject**")
        st.bar_chart(student_df.set_index("subject")["marks"])

    # Display styled subject breakdown table
    st.subheader("Subject Breakdown")
    display_df = student_df[["subject", "attendance", "marks", "Flag Reason"]].rename(
        columns={"subject": "Subject", "attendance": "Attendance (%)", "marks": "Marks"}
    )
    styled_df = display_df.style.apply(highlight_flagged_rows, axis=1).format(
        {"Attendance (%)": "{:.1f}%", "Marks": "{:.1f}"}
    )
    st.dataframe(styled_df, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------------------
# Faculty Dashboard View
# ------------------------------------------------------------------------------


def render_faculty_dashboard() -> None:
    """Render the full Faculty Dashboard with upload, thresholds, KPIs, and tabs."""
    # Read authenticated faculty user info from session state
    user = st.session_state.get("user") or {}

    # Sidebar Section 1: Account & Logout
    st.sidebar.header("Faculty Account")
    st.sidebar.write(f"**Email:** `{user.get('email', 'faculty@university.edu')}`")
    st.sidebar.success("Role: Faculty")
    if st.sidebar.button("Logout", use_container_width=True):
        logout_user()

    st.sidebar.divider()

    # Sidebar Section 2: CSV / Excel Data Upload & Preview
    st.sidebar.header("Data Upload")
    uploaded_file = st.sidebar.file_uploader(
        "Upload Student Records (.csv or .xlsx)",
        type=["csv", "xlsx"],
        help="Expected columns: student_id, name, subject, attendance, marks",
    )

    # Parse, preview, and save the uploaded file when provided
    if uploaded_file is not None:
        try:
            # Read CSV or Excel file based on extension
            if uploaded_file.name.lower().endswith(".csv"):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file, engine="openpyxl")

            # Show a 5-row preview of the uploaded DataFrame in the sidebar
            st.sidebar.caption("Preview (first 5 rows):")
            st.sidebar.dataframe(uploaded_df.head(), use_container_width=True, hide_index=True)

            # Trigger backend save_records() when the user clicks "Save to Database"
            if st.sidebar.button("Save to Database", type="primary", use_container_width=True):
                normalized_upload = normalize_records_df(uploaded_df)
                if normalized_upload.empty:
                    st.sidebar.error(
                        f"Invalid schema. Required columns: {', '.join(EXPECTED_COLUMNS)}."
                    )
                else:
                    ok, message = logic.save_records(normalized_upload)
                    if ok:
                        st.sidebar.success(message)
                        st.rerun()
                    else:
                        st.sidebar.error(message)
        except Exception as exc:
            st.sidebar.error(f"Failed to read uploaded file: {exc}")

    st.sidebar.divider()

    # Sidebar Section 3: Threshold & Filter Controls
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
    # Display the fixed 75% attendance requirement clearly
    st.sidebar.info(f"Minimum Attendance Threshold: **{MIN_ATTENDANCE_THRESHOLD:.0f}%** (Fixed)")

    # Main Dashboard Header
    st.title("📊 Student Attendance & Performance Insights Dashboard")
    st.caption("SW-12 | Faculty Analytics & At-Risk Student Monitoring")

    # Fetch records from backend hook (or mock fallback) and normalize columns
    raw_df = logic.fetch_all_records()
    df = normalize_records_df(raw_df)

    # Handle empty database state gracefully
    if df.empty:
        st.info("No records found. Upload a CSV or Excel file to begin.")
        return

    # Build Subject filter selectbox in the sidebar
    subjects = ["All Subjects"] + sorted(df["subject"].dropna().unique().tolist())
    selected_subject = st.sidebar.selectbox("Filter by Subject", options=subjects)

    # Filter the dataset by the selected subject
    filtered_df = df if selected_subject == "All Subjects" else df[df["subject"] == selected_subject].copy()
    if filtered_df.empty:
        st.info("No records found. Upload a CSV or Excel file to begin.")
        return

    # Compute Flag Reason for every row and isolate at-risk rows
    filtered_df = filtered_df.copy()
    filtered_df["Flag Reason"] = filtered_df.apply(
        lambda r: compute_flag_reason(float(r["attendance"]), float(r["marks"]), pass_mark),
        axis=1,
    )
    at_risk_df = filtered_df[filtered_df["Flag Reason"] != "On Track"].copy()

    # Compute and render the 4 top-level KPI metrics
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

    # Create the 3 main navigation tabs
    tab1, tab2, tab3 = st.tabs(
        [
            "🚨 At-Risk Alerts",
            "📚 Subject-Wise Insights",
            "🎓 Student-Wise Insights",
        ]
    )

    # Tab 1: At-Risk Alerts (Priority View)
    with tab1:
        st.subheader("At-Risk Alerts (Priority View)")
        if at_risk_df.empty:
            st.success("No at-risk students found under the current thresholds.")
        else:
            # Rename columns for clean display and apply light-red row highlighting
            alerts_display = at_risk_df[
                ["student_id", "name", "subject", "attendance", "marks", "Flag Reason"]
            ].rename(
                columns={
                    "student_id": "Student ID",
                    "name": "Name",
                    "subject": "Subject",
                    "attendance": "Attendance (%)",
                    "marks": "Marks",
                }
            )
            styled_alerts = alerts_display.style.apply(highlight_flagged_rows, axis=1).format(
                {"Attendance (%)": "{:.1f}%", "Marks": "{:.1f}"}
            )
            st.dataframe(styled_alerts, use_container_width=True, hide_index=True)

    # Tab 2: Subject-Wise Insights
    with tab2:
        st.subheader("Subject-Wise Insights")
        # Aggregate unique student count, average attendance, and average marks per subject
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

        # Render side-by-side bar charts for attendance and marks
        chart_left, chart_right = st.columns(2)
        with chart_left:
            st.markdown("**Average Attendance (%) by Subject**")
            st.bar_chart(subject_summary.set_index("subject")["avg_attendance"])
        with chart_right:
            st.markdown("**Average Marks by Subject**")
            st.bar_chart(subject_summary.set_index("subject")["avg_marks"])

        # Display the aggregated subject summary table
        st.markdown("**Subject Summary Table**")
        summary_display = subject_summary.rename(
            columns={
                "subject": "Subject",
                "students": "Students",
                "avg_attendance": "Avg Attendance (%)",
                "avg_marks": "Avg Marks",
            }
        )
        st.dataframe(summary_display, use_container_width=True, hide_index=True)

    # Tab 3: Student-Wise Insights
    with tab3:
        st.subheader("Student-Wise Insights")
        # Build unique student options formatted as "student_id — name"
        student_options_df = (
            filtered_df[["student_id", "name"]]
            .drop_duplicates()
            .sort_values("student_id")
        )
        student_labels = [
            f"{row['student_id']} — {row['name']}"
            for _, row in student_options_df.iterrows()
        ]
        chosen_label = st.selectbox("Select Student", options=student_labels)
        chosen_id = chosen_label.split(" — ")[0].strip()

        # Filter records for the selected student and compute overall averages
        single_student_df = filtered_df[filtered_df["student_id"] == chosen_id].copy()
        s_att = float(single_student_df["attendance"].mean())
        s_marks = float(single_student_df["marks"].mean())

        # Display overall metrics for the chosen student
        sk1, sk2 = st.columns(2)
        sk1.metric("Overall Attendance (%)", f"{s_att:.1f}%")
        sk2.metric("Overall Average Marks", f"{s_marks:.1f}")

        # Render grouped bar chart of subject-wise attendance and marks
        st.markdown(f"**Subject-Wise Attendance & Marks — {chosen_label}**")
        chart_df = single_student_df.set_index("subject")[["attendance", "marks"]].rename(
            columns={"attendance": "Attendance (%)", "marks": "Marks"}
        )
        st.bar_chart(chart_df)

        # Display detailed subject breakdown table with Pandas Styler highlighting
        st.markdown("**Detailed Subject Breakdown**")
        breakdown_df = single_student_df[
            ["subject", "attendance", "marks", "Flag Reason"]
        ].rename(
            columns={
                "subject": "Subject",
                "attendance": "Attendance (%)",
                "marks": "Marks",
            }
        )
        styled_breakdown = breakdown_df.style.apply(highlight_flagged_rows, axis=1).format(
            {"Attendance (%)": "{:.1f}%", "Marks": "{:.1f}"}
        )
        st.dataframe(styled_breakdown, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------------------
# Main Application Entrypoint
# ------------------------------------------------------------------------------


def main() -> None:
    """Route visitors to Login, Student Portal, or Faculty Dashboard based on session state."""
    # Ensure required session keys exist before checking authentication
    init_session_state()

    # Show the login screen if no user is authenticated
    if st.session_state.get("user") is None:
        render_login_screen()
        return

    # Route authenticated users to either the Student Portal or Faculty Dashboard
    if st.session_state.get("role") == "student":
        render_student_portal()
    else:
        render_faculty_dashboard()


# Execute the Streamlit app entrypoint
if __name__ == "__main__":
    main()