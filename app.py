import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# ----------------- CONFIG -----------------
GOOGLE_SHEET_ID = "1ix4XIjylwxWY6VNm4jDF8ZdKUgIN3f8cBh4KPOP9fEY"
REFERENCE_SHEET_NAME = "Sheet1"
SUBMISSION_SHEET_NAME = "Sheet2"
ADMIN_PASSWORD = "12345"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Authenticate Google Sheets client (works locally & in Streamlit Cloud)
@st.cache_resource
def get_gspread_client():
    try:
        if "google_service_account" in st.secrets:
            # Running on Streamlit Cloud
            creds = Credentials.from_service_account_info(
                dict(st.secrets["google_service_account"]), scopes=SCOPES
            )
        else:
            # Running locally
            SERVICE_ACCOUNT_FILE = "service_account.json"
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        st.stop()

# Load reference sheet into DataFrame
@st.cache_data
def load_reference_data():
    worksheet = get_gspread_client().open_by_key(GOOGLE_SHEET_ID).worksheet(REFERENCE_SHEET_NAME)
    return pd.DataFrame(worksheet.get_all_records())

# Always fresh submission data
def load_submission_data():
    worksheet = get_gspread_client().open_by_key(GOOGLE_SHEET_ID).worksheet(SUBMISSION_SHEET_NAME)
    return pd.DataFrame(worksheet.get_all_records())

# Append data to submissions sheet
def append_submission(id_number, name, phone, marks):
    worksheet = get_gspread_client().open_by_key(GOOGLE_SHEET_ID).worksheet(SUBMISSION_SHEET_NAME)
    worksheet.append_row([str(id_number), str(name), str(phone), str(marks)])

# ----------------- STREAMLIT UI -----------------
st.set_page_config(page_title="ID Lookup & History", page_icon="📝", layout="centered")

# Sidebar navigation
page = st.sidebar.radio("📌 Select Page", ["ID Submission", "History"])

# ----------------- PAGE 1: ID Submission -----------------
if page == "ID Submission":
    for key in ["verified", "submitted", "name", "phone", "id_number", "marks"]:
        if key not in st.session_state:
            st.session_state[key] = "" if key not in ["verified", "submitted"] else False

    if st.session_state.submitted:
        st.markdown("<h1 style='text-align: center; color: green;'>✅ Thank You!</h1>", unsafe_allow_html=True)
        st.write("Your submission has been recorded successfully.")
        st.stop()

    st.title("🔍 ID Verification & Submission")

    if not st.session_state.verified:
        id_number = st.text_input("Enter your ID Number:")
        if st.button("Check"):
            if not id_number.strip():
                st.error("Please enter an ID number.")
            else:
                try:
                    df = load_reference_data()
                    match = df[df["ID Number"].astype(str) == id_number.strip()]

                    if match.empty:
                        st.error("❌ ID not found. Please check and try again.")
                    else:
                        st.session_state.id_number = id_number.strip()
                        st.session_state.name = str(match.iloc[0]["Name"])
                        st.session_state.phone = str(match.iloc[0]["Phone Number"])
                        st.session_state.verified = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Error connecting to Google Sheets: {e}")
    else:
        st.success("✅ ID found! Please verify your details.")
        st.text_input("Name:", value=st.session_state.name, disabled=True)
        st.text_input("Phone Number:", value=st.session_state.phone, disabled=True)
        st.session_state.marks = st.text_input("Enter Marks:")

        if st.button("Confirm & Submit"):
            if not st.session_state.marks.strip():
                st.error("Please enter marks before submitting.")
            else:
                try:
                    append_submission(
                        st.session_state.id_number,
                        st.session_state.name,
                        st.session_state.phone,
                        st.session_state.marks
                    )
                    st.session_state.submitted = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error submitting data: {e}")

# ----------------- PAGE 2: History (Password Protected) -----------------
elif page == "History":
    st.title("🔐 Admin Login Required")

    if "history_access" not in st.session_state:
        st.session_state.history_access = False

    if not st.session_state.history_access:
        password_input = st.text_input("Enter Admin Password:", type="password")
        if st.button("Login"):
            if password_input == ADMIN_PASSWORD:
                st.session_state.history_access = True
                st.rerun()
            else:
                st.error("Incorrect password. Access denied.")
    else:
        st.title("📜 Submission History")
        try:
            df_history = load_submission_data()
            if df_history.empty:
                st.info("No submissions found yet.")
            else:
                st.dataframe(df_history, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading submission history: {e}")
