"""
Student Attendance & Performance Insights Dashboard (Problem Statement SW-12)
This file (`app.py`) builds the visual webpage that users interact with.
All database and login work is kept separate in `logic.py` (with built-in sample data if `logic.py` is not ready yet).
"""

# Bring in helper tools that let us describe what kind of data each function expects (text, numbers, lists, etc.)
from typing import Any, Dict, List, Optional, Tuple

# Bring in 'pandas' (used for working with spreadsheet-style tables) and 'streamlit' (used to draw the website)
import pandas as pd
import streamlit as st

# Set the school's fixed minimum attendance rule: any student below 75% will be flagged
MIN_ATTENDANCE_THRESHOLD: float = 75.0
# Set the default passing score (40 out of 100); teachers can change this number on the screen
DEFAULT_PASS_MARK: float = 40.0
# List the exact 5 column names that every uploaded spreadsheet or database table must have
EXPECTED_COLUMNS: List[str] = ["student_id", "name", "subject", "attendance", "marks"]


# ------------------------------------------------------------------------------
# Section 1: Sample Data & Backup System (Used if `logic.py` is not connected yet)
# ------------------------------------------------------------------------------


def _build_mock_records() -> pd.DataFrame:
    """Create a small set of fake student records so the dashboard can be tested right away."""
    # Make a list of 15 pretend student-subject rows (covering good students and struggling students)
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
    # Turn that list into a structured table (DataFrame) with our 5 expected column names
    return pd.DataFrame(data, columns=EXPECTED_COLUMNS)


class _MockLogicModule:
    """A pretend version of the backend (`logic.py`) so this app still works even without a live database."""

    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
        # If the user left either the email or password box blank, reject the login
        if not email or not password:
            return None
        # Decide if this test login is a student or teacher based on whether "student" is in the email
        role = "student" if "student" in email.lower() else "faculty"
        # Hand back a pretend user profile containing an ID, email, and (for students) a student ID
        return {
            "user_id": "demo-user-001",
            "email": email.strip(),
            "student_id": "STU002" if role == "student" else None,
        }

    @staticmethod
    def get_user_role(user_id: str) -> str:
        # Check if the user ID mentions "student"; if not, treat the user as "faculty" (a teacher)
        return "student" if "student" in str(user_id).lower() else "faculty"

    @staticmethod
    def fetch_all_records() -> pd.DataFrame:
        # The first time we need data, save our pretend student table into the browser's temporary memory
        if "mock_records_df" not in st.session_state:
            st.session_state["mock_records_df"] = _build_mock_records()
        # Return a fresh copy of the table so viewing or filtering it doesn't accidentally alter the original
        return st.session_state["mock_records_df"].copy()

    @staticmethod
    def save_records(df: pd.DataFrame) -> Tuple[bool, str]:
        # Stop and show an error if someone tries to save an empty spreadsheet
        if df.empty:
            return False, "Cannot save an empty DataFrame."
        # Replace the pretend stored data in browser memory with the newly uploaded table
        st.session_state["mock_records_df"] = df.copy()
        # Report back that the save succeeded and tell the user how many rows were saved
        return True, f"Saved {len(df)} record(s) to local demo store."


# Try to connect to the real `logic.py` file if it exists in the same folder
try:
    import logic as _imported_logic

    # Make sure `logic.py` actually contains all 4 required functions before using it
    required_hooks = ("authenticate_user", "get_user_role", "fetch_all_records", "save_records")
    if all(hasattr(_imported_logic, hook) for hook in required_hooks):
        # Success: use the real `logic.py` file and turn off mock mode
        logic = _imported_logic
        USING_MOCK_LOGIC = False
    else:
        # `logic.py` exists, but doesn't have those 4 functions yet—so use our pretend backup instead
        logic = _MockLogicModule()
        USING_MOCK_LOGIC = True
except ImportError:
    # `logic.py` doesn't exist yet—use our pretend backup so the app still runs smoothly
    logic = _MockLogicModule()
    USING_MOCK_LOGIC = True


# ------------------------------------------------------------------------------
# Section 2: Webpage Setup & Login Memory Helpers
# ------------------------------------------------------------------------------

# Set the browser tab name, small tab icon, and tell Streamlit to use the full width of the screen
st.set_page_config(
    page_title="Student Attendance & Performance Insights Dashboard",
    page_icon="📊",
    layout="wide",
)


def init_session_state() -> None:
    """Set up empty memory slots in the browser to remember who is logged in."""
    # These 4 slots keep track of: who is logged in, their role (teacher/student), their ID, and demo mode
    defaults: Dict[str, Any] = {
        "user": None,
        "role": None,
        "student_id": None,
        "demo_mode": False,
    }
    # Only create a slot if it doesn't already exist (so we don't erase someone who is already logged in)
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout_user() -> None:
    """Erase the current user's login memory and send them back to the login page."""
    # Clear all 4 login memory slots
    st.session_state["user"] = None
    st.session_state["role"] = None
    st.session_state["student_id"] = None
    st.session_state["demo_mode"] = False
    # Refresh the webpage immediately so the login screen appears
    st.rerun()


def activate_demo_mode(role: str = "faculty", student_id: Optional[str] = None) -> None:
    """Let someone preview the dashboard right away without typing a real email or password."""
    # Fill in a pretend user profile so the app thinks someone is logged in
    st.session_state["user"] = {
        "user_id": f"demo-{role}",
        "email": f"demo.{role}@institution.edu",
    }
    # Set whether we are previewing as a teacher ("faculty") or a "student"
    st.session_state["role"] = role
    st.session_state["student_id"] = student_id
    st.session_state["demo_mode"] = True
    # Refresh the webpage immediately to open the chosen dashboard
    st.rerun()


# ------------------------------------------------------------------------------
# Section 3: Table Cleanup & At-Risk Warning Rules
# ------------------------------------------------------------------------------


def normalize_records_df(df: pd.DataFrame) -> pd.DataFrame:
    """Clean up an uploaded or fetched table so all columns and numbers are formatted properly."""
    # If there is no data at all, return an empty table with the 5 expected column headers
    if df is None or df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    # Make a safe copy and convert all column headers to lowercase without extra spaces
    cleaned = df.copy()
    cleaned.columns = [str(col).strip().lower() for col in cleaned.columns]
    # Check that every required column is present; if any is missing, return an empty table
    for col in EXPECTED_COLUMNS:
        if col not in cleaned.columns:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)

    # Keep only the 5 required columns and trim extra spaces from text fields
    cleaned = cleaned[EXPECTED_COLUMNS].copy()
    cleaned["student_id"] = cleaned["student_id"].astype(str).str.strip()
    cleaned["name"] = cleaned["name"].astype(str).str.strip()
    cleaned["subject"] = cleaned["subject"].astype(str).str.strip()
    # Make sure attendance and marks are treated as decimal numbers (turn invalid blanks into 0.0)
    cleaned["attendance"] = pd.to_numeric(cleaned["attendance"], errors="coerce").fillna(0.0)
    cleaned["marks"] = pd.to_numeric(cleaned["marks"], errors="coerce").fillna(0.0)
    return cleaned


def compute_flag_reason(attendance: float, marks: float, pass_mark: float) -> str:
    """Decide whether a student is 'On Track' or needs attention in a subject."""
    # Check if attendance is under 75% and if marks are under the passing score
    low_attendance = attendance < MIN_ATTENDANCE_THRESHOLD
    low_marks = marks < pass_mark
    # Return a clear label explaining why the student was flagged
    if low_attendance and low_marks:
        return "Both"
    if low_attendance:
        return "Low Attendance"
    if low_marks:
        return "Low Marks"
    return "On Track"


def highlight_flagged_rows(row: pd.Series) -> List[str]:
    """Color a table row light red whenever the student is flagged for low attendance or low marks."""
    # If the row's status is anything other than "On Track", paint every cell in that row light red
    if row.get("Flag Reason", "On Track") != "On Track":
        return ["background-color: #FADBD8; color: #78281F"] * len(row)
    # Otherwise, leave the row with its normal white/default background
    return [""] * len(row)


# ------------------------------------------------------------------------------
# Section 4: Login Screen (Shown before a user signs in)
# ------------------------------------------------------------------------------


def render_login_screen() -> None:
    """Draw the Login page, including the email/password box and quick Demo Mode buttons."""
    # Show the main dashboard title and a short description at the top
    st.title("📊 Student Attendance & Performance Insights Dashboard")
    st.caption("SW-12 | Sign in to access the Faculty Analytics Dashboard or Student Portal.")

    # Let the user know if the app is currently running with built-in sample data
    if USING_MOCK_LOGIC:
        st.info("Running with built-in demo data (`logic.py` hooks not detected). Use **Demo Mode** or any credentials to preview.")

    # Add a quick "Demo Mode" button in the left sidebar so anyone can skip login during testing
    st.sidebar.header("Developer Preview")
    if st.sidebar.button("Demo Mode (Bypass Login)", use_container_width=True):
        activate_demo_mode(role="faculty")

    # Create 3 columns and use only the middle one so the login box sits neatly in the center
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        # Draw the login box with Email, Password, and a "Log In" button
        with st.form("login_form"):
            st.subheader("Sign In")
            email = st.text_input("Email", placeholder="faculty@university.edu")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)

        # When the user clicks "Log In", check their email and password with `logic.py`
        if submitted:
            auth_result = logic.authenticate_user(email.strip(), password)
            if not auth_result:
                # Show a red error message if the login failed
                st.error("Invalid email or password. Please try again.")
            else:
                # Look up whether this user is a teacher ("faculty") or a "student"
                user_id = auth_result.get("user_id") or auth_result.get("id") or email.strip()
                role = auth_result.get("role") or logic.get_user_role(user_id)
                # Save their login details in browser memory and refresh into their dashboard
                st.session_state["user"] = auth_result
                st.session_state["role"] = role
                st.session_state["student_id"] = auth_result.get("student_id")
                st.session_state["demo_mode"] = False
                st.rerun()

        # Draw a horizontal line and two quick buttons to preview Faculty or Student views
        st.divider()
        demo_col1, demo_col2 = st.columns(2)
        if demo_col1.button("Preview as Faculty (Demo)", use_container_width=True):
            activate_demo_mode(role="faculty")
        if demo_col2.button("Preview as Student (Demo)", use_container_width=True):
            activate_demo_mode(role="student", student_id="STU002")


# ------------------------------------------------------------------------------
# Section 5: Student Portal (Read-only view showing only one student's own data)
# ------------------------------------------------------------------------------


def render_student_portal() -> None:
    """Draw the restricted Student Portal so a student only sees their own grades and attendance."""
    # Look up who is currently logged in from browser memory
    user = st.session_state.get("user") or {}
    student_id = st.session_state.get("student_id")

    # Show the student's email, role badge, and a Logout button in the left sidebar
    st.sidebar.header("Student Account")
    st.sidebar.write(f"**Email:** `{user.get('email', 'student@university.edu')}`")
    st.sidebar.info("Role: Student (Read-Only)")
    if st.sidebar.button("Logout", use_container_width=True):
        logout_user()

    # Show the page title for the Student Portal
    st.title("🎓 Student Performance Portal")
    st.caption("Read-only view of your attendance and subject marks.")

    # Load all student records from `logic.py` and clean up the table format
    raw_df = logic.fetch_all_records()
    df = normalize_records_df(raw_df)

    # If the database has no records yet, show a helpful message and stop here
    if df.empty:
        st.info("No records found. Upload a CSV or Excel file to begin.")
        return

    # Keep ONLY the rows that belong to this specific student (hiding everyone else's data)
    target_id = student_id or str(df["student_id"].iloc[0])
    student_df = df[df["student_id"] == target_id].copy()

    # If no rows match this student's ID, show a friendly message and stop
    if student_df.empty:
        st.info("No records found. Upload a CSV or Excel file to begin.")
        return

    # Greet the student by name and calculate their average attendance and average marks
    student_name = str(student_df["name"].iloc[0])
    st.subheader(f"Welcome, {student_name} (`{target_id}`)")

    avg_attendance = float(student_df["attendance"].mean())
    avg_marks = float(student_df["marks"].mean())

    # Show 3 summary number cards side by side
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Overall Attendance (%)", f"{avg_attendance:.1f}%")
    kpi2.metric("Average Marks", f"{avg_marks:.1f}")
    kpi3.metric("Subjects Enrolled", f"{len(student_df)}")

    # Check every subject to see if attendance is under 75% or marks are under 40
    student_df["Flag Reason"] = student_df.apply(
        lambda r: compute_flag_reason(float(r["attendance"]), float(r["marks"]), DEFAULT_PASS_MARK),
        axis=1,
    )
    # Collect only the subjects that triggered a warning
    at_risk_df = student_df[student_df["Flag Reason"] != "On Track"]

    # Show yellow warning boxes for any subject that needs improvement, or a green success box
    if not at_risk_df.empty:
        for _, row in at_risk_df.iterrows():
            st.warning(
                f"**{row['subject']}** — {row['Flag Reason']} "
                f"(Attendance: {row['attendance']:.1f}%, Marks: {row['marks']:.1f})"
            )
    else:
        st.success("All subjects meet the 75% attendance and 40 pass mark thresholds.")

    st.divider()

    # Draw two bar charts side by side: one for Attendance % and one for Marks
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**Attendance (%) by Subject**")
        st.bar_chart(student_df.set_index("subject")["attendance"])
    with chart_col2:
        st.markdown("**Marks by Subject**")
        st.bar_chart(student_df.set_index("subject")["marks"])

    # Show the student's detailed table with light-red highlighting on any flagged subjects
    st.subheader("Subject Breakdown")
    display_df = student_df[["subject", "attendance", "marks", "Flag Reason"]].rename(
        columns={"subject": "Subject", "attendance": "Attendance (%)", "marks": "Marks"}
    )
    styled_df = display_df.style.apply(highlight_flagged_rows, axis=1).format(
        {"Attendance (%)": "{:.1f}%", "Marks": "{:.1f}"}
    )
    st.dataframe(styled_df, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------------------
# Section 6: Faculty Dashboard (Full teacher view with uploads, filters, and charts)
# ------------------------------------------------------------------------------


def render_faculty_dashboard() -> None:
    """Draw the full Faculty Dashboard with file uploads, threshold controls, KPIs, and 3 tabs."""
    # Look up the logged-in teacher's details from browser memory
    user = st.session_state.get("user") or {}

    # Sidebar Part 1: Show who is signed in and provide a Logout button
    st.sidebar.header("Faculty Account")
    st.sidebar.write(f"**Email:** `{user.get('email', 'faculty@university.edu')}`")
    st.sidebar.success("Role: Faculty")
    if st.sidebar.button("Logout", use_container_width=True):
        logout_user()

    st.sidebar.divider()

    # Sidebar Part 2: File uploader so teachers can upload CSV or Excel spreadsheets
    st.sidebar.header("Data Upload")
    uploaded_file = st.sidebar.file_uploader(
        "Upload Student Records (.csv or .xlsx)",
        type=["csv", "xlsx"],
        help="Expected columns: student_id, name, subject, attendance, marks",
    )

    # If the teacher selected a file, read it, show a preview, and offer a "Save to Database" button
    if uploaded_file is not None:
        try:
            # Use the CSV reader for .csv files or the Excel reader for .xlsx files
            if uploaded_file.name.lower().endswith(".csv"):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file, engine="openpyxl")

            # Display the first 5 rows in the sidebar so the teacher can double-check their file
            st.sidebar.caption("Preview (first 5 rows):")
            st.sidebar.dataframe(uploaded_df.head(), use_container_width=True, hide_index=True)

            # When "Save to Database" is clicked, validate the columns and send the data to `logic.py`
            if st.sidebar.button("Save to Database", type="primary", use_container_width=True):
                normalized_upload = normalize_records_df(uploaded_df)
                if normalized_upload.empty:
                    # Tell the user if the file is missing any of the 5 required columns
                    st.sidebar.error(
                        f"Invalid schema. Required columns: {', '.join(EXPECTED_COLUMNS)}."
                    )
                else:
                    # Save the cleaned table and show either a green success or red error message
                    ok, message = logic.save_records(normalized_upload)
                    if ok:
                        st.sidebar.success(message)
                        st.rerun()
                    else:
                        st.sidebar.error(message)
        except Exception as exc:
            # Show a clear error if the uploaded file is corrupted or unreadable
            st.sidebar.error(f"Failed to read uploaded file: {exc}")

    st.sidebar.divider()

    # Sidebar Part 3: Let the teacher adjust the Pass Mark (default 40) and view the fixed 75% rule
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
    # Display a note reminding the teacher that 75% minimum attendance is fixed
    st.sidebar.info(f"Minimum Attendance Threshold: **{MIN_ATTENDANCE_THRESHOLD:.0f}%** (Fixed)")

    # Main Page Title
    st.title("📊 Student Attendance & Performance Insights Dashboard")
    st.caption("SW-12 | Faculty Analytics & At-Risk Student Monitoring")

    # Fetch all saved student records from `logic.py` and clean up the table
    raw_df = logic.fetch_all_records()
    df = normalize_records_df(raw_df)

    # If no records exist yet, show a helpful prompt instead of crashing
    if df.empty:
        st.info("No records found. Upload a CSV or Excel file to begin.")
        return

    # Build a dropdown menu in the sidebar so the teacher can filter by a specific subject
    subjects = ["All Subjects"] + sorted(df["subject"].dropna().unique().tolist())
    selected_subject = st.sidebar.selectbox("Filter by Subject", options=subjects)

    # Keep all rows if "All Subjects" is chosen, or filter down to just the chosen subject
    filtered_df = df if selected_subject == "All Subjects" else df[df["subject"] == selected_subject].copy()
    if filtered_df.empty:
        st.info("No records found. Upload a CSV or Excel file to begin.")
        return

    # Check every row against the 75% attendance rule and the teacher's Pass Mark setting
    filtered_df = filtered_df.copy()
    filtered_df["Flag Reason"] = filtered_df.apply(
        lambda r: compute_flag_reason(float(r["attendance"]), float(r["marks"]), pass_mark),
        axis=1,
    )
    # Create a separate table containing only the rows that failed one or both rules
    at_risk_df = filtered_df[filtered_df["Flag Reason"] != "On Track"].copy()

    # Calculate the 4 top summary numbers (total students, avg attendance, avg marks, at-risk count)
    total_students = int(filtered_df["student_id"].nunique())
    avg_attendance = float(filtered_df["attendance"].mean())
    avg_marks = float(filtered_df["marks"].mean())
    flagged_students_count = int(at_risk_df["student_id"].nunique()) if not at_risk_df.empty else 0

    # Display those 4 summary numbers as metric cards across the top of the dashboard
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Students", f"{total_students}")
    col2.metric("Average Attendance (%)", f"{avg_attendance:.1f}%")
    col3.metric("Average Marks", f"{avg_marks:.1f}")
    col4.metric("Flagged At-Risk Students", f"{flagged_students_count}")

    st.divider()

    # Split the main dashboard into 3 clickable tabs
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
            # Show a green confirmation message if every student is passing and attending enough
            st.success("No at-risk students found under the current thresholds.")
        else:
            # Format column titles nicely and highlight every flagged row in light red
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

    # Tab 2: Compare average attendance and marks across different subjects
    with tab2:
        st.subheader("Subject-Wise Insights")
        # Group all records by subject to find student count, average attendance, and average marks
        subject_summary = (
            filtered_df.groupby("subject", as_index=False)
            .agg(
                students=("student_id", "nunique"),
                avg_attendance=("attendance", "mean"),
                avg_marks=("marks", "mean"),
            )
            .sort_values("subject")
        )
        # Round averages to 2 decimal places for cleaner charts and tables
        subject_summary["avg_attendance"] = subject_summary["avg_attendance"].round(2)
        subject_summary["avg_marks"] = subject_summary["avg_marks"].round(2)

        # Draw two bar charts side by side: Attendance % on the left, Marks on the right
        chart_left, chart_right = st.columns(2)
        with chart_left:
            st.markdown("**Average Attendance (%) by Subject**")
            st.bar_chart(subject_summary.set_index("subject")["avg_attendance"])
        with chart_right:
            st.markdown("**Average Marks by Subject**")
            st.bar_chart(subject_summary.set_index("subject")["avg_marks"])

        # Display the subject-by-subject summary table underneath the charts
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

    # Tab 3: Inspect one individual student in detail
    with tab3:
        st.subheader("Student-Wise Insights")
        # Build a dropdown list of every unique student formatted as "ID — Name"
        student_options_df = (
            filtered_df[["student_id", "name"]]
            .drop_duplicates()
            .sort_values("student_id")
        )
        student_labels = [
            f"{row['student_id']} — {row['name']}"
            for _, row in student_options_df.iterrows()
        ]
        # Let the teacher pick a student from the dropdown
        chosen_label = st.selectbox("Select Student", options=student_labels)
        chosen_id = chosen_label.split(" — ")[0].strip()

        # Filter down to only the chosen student's subjects and calculate their overall averages
        single_student_df = filtered_df[filtered_df["student_id"] == chosen_id].copy()
        s_att = float(single_student_df["attendance"].mean())
        s_marks = float(single_student_df["marks"].mean())

        # Show the selected student's overall attendance and average marks
        sk1, sk2 = st.columns(2)
        sk1.metric("Overall Attendance (%)", f"{s_att:.1f}%")
        sk2.metric("Overall Average Marks", f"{s_marks:.1f}")

        # Draw a bar chart comparing the student's attendance and marks in each subject
        st.markdown(f"**Subject-Wise Attendance & Marks — {chosen_label}**")
        chart_df = single_student_df.set_index("subject")[["attendance", "marks"]].rename(
            columns={"attendance": "Attendance (%)", "marks": "Marks"}
        )
        st.bar_chart(chart_df)

        # Show a detailed subject table for that student with light-red highlighting on flagged rows
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
# Section 7: Application Starting Point
# ------------------------------------------------------------------------------


def main() -> None:
    """Decide which screen to show: Login, Student Portal, or Faculty Dashboard."""
    # Make sure the browser's login memory slots are set up
    init_session_state()

    # If nobody is logged in yet, show the Login screen and stop
    if st.session_state.get("user") is None:
        render_login_screen()
        return

    # If the logged-in user is a student, show the read-only Student Portal; otherwise show Faculty Dashboard
    if st.session_state.get("role") == "student":
        render_student_portal()
    else:
        render_faculty_dashboard()


# Run the main() function whenever Streamlit starts this file
if __name__ == "__main__":
    main()