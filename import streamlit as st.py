import streamlit as st
import pandas as pd
import datetime

# --- 1. FULL DATA FROM YOUR CHART ---
FRUIT_SPECS = {
    "Apple": {"life": 10, "opt_t": 1, "opt_h": 92},
    "Mango": {"life": 7, "opt_t": 12, "opt_h": 87},
    "Banana": {"life": 5, "opt_t": 14, "opt_h": 87},
    "Guava": {"life": 3, "opt_t": 9, "opt_h": 92},
    "Orange": {"life": 14, "opt_t": 6, "opt_h": 87},
    "Sapota": {"life": 3, "opt_t": 14, "opt_h": 87},
    "Pineapple": {"life": 6, "opt_t": 9, "opt_h": 87},
    "Pomegranate": {"life": 15, "opt_t": 6, "opt_h": 92},
    "Grapes": {"life": 5, "opt_t": 1, "opt_h": 92},
    "Papaya": {"life": 4, "opt_t": 12, "opt_h": 87}
}

if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=[
        "Batch ID", "Fruit", "Qty (kg)", "Wholesale Price", "Date Procured"
    ])

# --- 2. HIGH-MARGIN PRICING LOGIC ---
def get_business_price(cost, date_procured, temp, humidity, fruit, target_margin):
    specs = FRUIT_SPECS[fruit]
    days_old = (datetime.date.today() - date_procured).days
    
    # Wastage Buffer: We add 10% to the cost to cover the 'dull/unsellable' fruits
    effective_cost = cost * 1.10
    
    # Base Retail Price based on your high-margin requirement
    base_retail = effective_cost * (1 + (target_margin / 100))
    
    # 3-Day Profit Lock: No discounts for the first 3 days or 30% of life
    lock_period = max(3, specs['life'] * 0.3)
    if days_old <= lock_period:
        return round(base_retail, 2), "PREMIUM"

    # Gradual Decay (Very slow to protect margin)
    h_buffer = 0.5 if humidity > 85 else 1.0
    decay = (days_old * 0.01) + (max(0, temp - specs['opt_t']) * 0.005 * h_buffer)
    
    final_price = base_retail * (1 - decay)
    
    # Floor: Never sell below Wholesale + 25% profit to stay competitive but profitable
    floor = cost * 1.25
    return round(max(final_price, floor), 2), "DISCOUNTED"

# --- 3. THE APP INTERFACE ---
st.set_page_config(page_title="Fresgo Retail Manager", layout="wide")
st.title("🚀 Fresgo: High-Margin Retail OS")

tab1, tab2, tab3 = st.tabs(["📥 Inventory Upload", "📊 Daily Pricing", "💡 Strategy"])

with tab1:
    st.header("Stock Entry")
    # CSV Uploader
    uploaded_file = st.file_uploader("Upload Procurement CSV (Columns: Batch ID, Fruit, Qty (kg), Wholesale Price, Date Procured)", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        # Convert text dates to real dates
        df['Date Procured'] = pd.to_datetime(df['Date Procured']).dt.date
        st.session_state.inventory = pd.concat([st.session_state.inventory, df], ignore_index=True)
        st.success("File Uploaded!")

    # Manual Entry (Optional)
    with st.expander("Or Add Manually"):
        col1, col2, col3, col4 = st.columns(4)
        m_fruit = col1.selectbox("Fruit", list(FRUIT_SPECS.keys()))
        m_qty = col2.number_input("Qty", 1.0)
        m_cost = col3.number_input("Wholesale", 1.0)
        m_date = col4.date_input("Received Date", datetime.date.today())
        if st.button("Add Item"):
            new_row = {"Batch ID": f"MAN-{len(st.session_state.inventory)}", "Fruit": m_fruit, "Qty (kg)": m_qty, "Wholesale Price": m_cost, "Date Procured": m_date}
            st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_row])], ignore_index=True)

with tab2:
    st.header("Today's Store Prices")
    c1, c2, c3 = st.columns(3)
    current_t = c1.slider("Store Temp (°C)", 15, 45, 30)
    current_h = c2.slider("Humidity (%)", 30, 100, 75)
    target_m = c3.number_input("Target Margin %", value=50) # Set high by default

    if not st.session_state.inventory.empty:
        inv_display = st.session_state.inventory.copy()
        
        # Calculate dynamic values
        prices = []
        statuses = []
        for index, row in inv_display.iterrows():
            p, s = get_business_price(row['Wholesale Price'], row['Date Procured'], current_t, current_h, row['Fruit'], target_m)
            prices.append(p)
            statuses.append(s)
        
        inv_display['Recommended Price'] = prices
        inv_display['Status'] = statuses
        st.table(inv_display)
    else:
        st.info("Upload or Add inventory to see prices.")

with tab3:
    st.header("Big-Box Tactics")
    st.subheader("1. Bundle Strategy")
    st.write("To move 'dull' stock, offer a 'Family Pack': 3kg for the price of 2.5kg.")
    st.subheader("2. Competitor Shield")
    st.write("If Reliance/Big-Basket drops prices, use your 'Loss Leader'—price your Bananas at cost to bring people in for high-margin Juices.")
