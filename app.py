import os
import json
import random
import uuid
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Grivalia Social Hub", page_icon="💬", layout="wide")
st.set_option("client.showErrorDetails", False)

st.markdown("""
<style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1280px;
    }

    .main {
        background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
    }

    .hero-wrap {
        background:
            radial-gradient(circle at top right, rgba(96,165,250,0.22), transparent 28%),
            radial-gradient(circle at bottom left, rgba(139,92,246,0.16), transparent 22%),
            linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #60a5fa 100%);
        border-radius: 24px;
        padding: 1.8rem 1.8rem 1.5rem 1.8rem;
        color: white;
        margin-bottom: 1rem;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.24);
    }

    .hero-kicker {
        display: inline-block;
        font-size: 0.82rem;
        font-weight: 700;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.12);
        backdrop-filter: blur(6px);
        margin-bottom: 0.8rem;
    }

    .hero-title {
        font-size: 2.25rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.3rem;
        line-height: 1.1;
    }

    .hero-subtitle {
        font-size: 1rem;
        color: rgba(255,255,255,0.86);
        margin-bottom: 0.9rem;
    }

    .hero-stats {
        display: flex;
        gap: 0.8rem;
        flex-wrap: wrap;
        margin-top: 0.5rem;
    }

    .hero-stat {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.09);
        padding: 0.8rem 1rem;
        border-radius: 16px;
        min-width: 150px;
    }

    .hero-stat-label {
        font-size: 0.8rem;
        color: rgba(255,255,255,0.72);
        margin-bottom: 0.15rem;
    }

    .hero-stat-value {
        font-size: 1.15rem;
        font-weight: 800;
        color: white;
    }

    .section-card {
        background: rgba(255,255,255,0.84);
        border: 1px solid rgba(226,232,240,0.95);
        border-radius: 20px;
        padding: 1rem 1rem 0.9rem 1rem;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        margin-bottom: 1rem;
    }

    .section-title {
        font-size: 1.28rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }

    .section-subtitle {
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 0.8rem;
    }

    .top-chip {
        display: inline-block;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 700;
        margin-right: 0.35rem;
        margin-bottom: 0.35rem;
    }

    .chip-user {
        background: #e0f2fe;
        color: #075985;
    }

    .chip-admin {
        background: #ede9fe;
        color: #5b21b6;
    }

    .chip-guest {
        background: #f1f5f9;
        color: #475569;
    }

    .event-card {
        background: rgba(255,255,255,0.92);
        border: 1px solid #e2e8f0;
        border-radius: 22px;
        padding: 1.15rem;
        margin-bottom: 1rem;
        box-shadow: 0 10px 28px rgba(15,23,42,0.06);
    }

    .event-header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.8rem;
        margin-bottom: 0.45rem;
    }

    .event-title {
        font-size: 1.4rem;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.15;
    }

    .event-pill {
        display: inline-block;
        padding: 0.38rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
    }

    .pill-open {
        background: #dcfce7;
        color: #166534;
    }

    .pill-warning {
        background: #fef3c7;
        color: #92400e;
    }

    .pill-full {
        background: #fee2e2;
        color: #991b1b;
    }

    .pill-paid {
        background: #f3e8ff;
        color: #7e22ce;
    }

    .event-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0,1fr));
        gap: 0.65rem;
        margin-top: 0.7rem;
        margin-bottom: 0.7rem;
    }

    .meta-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
    }

    .meta-label {
        font-size: 0.76rem;
        color: #64748b;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.18rem;
    }

    .meta-value {
        color: #0f172a;
        font-size: 0.97rem;
        font-weight: 600;
    }

    .description-box {
        background: #fcfcff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 0.9rem;
        color: #334155;
        margin-top: 0.25rem;
        margin-bottom: 0.55rem;
    }

    .metrics-row {
        display: grid;
        grid-template-columns: repeat(3, minmax(0,1fr));
        gap: 0.7rem;
        margin-top: 0.7rem;
        margin-bottom: 0.8rem;
    }

    .metric-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 0.9rem;
        text-align: center;
    }

    .metric-value {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.1;
    }

    .metric-label {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 0.2rem;
    }

    .team-box-blue {
        background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
        border: 1px solid #bfdbfe;
        border-radius: 16px;
        padding: 0.95rem;
        margin-top: 0.5rem;
    }

    .team-box-red {
        background: linear-gradient(180deg, #fef2f2 0%, #fee2e2 100%);
        border: 1px solid #fecaca;
        border-radius: 16px;
        padding: 0.95rem;
        margin-top: 0.5rem;
    }

    .payment-box {
        background: linear-gradient(180deg, #faf5ff 0%, #f3e8ff 100%);
        border: 1px solid #e9d5ff;
        border-radius: 16px;
        padding: 0.95rem;
        margin-top: 0.55rem;
        margin-bottom: 0.45rem;
        color: #581c87;
    }

    .soft-divider {
        height: 1px;
        background: linear-gradient(90deg, rgba(148,163,184,0.12), rgba(148,163,184,0.6), rgba(148,163,184,0.12));
        margin-top: 0.85rem;
        margin-bottom: 0.85rem;
        border-radius: 999px;
    }

    .small-muted {
        color: #64748b;
        font-size: 0.9rem;
    }

    .stButton > button {
        border-radius: 14px;
        height: 2.9rem;
        font-weight: 700;
        border: 1px solid #dbe1ea;
        box-shadow: 0 4px 14px rgba(15,23,42,0.04);
    }

    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stDateInput input,
    .stTimeInput input,
    .stNumberInput input,
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        border-radius: 12px !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.45rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        white-space: nowrap;
        border-radius: 14px 14px 0 0;
        padding-left: 1rem;
        padding-right: 1rem;
        font-weight: 700;
    }

    .panel-note {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e3a8a;
        border-radius: 14px;
        padding: 0.85rem 0.95rem;
        font-size: 0.92rem;
        margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CATEGORY_ICONS = {
    "Basketball": "🏀",
    "Drinks": "🍻",
    "Football": "⚽",
    "Lunch": "🍽️",
    "Padel": "🎾",
    "Other": "🎉",
}

SPORT_CATEGORIES = ["Basketball", "Football", "Padel"]
PAYMENT_OPTIONS = ["IRIS", "IBAN (Eurobank)", "Cash"]

IRIS_NUMBER = "6944176835"
EUROBANK_IBAN = "GR2402600020000630202608586"


def get_category_icon(category):
    return CATEGORY_ICONS.get(str(category).strip(), "🎉")


def normalize_name(name):
    return " ".join(str(name).strip().split())


def normalize_username(username):
    return normalize_name(username).replace(" ", "").lower()


def ensure_columns(df, expected_columns):
    if df.empty:
        return pd.DataFrame(columns=expected_columns)

    df.columns = [str(c).strip() for c in df.columns]

    for col in expected_columns:
        if col not in df.columns:
            df[col] = ""

    return df[expected_columns]


def format_event_datetime(date_str, time_str):
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt.strftime("%A, %d %B %Y at %H:%M")
    except Exception:
        return f"{date_str} {time_str}"


def parse_price(value):
    raw = str(value).strip()
    if not raw:
        return None

    raw = raw.replace("€", "").replace(" ", "")

    if "," in raw and "." in raw:
        raw = raw.replace(",", "")
    elif "," in raw and "." not in raw:
        raw = raw.replace(",", ".")

    try:
        return float(raw)
    except Exception:
        return None


def format_price(value):
    parsed = parse_price(value)
    if parsed is None:
        return ""
    return f"{parsed:.2f}"


def show_message(msg, msg_type="info"):
    if msg_type == "success":
        st.success(msg)
    elif msg_type == "warning":
        st.warning(msg)
    elif msg_type == "error":
        st.error(msg)
    else:
        st.info(msg)


def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "display_name" not in st.session_state:
        st.session_state.display_name = ""
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False


@st.cache_resource
def connect_to_gsheet():
    service_account_raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_key = os.getenv("GOOGLE_SHEET_ID")

    if not service_account_raw:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON.")

    if not sheet_key:
        raise ValueError("Missing GOOGLE_SHEET_ID.")

    creds_info = json.loads(service_account_raw)

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_key)


@st.cache_resource
def get_worksheets():
    sheet = connect_to_gsheet()
    events_ws = sheet.worksheet("events")
    signups_ws = sheet.worksheet("signups")
    users_ws = sheet.worksheet("users")
    return events_ws, signups_ws, users_ws


@st.cache_data(ttl=60)
def load_data():
    events_ws, signups_ws, users_ws = get_worksheets()

    events_df = pd.DataFrame(events_ws.get_all_records())
    signups_df = pd.DataFrame(signups_ws.get_all_records())
    users_df = pd.DataFrame(users_ws.get_all_records())

    events_df = ensure_columns(events_df, [
        "event_id", "title", "category", "date", "time", "location",
        "max_participants", "description", "status", "created_at",
        "is_paid", "price", "payment_methods", "payment_details",
        "signups_open", "teams_generated", "teams_data"
    ])

    signups_df = ensure_columns(signups_df, [
        "signup_id", "event_id", "participant_name", "signup_time", "status"
    ])

    users_df = ensure_columns(users_df, [
        "user_id", "username", "password", "display_name", "created_at", "is_admin"
    ])

    return events_df, signups_df, users_df


def refresh_data():
    load_data.clear()


def login_user(users_df, username, password):
    required_cols = ["username", "password", "display_name", "is_admin"]
    missing_cols = [col for col in required_cols if col not in users_df.columns]

    if missing_cols:
        return False, f"Users sheet is missing columns: {', '.join(missing_cols)}"

    if users_df.empty:
        return False, "No users found."

    username = normalize_username(username)
    password = str(password).strip()

    usernames = users_df["username"].astype(str).str.strip().str.lower()
    passwords = users_df["password"].astype(str).str.strip()

    match = users_df[(usernames == username) & (passwords == password)]

    if match.empty:
        return False, "Invalid username or password."

    user = match.iloc[0]
    st.session_state.logged_in = True
    st.session_state.username = str(user["username"]).strip()
    st.session_state.display_name = normalize_name(user["display_name"])
    st.session_state.is_admin = str(user["is_admin"]).strip().lower() in ["yes", "true", "1", "admin"]

    return True, "Logged in successfully."


def create_account(users_ws, users_df, display_name, username, password, confirm_password):
    display_name = normalize_name(display_name)
    username = normalize_username(username)
    password = str(password).strip()
    confirm_password = str(confirm_password).strip()

    if not display_name:
        return False, "Display name is required."

    if not username:
        return False, "Username is required."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if not password:
        return False, "Password is required."

    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    if password != confirm_password:
        return False, "Passwords do not match."

    if not users_df.empty:
        existing = users_df[
            users_df["username"].astype(str).str.strip().str.lower() == username
        ]
        if not existing.empty:
            return False, "This username is already taken."

    users_ws.append_row([
        str(uuid.uuid4()),
        username,
        password,
        display_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "no"
    ])

    return True, "Account created successfully. You can now log in."


def logout_user():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.display_name = ""
    st.session_state.is_admin = False


def get_event_signups(signups_df, event_id):
    if signups_df.empty:
        empty = pd.DataFrame(columns=["signup_id", "event_id", "participant_name", "signup_time", "status"])
        return empty, empty

    event_signups = signups_df[signups_df["event_id"].astype(str) == str(event_id)].copy()

    if event_signups.empty:
        empty = pd.DataFrame(columns=signups_df.columns)
        return empty, empty

    confirmed = event_signups[event_signups["status"].astype(str) == "confirmed"].copy()
    waitlist = event_signups[event_signups["status"].astype(str) == "waitlist"].copy()

    if not confirmed.empty and "signup_time" in confirmed.columns:
        confirmed = confirmed.sort_values(by="signup_time", ascending=True)
    if not waitlist.empty and "signup_time" in waitlist.columns:
        waitlist = waitlist.sort_values(by="signup_time", ascending=True)

    return confirmed, waitlist


def user_signup_status(signups_df, event_id, participant_name):
    if signups_df.empty:
        return None

    participant_name = normalize_name(participant_name).lower()

    match = signups_df[
        (signups_df["event_id"].astype(str) == str(event_id)) &
        (signups_df["participant_name"].astype(str).str.strip().str.lower() == participant_name)
    ]

    if match.empty:
        return None

    return str(match.iloc[0]["status"]).strip()


def signup_user(signups_ws, signups_df, event_id, participant_name, max_participants):
    participant_name = normalize_name(participant_name)

    if not participant_name:
        return "Invalid user.", "warning"

    existing_status = user_signup_status(signups_df, event_id, participant_name)
    if existing_status is not None:
        if existing_status == "confirmed":
            return "You are already confirmed for this event.", "warning"
        return "You are already on the waitlist for this event.", "warning"

    confirmed, _ = get_event_signups(signups_df, event_id)
    status = "confirmed" if len(confirmed) < int(max_participants) else "waitlist"

    signups_ws.append_row([
        str(uuid.uuid4()),
        event_id,
        participant_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status
    ])

    if status == "confirmed":
        return "You're in! 🎉", "success"
    return "Event is full — you were added to the waitlist ⏳", "info"


def promote_first_waitlisted(signups_ws, event_id):
    records = signups_ws.get_all_records()
    waitlist_rows = []

    for i, row in enumerate(records, start=2):
        if (
            str(row.get("event_id", "")).strip() == str(event_id)
            and str(row.get("status", "")).strip() == "waitlist"
        ):
            waitlist_rows.append((i, row))

    if not waitlist_rows:
        return

    first_row_index = waitlist_rows[0][0]
    signups_ws.update_cell(first_row_index, 5, "confirmed")


def cancel_signup(signups_ws, event_id, participant_name):
    participant_name = normalize_name(participant_name).lower()
    records = signups_ws.get_all_records()

    row_to_delete = None
    deleted_status = None

    for i, row in enumerate(records, start=2):
        if (
            str(row.get("event_id", "")).strip() == str(event_id)
            and normalize_name(row.get("participant_name", "")).lower() == participant_name
        ):
            row_to_delete = i
            deleted_status = str(row.get("status", "")).strip()
            break

    if row_to_delete is None:
        return "Signup not found.", "warning"

    signups_ws.delete_rows(row_to_delete)

    if deleted_status == "confirmed":
        promote_first_waitlisted(signups_ws, event_id)

    return "Your booking has been cancelled.", "success"


def add_event(
    events_ws,
    title,
    category,
    date_value,
    time_value,
    location,
    max_participants,
    description,
    is_paid,
    price,
    payment_methods
):
    if not normalize_name(title):
        return "Title is required.", "warning"

    stored_price = format_price(price) if is_paid else ""

    payment_details_parts = []
    if is_paid:
        if "IRIS" in payment_methods:
            payment_details_parts.append(f"IRIS: {IRIS_NUMBER}")
        if "IBAN (Eurobank)" in payment_methods:
            payment_details_parts.append(f"Eurobank IBAN: {EUROBANK_IBAN}")
        if "Cash" in payment_methods:
            payment_details_parts.append("Cash accepted")

    payment_details = " | ".join(payment_details_parts)

    events_ws.append_row([
        str(uuid.uuid4()),
        normalize_name(title),
        category,
        str(date_value),
        time_value.strftime("%H:%M"),
        normalize_name(location),
        int(max_participants),
        str(description).strip(),
        "open",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "yes" if is_paid else "no",
        stored_price,
        ",".join(payment_methods) if is_paid else "",
        payment_details if is_paid else "",
        "open",
        "no",
        ""
    ])

    return "Event created successfully.", "success"


def update_event(
    events_ws,
    event_id,
    title,
    category,
    date_value,
    time_value,
    location,
    max_participants,
    description,
    status,
    is_paid,
    price,
    payment_methods,
    signups_open,
    teams_generated,
    teams_data
):
    records = events_ws.get_all_records()

    payment_details_parts = []
    if is_paid:
        if "IRIS" in payment_methods:
            payment_details_parts.append(f"IRIS: {IRIS_NUMBER}")
        if "IBAN (Eurobank)" in payment_methods:
            payment_details_parts.append(f"Eurobank IBAN: {EUROBANK_IBAN}")
        if "Cash" in payment_methods:
            payment_details_parts.append("Cash accepted")

    payment_details = " | ".join(payment_details_parts)

    for i, row in enumerate(records, start=2):
        if str(row.get("event_id", "")).strip() == str(event_id):
            events_ws.update(f"A{i}:Q{i}", [[
                event_id,
                normalize_name(title),
                category,
                str(date_value),
                time_value.strftime("%H:%M"),
                normalize_name(location),
                int(max_participants),
                str(description).strip(),
                status,
                row.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "yes" if is_paid else "no",
                format_price(price) if is_paid else "",
                ",".join(payment_methods) if is_paid else "",
                payment_details if is_paid else "",
                signups_open,
                teams_generated,
                teams_data
            ]])
            return "Event updated successfully.", "success"

    return "Event not found.", "warning"


def delete_event(events_ws, signups_ws, event_id):
    event_records = events_ws.get_all_records()
    signup_records = signups_ws.get_all_records()

    event_row = None
    for i, row in enumerate(event_records, start=2):
        if str(row.get("event_id", "")).strip() == str(event_id):
            event_row = i
            break

    if event_row is None:
        return "Event not found.", "warning"

    signup_rows_to_delete = []
    for i, row in enumerate(signup_records, start=2):
        if str(row.get("event_id", "")).strip() == str(event_id):
            signup_rows_to_delete.append(i)

    for row_index in reversed(signup_rows_to_delete):
        signups_ws.delete_rows(row_index)

    events_ws.delete_rows(event_row)

    return "Event deleted successfully.", "success"


def generate_teams_data(player_names):
    players = [normalize_name(p) for p in player_names if normalize_name(p)]
    if len(players) < 2:
        return None

    random.shuffle(players)
    half = len(players) // 2
    blue = players[:half]
    red = players[half:]

    return f"Blue:{','.join(blue)}|Red:{','.join(red)}"


def parse_teams_data(teams_data):
    if not str(teams_data).strip() or "|" not in str(teams_data):
        return [], []

    blue_part, red_part = str(teams_data).split("|", 1)

    blue_players = blue_part.replace("Blue:", "").split(",")
    red_players = red_part.replace("Red:", "").split(",")

    blue_players = [p.strip() for p in blue_players if p.strip()]
    red_players = [p.strip() for p in red_players if p.strip()]

    return blue_players, red_players


def render_status_pill(spots_left):
    if spots_left == 0:
        return '<span class="event-pill pill-full">Full</span>'
    if spots_left <= 2:
        return '<span class="event-pill pill-warning">Almost full</span>'
    return '<span class="event-pill pill-open">Open for sign-ups</span>'


def render_login_and_signup(users_ws, users_df):
    st.markdown(f"""
    <div class="hero-wrap">
        <div class="hero-kicker">Private employee access</div>
        <div class="hero-title">Grivalia Social Hub</div>
        <div class="hero-subtitle">Please log in or create an account to access the internal events platform.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Access your account</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Only signed-in users can view events, plans, and bookings.</div>', unsafe_allow_html=True)

    login_col, signup_col = st.columns(2)

    with login_col:
        st.markdown("### 🔐 Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                ok, msg = login_user(users_df, username, password)
                if ok:
                    st.success(msg)
                    refresh_data()
                    st.rerun()
                else:
                    st.error(msg)

    with signup_col:
        st.markdown("### ✨ Create Account")
        with st.form("signup_form"):
            display_name = st.text_input("Display name")
            new_username = st.text_input("Choose a username")
            new_password = st.text_input("Choose a password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            create_submitted = st.form_submit_button("Create Account", use_container_width=True)

            if create_submitted:
                ok, msg = create_account(
                    users_ws,
                    users_df,
                    display_name,
                    new_username,
                    new_password,
                    confirm_password
                )
                if ok:
                    st.success(msg)
                    refresh_data()
                else:
                    st.error(msg)

    st.markdown('</div>', unsafe_allow_html=True)


init_session()

try:
    events_ws, signups_ws, users_ws = get_worksheets()
    events_df, signups_df, users_df = load_data()
except Exception:
    st.error("Could not load Google Sheets data.")
    st.stop()

if not st.session_state.logged_in:
    render_login_and_signup(users_ws, users_df)
    st.stop()

total_open_events = 0 if events_df.empty else len(events_df[events_df["status"].astype(str).str.lower() == "open"])
total_signups = 0 if signups_df.empty else len(signups_df)
total_users = 0 if users_df.empty else len(users_df)

st.markdown(f"""
<div class="hero-wrap">
    <div class="hero-kicker">Internal community platform</div>
    <div class="hero-title">Grivalia Social Hub</div>
    <div class="hero-subtitle">Our way to organize sports, drinks, lunches, and social plans — all in one place.</div>
    <div class="hero-stats">
        <div class="hero-stat">
            <div class="hero-stat-label">Open events</div>
            <div class="hero-stat-value">{total_open_events}</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-label">Total signups</div>
            <div class="hero-stat-value">{total_signups}</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-label">Users</div>
            <div class="hero-stat-value">{total_users}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

top_left, top_mid, top_right = st.columns([3, 2, 1])

with top_left:
    role_chip = "chip-admin" if st.session_state.is_admin else "chip-user"
    role_text = "Admin" if st.session_state.is_admin else "User"
    st.markdown(
        f'<span class="top-chip {role_chip}">Signed in as {st.session_state.display_name} · {role_text}</span>',
        unsafe_allow_html=True
    )

with top_mid:
    st.markdown(
        f"<div class='small-muted'>Username: <strong>{st.session_state.username}</strong></div>",
        unsafe_allow_html=True
    )

with top_right:
    if st.button("Refresh", use_container_width=True):
        refresh_data()
        st.rerun()

action_col1, action_col2, action_col3 = st.columns([1, 1, 4])
with action_col1:
    if st.button("Logout", use_container_width=True):
        logout_user()
        refresh_data()
        st.rerun()

tabs = ["🎈 What’s On", "📅 Your Plans"]
if st.session_state.is_admin:
    tabs.append("🛠️ Admin")

tab_objects = st.tabs(tabs)

with tab_objects[0]:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">What’s happening</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Browse upcoming plans, check availability, and join before spots run out.</div>', unsafe_allow_html=True)

    if events_df.empty:
        st.info("No events yet.")
    else:
        open_events = events_df[events_df["status"].astype(str).str.lower() == "open"].copy()

        if open_events.empty:
            st.info("No open events right now.")
        else:
            filter_col1, filter_col2 = st.columns([2, 4])
            with filter_col1:
                category_options = ["All"] + sorted(open_events["category"].dropna().astype(str).unique().tolist())
                selected_category = st.selectbox("Filter by activity", category_options)

            if selected_category != "All":
                open_events = open_events[open_events["category"].astype(str) == selected_category]

            open_events = open_events.sort_values(by=["date", "time"], ascending=True)

            for _, event in open_events.iterrows():
                event_id = event["event_id"]
                icon = get_category_icon(str(event["category"]))
                confirmed, waitlist = get_event_signups(signups_df, event_id)
                spots_left = max(int(event["max_participants"]) - len(confirmed), 0)

                my_status = user_signup_status(signups_df, event_id, st.session_state.display_name)

                signups_open = str(event.get("signups_open", "open")).strip().lower() == "open"
                teams_generated = str(event.get("teams_generated", "no")).strip().lower() == "yes"
                is_paid = str(event.get("is_paid", "no")).strip().lower() == "yes"

                st.markdown('<div class="event-card">', unsafe_allow_html=True)

                right_badges = render_status_pill(spots_left)
                if is_paid:
                    right_badges += ' <span class="event-pill pill-paid">Paid</span>'

                st.markdown(f"""
                <div class="event-header-row">
                    <div class="event-title">{icon} {event['title']}</div>
                    <div>{right_badges}</div>
                </div>
                """, unsafe_allow_html=True)

                if not signups_open:
                    st.warning("Signups are closed for this event.")

                st.markdown(f"""
                <div class="event-grid">
                    <div class="meta-card">
                        <div class="meta-label">When</div>
                        <div class="meta-value">{format_event_datetime(str(event['date']), str(event['time']))}</div>
                    </div>
                    <div class="meta-card">
                        <div class="meta-label">Where</div>
                        <div class="meta-value">{event['location']}</div>
                    </div>
                    <div class="meta-card">
                        <div class="meta-label">Category</div>
                        <div class="meta-value">{event['category']}</div>
                    </div>
                    <div class="meta-card">
                        <div class="meta-label">Capacity</div>
                        <div class="meta-value">{int(event['max_participants'])} participants</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if str(event["description"]).strip():
                    st.markdown(f"""
                    <div class="description-box">
                        <strong>About this event</strong><br>
                        {event["description"]}
                    </div>
                    """, unsafe_allow_html=True)

                if is_paid:
                    display_price = format_price(event.get("price", ""))
                    st.markdown(f"""
                    <div class="payment-box">
                        <strong>💰 Paid Event</strong><br>
                        Price per person: €{display_price}
                    </div>
                    """, unsafe_allow_html=True)

                    payment_methods = [m.strip() for m in str(event.get("payment_methods", "")).split(",") if m.strip()]
                    if payment_methods:
                        st.markdown("**Payment options**")
                        for method in payment_methods:
                            st.write(f"• {method}")

                    if "IRIS" in payment_methods:
                        st.write(f"IRIS: {IRIS_NUMBER}")
                    if "IBAN (Eurobank)" in payment_methods:
                        st.write(f"Eurobank IBAN: {EUROBANK_IBAN}")
                    if "Cash" in payment_methods:
                        st.write("Cash accepted")

                st.markdown(f"""
                <div class="metrics-row">
                    <div class="metric-box">
                        <div class="metric-value">{len(confirmed)}</div>
                        <div class="metric-label">Confirmed</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{spots_left}</div>
                        <div class="metric-label">Spots left</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{len(waitlist)}</div>
                        <div class="metric-label">Waitlist</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if my_status == "confirmed":
                    st.success("You are confirmed for this event.")
                elif my_status == "waitlist":
                    st.info("You are currently on the waitlist for this event.")

                if teams_generated and str(event.get("teams_data", "")).strip():
                    blue_players, red_players = parse_teams_data(event.get("teams_data", ""))

                    st.markdown("### Teams")
                    team_col1, team_col2 = st.columns(2)

                    with team_col1:
                        st.markdown('<div class="team-box-blue"><strong>🔵 Team Blue</strong></div>', unsafe_allow_html=True)
                        for p in blue_players:
                            st.write(f"• {p}")

                    with team_col2:
                        st.markdown('<div class="team-box-red"><strong>🔴 Team Red</strong></div>', unsafe_allow_html=True)
                        for p in red_players:
                            st.write(f"• {p}")

                detail_col1, detail_col2 = st.columns(2)

                with detail_col1:
                    with st.expander("🙌 Confirmed attendees"):
                        if confirmed.empty:
                            st.write("No confirmed attendees yet.")
                        else:
                            for idx, name in enumerate(confirmed["participant_name"].tolist(), start=1):
                                st.write(f"{idx}. {name}")

                with detail_col2:
                    with st.expander("⏳ Waitlist"):
                        if waitlist.empty:
                            st.write("No one on the waitlist.")
                        else:
                            for idx, name in enumerate(waitlist["participant_name"].tolist(), start=1):
                                st.write(f"{idx}. {name}")

                col_join, col_cancel = st.columns(2)

                with col_join:
                    join_disabled = my_status is not None or not signups_open
                    if st.button("Join Event", key=f"join_{event_id}", use_container_width=True, disabled=join_disabled):
                        msg, typ = signup_user(
                            signups_ws,
                            signups_df,
                            event_id,
                            st.session_state.display_name,
                            event["max_participants"],
                        )
                        show_message(msg, typ)
                        refresh_data()
                        st.rerun()

                with col_cancel:
                    cancel_disabled = my_status is None
                    if st.button("Cancel Booking", key=f"cancel_{event_id}", use_container_width=True, disabled=cancel_disabled):
                        msg, typ = cancel_signup(
                            signups_ws,
                            event_id,
                            st.session_state.display_name,
                        )
                        show_message(msg, typ)
                        refresh_data()
                        st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

with tab_objects[1]:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Your plans</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Track what you have joined and manage your bookings in one place.</div>', unsafe_allow_html=True)

    my_name = st.session_state.display_name
    my_signups = signups_df[
        signups_df["participant_name"].astype(str).str.strip().str.lower() == my_name.lower()
    ].copy() if not signups_df.empty else pd.DataFrame()

    if my_signups.empty:
        st.info("You have no bookings yet.")
    else:
        merged = my_signups.merge(events_df, on="event_id", how="left", suffixes=("_signup", "_event"))

        if merged.empty:
            st.info("You have no bookings yet.")
        else:
            merged = merged.sort_values(by=["date", "time"], ascending=True)

            for _, row in merged.iterrows():
                icon = get_category_icon(str(row.get("category", "Other")))
                status = str(row.get("status_signup", "")).strip()

                st.markdown('<div class="event-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="event-title">{icon} {row.get("title", "Unknown Event")}</div>', unsafe_allow_html=True)

                st.markdown(f"""
                <div class="event-grid">
                    <div class="meta-card">
                        <div class="meta-label">When</div>
                        <div class="meta-value">{format_event_datetime(str(row.get('date', '')), str(row.get('time', '')))}</div>
                    </div>
                    <div class="meta-card">
                        <div class="meta-label">Where</div>
                        <div class="meta-value">{row.get('location', '')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if str(row.get("is_paid", "no")).strip().lower() == "yes":
                    st.write(f"💰 Paid event — €{format_price(row.get('price', ''))} per person")

                if status == "confirmed":
                    st.success("Confirmed")
                elif status == "waitlist":
                    st.info("On waitlist")
                else:
                    st.write(status)

                if st.button("Cancel This Booking", key=f"my_cancel_{row['event_id']}", use_container_width=True):
                    msg, typ = cancel_signup(signups_ws, row["event_id"], st.session_state.display_name)
                    show_message(msg, typ)
                    refresh_data()
                    st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.is_admin:
    with tab_objects[2]:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Admin area</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Create events, update details, manage signups, payment options, and teams.</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-note">Changes made here update the live Google Sheet instantly.</div>', unsafe_allow_html=True)

        st.subheader("Create Event")
        with st.form("create_event_form"):
            title = st.text_input("Event title")
            category = st.selectbox("Category", list(CATEGORY_ICONS.keys()), key="create_category")
            date_value = st.date_input("Event date")
            time_value = st.time_input("Event time")
            location = st.text_input("Location")
            max_participants = st.number_input("Max participants", min_value=1, step=1, value=10)
            description = st.text_area("Description")

            st.markdown("### Payment settings")
            create_is_paid = st.checkbox("Paid event")
            create_price = st.number_input("Price (€)", min_value=0.0, step=0.5, value=0.0, format="%.2f")
            create_payment_methods = st.multiselect("Payment methods", PAYMENT_OPTIONS)

            submitted = st.form_submit_button("Create Event", use_container_width=True)

            if submitted:
                msg, typ = add_event(
                    events_ws,
                    title,
                    category,
                    date_value,
                    time_value,
                    location,
                    max_participants,
                    description,
                    create_is_paid,
                    create_price,
                    create_payment_methods
                )
                show_message(msg, typ)
                refresh_data()
                st.rerun()

        st.markdown("---")
        st.subheader("Edit, Payments, Signups & Teams")

        if events_df.empty:
            st.info("No events available.")
        else:
            event_options = {
                f"{get_category_icon(str(row['category']))} {row['title']} | {row['date']} {row['time']}": row["event_id"]
                for _, row in events_df.sort_values(by=["date", "time"], ascending=True).iterrows()
            }

            selected_label = st.selectbox("Select event", list(event_options.keys()))
            selected_event_id = event_options[selected_label]
            selected_event = events_df[events_df["event_id"].astype(str) == str(selected_event_id)].iloc[0]

            current_payment_methods = [
                m.strip() for m in str(selected_event.get("payment_methods", "")).split(",") if m.strip()
            ]
            current_is_paid = str(selected_event.get("is_paid", "no")).strip().lower() == "yes"
            current_signups_open = str(selected_event.get("signups_open", "open")).strip().lower()

            with st.form("edit_event_form"):
                edit_title = st.text_input("Title", value=str(selected_event["title"]))
                edit_category = st.selectbox(
                    "Category",
                    list(CATEGORY_ICONS.keys()),
                    index=list(CATEGORY_ICONS.keys()).index(str(selected_event["category"])) if str(selected_event["category"]) in CATEGORY_ICONS else 0,
                )
                edit_date = st.date_input("Date", value=pd.to_datetime(selected_event["date"]).date())
                edit_time = st.time_input("Time", value=pd.to_datetime(str(selected_event["time"]), format="%H:%M").time())
                edit_location = st.text_input("Location", value=str(selected_event["location"]))
                edit_max = st.number_input("Max participants", min_value=1, step=1, value=int(selected_event["max_participants"]))
                edit_description = st.text_area("Description", value=str(selected_event["description"]))
                edit_status = st.selectbox("Status", ["open", "closed"], index=0 if str(selected_event["status"]).strip().lower() == "open" else 1)

                st.markdown("### Payment settings")
                edit_is_paid = st.checkbox("Paid event", value=current_is_paid)
                edit_price = st.number_input(
                    "Price (€)",
                    min_value=0.0,
                    step=0.5,
                    value=parse_price(selected_event["price"]) if str(selected_event.get("price", "")).strip() else 0.0,
                    format="%.2f"
                )
                edit_payment_methods = st.multiselect(
                    "Payment methods",
                    PAYMENT_OPTIONS,
                    default=[m for m in current_payment_methods if m in PAYMENT_OPTIONS]
                )

                st.markdown("### Signup settings")
                edit_signups_open = st.selectbox(
                    "Signups",
                    ["open", "closed"],
                    index=0 if current_signups_open == "open" else 1
                )

                col_save, col_delete = st.columns(2)
                save_clicked = col_save.form_submit_button("Save Changes", use_container_width=True)
                delete_clicked = col_delete.form_submit_button("Delete Event", use_container_width=True)

                if save_clicked:
                    msg, typ = update_event(
                        events_ws,
                        selected_event_id,
                        edit_title,
                        edit_category,
                        edit_date,
                        edit_time,
                        edit_location,
                        edit_max,
                        edit_description,
                        edit_status,
                        edit_is_paid,
                        edit_price,
                        edit_payment_methods,
                        edit_signups_open,
                        str(selected_event.get("teams_generated", "no")),
                        str(selected_event.get("teams_data", ""))
                    )
                    show_message(msg, typ)
                    refresh_data()
                    st.rerun()

                if delete_clicked:
                    msg, typ = delete_event(events_ws, signups_ws, selected_event_id)
                    show_message(msg, typ)
                    refresh_data()
                    st.rerun()

            if str(selected_event.get("category", "")) in SPORT_CATEGORIES:
                st.markdown("---")
                st.subheader("Team Management")

                confirmed_for_event, _ = get_event_signups(signups_df, selected_event_id)
                current_players = confirmed_for_event["participant_name"].tolist() if not confirmed_for_event.empty else []

                st.write(f"Confirmed players available for teams: **{len(current_players)}**")

                current_teams_generated = str(selected_event.get("teams_generated", "no")).strip().lower() == "yes"
                current_teams_data = str(selected_event.get("teams_data", "")).strip()

                if current_teams_generated and current_teams_data:
                    blue_players, red_players = parse_teams_data(current_teams_data)

                    tc1, tc2 = st.columns(2)
                    with tc1:
                        st.markdown('<div class="team-box-blue"><strong>🔵 Current Team Blue</strong></div>', unsafe_allow_html=True)
                        for p in blue_players:
                            st.write(f"• {p}")

                    with tc2:
                        st.markdown('<div class="team-box-red"><strong>🔴 Current Team Red</strong></div>', unsafe_allow_html=True)
                        for p in red_players:
                            st.write(f"• {p}")

                team_col1, team_col2 = st.columns(2)

                with team_col1:
                    if st.button("Generate Teams Automatically", use_container_width=True):
                        teams_data = generate_teams_data(current_players)

                        if not teams_data:
                            st.warning("Not enough confirmed players to generate teams.")
                        else:
                            update_event(
                                events_ws,
                                selected_event_id,
                                selected_event["title"],
                                selected_event["category"],
                                pd.to_datetime(selected_event["date"]).date(),
                                pd.to_datetime(str(selected_event["time"]), format="%H:%M").time(),
                                selected_event["location"],
                                int(selected_event["max_participants"]),
                                selected_event["description"],
                                selected_event["status"],
                                str(selected_event.get("is_paid", "no")).strip().lower() == "yes",
                                parse_price(selected_event["price"]) if str(selected_event.get("price", "")).strip() else 0.0,
                                [m.strip() for m in str(selected_event.get("payment_methods", "")).split(",") if m.strip()],
                                str(selected_event.get("signups_open", "open")),
                                "yes",
                                teams_data
                            )
                            show_message("Teams generated successfully.", "success")
                            refresh_data()
                            st.rerun()

                with team_col2:
                    if st.button("Clear Teams", use_container_width=True):
                        update_event(
                            events_ws,
                            selected_event_id,
                            selected_event["title"],
                            selected_event["category"],
                            pd.to_datetime(selected_event["date"]).date(),
                            pd.to_datetime(str(selected_event["time"]), format="%H:%M").time(),
                            selected_event["location"],
                            int(selected_event["max_participants"]),
                            selected_event["description"],
                            selected_event["status"],
                            str(selected_event.get("is_paid", "no")).strip().lower() == "yes",
                            parse_price(selected_event["price"]) if str(selected_event.get("price", "")).strip() else 0.0,
                            [m.strip() for m in str(selected_event.get("payment_methods", "")).split(",") if m.strip()],
                            str(selected_event.get("signups_open", "open")),
                            "no",
                            ""
                        )
                        show_message("Teams cleared successfully.", "success")
                        refresh_data()
                        st.rerun()

                st.markdown("### Manual Teams")
                st.markdown('<div class="small-muted">Enter names separated by commas.</div>', unsafe_allow_html=True)

                manual_blue_default = ""
                manual_red_default = ""
                if current_teams_generated and current_teams_data:
                    current_blue, current_red = parse_teams_data(current_teams_data)
                    manual_blue_default = ", ".join(current_blue)
                    manual_red_default = ", ".join(current_red)

                with st.form("manual_teams_form"):
                    manual_blue = st.text_area("Team Blue", value=manual_blue_default)
                    manual_red = st.text_area("Team Red", value=manual_red_default)
                    manual_save = st.form_submit_button("Save Manual Teams", use_container_width=True)

                    if manual_save:
                        blue_players = [normalize_name(x) for x in manual_blue.split(",") if normalize_name(x)]
                        red_players = [normalize_name(x) for x in manual_red.split(",") if normalize_name(x)]

                        if not blue_players or not red_players:
                            st.warning("Both teams must have at least one player.")
                        else:
                            manual_teams_data = f"Blue:{','.join(blue_players)}|Red:{','.join(red_players)}"

                            update_event(
                                events_ws,
                                selected_event_id,
                                selected_event["title"],
                                selected_event["category"],
                                pd.to_datetime(selected_event["date"]).date(),
                                pd.to_datetime(str(selected_event["time"]), format="%H:%M").time(),
                                selected_event["location"],
                                int(selected_event["max_participants"]),
                                selected_event["description"],
                                selected_event["status"],
                                str(selected_event.get("is_paid", "no")).strip().lower() == "yes",
                                parse_price(selected_event["price"]) if str(selected_event.get("price", "")).strip() else 0.0,
                                [m.strip() for m in str(selected_event.get("payment_methods", "")).split(",") if m.strip()],
                                str(selected_event.get("signups_open", "open")),
                                "yes",
                                manual_teams_data
                            )
                            show_message("Manual teams saved successfully.", "success")
                            refresh_data()
                            st.rerun()

        st.markdown("---")
        st.subheader("All Signups")
        if signups_df.empty:
            st.info("No signups yet.")
        else:
            signups_view = signups_df.merge(
                events_df[["event_id", "title", "date", "time"]],
                on="event_id",
                how="left"
            )
            st.dataframe(signups_view, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)
