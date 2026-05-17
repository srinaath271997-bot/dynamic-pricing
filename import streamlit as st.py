import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- 1. BIOLOGICAL DATA & POS MAPPING ---
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

# --- 2. SECURE CLOUD DATABASE LOGIC (UNTOUCHED) ---
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

# --- 3. PRICING ENGINE ---
def get_price(cost, date_p, temp, humidity, fruit, margin):
    if fruit not in FRUIT_SPECS:
        return round(cost * (1 + (margin/100)), 2), "UNKNOWN"
    
    specs = FRUIT_SPECS[fruit]
    age = (datetime.date.today() - date_p).days
    
    real_cost = cost * 1.15 
    target_price = real_cost * (1 + (margin / 100))
    
    if age <= 2:
        return round(target_price, 2), "PREMIUM"
        
    h_buffer = 0.5 if humidity > specs.get('opt_h', 85) else 1.0
    age_decay = max(0, (age - 2) * 0.02)
    temp_decay = max(0, (temp - specs['opt_t']) * 0.005 * h_buffer)
    total_decay = age_decay + temp_decay
    
    final_price = target_price * (1 - total_decay)
    
    floor = cost * 1.25 
    status = "DISCOUNTED" if final_price < target_price else "STANDARD"
    return round(max(final_price, floor), 2), status

# --- 4. APP INTERFACE ---
st.set_page_config(page_title="Fresgo OS", layout="wide")
st.title("🚀 Fresgo: Complete Cloud Retail OS")

if 'inventory' not in st.session_state:
    st.session_state.inventory = load_from_google()

# 5 Dedicated Tabs for clear workflow
tab_hub, tab_overview, tab_price, tab_profit, tab_alerts = st.tabs([
    "🔄 Data Hub", "📦 Stock Overview", "🏷️ Smart Pricing", "💰 Profit Calc", "🚨 Action Alerts"
])

# --- TAB 1: DATA HUB (Uploads & Deductions) ---
with tab_hub:
    st.info("Use this tab to upload new stock or deduct daily sales from your cloud database.")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Stock Inward (Purchase)")
        up_purch = st.file_uploader("Upload purchase.csv", type="csv")
        if up_purch:
            df_new = pd.read_csv(up_purch)
            df_new['Date Procured'] = pd.to_datetime(df_new['Date Procured']).dt.date
            st.session_state.inventory = pd.concat([st.session_state.inventory, df_new], ignore_index=True)
            save_to_google(st.session_state.inventory)
            st.success("Purchase synced to Cloud!")
            
    with col2:
        st.subheader("2. Stock Outward (Deduct Sales)")
        up_sales = st.file_uploader("Upload IWSR.CSV to Deduct Stock", type="csv", key="deduct")
        if up_sales:
            df_sales = pd.read_csv(up_sales, skiprows=5) 
            if 'ITEM NAME' in df_sales.columns and 'QTY' in df_sales.columns:
                df_sales['ITEM NAME'] = df_sales['ITEM NAME'].str.strip()
                df_sales['Mapped'] = df_sales['ITEM NAME'].map(POS_MAPPING)
                
                fruit_sales = df_sales.dropna(subset=['Mapped'])
                daily_totals = fruit_sales.groupby('Mapped')['QTY'].sum()
                st.dataframe(daily_totals)
                
                if st.button("Deduct Sales & Update Cloud"):
                    inv = st.session_state.inventory.copy()
                    for fruit, sold_qty in daily_totals.items():
                        fruit_idx = inv[inv['Fruit'] == fruit].sort_values('Date Procured').index
                        for idx in fruit_idx:
                            if sold_qty <= 0: break
                            available = inv.at[idx, 'Qty (kg)']
                            deduct = min(available, sold_qty)
                            inv.at[idx, 'Qty (kg)'] -= deduct
                            sold_qty -= deduct
                    
                    inv = inv[inv['Qty (kg)'] > 0].reset_index(drop=True)
                    st.session_state.inventory = inv
                    save_to_google(inv)
                    st.success("Sales deducted! Cloud inventory updated.")

# --- TAB 2: INVENTORY OVERLOOK ---
with tab_overview:
    st.header("Current Store Inventory")
    if not st.session_state.inventory.empty:
        inv_data = st.session_state.inventory.copy()
        
        # Group data to make it easy to read
        summary = inv_data.groupby('Fruit').agg(
            Total_Qty=('Qty (kg)', 'sum'),
            Avg_Cost=('Wholesale Price', 'mean')
        ).reset_index()
        
        # Format for display
        summary.columns = ['Fruit', 'Total Qty (kg)', 'Avg Wholesale Cost (₹/kg)']
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        st.info("Your store has no stock. Please upload a purchase file.")

# --- TAB 3: SMART PRICING (Simplified & Innovative) ---
with tab_price:
    st.header("Shelf Pricing Board")
    
    # Smaller sliders clustered to the left side
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        store_temp = st.slider("Temp (°C)", 15, 45, 30)
    with c2:
        store_humid = st.slider("Humidity (%)", 30, 100, 70)
        
    st.write("---")
    
    if not st.session_state.inventory.empty:
        inv_display = st.session_state.inventory.copy()
        
        # Expandable margins to keep UI clean
        with st.expander("Adjust Individual Target Margins"):
            active_fruits = inv_display['Fruit'].unique()
            margin_cols = st.columns(min(len(active_fruits), 5))
            individual_margins = {}
            for i, fruit_name in enumerate(active_fruits):
                col = margin_cols[i % 5]
                individual_margins[fruit_name] = col.number_input(f"{fruit_name} Margin %", value=60, step=5)
        
        # INNOVATION: Calculate price based on the OLDEST batch to clear stock, and group it.
        # This makes the dashboard 10x easier to read for staff.
        pricing_board = []
        for fruit in inv_display['Fruit'].unique():
            fruit_stock = inv_display[inv_display['Fruit'] == fruit].sort_values('Date Procured')
            oldest_batch = fruit_stock.iloc[0] # Get the oldest batch
            
            f_margin = individual_margins.get(fruit, 60)
            price, status = get_price(oldest_batch['Wholesale Price'], oldest_batch['Date Procured'], store_temp, store_humid, fruit, f_margin)
            
            pricing_board.append({
                "Fruit": fruit,
                "Oldest Batch Date": oldest_batch['Date Procured'],
                "Recommended Shelf Price (₹/kg)": price,
                "Status": status
            })
            
        st.dataframe(pd.DataFrame(pricing_board), use_container_width=True, hide_index=True)
    else:
        st.info("Add inventory to see pricing recommendations.")

# --- TAB 4: PROFIT CALCULATOR (NEW) ---
with tab_profit:
    st.header("Daily Profit Analyzer")
    st.caption("Upload your end-of-day IWSR.CSV to calculate actual real-world profit against your average wholesale costs.")
    
    calc_sales = st.file_uploader("Upload IWSR.CSV for Profit Check", type="csv", key="profit_calc")
    
    if calc_sales and not st.session_state.inventory.empty:
        df_calc = pd.read_csv(calc_sales, skiprows=5)
        if 'ITEM NAME' in df_calc.columns and 'AMOUNT' in df_calc.columns and 'QTY' in df_calc.columns:
            df_calc['ITEM NAME'] = df_calc['ITEM NAME'].str.strip()
            df_calc['Mapped'] = df_calc['ITEM NAME'].map(POS_MAPPING)
            df_calc = df_calc.dropna(subset=['Mapped'])
            
            # Aggregate Sales
            sales_summary = df_calc.groupby('Mapped').agg(
                Sold_Qty=('QTY', 'sum'),
                Revenue=('AMOUNT', 'sum')
            ).reset_index()
            
            # Get Average Cost from Current Inventory
            inv_costs = st.session_state.inventory.groupby('Fruit')['Wholesale Price'].mean().reset_index()
            
            # Merge to calculate profit
            analysis = pd.merge(sales_summary, inv_costs, left_on='Mapped', right_on='Fruit', how='left')
            analysis = analysis.dropna(subset=['Wholesale Price']) # Only calculate if we know the cost
            
            # COGS = Qty * Avg Cost * 1.15 (Wastage buffer logic applied backward to find true cost)
            analysis['True Cost'] = analysis['Sold_Qty'] * analysis['Wholesale Price'] * 1.15
            analysis['Gross Profit (₹)'] = analysis['Revenue'] - analysis['True Cost']
            
            st.dataframe(analysis[['Fruit', 'Sold_Qty', 'Revenue', 'True Cost', 'Gross Profit (₹)']], hide_index=True, use_container_width=True)
            
            total_profit = analysis['Gross Profit (₹)'].sum()
            st.metric("Total Day Profit (Adjusted for Wastage)", f"₹{total_profit:,.2f}")
            
# --- TAB 5: ACTION ALERTS ---
with tab_alerts:
    st.header("Store Action Dashboard")
    if not st.session_state.inventory.empty:
        inv_data = st.session_state.inventory.copy()
        total_capital = (inv_data['Qty (kg)'] * inv_data['Wholesale Price']).sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Capital Tied in Stock", f"₹{total_capital:,.2f}")
        c2.metric("Total Stock Volume", f"{inv_data['Qty (kg)'].sum():,.1f} kg")
        
        st.write("---")
        st.subheader("🚨 Urgent Clearance & Juice Bar Transfers")
        
        alerts = []
        for _, row in inv_data.iterrows():
            age = (datetime.date.today() - row['Date Procured']).days
            f_life = FRUIT_SPECS.get(row['Fruit'], {}).get('life', 7)
            
            if age >= (f_life * 0.70):
                alerts.append(row)
                
        if alerts:
            st.error("The following items must be moved to the dark store for processing (Jam/Juice) or heavily discounted.")
            alert_df = pd.DataFrame(alerts)
            st.table(alert_df[['Fruit', 'Qty (kg)', 'Date Procured']])
        else:
            st.success("All stock is healthy! No urgent action required.")
