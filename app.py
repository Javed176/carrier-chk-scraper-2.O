import streamlit as st
import requests
import time
import json
import csv
import io
import re
import uuid
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

# ─── PAGE CONFIG ───
st.set_page_config(
    page_title="CarrierChk Pro",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── SECRETS ───
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
CARRIER_TOKEN = st.secrets.get("CARRIER_TOKEN", "")
CARRIER_API_URL = st.secrets.get("CARRIER_API_URL", "https://carrierchk.com/api/carrier")

# ─── SUPABASE CLIENT ───
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None

# ─── SESSION STATE ───
for key in ["authenticated", "current_user", "is_admin", "session_token",
            "last_session_check", "harvesting", "current_mc", "harvested",
            "harvest_log", "page"]:
    if key not in st.session_state:
        if key in ["authenticated", "is_admin", "harvesting"]:
            st.session_state[key] = False
        elif key in ["current_user", "session_token", "page"]:
            st.session_state[key] = ""
        elif key == "current_mc":
            st.session_state[key] = 1800000
        elif key in ["harvested", "harvest_log"]:
            st.session_state[key] = []
        else:
            st.session_state[key] = time.time()

# ─── CUSTOM CSS ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    color: #e2e8f0;
}
.glass-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.glass-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
    border-color: rgba(255, 255, 255, 0.15);
}
.app-title {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(90deg, #00d4ff, #7b2cbf, #ff006e);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 40px rgba(0, 212, 255, 0.3);
    letter-spacing: -1px;
    margin-bottom: 4px;
}
.badge-active {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    background: rgba(0, 255, 136, 0.1);
    border: 1px solid rgba(0, 255, 136, 0.4);
    color: #00ff88;
    font-weight: 700;
    font-size: 0.85rem;
    box-shadow: 0 0 12px rgba(0, 255, 136, 0.2);
}
.badge-inactive {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    background: rgba(255, 71, 87, 0.1);
    border: 1px solid rgba(255, 71, 87, 0.4);
    color: #ff4757;
    font-weight: 700;
    font-size: 0.85rem;
    box-shadow: 0 0 12px rgba(255, 71, 87, 0.2);
}
.badge-broker {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    background: rgba(255, 165, 2, 0.1);
    border: 1px solid rgba(255, 165, 2, 0.4);
    color: #ffa502;
    font-weight: 700;
    font-size: 0.85rem;
    box-shadow: 0 0 12px rgba(255, 165, 2, 0.2);
}
.stButton>button {
    background: linear-gradient(135deg, #00d4ff, #7b2cbf) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    box-shadow: 0 4px 20px rgba(0, 212, 255, 0.3) !important;
    transition: all 0.3s ease !important;
}
.stButton>button:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 8px 30px rgba(0, 212, 255, 0.5) !important;
}
.stTextInput>div>div>input, .stNumberInput>div>div>input {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    padding: 14px 18px !important;
    font-size: 1rem !important;
}
.stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.15) !important;
}
[data-testid="stSidebar"] {
    background: rgba(15, 12, 41, 0.8) !important;
    backdrop-filter: blur(20px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
}
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255, 255, 255, 0.03) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #94a3b8 !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(0, 212, 255, 0.15) !important;
    color: #00d4ff !important;
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.25); }
.metric-card {
    background: rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.06);
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: #00d4ff;
}
.metric-label {
    font-size: 0.8rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 20px rgba(0, 212, 255, 0.2); }
    50% { box-shadow: 0 0 40px rgba(0, 212, 255, 0.5); }
}
.harvest-active {
    animation: pulse-glow 2s ease-in-out infinite;
    border: 1px solid rgba(0, 212, 255, 0.4);
    border-radius: 16px;
    padding: 20px;
    background: rgba(0, 212, 255, 0.05);
}
.stDownloadButton>button {
    background: linear-gradient(135deg, #7b2cbf, #ff006e) !important;
    box-shadow: 0 4px 20px rgba(123, 44, 191, 0.3) !important;
}
/* Running person animation */
@keyframes run-slide {
    0% { transform: translateX(0); }
    50% { transform: translateX(30px); }
    100% { transform: translateX(0); }
}
@keyframes run-bounce {
    0%, 100% { transform: translateY(0); }
    25% { transform: translateY(-8px); }
    50% { transform: translateY(0); }
    75% { transform: translateY(-4px); }
}
.runner-box {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    background: rgba(0, 212, 255, 0.05);
    border-radius: 12px;
    border: 1px solid rgba(0, 212, 255, 0.2);
}
.runner-emoji {
    font-size: 2rem;
    animation: run-slide 1.2s ease-in-out infinite, run-bounce 0.6s ease-in-out infinite;
    filter: drop-shadow(0 0 8px rgba(0, 212, 255, 0.6));
}
.runner-text {
    color: #00d4ff;
    font-weight: 700;
    font-size: 1.1rem;
}
</style>
""", unsafe_allow_html=True)

# ─── AUTH FUNCTIONS ───
def verify_active_session():
    if st.session_state.authenticated and st.session_state.current_user:
        now = time.time()
        if now - st.session_state.last_session_check < 30.0:
            return True
        st.session_state.last_session_check = now
        try:
            if supabase:
                res = supabase.table("users").select("active_session_id").eq("email", st.session_state.current_user).execute()
                if res.data and res.data[0].get("active_session_id") != st.session_state.session_token:
                    return False
        except Exception:
            pass
    return True

def login_user(email, password):
    if not supabase:
        return False, "Database connection failed"
    try:
        res = supabase.table("users").select("*").eq("email", email).execute()
        if not res.data:
            return False, "Invalid credentials"
        user = res.data[0]
        if user.get("password") != password:
            return False, "Invalid credentials"
        new_token = str(uuid.uuid4())
        supabase.table("users").update({
            "active_session_id": new_token
        }).eq("email", email).execute()
        st.session_state.authenticated = True
        st.session_state.current_user = email
        st.session_state.is_admin = user.get("is_admin", False)
        st.session_state.session_token = new_token
        st.session_state.last_session_check = time.time()
        return True, "Success"
    except Exception as e:
        return False, f"Login error: {e}"

def logout_user():
    if supabase and st.session_state.current_user:
        try:
            supabase.table("users").update({"active_session_id": None}).eq("email", st.session_state.current_user).execute()
        except Exception:
            pass
    for key in ["authenticated", "current_user", "is_admin", "session_token", "harvesting"]:
        st.session_state[key] = False if key != "session_token" else ""
    st.rerun()

# ─── API FUNCTIONS ───
http_session = requests.Session()

def get_carrier_info(query, token, api_url):
    if not query or not token:
        return None
    q = str(query).strip()
    search_type = "mc" if q.isdigit() and len(q) <= 8 else "dot" if q.isdigit() else "email"
    params = {"type": search_type, "value": q, "token": token}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://carrierchk.com/"
    }
    try:
        r = http_session.get(api_url, params=params, headers=headers, timeout=12.0)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            time.sleep(2)
            r2 = http_session.get(api_url, params=params, headers=headers, timeout=12.0)
            if r2.status_code == 200:
                return r2.json()
        return {"_error": f"HTTP {r.status_code}", "_status": r.status_code}
    except requests.exceptions.Timeout:
        return {"_error": "Request timed out", "_status": 0}
    except Exception as e:
        return {"_error": str(e), "_status": 0}

def find_val_by_keys(d, keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d:
            return d[k]
    for v in d.values():
        if isinstance(v, dict):
            found = find_val_by_keys(v, keys)
            if found is not None:
                return found
    return None

def flatten_dict_values(d):
    vals = []
    if isinstance(d, dict):
        for v in d.values():
            if isinstance(v, dict):
                vals.extend(flatten_dict_values(v))
            elif isinstance(v, list):
                for item in v:
                    vals.extend(flatten_dict_values(item) if isinstance(item, dict) else [str(item)])
            else:
                vals.append(str(v))
    return vals

# ─── PARSE CARRIER DATA ───
# ONLY CHANGE: Fixed keyword lists to use exact matching instead of substring
def parse_carrier_data(c):
    if not c or not isinstance(c, dict):
        return None
    if "_error" in c:
        return None

    data = c.get("carrier") or c.get("data") or c

    # Basic info
    name = find_val_by_keys(data, ["legal_name", "name", "company_name", "carrier_name", "dba_name", "doing_business_as"]) or "Unknown"
    dot = find_val_by_keys(data, ["usdot_number", "dot_number", "usdot", "dot"]) or "N/A"
    mc = find_val_by_keys(data, ["mc_number", "mc", "docket_number", "mc_docket"]) or "N/A"
    phone = find_val_by_keys(data, ["phone", "business_phone", "contact_phone", "telephone"]) or "N/A"
    email = find_val_by_keys(data, ["email", "business_email", "contact_email", "email_address"]) or "N/A"
    city = find_val_by_keys(data, ["city", "physical_city", "business_city"]) or ""
    state = find_val_by_keys(data, ["state", "physical_state", "business_state", "state_code"]) or ""
    location = f"{city}, {state}".strip(", ") or "N/A"

    # Entity type
    entity_type = find_val_by_keys(data, ["entity_type", "carrier_type", "operation_type", "company_type", "business_type"]) or ""
    entity_val = str(entity_type).upper().strip()

    # Authority statuses
    broker_auth = find_val_by_keys(data, ["broker_authority_status", "brokerAuthStatus", "broker_status", "brokerAuthority", "broker_auth"]) or ""
    common_auth = find_val_by_keys(data, ["common_authority_status", "commonAuthStatus", "common_status", "commonAuthority"]) or ""
    contract_auth = find_val_by_keys(data, ["contract_authority_status", "contractAuthStatus", "contract_status", "contractAuthority"]) or ""

    broker_auth_str = str(broker_auth).upper().strip()
    common_auth_str = str(common_auth).upper().strip()
    contract_auth_str = str(contract_auth).upper().strip()

    is_broker_auth = broker_auth_str in ["A", "ACTIVE", "Y", "YES", "TRUE", "1", "AUTHORIZED"]
    has_common_auth = common_auth_str in ["A", "ACTIVE", "Y", "YES", "TRUE", "1", "AUTHORIZED"]
    has_contract_auth = contract_auth_str in ["A", "ACTIVE", "Y", "YES", "TRUE", "1", "AUTHORIZED"]

    # BROKER DETECTION - Removed full JSON text scan "BROKER" in c_text
    is_broker = (
        is_broker_auth or
        "BROKER" in entity_val or
        any(b in name for b in ["BROKERAGE", "BROKER", "LOGISTICS", "DISPATCH", "TQL", "TOTAL QUALITY LOGISTICS", "CH ROBINSON", "LANDSTAR", "XPO", "SCHNEIDER", "KNIGHT", "HUB GROUP", "MODE TRANSPORTATION", "AMAZON", "UBER", "LYFT", "DAT", "TRUCKSTOP", "LOADBOARD", "FREIGHTOS", "CONVOY", "NEXT", "TRANFIX", "EKO"])
    )

    entity_label = "BROKER" if is_broker else "CARRIER"

    # STATUS DETECTION - FIXED: Removed single-letter and partial keywords
    status_raw = find_val_by_keys(data, [
        "operating_status", "status", "authority_status", "carrier_status",
        "operation_status", "active_status", "current_status", "record_status"
    ]) or ""
    status_str_raw = str(status_raw).upper().strip()

    is_active = False

    # Phase 1: Exact match for explicit status values (NO single letters!)
    if status_str_raw in ["ACTIVE", "AUTHORIZED", "AUTHORISED", "OPERATING", "OPERATIONAL"]:
        is_active = True
    elif status_str_raw in ["INACTIVE", "NOT AUTHORIZED", "NOT AUTHORISED", "REVOKED", "SUSPENDED", "NONE", "PENDING REVOCATION"]:
        is_active = False
    elif status_str_raw in ["A", "Y", "YES", "TRUE", "1"]:
        is_active = True
    elif status_str_raw in ["I", "N", "NO", "FALSE", "0"]:
        is_active = False

    # Phase 2: Check authority statuses
    if is_active is False:
        if has_common_auth or has_contract_auth or is_broker_auth:
            is_active = True

    # Phase 3: Conservative payload scan (only multi-word phrases, no single letters)
    c_text = str(c).upper()
    if "INACTIVE" in c_text or "NOT AUTHORIZED" in c_text or "REVOKED" in c_text or "SUSPENDED" in c_text:
        is_active = False
    elif "ACTIVE" in c_text and "INACTIVE" not in c_text:
        is_active = True

    status_str = "ACTIVE" if is_active else "INACTIVE"

    # Insurance
    bipd = find_val_by_keys(data, ["bipd_required", "bipd_amount", "bi_pd_amount"]) or "N/A"
    cargo = find_val_by_keys(data, ["cargo_required", "cargo_amount", "cargo_coverage"]) or "N/A"

    # Fleet
    power = find_val_by_keys(data, ["power_units", "total_power_units", "fleet_size", "number_of_power_units"]) or "N/A"
    drivers = find_val_by_keys(data, ["drivers", "total_drivers", "number_of_drivers", "driver_count"]) or "N/A"

    # Safety
    safety = find_val_by_keys(data, ["safety_rating", "safety_rating_date", "rating"]) or "Not Rated"

    # Age / Risk
    age_months = None
    auth_date = find_val_by_keys(data, ["authority_date", "authority_issue_date", "date_authorized", "active_since"])
    if auth_date:
        try:
            dt = pd.to_datetime(auth_date)
            age_months = (datetime.now() - dt).days / 30.44
        except Exception:
            pass

    risk_flag = ""
    if not is_active:
        risk_flag = "INACTIVE AUTHORITY"
    elif age_months is not None and age_months < 6:
        risk_flag = "NEW CARRIER (< 6 MO)"
    else:
        risk_flag = "VERIFIED"

    return {
        "name": name,
        "dot": dot,
        "mc": mc,
        "phone": phone,
        "email": email,
        "location": location,
        "status": status_str,
        "is_active": is_active,
        "entity_type": entity_label,
        "is_broker": is_broker,
        "bipd": bipd,
        "cargo": cargo,
        "power_units": power,
        "drivers": drivers,
        "safety": safety,
        "risk_flag": risk_flag,
        "age_months": age_months,
        "raw": data
    }

# ─── HARVEST ENGINE ───
def run_harvest(start_mc, count, delay_ms, token, api_url):
    results = []
    current = int(start_mc)
    for i in range(count):
        if not st.session_state.harvesting:
            break
        res = get_carrier_info(str(current), token, api_url)
        if res and "_error" not in res:
            parsed = parse_carrier_data(res)
            if parsed:
                results.append(parsed)
                st.session_state.harvested.append(parsed)
                st.session_state.harvest_log.append(f"OK MC-{current}: {parsed['name']} [{parsed['status']}]")
            else:
                st.session_state.harvest_log.append(f"WARN MC-{current}: Parse failed")
        else:
            err = res.get("_error", "Unknown") if res else "No response"
            st.session_state.harvest_log.append(f"ERR MC-{current}: {err}")
        current += 1
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
    st.session_state.harvesting = False
    st.session_state.current_mc = current
    return results

# ─── LOGIN PAGE ───
if not st.session_state.authenticated:
    st.markdown("<div class='app-title'>🚛 CarrierChk Pro</div>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:1.1rem; margin-bottom:40px;'>FMCSA Carrier Verification & Lead Harvesting Portal</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-bottom:24px;'>Secure Login</h3>", unsafe_allow_html=True)
        email_in = st.text_input("Email", key="login_email", placeholder="your@email.com")
        pass_in = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
        if st.button("Sign In", use_container_width=True):
            if not supabase:
                st.error("Cannot connect to database. Your Supabase project may be paused. Go to supabase.com and resume it.")
            else:
                ok, msg = login_user(email_in, pass_in)
                if ok:
                    st.success("Welcome back!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ─── SESSION CHECK ───
if not verify_active_session():
    st.error("Logged in from another tab or device.")
    st.session_state.authenticated = False
    time.sleep(1.5)
    st.rerun()

# ─── MAIN APP ───
with st.sidebar:
    st.markdown(f"<h3 style='color:#00d4ff;'>👤 {st.session_state.current_user}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#94a3b8; font-size:0.85rem;'>{'Admin' if st.session_state.is_admin else 'User'}</p>", unsafe_allow_html=True)
    st.divider()
    if st.button("Logout", use_container_width=True):
        logout_user()
    if st.session_state.is_admin:
        st.divider()
        st.markdown("<p style='color:#ffa502; font-size:0.8rem;'>Admin Panel</p>", unsafe_allow_html=True)

st.markdown("<div class='app-title'>🚛 CarrierChk Pro</div>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8; margin-bottom:24px;'>FMCSA Carrier Verification & Lead Harvesting</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Lookup", "Harvest Engine", "Leads"])

# ─── TAB 1: LOOKUP ───
with tab1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Enter DOT, MC, Phone, or Email", placeholder="e.g. 1066434 or MC-322572", key="lookup_input")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_btn = st.button("Search", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if search_btn and search_query:
        with st.spinner("Fetching carrier data..."):
            raw = get_carrier_info(search_query, CARRIER_TOKEN, CARRIER_API_URL)
        if raw and "_error" not in raw:
            info = parse_carrier_data(raw)
            if info:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"<h2 style='margin:0;'>{info['name']}</h2>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#94a3b8;'>📍 {info['location']}</p>", unsafe_allow_html=True)
                with c2:
                    badge_class = "badge-active" if info['is_active'] else "badge-inactive"
                    st.markdown(f"<span class='{badge_class}'>{info['status']}</span>", unsafe_allow_html=True)
                with c3:
                    entity_badge = "badge-broker" if info['is_broker'] else "badge-active"
                    st.markdown(f"<span class='{entity_badge}'>{info['entity_type']}</span>", unsafe_allow_html=True)

                st.divider()
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.markdown(f"<div class='metric-card'><div class='metric-value'>{info['dot']}</div><div class='metric-label'>USDOT</div></div>", unsafe_allow_html=True)
                with m2:
                    st.markdown(f"<div class='metric-card'><div class='metric-value'>{info['mc']}</div><div class='metric-label'>MC Number</div></div>", unsafe_allow_html=True)
                with m3:
                    st.markdown(f"<div class='metric-card'><div class='metric-value'>{info['power_units']}</div><div class='metric-label'>Power Units</div></div>", unsafe_allow_html=True)
                with m4:
                    st.markdown(f"<div class='metric-card'><div class='metric-value'>{info['drivers']}</div><div class='metric-label'>Drivers</div></div>", unsafe_allow_html=True)

                st.divider()
                d1, d2 = st.columns(2)
                with d1:
                    st.markdown("**Contact**")
                    st.write(f"Phone: {info['phone']}")
                    st.write(f"Email: {info['email']}")
                    st.write(f"Safety: {info['safety']}")
                with d2:
                    st.markdown("**Insurance & Risk**")
                    st.write(f"BI&PD: {info['bipd']}")
                    st.write(f"Cargo: {info['cargo']}")
                    st.write(f"Risk: {info['risk_flag']}")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.error("Could not parse carrier data")
        else:
            err = raw.get("_error", "Unknown error") if raw else "No response"
            st.error(f"API Error: {err}")

# ─── TAB 2: HARVEST ENGINE ───
with tab2:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    hc1, hc2, hc3 = st.columns(3)
    with hc1:
        start_mc = st.number_input("Start MC Number", min_value=1, value=int(st.session_state.get("current_mc", 1800000)), step=1, key="harvest_start")
    with hc2:
        harvest_count = st.number_input("Records to Harvest", min_value=1, max_value=500, value=50, step=10)
    with hc3:
        delay_ms = st.number_input("Delay (ms)", min_value=0, max_value=5000, value=500, step=100)

    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if st.button("Start Live Engine", use_container_width=True, disabled=st.session_state.harvesting):
            st.session_state.harvesting = True
            st.session_state.harvest_log = []
            st.rerun()
    with bc2:
        if st.button("STOP Engine", use_container_width=True, disabled=not st.session_state.harvesting):
            st.session_state.harvesting = False
            st.rerun()
    with bc3:
        if st.button("Clear Data", use_container_width=True):
            st.session_state.harvested = []
            st.session_state.harvest_log = []
            st.session_state.harvesting = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Running person animation when harvesting
    if st.session_state.harvesting:
        st.markdown("""
        <div class="runner-box">
            <div class="runner-emoji">🏃</div>
            <div class="runner-text">Engine Running... Harvesting Live Data</div>
        </div>
        """, unsafe_allow_html=True)
        run_harvest(int(start_mc), int(harvest_count), int(delay_ms), CARRIER_TOKEN, CARRIER_API_URL)
        st.rerun()

    if st.session_state.harvest_log:
        st.markdown("<div class='glass-card' style='max-height:400px; overflow-y:auto;'>", unsafe_allow_html=True)
        for log in reversed(st.session_state.harvest_log[-50:]):
            st.write(log)
        st.markdown("</div>", unsafe_allow_html=True)

# ─── TAB 3: LEADS ───
with tab3:
    if st.session_state.harvested:
        df = pd.DataFrame(st.session_state.harvested)
        df["status_clean"] = df["status"]
        df["entity_clean"] = df["entity_type"]

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        f1, f2 = st.columns(2)
        with f1:
            status_filter = st.multiselect("Filter by Status", options=df["status_clean"].unique().tolist(), default=df["status_clean"].unique().tolist())
        with f2:
            entity_filter = st.multiselect("Filter by Type", options=df["entity_clean"].unique().tolist(), default=df["entity_clean"].unique().tolist())

        filtered = df[df["status_clean"].isin(status_filter) & df["entity_clean"].isin(entity_filter)]
        st.dataframe(filtered[["name", "mc", "dot", "phone", "email", "location", "status", "entity_type", "risk_flag"]], use_container_width=True, hide_index=True)

        csv_buf = io.StringIO()
        filtered[["name", "mc", "dot", "phone", "email", "location", "status", "entity_type", "power_units", "drivers", "safety", "risk_flag"]].to_csv(csv_buf, index=False)
        st.download_button("Download CSV", csv_buf.getvalue(), file_name=f"carrier_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No harvested data yet. Go to the Harvest Engine tab to start collecting leads.")
