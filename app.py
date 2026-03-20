import uuid
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Grivalia Social Hub", page_icon="🎉", layout="wide")

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
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open(st.secrets["sheet_name"])
    return sheet


def load_data():
    sheet = connect_to_gsheet()
    events_ws = sheet.worksheet("events")
    signups_ws = sheet.worksheet("signups")

    events_df = pd.DataFrame(events_ws.get_all_records())
    signups_df = pd.DataFrame(signups_ws.get_all_records())

    if events_df.empty:
        events_df = pd.DataFrame(columns=[
            "event_id", "title", "category", "date", "time", "location",
            "max_participants", "description", "status", "created_at"
        ])

    if signups_df.empty:
        signups_df = pd.DataFrame(columns=[
            "signup_id", "event_id", "participant_name", "signup_time", "status"
        ])

    return events_ws, signups_ws, events_df, signups_df


def format_event_datetime(date_str, time_str):
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt.strftime("%A, %d %B %Y at %H:%M")
    except:
        return f"{date_str} {time_str}"


def normalize_name(name):
    return " ".join(name.strip().split())


def get_event_signups(signups_df, event_id):
    event_signups = signups_df[signups_df["event_id"] == event_id]
    confirmed = event_signups[event_signups["status"] == "confirmed"]
    waitlist = event_signups[event_signups["status"] == "waitlist"]
    return confirmed, waitlist


def signup_user(signups_ws, signups_df, event_id, name, max_participants):
    name = normalize_name(name)

    if not name:
        return "Enter your name.", "warning"

    existing = signups_df[
        (signups_df["event_id"] == event_id) &
        (signups_df["participant_name"].str.lower() == name.lower())
    ]

    if not existing.empty:
        return "Already signed up.", "warning"

    confirmed, _ = get_event_signups(signups_df, event_id)
    status = "confirmed" if len(confirmed) < int(max_participants) else "waitlist"

    signups_ws.append_row([
        str(uuid.uuid4()),
        event_id,
        name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status
    ])

    if status == "confirmed":
        return "You're in! 🎉", "success"
    return "Added to waitlist ⏳", "info"


def cancel_signup(signups_ws, event_id, name):
    name = normalize_name(name)

    records = signups_ws.get_all_records()

    for i, row in enumerate(records, start=2):
        if (
            str(row["event_id"]) == str(event_id)
            and str(row["participant_name"]).strip().lower() == name.lower()
        ):
            signups_ws.delete_rows(i)
            return "Signup cancelled.", "success"

    return "Not found.", "warning"


def add_event(events_ws, title, category, date_value, time_value, location, max_participants, description):
    if not title.strip():
        return "Title required.", "warning"

    events_ws.append_row([
        str(uuid.uuid4()),
        title,
        category,
        str(date_value),
        time_value.strftime("%H:%M"),
        location,
        int(max_participants),
        description,
        "open",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])

    return "Event created!", "success"


def show_message(msg, msg_type):
    if msg_type == "success":
        st.success(msg)
    elif msg_type == "warning":
        st.warning(msg)
    else:
        st.info(msg)


# UI
st.title("🎉 Grivalia Social Hub")
st.markdown("### Your place for events")
st.markdown("---")

tab1, tab2 = st.tabs(["🎈 Events", "🔐 Admin"])


# EVENTS TAB
with tab1:
    events_ws, signups_ws, events_df, signups_df = load_data()

    if events_df.empty:
        st.info("No events yet.")
    else:
        open_events = events_df[events_df["status"] == "open"]

        for _, event in open_events.iterrows():
            event_id = event["event_id"]
            icon = get_category_icon(event["category"])

            confirmed, waitlist = get_event_signups(signups_df, event_id)
            spots_left = int(event["max_participants"]) - len(confirmed)

            with st.container(border=True):
                st.markdown(f"## {icon} {event['title']}")
                st.write(format_event_datetime(event["date"], event["time"]))
                st.write(f"📍 {event['location']}")
                st.write(f"Spots left: {spots_left}")

                name = st.text_input("Your name", key=f"name_{event_id}")

                if st.button("Join", key=f"join_{event_id}"):
                    msg, t = signup_user(signups_ws, signups_df, event_id, name, event["max_participants"])
                    show_message(msg, t)
                    st.rerun()

                cancel_name = st.text_input("Cancel name", key=f"cancel_{event_id}")

                if st.button("Cancel", key=f"cancelbtn_{event_id}"):
                    msg, t = cancel_signup(signups_ws, event_id, cancel_name)
                    show_message(msg, t)
                    st.rerun()


# ADMIN TAB
with tab2:
    password = st.text_input("Password", type="password")

    if password == st.secrets["admin_password"]:
        st.success("Access granted")

        events_ws, signups_ws, events_df, signups_df = load_data()

        st.subheader("Create Event")

        with st.form("create"):
            title = st.text_input("Title")
            category = st.selectbox("Category", list(CATEGORY_ICONS.keys()))
            date_value = st.date_input("Date")
            time_value = st.time_input("Time")
            location = st.text_input("Location")
            max_participants = st.number_input("Max participants", min_value=1, value=10)
            description = st.text_area("Description")

            submit = st.form_submit_button("Create")

            if submit:
                msg, t = add_event(
                    events_ws,
                    title,
                    category,
                    date_value,
                    time_value,
                    location,
                    max_participants,
                    description
                )
                show_message(msg, t)
                st.rerun()

    elif password:
        st.error("Wrong password")
