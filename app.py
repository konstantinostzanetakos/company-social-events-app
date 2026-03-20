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

    events_data = events_ws.get_all_records()
    signups_data = signups_ws.get_all_records()

    events_df = pd.DataFrame(events_data)
    signups_df = pd.DataFrame(signups_data)

    if events_df.empty:
        events_df = pd.DataFrame(columns=[
            "event_id", "title", "category", "date", "time", "location",
            "max_participants", "description", "status", "created_at"
        ])

    if signups_df.empty:
        signups_df = pd.DataFrame(columns=[
            "signup_id", "event_id", "participant_name", "signup_time", "status"
        ])

    return sheet, events_ws, signups_ws, events_df, signups_df


def format_event_datetime(date_str, time_str):
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt.strftime("%A, %d %B %Y at %H:%M")
    except Exception:
        return f"{date_str} {time_str}"


def normalize_name(name):
    return " ".join(name.strip().split())


def get_event_signups(signups_df, event_id):
    event_signups = signups_df[signups_df["event_id"] == event_id].copy()
    confirmed = event_signups[event_signups["status"] == "confirmed"]
    waitlist = event_signups[event_signups["status"] == "waitlist"]
    return confirmed, waitlist


def signup_user(signups_ws, signups_df, event_id, participant_name, max_participants):
    participant_name = normalize_name(participant_name)

    if not participant_name:
        return "Please enter your name.", "warning"

    if signups_df.empty:
        existing = pd.DataFrame()
    else:
        existing = signups_df[
            (signups_df["event_id"] == event_id) &
            (signups_df["participant_name"].astype(str).str.strip().str.lower() == participant_name.lower())
        ]

    if not existing.empty:
        return "You have already signed up for this event.", "warning"

    confirmed, _ = get_event_signups(signups_df, event_id)
    signup_status = "confirmed" if len(confirmed) < int(max_participants) else "waitlist"

    signups_ws.append_row([
        str(uuid.uuid4()),
        event_id,
        participant_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        signup_status
    ])

    if signup_status == "confirmed":
        return "You're in! See you there 🎉", "success"

    return "Event is full — you’ve been added to the waitlist ⏳", "info"


def cancel_signup(signups_ws, event_id, participant_name):
    participant_name = normalize_name(participant_name)

    if not participant_name:
        return "Please enter your name.", "warning"

    records = signups_ws.get_all_records()
    row_to_delete = None
    deleted_status = None

    for i, row in enumerate(records, start=2):
        row_event_id = str(row.get("event_id", ""))
        row_name = normalize_name(str(row.get("participant_name", "")))

        if row_event_id == str(event_id) and row_name.lower() == participant_name.lower():
            row_to_delete = i
            deleted_status = row.get("status", "")
            break

    if row_to_delete is None:
        return "No signup found under this name for this event.", "warning"

    signups_ws.delete_rows(row_to_delete)

    if deleted_status == "confirmed":
        updated_records = signups_ws.get_all_records()
        updated_df = pd.DataFrame(updated_records)

        if not updated_df.empty:
            waitlist = updated_df[
                (updated_df["event_id"] == event_id) &
                (updated_df["status"] == "waitlist")
            ]

            if not waitlist.empty:
                first_waitlist_name = str(waitlist.iloc[0]["participant_name"]).strip()

                all_records = signups_ws.get_all_records()
                for i, row in enumerate(all_records, start=2):
                    if (
                        str(row.get("event_id", "")) == str(event_id)
                        and str(row.get("participant_name", "")).strip() == first_waitlist_name
                        and str(row.get("status", "")) == "waitlist"
                    ):
                        signups_ws.update_cell(i, 5, "confirmed")
                        break

    return "Your signup has been cancelled.", "success"


def add_event(events_ws, title, category, date_value, time_value, location, max_participants, description):
    if not title.strip():
        return "Event title is required.", "warning"

    events_ws.append_row([
        str(uuid.uuid4()),
        title.strip(),
        category,
        str(date_value),
        time_value.strftime("%H:%M"),
        location.strip(),
        int(max_participants),
        description.strip(),
        "open",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])

    return "Event created successfully.", "success"


def close_event(events_ws, event_id):
    records = events_ws.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row.get("event_id", "")) == str(event_id):
            events_ws.update_cell(i, 9, "closed")
            return "Event closed successfully.", "success"
    return "Event not found.", "warning"


def show_message(message, message_type="info"):
    if message_type == "success":
        st.success(message)
    elif message_type == "warning":
        st.warning(message)
    elif message_type == "error":
        st.error(message)
    else:
        st.info(message)


st.title("🎉 Grivalia Social Hub")
st.markdown("### Your place for basketball, drinks, lunch plans and more")
st.markdown("---")

tab1, tab2 = st.tabs(["🎈 Upcoming Events", "🔐 Admin"])

with tab1:
    st.markdown("## What's happening")

    try:
        sheet, events_ws, signups_ws, events_df, signups_df = load_data()

        if events_df.empty:
            st.info("No events yet — check back soon 👀")
        else:
            open_events = events_df[events_df["status"] == "open"].copy()

            if open_events.empty:
                st.info("No open events right now.")
            else:
                category_options = ["All"] + sorted(open_events["category"].dropna().unique().tolist())
                selected_category = st.selectbox("Filter by activity", category_options)

                if selected_category != "All":
                    open_events = open_events[open_events["category"] == selected_category]

                open_events = open_events.sort_values(by=["date", "time"], ascending=True)

                for _, event in open_events.iterrows():
                    event_id = event["event_id"]
                    icon = get_category_icon(event["category"])
                    confirmed, waitlist = get_event_signups(signups_df, event_id)
                    spots_left = max(int(event["max_participants"]) - len(confirmed), 0)

                    status_badge = "🟢 Open" if spots_left > 0 else "🔴 Full"

                    with st.container(border=True):
                        st.markdown(f"## {icon} {event['title']}")
                        st.markdown(f"**{status_badge}**")
                        st.write(f"**Activity:** {event['category']}")
                        st.write(f"**When:** {format_event_datetime(str(event['date']), str(event['time']))}")
                        st.write(f"**Where:** {event['location']}")
                        if str(event["description"]).strip():
                            st.write(f"**About:** {event['description']}")

                        metric1, metric2, metric3 = st.columns(3)
                        metric1.metric("Confirmed", len(confirmed))
                        metric2.metric("Spots left", spots_left)
                        metric3.metric("Waitlist", len(waitlist))

                        attendee_names = confirmed["participant_name"].tolist() if not confirmed.empty else []
                        waitlist_names = waitlist["participant_name"].tolist() if not waitlist.empty else []

                        with st.expander("🙌 Who's in"):
                            if attendee_names:
                                for idx, name in enumerate(attendee_names, start=1):
                                    st.write(f"{idx}. {name}")
                            else:
                                st.write("No confirmed attendees yet.")

                        with st.expander("⏳ Waitlist"):
                            if waitlist_names:
                                for idx, name in enumerate(waitlist_names, start=1):
                                    st.write(f"{idx}. {name}")
                            else:
                                st.write("No one on the waitlist.")

                        col1, col2 = st.columns(2)

                        with col1:
                            join_name = st.text_input(
                                "Your name",
                                key=f"join_{event_id}",
                                placeholder="Type your name here"
                            )
                            if st.button(f"Join {icon}", key=f"join_btn_{event_id}", use_container_width=True):
                                message, msg_type = signup_user(
                                    signups_ws,
                                    signups_df,
                                    event_id,
                                    join_name,
                                    event["max_participants"]
                                )
                                show_message(message, msg_type)
                                if msg_type in ["success", "info"]:
                                    st.rerun()

                        with col2:
                            cancel_name = st.text_input(
                                "Cancel by name",
                                key=f"cancel_{event_id}",
                                placeholder="Type your name here"
                            )
                            if st.button("Cancel signup", key=f"cancel_btn_{event_id}", use_container_width=True):
                                message, msg_type = cancel_signup(
                                    signups_ws,
                                    event_id,
                                    cancel_name
                                )
                                show_message(message, msg_type)
                                if msg_type == "success":
                                    st.rerun()

    except Exception as e:
        st.error("Something went wrong while loading events.")
        st.exception(e)

with tab2:
    st.markdown("## Admin area")

    admin_password_input = st.text_input("Enter admin password", type="password")

        if admin_password_input == st.secrets["admin_password"]:
        st.success("Admin access granted.")

        try:
            sheet, events_ws, signups_ws, events_df, signups_df = load_data()

            st.markdown("### ✨ Create a new hangout")

            with st.form("create_event_form"):
                title = st.text_input("Event title", placeholder="e.g. Thursday Basketball Run")
                category = st.selectbox("Category", ["Basketball", "Drinks", "Football", "Lunch", "Padel", "Other"])
                date_value = st.date_input("Event date")
                time_value = st.time_input("Event time")
                location = st.text_input("Location", placeholder="e.g. Arsakeia Ekalis")
                max_participants = st.number_input("Max participants", min_value=1, step=1, value=10)
                description = st.text_area("Description", placeholder="Add details, notes, cost, meeting point, etc.")
                submitted = st.form_submit_button("Create Event", use_container_width=True)

                if submitted:
                    message, msg_type = add_event(
                        events_ws,
                        title,
                        category,
                        date_value,
                        time_value,
                        location,
                        max_participants,
                        description
                    )
                    show_message(message, msg_type)
                    if msg_type == "success":
                        st.rerun()

        except Exception as e:
            st.error("Something went wrong in the admin section.")
            st.exception(e)

    elif admin_password_input:
        st.error("Wrong password.")
