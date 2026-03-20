import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Social Hub", page_icon="🎯", layout="wide")

st.title("🎯 Social Hub")
st.subheader("Internal Events Platform")

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

try:
    sheet = connect_to_gsheet()
    events_ws = sheet.worksheet("events")
    signups_ws = sheet.worksheet("signups")

    events_data = events_ws.get_all_records()
    signups_data = signups_ws.get_all_records()

    events_df = pd.DataFrame(events_data)
    signups_df = pd.DataFrame(signups_data)

    st.success("Connected to Google Sheets successfully.")

    st.markdown("### Events table")
    st.dataframe(events_df, use_container_width=True)

    st.markdown("### Signups table")
    st.dataframe(signups_df, use_container_width=True)

except Exception as e:
    st.error("Connection failed.")
    st.exception(e)
