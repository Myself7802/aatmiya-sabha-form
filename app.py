import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# ----------------- CONFIG -----------------
GOOGLE_SHEET_ID = "1ix4XIjylwxWY6VNm4jDF8ZdKUgIN3f8cBh4KPOP9fEY"
REFERENCE_SHEET_NAME = "Sheet1"
SUBMISSION_SHEET_NAME = "Sheet2"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Authenticate Google Sheets client (works locally and on Streamlit Cloud)
@st.cache_resource
def get_gspread_client():
    try:
        if "GOOGLE_SERVICE_ACCOUNT" in st.secrets:  # Running on Streamlit Cloud
            creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:  # Running locally
            SERVICE_ACCOUNT_FILE = "service_account.json"
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        st.stop()

# Load reference sheet into DataFrame
@st.cache_data
def load_reference_data():
    client = get_gspread_client()
    worksheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(REFERENCE_SHEET_NAME)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# Append data to submissions sheet
def append_submission(id_number, name, phone, marks):
    client = get_gspread_client()
    worksheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(SUBMISSION_SHEET_NAME)
    row = [str(id_number), str(name), str(phone), str(marks)]
    worksheet.append_row(row)

# ----------------- STREAMLIT UI -----------------
st.set_page_config(page_title="ID Lookup & Submit", page_icon="📝", layout="centered")

# Initialize session state
for key, value in {
    "verified": False, "submitted": False,
    "name": "", "phone": "", "id_number": "", "marks": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

# If already submitted, show Thank You page
if st.session_state.submitted:
    st.markdown("<h1 style='text-align: center; color: green;'>✅ Thank You!</h1>", unsafe_allow_html=True)
    st.write("Your submission has been recorded successfully.")
    st.stop()

st.title("🔍 ID Verification & Submission")

# Step 1: User enters ID
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

# Step 2: Show verification + Marks + Submit button
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
