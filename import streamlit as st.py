import streamlit as st
import datetime
import pandas as pd

# --- CONFIGURATION & CONSTANTS ---
BASE_PRICE = 100.0  # Base price per kg
OPTIMAL_TEMP = 20.0 # Celsius
OPTIMAL_HUMIDITY = 60.0 # Percentage
DECAY_SENSITIVITY = 0.05 # How fast price drops per degree/percent deviation

# Hardcoded Auspicious/Festival Days for simulation
# In a full system, you'd pull this from a Calendar API
AUSPICIOUS_DAYS = {
    datetime.date(2026, 5, 15): "Local Festival",
    datetime.date(2026, 5, 25): "Muhurtham Date",
}

def calculate_dynamic_price(base_price, days_passed, temp, humidity, next_event_date):
    # 1. Calculate Shelf Life Penalty (Decay)
    # Higher temp/humidity beyond optimal reduces value
    temp_penalty = max(0, (temp - OPTIMAL_TEMP) * DECAY_SENSITIVITY)
    humid_penalty = max(0, (humidity - OPTIMAL_HUMIDITY) * (DECAY_SENSITIVITY / 2))
    total_decay = (days_passed * 2) + temp_penalty + humid_penalty
    
    current_value = base_price - total_decay
    
    # 2. Calculate Auspicious Premium (Demand)
    premium = 0
    if next_event_date:
        days_until_event = (next_event_date - datetime.date.today()).days
        if 0 <= days_until_event <= 3:
            # 20% hike if the event is within 3 days
            premium = base_price * 0.20
            
    final_price = max(current_value + premium, base_price * 0.3) # Floor price at 30%
    return round(final_price, 2)

# --- STREAMLIT DASHBOARD UI ---
st.title("🍎 Smart Retail Dynamic Pricing")
st.subheader("Inventory & Environmental Monitoring")

# Sidebar - Inputs
st.sidebar.header("Input Parameters")
fruit_type = st.sidebar.selectbox("Select Fruit", ["Mango", "Banana", "Orange"])
date_received = st.sidebar.date_input("Date Received", datetime.date.today() - datetime.timedelta(days=2))
temp = st.sidebar.slider("Current Store Temp (°C)", 10, 45, 28)
humidity = st.sidebar.slider("Current Humidity (%)", 30, 95, 75)

# Logic Processing
days_on_shelf = (datetime.date.today() - date_received).days
next_event = min([d for d in AUSPICIOUS_DAYS.keys() if d >= datetime.date.today()], default=None)

current_price = calculate_dynamic_price(BASE_PRICE, days_on_shelf, temp, humidity, next_event)

# --- DISPLAY RESULTS ---
col1, col2, col3 = st.columns(3)
col1.metric("Current Price", f"₹{current_price}")
col2.metric("Days on Shelf", f"{days_on_shelf} Days")
col3.metric("Event Premium", "Active" if (next_event and (next_event - datetime.date.today()).days <= 3) else "None")

if next_event:
    st.info(f"Next High-Demand Event: **{AUSPICIOUS_DAYS[next_event]}** on {next_event}")

# Strategy Recommendation
if current_price < (BASE_PRICE * 0.5):
    st.warning("⚠️ CRITICAL: Low Shelf Life. Redirecting to Processing Unit for Marmalade/Juice.")
else:
    st.success("✅ Quality high. Maintain premium shelf placement.")