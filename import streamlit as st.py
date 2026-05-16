pip install streamlit pandas
import streamlit as st
import pandas as pd

# --- DATA FROM YOUR CHART ---
FRUIT_DATA = {
    "Apple": {"opt_temp": 1, "opt_humidity": 92, "ambient_life": 10},
    "Mango": {"opt_temp": 12, "opt_humidity": 87, "ambient_life": 6},
    "Banana": {"opt_temp": 14, "opt_humidity": 87, "ambient_life": 4},
    "Guava": {"opt_temp": 9, "opt_humidity": 92, "ambient_life": 3},
    "Orange": {"opt_temp": 6, "opt_humidity": 87, "ambient_life": 10},
    "Sapota": {"opt_temp": 14, "opt_humidity": 87, "ambient_life": 3},
    "Pineapple": {"opt_temp": 9, "opt_humidity": 87, "ambient_life": 6},
    "Pomegranate": {"opt_temp": 6, "opt_humidity": 92, "ambient_life": 12},
}

def calculate_dynamic_price(wholesale, margin, fruit_name, days, temp, humidity):
    data = FRUIT_DATA[fruit_name]
    base_retail = wholesale * (1 + (margin / 100))
    
    # 1. PROFIT LOCK: Protect margin for the first 40% of ambient life
    freshness_window = data["ambient_life"] * 0.4
    
    if days <= freshness_window:
        return round(base_retail, 2), "PREMIUM QUALITY", (base_retail - wholesale)
    
    # 2. CALC PENALTIES (Only after Freshness Window)
    # Humidity Buffer: High humidity slows down the heat damage
    humid_buffer = 0.5 if humidity > 80 else 1.0
    
    # Tiny temp penalty (0.5% per degree above optimal)
    temp_diff = max(0, temp - data["opt_temp"])
    temp_penalty = (temp_diff * 0.005) * humid_buffer
    
    # Age penalty (15% max impact over total life)
    age_penalty = (days / data["ambient_life"]) * 0.15
    
    final_price = base_retail * (1 - temp_penalty - age_penalty)
    
    # 3. FLOOR LOCK: Minimum 15% profit guaranteed
    floor_price = wholesale * 1.15
    
    if final_price < floor_price:
        return round(floor_price, 2), "MOVE TO PROCESSING", (floor_price - wholesale)
    
    return round(final_price, 2), "PROMOTIONAL PRICE", (final_price - wholesale)

# --- STREAMLIT UI ---
st.set_page_config(page_title="Fresgo Dynamic Pricing", layout="centered")

st.title("🍓 Fresgo Smart Pricing Engine")
st.markdown("---")

# Layout Columns
col1, col2 = st.columns(2)

with col1:
    st.header("Inventory Data")
    fruit_choice = st.selectbox("Select Fruit", list(FRUIT_DATA.keys()))
    wholesale_input = st.number_input("Wholesale Price (₹/kg)", min_value=10.0, value=80.0, step=1.0)
    margin_input = st.number_input("Target Margin (%)", min_value=15.0, value=40.0, step=5.0)
    days_input = st.slider("Days on Shelf", 0, 15, 1)

with col2:
    st.header("Store Environment")
    temp_input = st.slider("Store Temp (°C)", 15, 45, 30)
    humid_input = st.slider("Relative Humidity (%)", 30, 100, 75)

# Calculation
final_p, status, profit = calculate_dynamic_price(
    wholesale_input, margin_input, fruit_choice, days_input, temp_input, humid_input
)

# Output Display
st.markdown("---")
res1, res2, res3 = st.columns(3)

res1.metric("Selling Price", f"₹{final_p}")
res2.metric("Profit per Kg", f"₹{round(profit, 2)}")

if status == "PREMIUM QUALITY":
    res3.success(status)
elif status == "PROMOTIONAL PRICE":
    res3.warning(status)
else:
    res3.error(status)
    st.error(f"⚠️ ALERT: Transfer {fruit_choice} to the Dark Store for Juices/Bakery immediately.")

st.info(f"**Retail Logic:** For {fruit_choice}, your profit is locked for the first {int(FRUIT_DATA[fruit_choice]['ambient_life']*0.4)} days.")
