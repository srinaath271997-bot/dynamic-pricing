import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- 1. BIOLOGICAL DATA & POS MAPPING ---
FRUIT_SPECS = {
    "Apple": {"life": 12, "opt_t": 1},
    "Mango": {"life": 6, "opt_t": 12},
    "Banana": {"life": 4, "opt_t": 14},
    "Guava": {"life": 3, "opt_t": 9},
    "Orange": {"life": 10, "opt_t": 6},
    "Pomegranate": {"life": 12, "opt_t": 6},
    "Grapes": {"life": 4, "opt_t": 1},
    "Papaya": {"life": 4, "opt_t": 12},
    "Sapota": {"life": 3, "opt_t": 14},
    "Pineapple": {"life": 6, "opt_t": 9}
}

POS_MAPPING = {
    'APPLE': 'Apple', 'ORANGE': 'Orange', 'USA ORANGE': 'Orange', 'SATHUGUDI': 'Orange',
    'MADULAI': 'Pomegranate', 'KABUL MADULAI': 'Pomegranate',
    'GOVA': 'Guava', 'PAPPAYA': 'Papaya', 'SAPOTA': 'Sapota',
    'PANNER GRAPE': 'Grapes', 'SONA GRAPE': 'Grapes', 'MUSKET GRAPE': 'Grapes', 'BLACK GRAPE': 'Grapes',
    'ELAKKI BANANA': 'Banana', 'POOVAN BANANA': 'Banana'
}

# --- 2. SECURE CLOUD DATABASE LOGIC ---
def get_gsh_client():
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

def load_from_google():
    try:
        client = get_gsh_client()
        sheet = client.open("Fresgo_Inventory").sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date Procured'] = pd.to_datetime(df['Date Procured']).dt.date
        else:
            df = pd.DataFrame(columns=["Fruit", "Qty (kg)", "Wholesale Price", "Date Procured"])
        return df
    except Exception as e:
        st.error(f"Cloud Load Error: {e}")
        return pd.DataFrame(columns=["Fruit", "Qty (kg)", "Wholesale Price", "Date Procured"])

def save_to_google(df):
    try:
        client = get_gsh_client()
        sheet = client.open("Fresgo_Inventory").sheet1
        sheet.clear()
        if not df.empty:
            df_save = df.copy()
            df_save['Date Procured'] = df_save['Date Procured'].astype(str)
            sheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    except Exception as e:
        st.error(f"Cloud Save Error: {e}")

# --- 3. HIGH-MARGIN PRICING ENGINE ---
def get_price(cost, date_p, temp, fruit, margin):
    if fruit not in FRUIT_SPECS:
        return round(cost * (1 + (margin/100)), 2), "UNKNOWN"
    
    age = (datetime.date.today() - date_p).days
    
    # 15% Wastage Buffer ensures bad fruit doesn't kill profits
    real_cost = cost * 1.15 
    target_price = real_cost * (1 + (margin / 100))
    
    # Profit Lock: No discounts for the first 2 days
    if age <= 2:
        return round(target_price, 2), "PREMIUM"
        
    # Gradual Decay based on age
    decay = max(0, (age - 2) * 0.02)
    final_price = target_price * (1 - decay)
    
    # Absolute Floor: Never sell below 25% profit over base cost
    floor = cost * 1.25 
    status = "DISCOUNTED" if final_price < target_price else "STANDARD"
    return round(max(final_price, floor), 2), status

# --- 4. APP INTERFACE ---
st.set_page_config(page_title="Fresgo OS", layout="wide")
st.title("🚀 Fresgo: Complete Cloud Retail OS")

if 'inventory' not in st.session_state:
    st.session_state.inventory = load_from_google()

tab_inv, tab_price, tab_analytics = st.tabs(["📦 Inventory & Sales", "🏷️ Smart Pricing", "📊 Profit Monitor"])

# --- TAB 1: UPLOADS & DEDUCTIONS ---
with tab_inv:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Inward (Procurement)")
        up_purch = st.file_uploader("Upload simple purchase.csv", type="csv")
        if up_purch:
            df_new = pd.read_csv(up_purch)
            df_new['Date Procured'] = pd.to_datetime(df_new['Date Procured']).dt.date
            st.session_state.inventory = pd.concat([st.session_state.inventory, df_new], ignore_index=True)
            save_to_google(st.session_state.inventory)
            st.success("Purchase synced to Cloud!")
            
    with col2:
        st.subheader("2. Outward (Daily Sales)")
        up_sales = st.file_uploader("Upload IWSR.CSV", type="csv")
        if up_sales:
            # Skips your 5 lines of POS metadata
            df_sales = pd.read_csv(up_sales, skiprows=5) 
            if 'ITEM NAME' in df_sales.columns and 'QTY' in df_sales.columns:
                df_sales['ITEM NAME'] = df_sales['ITEM NAME'].str.strip()
                df_sales['Mapped'] = df_sales['ITEM NAME'].map(POS_MAPPING)
                
                st.write("Recognized Sales by Category:")
                fruit_sales = df_sales.dropna(subset=['Mapped'])
                daily_totals = fruit_sales.groupby('Mapped')['QTY'].sum()
                st.dataframe(daily_totals)
                
                if st.button("Deduct Sales & Update Cloud"):
                    inv = st.session_state.inventory.copy()
                    
                    # FIFO Logic: Deduct from oldest stock first
                    for fruit, sold_qty in daily_totals.items():
                        fruit_idx = inv[inv['Fruit'] == fruit].sort_values('Date Procured').index
                        for idx in fruit_idx:
                            if sold_qty <= 0:
                                break
                            available = inv.at[idx, 'Qty (kg)']
                            deduct = min(available, sold_qty)
                            inv.at[idx, 'Qty (kg)'] -= deduct
                            sold_qty -= deduct
                    
                    # Clean up empty stock
                    inv = inv[inv['Qty (kg)'] > 0].reset_index(drop=True)
                    st.session_state.inventory = inv
                    save_to_google(inv)
                    st.success("Sales deducted! Cloud inventory is up to date.")
            else:
                st.error("Could not find ITEM NAME or QTY in the file. Check formatting.")

# --- TAB 2: LIVE PRICING ENGINE ---
with tab_price:
    st.header("Today's Shelf Prices")
    c1, c2 = st.columns(2)
    store_temp = c1.slider("Store Temp (°C)", 15, 45, 30)
    target_m = c2.number_input("Target Margin %", value=60)
    
    if not st.session_state.inventory.empty:
        inv_display = st.session_state.inventory.copy()
        prices = []
        statuses = []
        
        for _, row in inv_display.iterrows():
            p, s = get_price(row['Wholesale Price'], row['Date Procured'], store_temp, row['Fruit'], target_m)
            prices.append(p)
            statuses.append(s)
        
        inv_display['Selling Price (₹)'] = prices
        inv_display['Status'] = statuses
        st.table(inv_display)
    else:
        st.info("Inventory is empty. Upload procurement data.")

# --- TAB 3: BUSINESS TACTICS ---
with tab_analytics:
    st.header("Margin & Strategy Monitor")
    st.info("Your pricing engine automatically inflates your wholesale cost by **15%** behind the scenes. This ensures that even if you lose 1.5kg out of every 10kg to spoilage, your target margin remains intact on the sold goods.")
    st.write("### Competitor Shield")
    st.write("If nearby markets drop their prices, rely on the **Absolute Floor** logic built into Tab 2. Even on your oldest fruit, the system will mathematically prevent you from pricing below a 25% profit margin.")
