import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# ----------------- CONFIG -----------------
GOOGLE_SHEET_ID = "1ix4XIjylwxWY6VNm4jDF8ZdKUgIN3f8cBh4KPOP9fEY"  # Google Sheet file ID

REFERENCE_SHEET_NAME = "NAME_LIST"  # Tab name for reference data
SUBMISSION_SHEET_NAME = "MARKS SHEET LIST"  # Tab name for submissions
ADMIN_PASSWORD = "exam@atm"  # Password for history & not submitted page

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Authenticate Google Sheets client (works locally and on Streamlit Cloud)
@st.cache_resource
def get_gspread_client():
    try:
        if "google_service_account" in st.secrets:  # Running on Streamlit Cloud
            creds_dict = dict(st.secrets["google_service_account"])
            # Fix private_key newlines
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
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
@st.cache_data(ttl=0)
def load_reference_data():
    client = get_gspread_client()
    worksheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(REFERENCE_SHEET_NAME)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # Ensure correct column names
    df.rename(columns={
    "NO": "NO",
    "ID Number": "SMK NO",
    "Name": "FULL NAME",
    "Phone Number": "PHONE NO"
    }, inplace=True)

    # If ATM NO column is missing in the sheet, add empty column
    if "ATM NO" not in df.columns:
        df["ATM NO"] = ""

    return df

# Load submissions sheet into DataFrame (no caching so it always refreshes)
def load_submission_data():
    client = get_gspread_client()
    worksheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(SUBMISSION_SHEET_NAME)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# Append data to submissions sheet
def append_submission(no, smk_no, atm_no, full_name, phone_no, marks):
    client = get_gspread_client()
    worksheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(SUBMISSION_SHEET_NAME)
    row = [str(no), str(smk_no), str(atm_no), str(full_name), str(phone_no), str(marks)]
    worksheet.append_row(row)

# ----------------- STREAMLIT UI -----------------
st.set_page_config(page_title="MARKS ENTRY", page_icon="📝", layout="centered")

# Sidebar navigation
page = st.sidebar.radio("📌 Select Page", ["MARKS ENTRY", "MARKS SHEET LIST", "PENDING MARK ENTRY"])

# ----------------- Helper: Admin Login -----------------
def admin_login(session_key):
    if session_key not in st.session_state:
        st.session_state[session_key] = False

    if not st.session_state[session_key]:
        password_input = st.text_input("Enter Admin Password:", type="password", key=f"pwd_{session_key}")
        if st.button("Login", key=f"login_btn_{session_key}"):
            if password_input == ADMIN_PASSWORD:
                st.session_state[session_key] = True
                st.rerun()
            else:
                st.error("Incorrect password. Access denied.")
                return False
    return st.session_state[session_key]

# ----------------- PAGE 1: MARKS ENTRY -----------------
if page == "MARKS ENTRY":
    if "verified" not in st.session_state:
        st.session_state.verified = False
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "smk_no" not in st.session_state:
        st.session_state.smk_no = ""
    if "atm_no" not in st.session_state:
        st.session_state.atm_no = ""
    if "full_name" not in st.session_state:
        st.session_state.full_name = ""
    if "phone_no" not in st.session_state:
        st.session_state.phone_no = ""
    if "marks" not in st.session_state:
        st.session_state.marks = ""

    if st.session_state.submitted:
        st.markdown("<h1 style='text-align: center; color: green;'>✅ Thank You!</h1>", unsafe_allow_html=True)
        st.write("Your submission has been recorded successfully.")
        st.stop()

    st.title("🔍 MARKS ENTRY")

    if not st.session_state.verified:
        smk_no = st.text_input("Enter your SMK NO:")
        if st.button("Check"):
            if not smk_no.strip():
                st.error("Please enter an SMK NO.")
            else:
                try:
                    df = load_reference_data()
                    match = df[df["SMK NO"].astype(str) == smk_no.strip()]

                    if match.empty:
                        st.error("❌ SMK NO not found. Please check and try again.")
                    else:
                        st.session_state.no = str(match.iloc[0]["NO"])
                        st.session_state.smk_no = smk_no.strip()
                        st.session_state.atm_no = str(match.iloc[0]["ATM NO"])
                        st.session_state.full_name = str(match.iloc[0]["FULL NAME"])
                        st.session_state.phone_no = str(match.iloc[0]["PHONE NO"])
                        st.session_state.verified = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Error connecting to Google Sheets: {e}")

    else:
        st.success("✅ SMK Found! Thanks.")
        st.text_input("SMK NO:", value=st.session_state.smk_no, disabled=True)
        st.text_input("ATM NO:", value=st.session_state.atm_no, disabled=True)
        st.text_input("Full Name:", value=st.session_state.full_name, disabled=True)
        st.text_input("Phone Number:", value=st.session_state.phone_no, disabled=True)
        st.session_state.marks = st.text_input("Enter Marks:")


        if st.button("Confirm & Submit"):
            if not st.session_state.marks.strip():
                st.error("Please enter marks before submitting.")
            else:
                try:
                    append_submission(
                        st.session_state.no,
                        st.session_state.smk_no,
                        st.session_state.atm_no,
                        st.session_state.full_name,
                        st.session_state.phone_no,
                        st.session_state.marks
                    )

                    st.session_state.submitted = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error submitting data: {e}")

# ----------------- PAGE 2: History -----------------
elif page == "MARKS SHEET LIST":
    st.title("📜 MARKS SHEET LIST")
    if admin_login("history_access"):
        try:
            df_history = load_submission_data()
            if df_history.empty:
                st.info("No submissions found yet.")
            else:
                st.dataframe(df_history, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading submission history: {e}")

# ----------------- PAGE 3: Not Submitted List -----------------
elif page == "PENDING MARK ENTRY":
    st.title("📜 PENDING MARK ENTRY")
    if admin_login("not_submitted_access"):
        try:
            df_ref = load_reference_data()
            df_sub = load_submission_data()

            # Ensure SMK NO column exists in both
            if "SMK NO" not in df_ref.columns or "SMK NO" not in df_sub.columns:
                st.error("SMK NO column missing in one of the sheets.")
            else:
                submitted_ids = set(df_sub["SMK NO"].astype(str))
                not_submitted_df = df_ref[~df_ref["SMK NO"].astype(str).isin(submitted_ids)]

                if not_submitted_df.empty:
                    st.success("🎉 All users have submitted the form.")
                else:
                    st.warning(f"⚠ {len(not_submitted_df)} users have not submitted the form.")
                    st.dataframe(not_submitted_df, use_container_width=True)

        except Exception as e:
            st.error(f"Error loading not submitted list: {e}")
