import streamlit as st
import pandas as pd
import datetime

# --- 1. SETTINGS & MASTER DATA ---
# Using your chart data as the baseline
FRUIT_SPECS = {
    "Mango": {"life": 7, "opt_t": 12, "opt_h": 87},
    "Banana": {"life": 5, "opt_t": 14, "opt_h": 87},
    "Orange": {"life": 14, "opt_t": 6, "opt_h": 87},
    "Guava": {"life": 3, "opt_t": 9, "opt_h": 92},
    "Pomegranate": {"life": 15, "opt_t": 6, "opt_h": 92}
}

# Initialize the "Database" in memory
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=[
        "Batch ID", "Fruit", "Qty (kg)", "Wholesale Price", "Date Procured", "Status"
    ])

# --- 2. THE PRICING ENGINE (Logic from previous versions) ---
def get_dynamic_price(cost, days, temp, humidity, fruit):
    specs = FRUIT_SPECS[fruit]
    base_retail = cost * 1.4  # Default 40% margin
    
    # Profit Lock: No discount for the first 30% of its life
    if days <= (specs['life'] * 0.3):
        return round(base_retail, 2)

    # Gradual Decay Logic
    # Humidity buffer: High humidity slows the decay
    h_factor = 0.5 if humidity > 85 else 1.0
    temp_penalty = max(0, (temp - specs['opt_t']) * 0.005) * h_factor
    age_penalty = (days / specs['life']) * 0.10
    
    final_price = base_retail * (1 - temp_penalty - age_penalty)
    return round(max(final_price, cost * 1.15), 2) # Never below 15% profit

# --- 3. THE UI LAYOUT ---
st.set_page_config(page_title="Fresgo Retail OS", layout="wide")
st.title("🍎 Fresgo Integrated Retail System")

tab_procure, tab_pricing, tab_tactics = st.tabs(["Inventory Manager", "Smart Pricing", "Big-Box Tactics"])

# --- TAB 1: PROCUREMENT & INVENTORY ---
with tab_procure:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("New Procurement")
        f_type = st.selectbox("Select Fruit", list(FRUIT_SPECS.keys()))
        f_qty = st.number_input("Quantity (kg)", min_value=1.0)
        f_cost = st.number_input("Wholesale Cost (₹/kg)", min_value=1.0)
        if st.button("Add to Inventory"):
            new_id = f"FRES-{len(st.session_state.inventory)+101}"
            new_row = {
                "Batch ID": new_id, "Fruit": f_type, "Qty (kg)": f_qty, 
                "Wholesale Price": f_cost, "Date Procured": datetime.date.today(),
                "Status": "Active"
            }
            st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_row])], ignore_index=True)
            st.success(f"Batch {new_id} Added!")

    with col2:
        st.subheader("Live Stock Ledger")
        st.dataframe(st.session_state.inventory, use_container_width=True)
        if st.button("Clear Sold Out Items"):
            # Logic to remove items with 0 qty
            pass

# --- TAB 2: SMART PRICING (Visual Tools) ---
with tab_pricing:
    st.header("Gradual Price Adjustment")
    # Simulation Sliders
    s_temp = st.slider("Store Temp (°C)", 15, 45, 30)
    s_humid = st.slider("Store Humidity (%)", 30, 100, 70)
    
    if not st.session_state.inventory.empty:
        # Calculate current prices for all active inventory
        display_inv = st.session_state.inventory.copy()
        
        def apply_pricing(row):
            age = (datetime.date.today() - row['Date Procured']).days
            return get_dynamic_price(row['Wholesale Price'], age, s_temp, s_humid, row['Fruit'])
        
        display_inv['Recommended Price'] = display_inv.apply(apply_pricing, axis=1)
        st.table(display_inv[['Batch ID', 'Fruit', 'Qty (kg)', 'Wholesale Price', 'Recommended Price']])
    else:
        st.warning("Please add inventory first to see dynamic pricing.")

# --- TAB 3: BIG-BOX TACTICS ---
with tab_tactics:
    st.header("Corporate Pricing Strategies")
    target_p = st.number_input("Input Base Price for Tactic:", value=100.0)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Psychological Pricing")
        st.write(f"Standard: ₹{target_p}")
        st.metric("Charm Price", f"₹{int(target_p)-0.01 if target_p > 1 else 0.99}")
        st.caption("Ending in .99 increases sales volume by up to 25%.")
    
    with c2:
        st.subheader("Bulk/Bundle Logic")
        st.write(f"1kg: ₹{target_p}")
        st.metric("3kg Pack Price", f"₹{round(target_p * 2.7, 0)}")
        st.caption("A 10% discount on 3kg encourages high-volume clearance.")
