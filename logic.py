"""
logic.py - the backend of the Student Attendance & Performance Dashboard.

app.py (the webpage) calls the 4 "hook" functions defined here:
    authenticate_user, get_user_role, fetch_all_records, save_records

This file has two parts:
    Part A - Login & authorization, handled by Supabase (Auth + `profiles` table)
    Part B - Student data, read live from Google Sheets through shareable links

The two parts are linked by one common value: `student_id`.
    - Supabase `profiles.student_id`  -> says which student a login belongs to
    - Google Sheet column `student id` -> says which student a row belongs to
"""

import io
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st

# `supabase` is only needed for real login. If it is not installed,
# app.py falls back to demo mode instead of crashing.
try:
    from supabase import create_client
except ImportError:  # pragma: no cover
    create_client = None

# The 5 columns every class Google Sheet must have (header names are matched
# case-insensitively, and "student id" / "student_id" / "Student-ID" all work).
REQUIRED_COLUMNS: List[str] = ["student_id", "name", "subject", "attendance", "marks"]

# How long (seconds) a downloaded sheet is remembered before Google is asked again.
# This is what makes the dashboard "live": edits in the sheet show up within ~1 minute.
CACHE_SECONDS: int = 60


# ------------------------------------------------------------------------------
# Part A: Supabase login & authorization
# ------------------------------------------------------------------------------

def is_configured() -> bool:
    """Return True only if the Supabase library and secrets are available."""
    try:
        return bool(create_client) and bool(st.secrets["SUPABASE_URL"]) and bool(st.secrets["SUPABASE_ANON_KEY"])
    except Exception:
        return False


def _client():
    """Give each browser session its OWN Supabase client.

    Important: the client remembers who is logged in, so it must never be shared
    between different users (that is why it lives in session_state and is not cached globally).
    """
    if "_sb_client" not in st.session_state:
        st.session_state["_sb_client"] = create_client(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"]
        )
    return st.session_state["_sb_client"]


@st.cache_resource
def _service_client():
    """Optional server-side client using the service-role key (never shown to users).

    It is used only to read the list of class sheet links, so students can see
    their own marks without being allowed to read the class list themselves.
    """
    try:
        key = st.secrets.get("SUPABASE_SERVICE_KEY")
        if not key:
            return None
        return create_client(st.secrets["SUPABASE_URL"], key)
    except Exception:
        return None


def _registry_client():
    """Use the service client for reading classes if available, else the user's own client."""
    return _service_client() or _client()


def _fetch_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Look up this user's role and student_id in the `profiles` table."""
    try:
        result = (
            _client()
            .table("profiles")
            .select("role, student_id, full_name")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Log in with Supabase and return the user's profile, or None if login is not allowed."""
    st.session_state.pop("auth_error", None)
    if not email or not password:
        return None

    try:
        response = _client().auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        st.session_state["auth_error"] = "Invalid email or password. Please try again."
        return None

    user = response.user
    if user is None:
        st.session_state["auth_error"] = "Invalid email or password. Please try again."
        return None

    # Authorization: a valid password alone is not enough. The account must also
    # have a profile row that says whether it is a student or faculty member.
    profile = _fetch_profile(user.id)
    if profile is None or profile.get("role") not in ("student", "faculty"):
        sign_out()
        st.session_state["auth_error"] = "Your account is not set up yet. Please contact the administrator."
        return None

    student_id = (profile.get("student_id") or "").strip().upper() or None
    if profile["role"] == "student" and not student_id:
        sign_out()
        st.session_state["auth_error"] = "Your account is not linked to a Student ID. Please contact the administrator."
        return None

    return {
        "user_id": user.id,
        "email": user.email or email.strip(),
        "role": profile["role"],
        "student_id": student_id,
        "full_name": profile.get("full_name"),
    }


def get_user_role(user_id: str) -> str:
    """Return 'faculty' or 'student'. If unsure, give the LOWER permission (student)."""
    profile = _fetch_profile(user_id)
    if profile and profile.get("role") == "faculty":
        return "faculty"
    return "student"


def sign_out() -> None:
    """End the Supabase session and forget this browser session's client."""
    try:
        _client().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("_sb_client", None)


# ------------------------------------------------------------------------------
# Part B: Google Sheets (read through shareable links)
# ------------------------------------------------------------------------------

def sheet_link_to_csv_url(link: str) -> str:
    """Turn a normal Google Sheets share link into a direct CSV download link.

    Works with:
      - https://docs.google.com/spreadsheets/d/<ID>/edit?usp=sharing
      - the same link with  #gid=123456  (picks a specific tab)
      - "Publish to web" links  (.../spreadsheets/d/e/<ID>/pubhtml)
    """
    link = (link or "").strip()
    gid_match = re.search(r"[#&?]gid=(\d+)", link)
    gid_part = f"&gid={gid_match.group(1)}" if gid_match else ""

    published = re.search(r"/spreadsheets/d/e/([\w-]+)", link)
    if published:
        return f"https://docs.google.com/spreadsheets/d/e/{published.group(1)}/pub?output=csv{gid_part}"

    normal = re.search(r"/spreadsheets/d/([\w-]+)", link)
    if not normal:
        raise ValueError("That does not look like a Google Sheets link.")
    return f"https://docs.google.com/spreadsheets/d/{normal.group(1)}/export?format=csv{gid_part}"


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def _download_sheet(csv_url: str) -> pd.DataFrame:
    """Download one sheet as a table. Results are remembered for CACHE_SECONDS."""
    response = requests.get(csv_url, timeout=20)
    content_type = response.headers.get("Content-Type", "")
    if response.status_code in (401, 403, 404) or "text/html" in content_type:
        raise PermissionError(
            "Could not read the sheet. In Google Sheets click Share -> General access -> "
            "'Anyone with the link' (Viewer)."
        )
    response.raise_for_status()
    response.encoding = "utf-8"
    # dtype=str keeps IDs like "007" exactly as typed; numbers are converted later in app.py.
    return pd.read_csv(io.StringIO(response.text), dtype=str)


def _standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make headers like 'Student ID' / 'student-id' become 'student_id'."""
    cleaned = df.copy()
    cleaned.columns = [re.sub(r"[\s\-]+", "_", str(col).strip().lower()) for col in cleaned.columns]
    return cleaned


def load_class_sheet(class_name: str, sheet_link: str) -> pd.DataFrame:
    """Load one class's Google Sheet and check that the 5 required columns exist."""
    raw = _download_sheet(sheet_link_to_csv_url(sheet_link))
    df = _standardise_columns(raw)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"missing column(s): {', '.join(missing)}. "
            "The first row must contain: student id, name, subject, attendance, marks."
        )

    df = df[REQUIRED_COLUMNS].copy()
    df["class_name"] = class_name
    return df


def list_classes() -> List[Dict[str, Any]]:
    """Return the registered classes: [{'id', 'class_name', 'sheet_url'}, ...]."""
    result = (
        _registry_client()
        .table("classes")
        .select("id, class_name, sheet_url")
        .order("class_name")
        .execute()
    )
    return result.data or []


def add_class(class_name: str, sheet_link: str) -> Tuple[bool, str]:
    """Register a new class. The sheet is test-loaded first, so broken links are rejected."""
    class_name = (class_name or "").strip()
    sheet_link = (sheet_link or "").strip()
    if not class_name or not sheet_link:
        return False, "Please enter both a class name and a Google Sheet link."

    try:
        load_class_sheet(class_name, sheet_link)
    except Exception as exc:
        return False, f"Could not use that sheet: {exc}"

    try:
        _client().table("classes").insert({"class_name": class_name, "sheet_url": sheet_link}).execute()
    except Exception as exc:
        return False, f"Could not save the class (class names must be unique, and only faculty can add classes): {exc}"

    return True, f"Added class '{class_name}'."


def remove_class(class_id: str) -> Tuple[bool, str]:
    """Remove a class from the list (the Google Sheet itself is not touched)."""
    try:
        _client().table("classes").delete().eq("id", class_id).execute()
        return True, "Class removed."
    except Exception as exc:
        return False, f"Could not remove the class: {exc}"


def refresh_data() -> None:
    """Forget remembered sheets so the next load asks Google again."""
    st.cache_data.clear()


def fetch_all_records() -> pd.DataFrame:
    """Load every registered class sheet and stack them into one table (adds a `class_name` column).

    If one sheet is broken, the others still load; the problems are saved in
    st.session_state["sheet_errors"] so app.py can show them.
    """
    empty = pd.DataFrame(columns=REQUIRED_COLUMNS + ["class_name"])
    try:
        classes = list_classes()
    except Exception as exc:
        st.session_state["sheet_errors"] = [f"Could not read the class list: {exc}"]
        return empty

    frames: List[pd.DataFrame] = []
    errors: List[str] = []
    for item in classes:
        try:
            frames.append(load_class_sheet(item["class_name"], item["sheet_url"]))
        except Exception as exc:
            errors.append(f"{item['class_name']}: {exc}")

    st.session_state["sheet_errors"] = errors
    if not frames:
        return empty
    return pd.concat(frames, ignore_index=True)


def save_records(df: pd.DataFrame) -> Tuple[bool, str]:
    """Uploads are not used in live mode: the Google Sheets are the single source of truth."""
    return False, "Records now come from Google Sheets. Edit the sheet (or add a class) instead of uploading."
