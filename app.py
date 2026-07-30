import os
import re
import time
import requests
from bs4 import BeautifulSoup
import streamlit as st
from supabase import create_client, Client

# ==============================================================================
# 1. SETUP & CONFIGURATION
# ==============================================================================
st.set_page_config(page_title="Carrier Harvester", layout="wide")

# Custom CSS / Glassmorphism Theme
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    .stMetric {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        backdrop-filter: blur(10px);
    }
    </style>
""", unsafe_allow_html=True)

# Supabase Credentials (Ensure these are set in st.secrets or environment)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase() -> Client:
    if SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

supabase = init_supabase()

# ==============================================================================
# 2. FMCSA SAFER SCRAPING ENGINE (Replaces CarrierChk API)
# ==============================================================================
def scrape_safer_by_mc(mc_number: str) -> dict:
    """
    Directly scrapes the FMCSA SAFER website for details given an MC/MX number.
    Returns a standardized dictionary.
    """
    url = "https://safer.fmcsa.dot.gov/query.asp"
    payload = {
        "searchtype": "ANY",
        "query_type": "queryCarrierDetail",
        "query_param": "MC_MX",
        "query_string": mc_number
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}"}

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Check if record exists
        if "Record Inactive" in response.text or "No records matching" in response.text:
            return {"mc_number": mc_number, "status": "NOT FOUND / INACTIVE"}

        # Extract Key Fields from HTML tables
        data = {
            "mc_number": mc_number,
            "legal_name": None,
            "dba_name": None,
            "entity_type": None,
            "operating_status": None,
            "emails": [],
            "raw_text": soup.get_text()
        }

        # Parse table cells for core attributes
        for row in soup.find_all("tr"):
            text = row.get_text()
            if "Legal Name:" in text:
                cols = row.find_all("td")
                if len(cols) > 1:
                    data["legal_name"] = cols[1].get_text(strip=True)
            elif "DBA Name:" in text:
                cols = row.find_all("td")
                if len(cols) > 1:
                    data["dba_name"] = cols[1].get_text(strip=True)
            elif "Entity Type:" in text:
                cols = row.find_all("td")
                if len(cols) > 1:
                    data["entity_type"] = cols[1].get_text(strip=True)
            elif "Operating Status:" in text:
                cols = row.find_all("td")
                if len(cols) > 1:
                    data["operating_status"] = cols[1].get_text(strip=True)

        # Regex email extraction from page content
        data["emails"] = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', response.text)))
        
        # Determine classification
        entity = (data["entity_type"] or "").upper()
        if "CARRIER" in entity:
            data["classification"] = "CARRIER"
        elif "BROKER" in entity or any(k in response.text.upper() for k in ["3PL", "FREIGHT FORWARDER"]):
            data["classification"] = "BROKER"
        else:
            data["classification"] = "UNKNOWN"

        return data

    except Exception as e:
        return {"error": str(e)}

# ==============================================================================
# 3. STREAMLIT SESSION & STATE MANAGEMENT
# ==============================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "harvesting" not in st.session_state:
    st.session_state.harvesting = False
if "harvested_records" not in st.session_state:
    st.session_state.harvested_records = []
if "current_mc" not in st.session_state:
    st.session_state.current_mc = 100000

# Simple Login Logic
if not st.session_state.authenticated:
    st.title("🔐 Authentication Required")
    pwd = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        # Replace with your actual auth check or Supabase logic
        st.session_state.authenticated = True
        st.rerun()
    st.stop()

# ==============================================================================
# 4. CONTROL PANEL & HARVESTING ENGINE
# ==============================================================================
st.title("🚛 FMCSA SAFER Direct Lead Harvester")

sidebar = st.sidebar
sidebar.header("Harvesting Controls")
start_mc = sidebar.number_input("Starting MC Number", value=st.session_state.current_mc, step=1)
delay_ms = sidebar.slider("Delay (ms)", min_value=100, max_value=2000, value=500, step=100)

col_btn1, col_btn2 = sidebar.columns(2)
if col_btn1.button("Start Harvester"):
    st.session_state.harvesting = True
    st.session_state.current_mc = start_mc

if col_btn2.button("Stop Harvester"):
    st.session_state.harvesting = False

# Continuous Loop Execution
if st.session_state.harvesting:
    st.markdown("### 🔄 Live Harvesting Active...")
    
    current = str(st.session_state.current_mc)
    result = scrape_safer_by_mc(current)
    
    if "error" not in result:
        st.session_state.harvested_records.append(result)
        # Optional: Persist to Supabase if client exists
        if supabase:
            try:
                supabase.table("harvested_leads").insert(result).execute()
            except Exception:
                pass

    # Increment MC Number and delay
    st.session_state.current_mc += 1
    time.sleep(delay_ms / 1000.0)
    st.rerun()

# ==============================================================================
# 5. DATA DASHBOARD & DISPLAY TABS
# ==============================================================================
st.subheader("Data Analytics")
m1, m2, m3 = st.columns(3)
m1.metric("Total Extracted", len(st.session_state.harvested_records))
m2.metric("Active Carriers", len([r for r in st.session_state.harvested_records if r.get("classification") == "CARRIER"]))
m3.metric("Emails Found", sum(len(r.get("emails", [])) for r in st.session_state.harvested_records))

tab1, tab2, tab3 = st.tabs(["📋 Master Log", "✅ Verified Leads", "📧 Raw Email List"])

with tab1:
    st.dataframe(st.session_state.harvested_records)

with tab2:
    verified = [r for r in st.session_state.harvested_records if r.get("operating_status") == "AUTHORIZED"]
    st.dataframe(verified)

with tab3:
    all_emails = []
    for r in st.session_state.harvested_records:
        all_emails.extend(r.get("emails", []))
    st.write(list(set(all_emails)))
