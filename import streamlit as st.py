import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- CLOUD-SECURE CONNECTION ---
def get_gsh_client():
    # This reads the key from Streamlit's hidden settings, not a local file
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

def load_from_google():
    try:
        client = get_gsh_client()
        # Ensure your Google Sheet is named exactly this
        sheet = client.open("Fresgo_Inventory").sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date Procured'] = pd.to_datetime(df['Date Procured']).dt.date
        return df
    except Exception as e:
        st.error(f"Cloud Connection Error: {e}")
        return pd.DataFrame(columns=["Fruit", "Qty (kg)", "Wholesale Price", "Date Procured"])

def save_to_google(df):
    client = get_gsh_client()
    sheet = client.open("Fresgo_Inventory").sheet1
    sheet.clear()
    df_save = df.copy()
    df_save['Date Procured'] = df_save['Date Procured'].astype(str)
    sheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())

# --- APP INTERFACE ---
st.title("☁️ Fresgo: Secure Cloud Sync")

if 'inventory' not in st.session_state:
    st.session_state.inventory = load_from_google()

# 1. UPLOAD (Now syncs to the cloud automatically)
uploaded_file = st.file_uploader("Upload Purchase CSV", type="csv")
if uploaded_file:
    df_new = pd.read_csv(uploaded_file)
    df_new['Date Procured'] = pd.to_datetime(df_new['Date Procured']).dt.date
    st.session_state.inventory = df_new
    save_to_google(df_new)
    st.success("Successfully saved to Google Sheets!")

# 2. DISPLAY
if not st.session_state.inventory.empty:
    st.subheader("Live Inventory from Google Sheets")
    st.table(st.session_state.inventory)
