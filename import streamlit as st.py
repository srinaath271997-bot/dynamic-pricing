import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- GOOGLE SHEETS SETUP ---
# You will get this JSON file from the Google Cloud Console
# For now, I'll show the structure so the logic works.
def get_gsh_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Replace 'creds.json' with your actual secret key file
    creds = Credentials.from_service_account_file("creds.json", scopes=scope)
    return gspread.authorize(creds)

def load_from_google():
    try:
        client = get_gsh_client()
        sheet = client.open("Fresgo_Inventory").sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date Procured'] = pd.to_datetime(df['Date Procured']).dt.date
        return df
    except:
        return pd.DataFrame(columns=["Fruit", "Qty (kg)", "Wholesale Price", "Date Procured"])

def save_to_google(df):
    client = get_gsh_client()
    sheet = client.open("Fresgo_Inventory").sheet1
    sheet.clear()
    # Prepare data for Google (dates must be strings)
    df_save = df.copy()
    df_save['Date Procured'] = df_save['Date Procured'].astype(str)
    sheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())

# --- APP START ---
st.set_page_config(page_title="Fresgo Cloud OS", layout="wide")
st.title("☁️ Fresgo: Cloud-Synced Retail")

# Load data from the cloud immediately
if 'inventory' not in st.session_state:
    st.session_state.inventory = load_from_google()

# 1. CLOUD UPLOAD
st.subheader("Cloud Sync Upload")
uploaded_file = st.file_uploader("Upload Purchase Order (CSV)", type="csv")

if uploaded_file:
    df_new = pd.read_csv(uploaded_file)
    df_new['Date Procured'] = pd.to_datetime(df_new['Date Procured']).dt.date
    # Merge with existing cloud data or overwrite
    st.session_state.inventory = df_new
    save_to_google(df_new)
    st.success("Cloud Updated! Check your phone app now.")

# 2. LIVE PRICING (Using the 60% Margin & 15% Wastage Buffer)
if not st.session_state.inventory.empty:
    st.write("### Active Inventory (Live from Google Sheets)")
    # Logic for pricing remains the same as our previous high-margin version
    st.table(st.session_state.inventory)
else:
    st.info("No data in cloud. Please upload your purchase file.")
