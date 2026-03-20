import uuid
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Grivalia Social Hub", page_icon="🏘️", layout="wide")

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


def get_category_icon(category):
    return CATEGORY_ICONS.get(category, "🎉")


@st.cache_resource
def connect_to_gsheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    return client.open(st.secrets["sheet_name"])


def load_data():
    sheet = connect_to_gsheet()
    events_ws = sheet.worksheet("events")
    signups_ws = sheet.worksheet("signups")
    users_ws = sheet.worksheet("users")

    events_df = pd.DataFrame(events_ws.get_all_records())
    signups_df = pd.DataFrame(signups_ws.get_all_records())
    users_df = pd.DataFrame(users_ws.get_all_records())

    if events_df.empty:
        events_df = pd.DataFrame(columns=[
            "event_id", "title", "category", "date", "time", "location",
            "max_participants", "description", "status", "created_at"
        ])

    if signups_df.empty:
        signups_df = pd.DataFrame(columns=[
            "signup_id", "event_id", "participant_name", "signup_time", "status"
        ])

    if users_df.empty:
        users_df = pd.DataFrame(columns=[
            "user_id", "username", "password", "display_name", "created_at", "is_admin"
        ])

    return events_ws, signups_ws, users_ws, events_df, signups_df, users_df


def normalize_name(name):
    return " ".join(str(name).strip().split())


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


def login_user(users_df, username, password):
    if users_df.empty:
        return False, "No users found."

    username = normalize_name(username).lower()
    password = str(password).strip()

    match = users_df[
        (users_df["username"].astype(str).str.strip().str.lower() == username) &
        (users_df["password"].astype(str).str.strip() == password)
    ]

    if match.empty:
        return False, "Invalid username or password."

    user = match.iloc[0]
    st.session_state.logged_in = True
    st.session_state.username = str(user["username"]).strip()
    st.session_state.display_name = normalize_name(user["display_name"])
    st.session_state.is_admin = str(user["is_admin"]).strip().lower() in ["yes", "true", "1", "admin"]

    return True, "Logged in successfully."


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


def add_event(events_ws, title, category, date_value, time_value, location, max_participants, description):
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
    ])

    return "Event created successfully.", "success"


def update_event(events_ws, event_id, title, category, date_value, time_value, location, max_participants, description, status):
    records = events_ws.get_all_records()

    for i, row in enumerate(records, start=2):
        if str(row.get("event_id", "")).strip() == str(event_id):
            events_ws.update(f"A{i}:J{i}", [[
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


def render_login(users_df):
    st.markdown("## Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            ok, msg = login_user(users_df, username, password)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


init_session()

try:
    events_ws, signups_ws, users_ws, events_df, signups_df, users_df = load_data()
except Exception as e:
    st.error("Could not load Google Sheets data.")
    st.exception(e)
    st.stop()

st.title("🎉 Grivalia Social Hub")
st.markdown("### Basketball, drinks, lunch plans and more")
st.markdown("---")

top_left, top_right = st.columns([3, 2])

with top_left:
    if st.session_state.logged_in:
        role = "Admin" if st.session_state.is_admin else "User"
        st.success(f"Logged in as {st.session_state.display_name} ({role})")
    else:
        st.info("Please log in to join and manage your bookings.")

with top_right:
    if st.session_state.logged_in:
        if st.button("Logout", use_container_width=True):
            logout_user()
            st.rerun()

tabs = ["🎈 Upcoming Events", "📋 My Bookings", "🔑 Login"]
if st.session_state.is_admin:
    tabs.append("🛠️ Admin")

tab_objects = st.tabs(tabs)

# Upcoming Events
with tab_objects[0]:
    st.markdown("## Upcoming Events")

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

                with st.container(border=True):
                    st.markdown(f"## {icon} {event['title']}")
                    st.write(f"**When:** {format_event_datetime(str(event['date']), str(event['time']))}")
                    st.write(f"**Where:** {event['location']}")
                    st.write(f"**Category:** {event['category']}")
                    if str(event["description"]).strip():
                        st.write(f"**About:** {event['description']}")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Confirmed", len(confirmed))
                    c2.metric("Spots left", spots_left)
                    c3.metric("Waitlist", len(waitlist))

                    if my_status == "confirmed":
                        st.success("You are confirmed for this event.")
                    elif my_status == "waitlist":
                        st.info("You are currently on the waitlist for this event.")

                    with st.expander("🙌 Who's in"):
                        if confirmed.empty:
                            st.write("No confirmed attendees yet.")
                        else:
                            for idx, name in enumerate(confirmed["participant_name"].tolist(), start=1):
                                st.write(f"{idx}. {name}")

                    with st.expander("⏳ Waitlist"):
                        if waitlist.empty:
                            st.write("No one on the waitlist.")
                        else:
                            for idx, name in enumerate(waitlist["participant_name"].tolist(), start=1):
                                st.write(f"{idx}. {name}")

                    if st.session_state.logged_in:
                        col_join, col_cancel = st.columns(2)

                        with col_join:
                            join_disabled = my_status is not None
                            if st.button("Join Event", key=f"join_{event_id}", use_container_width=True, disabled=join_disabled):
                                msg, typ = signup_user(
                                    signups_ws,
                                    signups_df,
                                    event_id,
                                    st.session_state.display_name,
                                    event["max_participants"],
                                )
                                show_message(msg, typ)
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
                                st.rerun()
                    else:
                        st.warning("Log in to join or cancel this event.")

# My Bookings
with tab_objects[1]:
    st.markdown("## My Bookings")

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
                        st.write(f"**When:** {format_event_datetime(str(row.get('date', '')), str(row.get('time', '')))}")
                        st.write(f"**Where:** {row.get('location', '')}")

                        if status == "confirmed":
                            st.success("Confirmed")
                        elif status == "waitlist":
                            st.info("On waitlist")
                        else:
                            st.write(status)

                        if st.button("Cancel This Booking", key=f"my_cancel_{row['event_id']}", use_container_width=True):
                            msg, typ = cancel_signup(signups_ws, row["event_id"], st.session_state.display_name)
                            show_message(msg, typ)
                            st.rerun()

# Login
with tab_objects[2]:
    if st.session_state.logged_in:
        st.success(f"You are logged in as {st.session_state.display_name}.")
    else:
        render_login(users_df)

# Admin
if st.session_state.is_admin:
    with tab_objects[3]:
        st.markdown("## Admin")

        st.subheader("Create Event")
        with st.form("create_event_form"):
            title = st.text_input("Event title")
            category = st.selectbox("Category", list(CATEGORY_ICONS.keys()), key="create_category")
            date_value = st.date_input("Event date")
            time_value = st.time_input("Event time")
            location = st.text_input("Location")
            max_participants = st.number_input("Max participants", min_value=1, step=1, value=10)
            description = st.text_area("Description")
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
                )
                show_message(msg, typ)
                st.rerun()

        st.markdown("---")
        st.subheader("Edit or Delete Event")

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
                    )
                    show_message(msg, typ)
                    st.rerun()

                if delete_clicked:
                    msg, typ = delete_event(events_ws, signups_ws, selected_event_id)
                    show_message(msg, typ)
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
