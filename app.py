import random
import uuid
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Grivalia Social Hub", page_icon="🎉", layout="wide")

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    .hero-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-radius: 18px;
        padding: 1.4rem 1.6rem;
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.18);
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }

    .hero-subtitle {
        font-size: 1rem;
        opacity: 0.9;
        margin-bottom: 0;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 800;
        margin-top: 0.2rem;
        margin-bottom: 0.8rem;
    }

    .mini-note {
        color: #475569;
        font-size: 0.95rem;
        margin-bottom: 0.8rem;
    }

    .status-chip-open {
        display: inline-block;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        background: #dcfce7;
        color: #166534;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 0.6rem;
    }

    .status-chip-warning {
        display: inline-block;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        background: #fef3c7;
        color: #92400e;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 0.6rem;
    }

    .status-chip-full {
        display: inline-block;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        background: #fee2e2;
        color: #991b1b;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 0.6rem;
    }

    .event-meta {
        color: #334155;
        font-size: 0.97rem;
        margin-bottom: 0.25rem;
    }

    .soft-divider {
        height: 1px;
        background: linear-gradient(90deg, rgba(148,163,184,0.2), rgba(148,163,184,0.6), rgba(148,163,184,0.2));
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
        border-radius: 999px;
    }

    .team-box-blue {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 0.9rem;
        margin-top: 0.5rem;
    }

    .team-box-red {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 12px;
        padding: 0.9rem;
        margin-top: 0.5rem;
    }

    .payment-box {
        background: #faf5ff;
        border: 1px solid #e9d5ff;
        border-radius: 12px;
        padding: 0.9rem;
        margin-top: 0.6rem;
        margin-bottom: 0.4rem;
    }

    .stButton > button {
        border-radius: 12px;
        height: 2.85rem;
        font-weight: 700;
        border: 1px solid #cbd5e1;
    }

    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stDateInput input,
    .stTimeInput input,
    .stNumberInput input {
        border-radius: 10px !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        white-space: nowrap;
        border-radius: 10px 10px 0 0;
        padding-left: 1rem;
        padding-right: 1rem;
        font-weight: 700;
    }

    .small-muted {
        color: #64748b;
        font-size: 0.9rem;
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
PAYMENT_OPTIONS = ["IRIS", "IBAN (Eurobank)", "Revolut", "Cash"]


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
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    return client.open(st.secrets["sheet_name"])


@st.cache_resource
def get_worksheets():
    sheet = connect_to_gsheet()
    events_ws = sheet.worksheet("events")
    signups_ws = sheet.worksheet("signups")
    users_ws = sheet.worksheet("users")
    return events_ws, signups_ws, users_ws


@st.cache_data(ttl=30)
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
    payment_methods,
    payment_details
):
    if not normalize_name(title):
        return "Title is required.", "warning"

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
        float(price) if is_paid else "",
        ",".join(payment_methods) if is_paid else "",
        str(payment_details).strip() if is_paid else "",
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
    payment_details,
    signups_open,
    teams_generated,
    teams_data
):
    records = events_ws.get_all_records()

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
                float(price) if is_paid else "",
                ",".join(payment_methods) if is_paid else "",
                str(payment_details).strip() if is_paid else "",
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


def render_login_and_signup(users_ws, users_df):
    login_col, signup_col = st.columns(2)

    with login_col:
        st.markdown('<div class="section-title">🔐 Login</div>', unsafe_allow_html=True)
        st.markdown('<div class="mini-note">Welcome back. Sign in to join events and manage your plans.</div>', unsafe_allow_html=True)

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
        st.markdown('<div class="section-title">✨ Create Account</div>', unsafe_allow_html=True)
        st.markdown('<div class="mini-note">New here? Create a quick account to join games and social plans.</div>', unsafe_allow_html=True)

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


def render_status_chip(spots_left):
    if spots_left == 0:
        st.markdown('<span class="status-chip-full">Full</span>', unsafe_allow_html=True)
    elif spots_left <= 2:
        st.markdown('<span class="status-chip-warning">Almost full</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-chip-open">Open for sign-ups</span>', unsafe_allow_html=True)


init_session()

try:
    events_ws, signups_ws, users_ws = get_worksheets()
    events_df, signups_df, users_df = load_data()
except Exception as e:
    st.error("Could not load Google Sheets data.")
    st.exception(e)
    st.stop()

st.markdown("""
<div class="hero-card">
    <div class="hero-title">🎉 Grivalia Social Hub</div>
    <p class="hero-subtitle">Internal events made simple — basketball, drinks, lunch plans and more.</p>
</div>
""", unsafe_allow_html=True)

top_left, top_mid, top_right = st.columns([3, 2, 1])

with top_left:
    if st.session_state.logged_in:
        role = "Admin" if st.session_state.is_admin else "User"
        st.success(f"Logged in as {st.session_state.display_name} ({role})")
    else:
        st.info("Log in or create an account to join events and manage your bookings.")

with top_mid:
    if st.session_state.logged_in:
        st.markdown(
            f"<div class='small-muted'>Signed in as <strong>{st.session_state.username}</strong></div>",
            unsafe_allow_html=True
        )

with top_right:
    if st.button("Refresh", use_container_width=True):
        refresh_data()
        st.rerun()

action_col1, action_col2, action_col3 = st.columns([1, 1, 4])
with action_col1:
    if st.session_state.logged_in:
        if st.button("Logout", use_container_width=True):
            logout_user()
            refresh_data()
            st.rerun()

tabs = ["🎈 What’s On", "📅 Your Plans", "🔑 Login / Sign Up"]
if st.session_state.is_admin:
    tabs.append("🛠️ Admin")

tab_objects = st.tabs(tabs)

with tab_objects[0]:
    st.markdown('<div class="section-title">🎯 What’s happening</div>', unsafe_allow_html=True)
    st.markdown('<div class="mini-note">Browse upcoming plans and jump in before spots run out.</div>', unsafe_allow_html=True)

    if events_df.empty:
        st.info("No events yet.")
    else:
        open_events = events_df[events_df["status"].astype(str).str.lower() == "open"].copy()

        if open_events.empty:
            st.info("No open events right now.")
        else:
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

                my_status = None
                if st.session_state.logged_in:
                    my_status = user_signup_status(signups_df, event_id, st.session_state.display_name)

                signups_open = str(event.get("signups_open", "open")).strip().lower() == "open"
                teams_generated = str(event.get("teams_generated", "no")).strip().lower() == "yes"
                is_paid = str(event.get("is_paid", "no")).strip().lower() == "yes"

                with st.container(border=True):
                    st.markdown(f"## {icon} {event['title']}")
                    render_status_chip(spots_left)

                    if not signups_open:
                        st.warning("Signups are closed for this event.")

                    st.markdown(f"<div class='event-meta'><strong>When:</strong> {format_event_datetime(str(event['date']), str(event['time']))}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='event-meta'><strong>Where:</strong> {event['location']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='event-meta'><strong>Category:</strong> {event['category']}</div>", unsafe_allow_html=True)

                    if str(event["description"]).strip():
                        st.markdown(f"<div class='event-meta'><strong>About:</strong> {event['description']}</div>", unsafe_allow_html=True)

                    if is_paid:
                        st.markdown(f"""
                        <div class="payment-box">
                            <strong>💰 Paid Event</strong><br>
                            Price per person: €{event.get("price", "")}
                        </div>
                        """, unsafe_allow_html=True)

                        payment_methods = [m.strip() for m in str(event.get("payment_methods", "")).split(",") if m.strip()]
                        if payment_methods:
                            st.markdown("**Payment options:**")
                            for method in payment_methods:
                                st.write(f"• {method}")

                        if str(event.get("payment_details", "")).strip():
                            st.info(str(event.get("payment_details", "")))

                    st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Confirmed", len(confirmed))
                    c2.metric("Spots left", spots_left)
                    c3.metric("Waitlist", len(waitlist))

                    if my_status == "confirmed":
                        st.success("You are confirmed for this event.")
                    elif my_status == "waitlist":
                        st.info("You are currently on the waitlist for this event.")

                    if teams_generated and str(event.get("teams_data", "")).strip():
                        blue_players, red_players = parse_teams_data(event.get("teams_data", ""))

                        st.markdown("### 🔥 Teams are ready")
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
                        with st.expander("🙌 Who's in"):
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

                    if st.session_state.logged_in:
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
                    else:
                        st.warning("Log in or create an account to join this event.")

with tab_objects[1]:
    st.markdown('<div class="section-title">📅 Your plans</div>', unsafe_allow_html=True)
    st.markdown('<div class="mini-note">See what you’ve joined and manage your bookings in one place.</div>', unsafe_allow_html=True)

    if not st.session_state.logged_in:
        st.info("Log in to see your bookings.")
    else:
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

                    with st.container(border=True):
                        st.markdown(f"### {icon} {row.get('title', 'Unknown Event')}")
                        st.markdown(f"<div class='event-meta'><strong>When:</strong> {format_event_datetime(str(row.get('date', '')), str(row.get('time', '')))}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='event-meta'><strong>Where:</strong> {row.get('location', '')}</div>", unsafe_allow_html=True)

                        if str(row.get("is_paid", "no")).strip().lower() == "yes":
                            st.write(f"💰 Paid event — €{row.get('price', '')} per person")

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

with tab_objects[2]:
    if st.session_state.logged_in:
        st.success(f"You are logged in as {st.session_state.display_name}.")
        st.markdown('<div class="mini-note">You can now join events, manage your plans, and keep track of your status.</div>', unsafe_allow_html=True)
    else:
        render_login_and_signup(users_ws, users_df)

if st.session_state.is_admin:
    with tab_objects[3]:
        st.markdown('<div class="section-title">🛠️ Admin area</div>', unsafe_allow_html=True)
        st.markdown('<div class="mini-note">Create events, update details, manage payments, close signups, and create teams.</div>', unsafe_allow_html=True)

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
            create_price = st.number_input("Price (€)", min_value=0.0, step=1.0, value=0.0)
            create_payment_methods = st.multiselect("Payment methods", PAYMENT_OPTIONS)
            create_payment_details = st.text_area("Payment details / instructions")

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
                    create_payment_methods,
                    create_payment_details,
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
                    step=1.0,
                    value=float(selected_event["price"]) if str(selected_event.get("price", "")).strip() else 0.0
                )
                edit_payment_methods = st.multiselect(
                    "Payment methods",
                    PAYMENT_OPTIONS,
                    default=[m for m in current_payment_methods if m in PAYMENT_OPTIONS]
                )
                edit_payment_details = st.text_area(
                    "Payment details / instructions",
                    value=str(selected_event.get("payment_details", ""))
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
                        edit_payment_details,
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
                            msg, typ = update_event(
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
                                float(selected_event["price"]) if str(selected_event.get("price", "")).strip() else 0.0,
                                [m.strip() for m in str(selected_event.get("payment_methods", "")).split(",") if m.strip()],
                                str(selected_event.get("payment_details", "")),
                                str(selected_event.get("signups_open", "open")),
                                "yes",
                                teams_data
                            )
                            show_message("Teams generated successfully.", "success")
                            refresh_data()
                            st.rerun()

                with team_col2:
                    if st.button("Clear Teams", use_container_width=True):
                        msg, typ = update_event(
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
                            float(selected_event["price"]) if str(selected_event.get("price", "")).strip() else 0.0,
                            [m.strip() for m in str(selected_event.get("payment_methods", "")).split(",") if m.strip()],
                            str(selected_event.get("payment_details", "")),
                            str(selected_event.get("signups_open", "open")),
                            "no",
                            ""
                        )
                        show_message("Teams cleared successfully.", "success")
                        refresh_data()
                        st.rerun()

                st.markdown("### Manual Teams")
                st.markdown('<div class="mini-note">Enter names separated by commas.</div>', unsafe_allow_html=True)

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

                            msg, typ = update_event(
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
                                float(selected_event["price"]) if str(selected_event.get("price", "")).strip() else 0.0,
                                [m.strip() for m in str(selected_event.get("payment_methods", "")).split(",") if m.strip()],
                                str(selected_event.get("payment_details", "")),
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
