import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import google.generativeai as genai

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="Fresgo OS", layout="wide")

# --- AI SETUP & DEBUGGING ---
import requests
import json

# --- DIRECT-HIT AI SETUP ---
if "gemini_api_key" in st.secrets:
    api_key = st.secrets["gemini_api_key"]
    
    # We will test the connection with a direct HTTP call first
    test_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": "Is the AI online?"}]}]}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(test_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            # If direct hit works, initialize the library
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            st.sidebar.success("✅ Fresgo AI is officially ONLINE")
        else:
            # This will show us the EXACT reason (e.g. PERMISSION_DENIED or API_KEY_INVALID)
            st.sidebar.error(f"Google Server Error: {response.status_code}")
            st.sidebar.write(response.json())
            model = None
            
    except Exception as e:
        st.sidebar.error(f"Connection Failed: {e}")
        model = None
# Biological Data & Mapping
FRUIT_SPECS = {
    "Apple": {"life": 12, "opt_t": 1, "opt_h": 90},
    "Mango": {"life": 6, "opt_t": 12, "opt_h": 85},
    "Banana": {"life": 4, "opt_t": 14, "opt_h": 85},
    "Guava": {"life": 3, "opt_t": 9, "opt_h": 90},
    "Orange": {"life": 10, "opt_t": 6, "opt_h": 85},
    "Pomegranate": {"life": 12, "opt_t": 6, "opt_h": 90},
    "Grapes": {"life": 4, "opt_t": 1, "opt_h": 90},
    "Papaya": {"life": 4, "opt_t": 12, "opt_h": 85},
    "Sapota": {"life": 3, "opt_t": 14, "opt_h": 85},
    "Pineapple": {"life": 6, "opt_t": 9, "opt_h": 85}
}

POS_MAPPING = {
    'APPLE': 'Apple', 'ORANGE': 'Orange', 'USA ORANGE': 'Orange', 'SATHUGUDI': 'Orange',
    'MADULAI': 'Pomegranate', 'KABUL MADULAI': 'Pomegranate',
    'GOVA': 'Guava', 'PAPPAYA': 'Papaya', 'SAPOTA': 'Sapota',
    'PANNER GRAPE': 'Grapes', 'SONA GRAPE': 'Grapes', 'MUSKET GRAPE': 'Grapes', 'BLACK GRAPE': 'Grapes',
    'ELAKKI BANANA': 'Banana', 'POOVAN BANANA': 'Banana'
}

# --- 2. SECURE CLOUD LOGIC (Now handles Inventory AND Sales) ---
def get_gsh_client():
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

def load_data(sheet_name, default_cols):
    try:
        client = get_gsh_client()
        sheet = client.open("Fresgo_Inventory").worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'Date Procured' in df.columns:
            df['Date Procured'] = pd.to_datetime(df['Date Procured']).dt.date
        elif not df.empty and 'Date Sold' in df.columns:
            df['Date Sold'] = pd.to_datetime(df['Date Sold']).dt.date
        else:
            df = pd.DataFrame(columns=default_cols)
        return df
    except Exception as e:
        return pd.DataFrame(columns=default_cols)

def save_data(df, sheet_name):
    try:
        client = get_gsh_client()
        sheet = client.open("Fresgo_Inventory").worksheet(sheet_name)
        sheet.clear()
        if not df.empty:
            df_save = df.copy()
            for col in df_save.columns:
                if 'Date' in col:
                    df_save[col] = df_save[col].astype(str)
            sheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    except Exception as e:
        st.error(f"Cloud Save Error: {e}")

# Load Initial State
if 'inventory' not in st.session_state:
    st.session_state.inventory = load_data("Inventory", ["Fruit", "Qty (kg)", "Wholesale Price", "Date Procured"])
if 'sales' not in st.session_state:
    st.session_state.sales = load_data("Sales", ["Date Sold", "Fruit", "Qty Sold (kg)", "Revenue (₹)"])

# --- 3. PRICING ENGINE ---
def get_price(cost, date_p, temp, humidity, fruit, margin):
    if fruit not in FRUIT_SPECS:
        return round(cost * (1 + (margin/100)), 2), "UNKNOWN"
    specs = FRUIT_SPECS[fruit]
    age = (datetime.date.today() - date_p).days
    target_price = (cost * 1.15) * (1 + (margin / 100))
    if age <= 2: return round(target_price, 2), "PREMIUM"
    h_buffer = 0.5 if humidity > specs.get('opt_h', 85) else 1.0
    total_decay = max(0, (age - 2) * 0.02) + max(0, (temp - specs['opt_t']) * 0.005 * h_buffer)
    final_price = target_price * (1 - total_decay)
    return round(max(final_price, cost * 1.25), 2), "DISCOUNTED" if final_price < target_price else "STANDARD"

# --- 4. APP INTERFACE ---
st.title("🚀 Fresgo: Complete Cloud Retail OS")

tab_hub, tab_overview, tab_price, tab_sales_ai, tab_alerts = st.tabs([
    "🔄 Data Hub", "📦 Stock Overview", "🏷️ Smart Pricing", "🤖 Sales & AI", "🚨 Action Alerts"
])

# --- TAB 1: DATA HUB ---
with tab_hub:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Stock Inward (Purchase)")
        up_purch = st.file_uploader("Upload purchase.csv", type="csv")
        if up_purch:
            df_new = pd.read_csv(up_purch)
            df_new['Date Procured'] = pd.to_datetime(df_new['Date Procured']).dt.date
            st.session_state.inventory = pd.concat([st.session_state.inventory, df_new], ignore_index=True)
            save_data(st.session_state.inventory, "Inventory")
            st.success("Purchase synced to Cloud!")
            
    with col2:
        st.subheader("2. Stock Outward (Deduct Sales)")
        up_sales = st.file_uploader("Upload IWSR.CSV to Deduct", type="csv", key="deduct")
        if up_sales:
            df_sales = pd.read_csv(up_sales, skiprows=5) 
            if 'ITEM NAME' in df_sales.columns and 'QTY' in df_sales.columns:
                df_sales['ITEM NAME'] = df_sales['ITEM NAME'].str.strip()
                df_sales['Mapped'] = df_sales['ITEM NAME'].map(POS_MAPPING)
                
                fruit_sales = df_sales.dropna(subset=['Mapped'])
                daily_totals = fruit_sales.groupby('Mapped').agg(Sold_Qty=('QTY', 'sum'), Revenue=('AMOUNT', 'sum')).reset_index()
                st.dataframe(daily_totals)
                
                if st.button("Deduct & Record Sales"):
                    # Deduct from Inventory
                    inv = st.session_state.inventory.copy()
                    for _, row in daily_totals.iterrows():
                        fruit, sold_qty = row['Mapped'], row['Sold_Qty']
                        fruit_idx = inv[inv['Fruit'] == fruit].sort_values('Date Procured').index
                        for idx in fruit_idx:
                            if sold_qty <= 0: break
                            available = inv.at[idx, 'Qty (kg)']
                            deduct = min(available, sold_qty)
                            inv.at[idx, 'Qty (kg)'] -= deduct
                            sold_qty -= deduct
                    st.session_state.inventory = inv[inv['Qty (kg)'] > 0].reset_index(drop=True)
                    save_data(st.session_state.inventory, "Inventory")
                    
                    # Append to Sales Record
                    new_sales = pd.DataFrame({
                        "Date Sold": [datetime.date.today()] * len(daily_totals),
                        "Fruit": daily_totals['Mapped'],
                        "Qty Sold (kg)": daily_totals['Sold_Qty'],
                        "Revenue (₹)": daily_totals['Revenue']
                    })
                    st.session_state.sales = pd.concat([st.session_state.sales, new_sales], ignore_index=True)
                    save_data(st.session_state.sales, "Sales")
                    
                    st.success("Sales deducted and recorded to Cloud!")

# --- TAB 2: INVENTORY OVERVIEW ---
with tab_overview:
    st.header("Current Store Inventory")
    if not st.session_state.inventory.empty:
        summary = st.session_state.inventory.groupby('Fruit').agg(Total_Qty=('Qty (kg)', 'sum'), Avg_Cost=('Wholesale Price', 'mean')).reset_index()
        summary.columns = ['Fruit', 'Total Qty (kg)', 'Avg Wholesale Cost (₹/kg)']
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        st.info("Your store has no stock.")

# --- TAB 3: SMART PRICING ---
with tab_price:
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: store_temp = st.slider("Temp (°C)", 15, 45, 30)
    with c2: store_humid = st.slider("Humidity (%)", 30, 100, 70)
        
    if not st.session_state.inventory.empty:
        inv_display = st.session_state.inventory.copy()
        with st.expander("Adjust Target Margins"):
            active_fruits = inv_display['Fruit'].unique()
            margin_cols = st.columns(min(len(active_fruits), 5))
            individual_margins = {f: margin_cols[i%5].number_input(f"{f} Margin %", value=60, step=5) for i, f in enumerate(active_fruits)}
        
        pricing_board = []
        for fruit in inv_display['Fruit'].unique():
            oldest_batch = inv_display[inv_display['Fruit'] == fruit].sort_values('Date Procured').iloc[0]
            price, status = get_price(oldest_batch['Wholesale Price'], oldest_batch['Date Procured'], store_temp, store_humid, fruit, individual_margins.get(fruit, 60))
            pricing_board.append({"Fruit": fruit, "Oldest Batch Date": oldest_batch['Date Procured'], "Shelf Price (₹/kg)": price, "Status": status})
            
        st.dataframe(pd.DataFrame(pricing_board), use_container_width=True, hide_index=True)

# --- TAB 4: SALES RECORD & AI CO-PILOT ---
with tab_sales_ai:
    st.header("Sales History & AI Assistant")
    
    col_data, col_ai = st.columns([1.5, 1])
    
    with col_data:
        st.subheader("📝 Editable Sales Ledger")
        st.caption("You can click directly on the cells below to fix POS errors. Hit Save when done.")
        
        # Interactive Editor
        edited_sales = st.data_editor(st.session_state.sales, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Save Changes to Cloud"):
            st.session_state.sales = edited_sales
            save_data(edited_sales, "Sales")
            st.success("Sales record successfully updated in Google Sheets!")
            
    with col_ai:
        st.subheader("🤖 Fresgo AI Assistant")
        st.caption("Ask questions about your margins, fast-moving items, or pricing strategies.")
        
        user_q = st.text_input("Ask the AI something about your shop:")
        if user_q and model:
            with st.spinner("Analyzing store data..."):
                # Feed the AI the current context of the store
                inv_summary = st.session_state.inventory.to_string()
                sales_summary = st.session_state.sales.tail(50).to_string() # Give it the last 50 sales
                
                prompt = f"""
                You are an expert retail store manager assistant for a high-quality fruit shop.
                Here is the current inventory data:
                {inv_summary}
                
                Here is the recent sales data:
                {sales_summary}
                
                The user asks: "{user_q}"
                Provide a short, highly actionable, and business-focused answer based strictly on the data provided.
                """
                response = model.generate_content(prompt)
                st.info(response.text)

# --- TAB 5: ACTION ALERTS ---
with tab_alerts:
    st.header("Urgent Action Dashboard")
    if not st.session_state.inventory.empty:
        inv_data = st.session_state.inventory.copy()
        alerts = [row for _, row in inv_data.iterrows() if (datetime.date.today() - row['Date Procured']).days >= (FRUIT_SPECS.get(row['Fruit'], {}).get('life', 7) * 0.70)]
                
        if alerts:
            st.error("The following items must be moved to the dark store for processing (Jam/Juice) or heavily discounted.")
            st.table(pd.DataFrame(alerts)[['Fruit', 'Qty (kg)', 'Date Procured']])
        else:
            st.success("All stock is healthy! No urgent action required.")
