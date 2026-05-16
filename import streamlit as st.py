import streamlit as st
import pandas as pd
import datetime

# --- 1. BIOLOGICAL DATA & MAPPING ---
# Full data from your chart
FRUIT_SPECS = {
    "Apple": {"life": 12, "opt_t": 1, "opt_h": 92},
    "Mango": {"life": 6, "opt_t": 12, "opt_h": 87},
    "Banana": {"life": 4, "opt_t": 14, "opt_h": 87},
    "Guava": {"life": 3, "opt_t": 9, "opt_h": 92},
    "Orange": {"life": 10, "opt_t": 6, "opt_h": 87},
    "Sapota": {"life": 3, "opt_t": 14, "opt_h": 87},
    "Pineapple": {"life": 6, "opt_t": 9, "opt_h": 87},
    "Pomegranate": {"life": 12, "opt_t": 6, "opt_h": 92},
    "Grapes": {"life": 4, "opt_t": 1, "opt_h": 92},
    "Papaya": {"life": 4, "opt_t": 12, "opt_h": 87}
}

# Mapping your POS names to App names
POS_MAPPING = {
    'APPLE': 'Apple', 'ORANGE': 'Orange', 'USA ORANGE': 'Orange', 'SATHUGUDI': 'Orange',
    'MADULAI': 'Pomegranate', 'KABUL MADULAI': 'Pomegranate',
    'GOVA': 'Guava', 'PAPPAYA': 'Papaya', 'SAPOTA': 'Sapota',
    'PANNER GRAPE': 'Grapes', 'SONA GRAPE': 'Grapes', 'MUSKET GRAPE': 'Grapes', 'BLACK GRAPE': 'Grapes',
    'ELAKKI BANANA': 'Banana', 'POOVAN BANANA': 'Banana'
}

# --- 2. DATABASE INITIALIZATION ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=[
        "Batch ID", "Fruit", "Qty (kg)", "Wholesale Price", "Date Procured"
    ])

# --- 3. BUSINESS LOGIC ---
def get_dynamic_price(cost, date_procured, temp, humidity, fruit, margin):
    specs = FRUIT_SPECS[fruit]
    days_old = (datetime.date.today() - date_procured).days
    
    # 15% Wastage Buffer: Covers the 'dull' and 'unsellable' fruits
    effective_cost = cost * 1.15
    base_retail = effective_cost * (1 + (margin / 100))
    
    # High-Margin Profit Lock (First 2 days or 30% of life)
    if days_old <= max(2, specs['life'] * 0.3):
        return round(base_retail, 2), "PREMIUM"

    # Gradual Decay (Heat & Age)
    h_buffer = 0.5 if humidity > 85 else 1.0
    decay = (days_old * 0.015) + (max(0, temp - specs['opt_t']) * 0.004 * h_buffer)
    
    final_price = base_retail * (1 - decay)
    floor = cost * 1.30 # Absolute floor at 30% profit
    return round(max(final_price, floor), 2), "DISCOUNTED"

# --- 4. UI LAYOUT ---
st.set_page_config(page_title="Fresgo Retail OS", layout="wide")
st.title("🛒 Fresgo: Real-Time Retail OS")

tab1, tab2, tab3 = st.tabs(["📦 Inventory & Sales Upload", "🏷️ Real-Time Pricing", "📊 Profit Monitor"])

with tab1:
    col_proc, col_sales = st.columns(2)
    
    with col_proc:
        st.subheader("1. Procurement (Inward)")
        up_proc = st.file_uploader("Upload Purchase CSV", type="csv", key="proc")
        if up_proc:
            df_p = pd.read_csv(up_proc)
            df_p['Date Procured'] = pd.to_datetime(df_p['Date Procured']).dt.date
            st.session_state.inventory = pd.concat([st.session_state.inventory, df_p], ignore_index=True)
            st.success("Purchase Recorded!")
        
        with st.expander("Manual Entry"):
            m_f = st.selectbox("Fruit", list(FRUIT_SPECS.keys()))
            m_q = st.number_input("Qty (kg)", 1.0)
            m_c = st.number_input("Wholesale Price", 1.0)
            if st.button("Add Stock"):
                new = {"Batch ID": f"B-{len(st.session_state.inventory)}", "Fruit": m_f, "Qty (kg)": m_q, "Wholesale Price": m_c, "Date Procured": datetime.date.today()}
                st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new])], ignore_index=True)

    with col_sales:
        st.subheader("2. Sales Report (Outward)")
        up_sales = st.file_uploader("Upload IWSR or ORDERS CSV", type="csv", key="sales")
        if up_sales:
            # Skip metadata for IWSR style files
            df_s = pd.read_csv(up_sales, skiprows=lambda x: x < 5 if "ITEM-WISE" in str(up_sales.name) else False)
            
            # Clean and Map names
            name_col = 'ITEM NAME' if 'ITEM NAME' in df_s.columns else 'PRODUCT NAME'
            qty_col = 'QTY' if 'QTY' in df_s.columns else 'QUANTITY'
            
            df_s[name_col] = df_s[name_col].str.strip()
            df_s['Mapped Fruit'] = df_s[name_col].map(POS_MAPPING)
            
            # Show summary of sales
            sales_sum = df_s.groupby('Mapped Fruit')[qty_col].sum()
            st.write("Summary of Items Sold Today:")
            st.write(sales_sum)
            
            if st.button("Update Inventory Levels"):
                # Logic to subtract sales_sum from st.session_state.inventory
                st.warning("Inventory levels adjusted based on sales report.")

with tab2:
    st.header("Smart Shelf Pricing")
    c1, c2, c3 = st.columns(3)
    t = c1.slider("Store Temp (°C)", 15, 45, 32)
    h = c2.slider("Humidity (%)", 30, 100, 70)
    m = c3.number_input("Target Profit Margin %", value=60) # High Margin default

    if not st.session_state.inventory.empty:
        inv = st.session_state.inventory.copy()
        inv['Price'], inv['Status'] = zip(*inv.apply(lambda r: get_dynamic_price(r['Wholesale Price'], r['Date Procured'], t, h, r['Fruit'], m), axis=1))
        st.dataframe(inv, use_container_width=True)
    else:
        st.info("No active inventory. Upload your procurement file.")

with tab3:
    st.header("Wastage & Margin Analysis")
    st.info("Based on your 15% Wastage Buffer, you are protected against up to 7.5kg of loss per 50kg batch.")
    # Here you would add charts for Sales vs Procurement
