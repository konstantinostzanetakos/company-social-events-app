import uuid
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Social Hub", page_icon="🎯", layout="wide")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


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


def get_event_signups(signups_df, event_id):
    event_signups = signups_df[signups_df["event_id"] == event_id].copy()
    confirmed = event_signups[event_signups["status"] == "confirmed"]
    waitlist = event_signups[event_signups["status"] == "waitlist"]
    return confirmed, waitlist


def signup_user(signups_ws, signups_df, event_id, participant_name, max_participants):
    participant_name = participant_name.strip()

    if not participant_name:
        return "Please enter your name."

    existing = signups_df[
        (signups_df["event_id"] == event_id) &
        (signups_df["participant_name"].str.lower() == participant_name.lower())
    ]

    if not existing.empty:
        return "You have already signed up for this event."

    confirmed, waitlist = get_event_signups(signups_df, event_id)

    signup_status = "confirmed" if len(confirmed) < int(max_participants) else "waitlist"

    signups_ws.append_row([
        str(uuid.uuid4()),
        event_id,
        participant_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        signup_status
    ])

    if signup_status == "confirmed":
        return "You have successfully joined the event."
    return "The event is full. You have been added to the waitlist."


def cancel_signup(signups_ws, signups_df, event_id, participant_name):
    participant_name = participant_name.strip()

    if not participant_name:
        return "Please enter your name."

    records = signups_ws.get_all_records()

    row_to_delete = None
    deleted_status = None

    for i, row in enumerate(records, start=2):
        if (
            str(row["event_id"]) == str(event_id)
            and str(row["participant_name"]).strip().lower() == participant_name.lower()
        ):
            row_to_delete = i
            deleted_status = row["status"]
            break

    if row_to_delete is None:
        return "No signup found under this name for this event."

    signups_ws.delete_rows(row_to_delete)

    if deleted_status == "confirmed":
        updated_df = pd.DataFrame(signups_ws.get_all_records())
        if not updated_df.empty:
            waitlist = updated_df[
                (updated_df["event_id"] == event_id) &
                (updated_df["status"] == "waitlist")
            ]

            if not waitlist.empty:
                first_waitlist_name = waitlist.iloc[0]["participant_name"]
                all_records = signups_ws.get_all_records()
                for i, row in enumerate(all_records, start=2):
                    if (
                        str(row["event_id"]) == str(event_id)
                        and str(row["participant_name"]).strip() == str(first_waitlist_name).strip()
                        and str(row["status"]) == "waitlist"
                    ):
                        signups_ws.update_cell(i, 5, "confirmed")
                        break

    return "Your signup has been cancelled."


def add_event(events_ws, title, category, date_value, time_value, location, max_participants, description):
    if not title.strip():
        return "Event title is required."

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

    return "Event created successfully."


def close_event(events_ws, events_df, event_id):
    records = events_ws.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row["event_id"]) == str(event_id):
            events_ws.update_cell(i, 9, "closed")
            return "Event closed successfully."
    return "Event not found."


st.title("🎯 Social Hub")
st.subheader("Internal Events Platform")

tab1, tab2 = st.tabs(["Upcoming Events", "Admin"])

with tab1:
    st.markdown("## Upcoming Events")

    try:
        sheet, events_ws, signups_ws, events_df, signups_df = load_data()

        if events_df.empty:
            st.info("No events available yet.")
        else:
            open_events = events_df[events_df["status"] == "open"].copy()

            if open_events.empty:
                st.info("No open events at the moment.")
            else:
                category_options = ["All"] + sorted(open_events["category"].dropna().unique().tolist())
                selected_category = st.selectbox("Filter by category", category_options)

                if selected_category != "All":
                    open_events = open_events[open_events["category"] == selected_category]

                open_events = open_events.sort_values(by=["date", "time"], ascending=True)

                for _, event in open_events.iterrows():
                    event_id = event["event_id"]
                    confirmed, waitlist = get_event_signups(signups_df, event_id)
                    spots_left = max(int(event["max_participants"]) - len(confirmed), 0)

                    with st.container(border=True):
                        st.markdown(f"### {event['title']}")
                        st.write(f"**Category:** {event['category']}")
                        st.write(f"**When:** {format_event_datetime(str(event['date']), str(event['time']))}")
                        st.write(f"**Location:** {event['location']}")
                        st.write(f"**Description:** {event['description']}")
                        st.write(f"**Confirmed:** {len(confirmed)} / {int(event['max_participants'])}")
                        st.write(f"**Spots left:** {spots_left}")
                        st.write(f"**Waitlist:** {len(waitlist)}")

                        attendee_names = confirmed["participant_name"].tolist() if not confirmed.empty else []
                        waitlist_names = waitlist["participant_name"].tolist() if not waitlist.empty else []

                        with st.expander("See attendees"):
                            if attendee_names:
                                for name in attendee_names:
                                    st.write(f"- {name}")
                            else:
                                st.write("No confirmed attendees yet.")

                        if waitlist_names:
                            with st.expander("See waitlist"):
                                for name in waitlist_names:
                                    st.write(f"- {name}")

                        col1, col2 = st.columns(2)

                        with col1:
                            join_name = st.text_input(
                                "Your name",
                                key=f"join_{event_id}"
                            )
                            if st.button("Join Event", key=f"join_btn_{event_id}"):
                                message = signup_user(
                                    signups_ws,
                                    signups_df,
                                    event_id,
                                    join_name,
                                    event["max_participants"]
                                )
                                if "successfully" in message or "waitlist" in message:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.warning(message)

                        with col2:
                            cancel_name = st.text_input(
                                "Cancel signup by name",
                                key=f"cancel_{event_id}"
                            )
                            if st.button("Cancel Signup", key=f"cancel_btn_{event_id}"):
                                message = cancel_signup(
                                    signups_ws,
                                    signups_df,
                                    event_id,
                                    cancel_name
                                )
                                if "cancelled" in message:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.warning(message)

    except Exception as e:
        st.error("Something went wrong while loading events.")
        st.exception(e)

with tab2:
    st.markdown("## Admin")

    admin_password_input = st.text_input("Enter admin password", type="password")

    if admin_password_input == st.secrets["admin_password"]:
        st.success("Admin access granted.")

        try:
            sheet, events_ws, signups_ws, events_df, signups_df = load_data()

            st.markdown("### Create New Event")

            with st.form("create_event_form"):
                title = st.text_input("Event title")
                category = st.selectbox("Category", ["Basketball", "Drinks", "Football", "Lunch", "Padel", "Other"])
                date_value = st.date_input("Event date")
                time_value = st.time_input("Event time")
                location = st.text_input("Location")
                max_participants = st.number_input("Max participants", min_value=1, step=1, value=10)
                description = st.text_area("Description")
                submitted = st.form_submit_button("Create Event")

                if submitted:
                    message = add_event(
                        events_ws,
                        title,
                        category,
                        date_value,
                        time_value,
                        location,
                        max_participants,
                        description
                    )
                    if "successfully" in message:
                        st.success(message)
                        st.rerun()
                    else:
                        st.warning(message)

            st.markdown("### Manage Events")

            if events_df.empty:
                st.info("No events created yet.")
            else:
                for _, event in events_df.sort_values(by=["date", "time"], ascending=True).iterrows():
                    with st.container(border=True):
                        st.write(f"**{event['title']}**")
                        st.write(f"{format_event_datetime(str(event['date']), str(event['time']))}")
                        st.write(f"Location: {event['location']}")
                        st.write(f"Status: {event['status']}")

                        if event["status"] == "open":
                            if st.button("Close Event", key=f"close_{event['event_id']}"):
                                message = close_event(events_ws, events_df, event["event_id"])
                                st.success(message)
                                st.rerun()

        except Exception as e:
            st.error("Something went wrong in the admin section.")
            st.exception(e)

    elif admin_password_input:
        st.error("Wrong password.")
