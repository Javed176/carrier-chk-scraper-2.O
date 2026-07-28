import os, time, uuid, json, re, requests, pandas as pd
import streamlit as st
from streamlit_lottie import st_lottie
import streamlit.components.v1 as components
from supabase import create_client, Client

st.set_page_config(page_title="Carrier Automation Portal", layout="wide")

# ═══════════════════════════════════════════════════════════════════════════
# MODERN 3D GLASSMORPHISM THEME
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); background-attachment: fixed; }
    .main-title { font-family: 'Space Grotesk', sans-serif; font-size: 3.2rem; font-weight: 800; text-align: center; margin-bottom: 0.3rem; background: linear-gradient(135deg, #00f5d4 0%, #00bbf9 50%, #9b5de5 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; text-shadow: 0 0 60px rgba(0, 245, 212, 0.3); letter-spacing: -1px; }
    .subtitle { font-size: 1.05rem; color: rgba(255,255,255,0.6); text-align: center; margin-bottom: 2rem; max-width: 600px; margin-left: auto; margin-right: auto; font-weight: 400; }
    .search-container { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 24px; padding: 2.5rem; margin-bottom: 2rem; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1); }
    .info-card { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border-radius: 20px; padding: 1.8rem; margin-bottom: 1.2rem; border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(255, 255, 255, 0.05); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    .info-card:hover { transform: translateY(-4px) scale(1.01); box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 30px rgba(0, 245, 212, 0.1); border-color: rgba(0, 245, 212, 0.2); }
    .info-card h3 { margin-top: 0; margin-bottom: 1.2rem; color: #fff; font-size: 1.15rem; font-weight: 700; font-family: 'Space Grotesk', sans-serif; border-bottom: 2px solid; border-image: linear-gradient(90deg, #00f5d4, #9b5de5) 1; padding-bottom: 0.7rem; display: flex; align-items: center; gap: 0.5rem; }
    .info-row { display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
    .info-row:last-child { border-bottom: none; }
    .info-label { color: rgba(255,255,255,0.5); font-weight: 500; font-size: 0.9rem; }
    .info-value { color: #fff; font-weight: 600; text-align: right; font-size: 0.95rem; }
    .badge { display: inline-block; padding: 5px 14px; border-radius: 50px; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; }
    .badge-active { background: rgba(0, 245, 212, 0.15); color: #00f5d4; border: 1px solid rgba(0, 245, 212, 0.3); box-shadow: 0 0 15px rgba(0, 245, 212, 0.2); }
    .badge-inactive { background: rgba(255, 71, 87, 0.15); color: #ff4757; border: 1px solid rgba(255, 71, 87, 0.3); box-shadow: 0 0 15px rgba(255, 71, 87, 0.2); }
    .badge-pending { background: rgba(255, 193, 7, 0.15); color: #ffc107; border: 1px solid rgba(255, 193, 7, 0.3); box-shadow: 0 0 15px rgba(255, 193, 7, 0.2); }
    .risk-green { color: #00f5d4; font-weight: 700; } .risk-orange { color: #ffc107; font-weight: 700; } .risk-red { color: #ff4757; font-weight: 700; }
    .stats-bar { display: flex; justify-content: center; gap: 2.5rem; margin: 2rem 0; flex-wrap: wrap; }
    .stat-item { display: flex; align-items: center; gap: 0.6rem; color: rgba(255,255,255,0.6); font-size: 0.9rem; font-weight: 500; background: rgba(255,255,255,0.05); padding: 0.6rem 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); }
    .stat-icon { font-size: 1.1rem; }
    .footer { text-align: center; color: rgba(255,255,255,0.35); font-size: 0.85rem; margin-top: 3rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.08); }
    div[data-baseweb="input"] > div { background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 14px !important; color: white !important; }
    div[data-baseweb="input"] > div:focus-within { border-color: #00f5d4 !important; box-shadow: 0 0 20px rgba(0, 245, 212, 0.15) !important; }
    .stButton > button { border-radius: 14px !important; font-weight: 600 !important; letter-spacing: 0.5px !important; transition: all 0.3s ease !important; border: none !important; }
    .stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(0, 245, 212, 0.3) !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #00f5d4 0%, #00bbf9 100%) !important; color: #0f0c29 !important; }
    .stButton > button[kind="secondary"] { background: rgba(255,255,255,0.08) !important; color: white !important; border: 1px solid rgba(255,255,255,0.15) !important; }
    button[data-baseweb="tab"] { color: rgba(255,255,255,0.5) !important; font-weight: 600 !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #00f5d4 !important; }
    section[data-testid="stSidebar"] { background: rgba(15, 12, 41, 0.95) !important; backdrop-filter: blur(20px) !important; border-right: 1px solid rgba(255,255,255,0.08) !important; }
    details { background: rgba(255,255,255,0.03) !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 16px !important; }
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.03) !important; border-radius: 16px !important; padding: 1rem !important; border: 1px solid rgba(255,255,255,0.08) !important; }
    div[data-testid="stMetric"] label { color: rgba(255,255,255,0.5) !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #00f5d4 !important; font-weight: 700 !important; }
    .stDownloadButton button { border-radius: 12px !important; background: linear-gradient(135deg, #9b5de5 0%, #f15bb5 100%) !important; color: white !important; border: none !important; font-weight: 600 !important; }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.25); }
</style>
""", unsafe_allow_html=True)


# --- CONFIGURATION ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
CARRIER_TOKEN = st.secrets.get("CARRIER_TOKEN") or os.environ.get("CARRIER_TOKEN")
CARRIER_API_URL = st.secrets.get("CARRIER_API_URL") or os.environ.get("CARRIER_API_URL")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("🔑 Missing SUPABASE_URL or SUPABASE_KEY in secrets.")
    st.stop()

ALL_US_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS",
    "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY",
    "NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
]

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def get_http() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"})
    return s

supabase = get_supabase()
http_session = get_http()

# --- BACKEND UTILITIES ---
def log_activity(email, action, detail=""):
    try:
        supabase.table("activity_logs").insert({"email": email, "action": action, "detail": detail}).execute()
    except Exception:
        pass

def get_system_config():
    config = {"throttle_delay_ms": 500.0, "override_global_speed": False}
    try:
        res = supabase.table("system_config").select("*").execute()
        for r in res.data:
            if r["key"] == "throttle_delay_ms": config["throttle_delay_ms"] = float(r["value"])
            elif r["key"] == "override_global_speed": config["override_global_speed"] = str(r["value"]).upper() == "TRUE"
    except Exception:
        pass
    return config

def update_global_config(delay_ms, override_bool):
    try:
        supabase.table("system_config").upsert({"key": "throttle_delay_ms", "value": f"{delay_ms:.4f}"}, on_conflict="key").execute()
        supabase.table("system_config").upsert({"key": "override_global_speed", "value": str(override_bool).upper()}, on_conflict="key").execute()
        return True
    except Exception as e:
        st.error(f"Config error: {e}")
        return False

def get_user_settings(email):
    try:
        res = supabase.table("users").select("delay_ms, session_duration_hours").eq("email", email).execute()
        if res.data:
            return float(res.data[0].get("delay_ms", 500.0)), float(res.data[0].get("session_duration_hours", 3.0))
    except Exception:
        pass
    return 500.0, 3.0

# --- RECURSIVE DICTIONARY SEARCH HELPER ---
def find_val_by_keys(d, target_keys):
    if not isinstance(d, dict):
        return None
    for k, v in d.items():
        if k.lower() in [tk.lower() for tk in target_keys]:
            if v is not None and str(v).strip() != "":
                return v
        if isinstance(v, dict):
            res = find_val_by_keys(v, target_keys)
            if res is not None:
                return res
    return None

# --- ROBUST SINGLE API CALLER WITH BUILT-IN 429 BACKOFF ---
def get_carrier_info(mc_number, token, retries=6):
    params = {"type": "mc", "value": str(mc_number).strip(), "token": token}
    
    for attempt in range(retries):
        try:
            res = http_session.get(CARRIER_API_URL, params=params, timeout=12.0)
            
            if res.status_code == 200:
                return 200, res.json()
            elif res.status_code in [404, 400]:
                return res.status_code, {"not_found": True}
            elif res.status_code == 429:
                sleep_time = 2.5 * (attempt + 1)
                time.sleep(sleep_time)
                continue
            elif res.status_code in [500, 502, 503, 504]:
                time.sleep(2.0 * (attempt + 1))
                continue
        except (requests.exceptions.Timeout, requests.exceptions.RequestException):
            time.sleep(2.0)
                
    return 429, {"throttled": True}

def parse_carrier_data(mc_number, status_code, raw_data):
    if status_code == 429 or (isinstance(raw_data, dict) and raw_data.get("throttled")):
        return {
            "MC Number": f"MC-{mc_number}",
            "Carrier Name": "⚠️ API THROTTLED (Retrying)",
            "Entity Type": "N/A",
            "Operating Status": "⚠️ UNKNOWN",
            "Phone Number": "N/A",
            "Email Address": "N/A",
            "Location": "N/A",
            "Raw Payload": raw_data
        }

    if status_code in [404, 400] or not isinstance(raw_data, dict) or raw_data.get("not_found") is True:
        return {
            "MC Number": f"MC-{mc_number}",
            "Carrier Name": "DOCKET NOT FOUND",
            "Entity Type": "N/A",
            "Operating Status": "❌ NOT FOUND",
            "Phone Number": "N/A",
            "Email Address": "N/A",
            "Location": "N/A",
            "Raw Payload": raw_data
        }

    c = raw_data.get("carrier") or raw_data.get("data") or raw_data
    if not isinstance(c, dict) or not c:
        return {
            "MC Number": f"MC-{mc_number}",
            "Carrier Name": "DOCKET NOT FOUND",
            "Entity Type": "N/A",
            "Operating Status": "❌ NOT FOUND",
            "Phone Number": "N/A",
            "Email Address": "N/A",
            "Location": "N/A",
            "Raw Payload": raw_data
        }

    name = str(c.get("dba_name") or c.get("legal_name") or c.get("name") or "N/A").strip().upper()
    if name in ["NONE", "NULL", "", "N/A", "NOT FOUND"]:
        return {
            "MC Number": f"MC-{mc_number}",
            "Carrier Name": "DOCKET NOT FOUND",
            "Entity Type": "N/A",
            "Operating Status": "❌ NOT FOUND",
            "Phone Number": "N/A",
            "Email Address": "N/A",
            "Location": "N/A",
            "Raw Payload": raw_data
        }

    # ═══════════════════════════════════════════════════════
    # FIXED: ROBUST OPERATING STATUS DETECTION
    # ═══════════════════════════════════════════════════════
    status_raw = str(find_val_by_keys(c, [
        "status", "operating_status", "carrier_status", "authority_status",
        "common_authority_status", "contract_authority_status", "commonStatus", "contractStatus",
        "operatingAuthorityStatus", "carrierOperatingStatus"
    ]) or "").upper().strip()

    is_active = None

    if status_raw:
        inactive_exact = ["INACTIVE", "REVOKED", "SUSPENDED", "CANCELED", "CANCELLED",
                          "DENIED", "NOT AUTHORIZED", "OUT OF SERVICE", "NO AUTHORITY",
                          "NOT ACTIVE", "UNAUTHORIZED"]
        if any(kw == status_raw or kw in status_raw for kw in inactive_exact):
            is_active = False
        elif any(kw in status_raw for kw in ["ACTIVE", "AUTHORIZED", "OPERATING"]):
            is_active = True
        else:
            is_active = False

    if is_active is None:
        allowed_val = find_val_by_keys(c, [
            "allowed_to_operate", "allowedToOperate", "is_active",
            "common_allowed_to_operate", "contract_allowed_to_operate"
        ])
        if allowed_val is True or str(allowed_val).upper() in ["Y", "YES", "TRUE", "1", "ACTIVE"]:
            is_active = True
        elif allowed_val is False or str(allowed_val).upper() in ["N", "NO", "FALSE", "0", "INACTIVE"]:
            is_active = False

    if is_active is None:
        payload_text = json.dumps(c).upper()
        inactive_signals = ["NOT AUTHORIZED", "AUTHORITY REVOKED", "SUSPENDED",
                           "INACTIVE", "OUT OF SERVICE", "CANCELED", "NOT ACTIVE",
                           "UNAUTHORIZED", "AUTHORITY DENIED"]
        if any(term in payload_text for term in inactive_signals):
            is_active = False
        elif any(term in payload_text for term in ["ACTIVE AUTHORITY", "AUTHORIZED TO OPERATE"]):
            is_active = True
        else:
            is_active = False

    status_str = "🟢 ACTIVE" if is_active else "🔴 INACTIVE"

    # ═══════════════════════════════════════════════════════
    # FIXED: BROKER VS CARRIER DETECTION
    # ═══════════════════════════════════════════════════════
    entity_val = str(find_val_by_keys(c, [
        "entity_type", "entitytype", "operating_type", "operatingtype",
        "carrier_type", "type", "authority_type"
    ]) or "").upper()

    broker_auth = find_val_by_keys(c, ["broker_authority_status", "brokerAuthStatus",
                                        "broker_authority", "brokerAuthority"])
    is_broker_auth = str(broker_auth).upper() in ["Y", "ACTIVE", "AUTHORIZED", "TRUE", "A", "YES"]

    known_broker_names = ["BROKER", "BROKERAGE", "3PL", "GLOBAL LOGISTICS", "ECHO GLOBAL",
                          "CH ROBINSON", "TQL", "RXO", "COYOTE", "UBER FREIGHT"]

    is_broker = (
        is_broker_auth or
        "BROKER" in entity_val or
        any(b in name for b in known_broker_names)
    )
    entity_label = "BROKER" if is_broker else "CARRIER"

    # --- CONTACT INFO & LOCATION ---
    def flatten_dict_values(d):
        vals = []
        for v in d.values():
            if isinstance(v, dict): vals.extend(flatten_dict_values(v))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict): vals.extend(flatten_dict_values(item))
                    else: vals.append(str(item))
            else: vals.append(str(v))
        return vals

    all_payload_text = " ".join(flatten_dict_values(c)).upper()

    phone = str(find_val_by_keys(c, ["phone", "cell_phone", "telephone", "phone_number"]) or "N/A").strip()
    if phone.lower() in ["none", "null", "", "not listed"]: phone = "N/A"

    email = str(find_val_by_keys(c, ["email_address", "email", "emailaddress"]) or "").strip()
    if not email or email.lower() in ["none", "null", "not listed", "", "n/a"]:
        emails_found = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', all_payload_text)
        valid_emails = [e for e in emails_found if not any(x in e.lower() for x in ["carrierchk", "example.com"])]
        email = valid_emails[0] if valid_emails else "Not Listed"

    city = str(find_val_by_keys(c, ["phy_city", "city", "physical_city"]) or "").strip()
    state = str(find_val_by_keys(c, ["phy_state", "state", "physical_state"]) or "").strip()
    location = f"{city}, {state}".strip(", ") if city or state else "N/A"

    return {
        "MC Number": f"MC-{mc_number}",
        "Carrier Name": name,
        "Entity Type": entity_label,
        "Operating Status": status_str,
        "Phone Number": phone,
        "Email Address": email,
        "Location": location,
        "Raw Payload": raw_data
    }
# --- STATE INIT ---
for key, val in [("authenticated", False), ("current_user", None), ("session_token", None), 
                 ("is_admin", False), ("login_time", None), ("running", False), 
                 ("scraped_rows", []), ("current_mc", ""), ("last_db_check", 0.0), ("last_session_check", 0.0),
                 ("reset_filters", False)]:
    if key not in st.session_state: st.session_state[key] = val

def force_logout(reason="Session Expired"):
    if st.session_state.authenticated and st.session_state.current_user:
        log_activity(st.session_state.current_user, "logout", reason)
        try: supabase.table("users").update({"active_session_id": None}).eq("email", st.session_state.current_user).execute()
        except Exception: pass
    for k in ["authenticated", "current_user", "session_token", "is_admin", "running"]:
        st.session_state[k] = False if isinstance(st.session_state[k], bool) else None
    st.session_state.scraped_rows = []
    st.session_state.current_mc = ""

def verify_active_session():
    if st.session_state.authenticated and st.session_state.current_user:
        now = time.time()
        if now - st.session_state.last_session_check < 30.0: return True
        st.session_state.last_session_check = now
        try:
            res = supabase.table("users").select("active_session_id").eq("email", st.session_state.current_user).execute()
            if res.data and res.data[0].get("active_session_id") != st.session_state.session_token:
                return False
        except Exception: pass
    return True

# --- LOGIN GATE ---
if not st.session_state.authenticated:
    st.title("🔒 Security Access Required")
    st.write("Enter credentials. Contact support if needed.")
    c1, c2 = st.columns(2)
    email_in = c1.text_input("Email:").strip().lower()
    pass_in = c2.text_input("Password:", type="password")
    if st.button("Verify & Unlock Engine", use_container_width=True):
        res = supabase.table("users").select("*").eq("email", email_in).execute()
        if res.data and res.data[0]["password"] == pass_in:
            token = str(uuid.uuid4())
            supabase.table("users").update({"active_session_id": token}).eq("email", email_in).execute()
            st.session_state.update({"authenticated": True, "current_user": email_in, "session_token": token,
                                     "is_admin": res.data[0].get("is_admin", False), "login_time": time.time(),
                                     "scraped_rows": [], "current_mc": ""})
            log_activity(email_in, "login", "Success")
            st.rerun()
        else: st.error("Access denied.")
    st.stop()

if not verify_active_session():
    st.error("⚠️ Logged in from another tab or device.")
    st.session_state.authenticated = False
    time.sleep(1.5)
    st.rerun()

# --- SPEED CONFIG & AUTO-LOCK ---
now = time.time()
if now - st.session_state.last_db_check > 30.0:
    cfg = get_system_config()
    if cfg["override_global_speed"]:
        st.session_state.cached_delay_ms = cfg["throttle_delay_ms"]
        st.session_state.cached_speed_str = f"🚨 Forced Override ({cfg['throttle_delay_ms']:.2f} ms)"
        _, st.session_state.cached_dur = get_user_settings(st.session_state.current_user)
    else:
        st.session_state.cached_delay_ms, st.session_state.cached_dur = get_user_settings(st.session_state.current_user)
        st.session_state.cached_speed_str = f"👤 {st.session_state.cached_delay_ms:.2f} ms"
    st.session_state.last_db_check = now

delay_ms = st.session_state.get("cached_delay_ms", 500.0)
session_dur = st.session_state.get("cached_dur", 3.0)
speed_str = st.session_state.get("cached_speed_str", "500 ms")

if st.session_state.login_time and (time.time() - st.session_state.login_time >= session_dur * 3600):
    force_logout("Auto-Expired")
    st.warning("⏱️ Session Expired.")
    st.rerun()

# --- SIDEBAR ---
st.sidebar.markdown(f"### 👤 Logged In As:\n`{st.session_state.current_user}`")
rem_sec = max(0, int((session_dur * 3600) - (time.time() - st.session_state.login_time)))
components.html(f"""
<div style="font-family:monospace;font-size:15px;font-weight:bold;color:#ff4b4b;background:#0e1117;padding:8px;border-radius:5px;text-align:center;border:1px solid #30363d;">
Auto-Locks In: <span id="clock">--</span>
</div>
<script>
    let rem = {rem_sec};
    function u(){{
        if(rem<=0){{ location.reload(); return; }}
        let h=Math.floor(rem/3600), m=Math.floor((rem%3600)/60), s=rem%60;
        document.getElementById('clock').textContent = (h<10?'0'+h:h)+'h '+(m<10?'0'+m:m)+'m '+(s<10?'0'+s:s)+'s';
        rem--;
    }}
    u(); setInterval(u, 1000);
</script>""", height=55)

if st.sidebar.button("🔓 Log Out", use_container_width=True):
    force_logout("Manual Logout")
    st.rerun()

show_admin = st.sidebar.checkbox("🛡️ Admin Dashboard", value=False) if st.session_state.is_admin else False

# --- ADMIN PANEL ---
if show_admin and st.session_state.is_admin:
    st.title("🛡️ Super Admin Control Dashboard")
    t1, t2, t3 = st.tabs(["👥 User Management", "📊 Activity History Logs", "⚙️ System Configuration"])
    
    with t1:
        st.subheader("➕ Register New User")
        col_a1, col_a2, col_a3 = st.columns(3)
        u_email = col_a1.text_input("New Email:").strip().lower()
        u_pass = col_a2.text_input("Set Password:")
        u_role = col_a3.selectbox("Role:", ["Standard User", "Super Admin"])
        
        col_a4, col_a5 = st.columns(2)
        u_delay = col_a4.number_input("Speed Limit (ms):", value=500.0, step=10.0)
        u_hrs = col_a5.number_input("Session Timeout (Hours):", value=3.0, step=0.5)
        
        if st.button("➕ Add User Account", use_container_width=True) and u_email and u_pass:
            supabase.table("users").insert({
                "email": u_email, "password": u_pass, "is_admin": (u_role == "Super Admin"), 
                "delay_ms": u_delay, "session_duration_hours": u_hrs
            }).execute()
            st.success(f"Registered new account for {u_email}!")
            st.rerun()

        st.markdown("---")
        st.subheader("📋 Registered Users Overview")
        user_list = supabase.table("users").select("*").execute().data
        if user_list:
            st.dataframe(pd.DataFrame(user_list)[["email", "is_admin", "delay_ms", "session_duration_hours"]], use_container_width=True)

    with t2:
        st.subheader("📊 Target User Activity History")
        logs = supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(200).execute().data
        if logs:
            st.dataframe(pd.DataFrame(logs)[["created_at", "email", "action", "detail"]], use_container_width=True)

    with t3:
        st.subheader("⚙️ Global Speed Overrides")
        cfg = get_system_config()
        over = st.checkbox("Global Speed Override", value=cfg["override_global_speed"])
        g_speed = st.number_input("Global Delay (ms):", value=cfg["throttle_delay_ms"])
        if st.button("💾 Save Global Settings"):
            update_global_config(g_speed, over)
            st.success("Saved!")
            st.rerun()

# --- MAIN LIVE SINGLE-MC HARVESTER ENGINE ---
if not show_admin:
    st.title("🚚 Automated Carrier Harvester (Live Single-MC Engine)")
    st.sidebar.success("CarrierChk API Active" if CARRIER_TOKEN else "Missing API Token")

    c1, c2 = st.columns(2)
    with c1:
        if st.session_state.current_mc == "":
            raw_mc = st.text_input("Starting MC Number:", placeholder="e.g. 1800000")
            if raw_mc.isdigit(): st.session_state.current_mc = int(raw_mc)
        else:
            st.session_state.current_mc = st.number_input("Set MC Number:", min_value=1, value=int(st.session_state.current_mc), step=1)
    with c2:
        st.metric("Session Speed Enforced", speed_str)

    b1, b2, b3 = st.columns(3)
    if b1.button("🚀 Start Live Engine", use_container_width=True):
        if st.session_state.current_mc != "":
            st.session_state.running = True
            st.rerun()
        else: st.error("Enter MC Number first.")

    if b2.button("🛑 STOP Engine", use_container_width=True):
        lottie_container.empty()
        st.session_state.running = False
        st.success("Stopped harvesting engine.")

    if b3.button("🗑️ Clear Data", use_container_width=True):
        lottie_container.empty()
        st.session_state.scraped_rows = []
        st.rerun()

    status_box = st.empty()

    # ═══════════════════════════════════════════════════════════════════════════
    # 🚛 LOTTIE TRUCK ANIMATION
    # Replace URL below with your own from https://lottiefiles.com
    # ═══════════════════════════════════════════════════════════════════════════
    TRUCK_LOTTIE_URL = "https://lottie.host/https://lottiefiles.com/free-animation/logistics-trucks-DHvuLcYVdQ.json"
    lottie_container = st.empty()

    if st.session_state.running and st.session_state.current_mc != "":
        
        # Show truck animation
        with lottie_container.container():
            cols = st.columns([1, 2, 1])
            with cols[1]:
                st_lottie(
                    TRUCK_LOTTIE_URL,
                    speed=1.5,
                    reverse=False,
                    loop=True,
                    quality="high",
                    height=200,
                    key="truck_running"
                )
                st.markdown("<p style='text-align:center;color:#00f5d4;font-weight:600;font-size:1.1rem;'>🚛 Engine Running...</p>", unsafe_allow_html=True)
        
        current_mc_val = int(st.session_state.current_mc)
        
        status_box.info(f"🔄 **Live Progress:** Processing **MC-{current_mc_val}**...")

        status_code, raw_info = get_carrier_info(current_mc_val, CARRIER_TOKEN)
        parsed = parse_carrier_data(current_mc_val, status_code, raw_info)

        st.session_state.scraped_rows.append(parsed)
        st.session_state.current_mc = current_mc_val + 1

        log_activity(st.session_state.current_user, "search_live_single", f"Harvested MC-{current_mc_val}")

        time.sleep(delay_ms / 1000.0)
        st.rerun()

    # --- FILTERING & DISPLAY ---
    st.markdown("---")
    if st.session_state.scraped_rows:
        base_df = pd.DataFrame(st.session_state.scraped_rows)

        for col in ["Entity Type", "Operating Status", "Carrier Name", "MC Number", "Location", "Email Address"]:
            if col not in base_df.columns: base_df[col] = "N/A"
            base_df[col] = base_df[col].fillna("N/A").astype(str)

        with st.expander("🔍 Filter Collected Records", expanded=True):
            r_col1, r_col2 = st.columns([4, 1])
            with r_col2:
                if st.button("🔄 Reset Filters", use_container_width=True):
                    st.session_state.reset_filters = not st.session_state.get("reset_filters", False)
                    st.rerun()

            f1, f2, f3, f4 = st.columns(4)
            sq = f1.text_input("🔎 Search Name / MC:", value="").strip().lower()
            sel_ent = f2.selectbox("🚛 Filter Entity Type:", ["ALL"] + sorted(list(base_df["Entity Type"].unique())))
            sel_stat = f3.selectbox("📌 Filter Status:", ["ALL"] + sorted(list(base_df["Operating Status"].unique())))
            sel_state = f4.selectbox("📍 Filter State:", ["ALL"] + sorted(list(ALL_US_STATES)))

        filtered_df = base_df.copy()
        if sq:
            filtered_df = filtered_df[filtered_df["Carrier Name"].str.lower().str.contains(sq) | filtered_df["MC Number"].str.lower().str.contains(sq)]
        if sel_ent != "ALL":
            filtered_df = filtered_df[filtered_df["Entity Type"] == sel_ent]
        if sel_stat != "ALL":
            filtered_df = filtered_df[filtered_df["Operating Status"] == sel_stat]
        if sel_state != "ALL":
            filtered_df = filtered_df[filtered_df["Location"].str.endswith(sel_state)]

        st.caption(f"Showing **{len(filtered_df)}** of **{len(base_df)}** total harvested records.")

        if len(filtered_df) == 0 and len(base_df) > 0:
            st.warning("⚠️ Your filters are hiding all records. Click **'🔄 Reset Filters'** above or change your filter selections to view them.")

        tab1, tab2, tab3, tab4 = st.tabs(["📋 Complete Master Log", "🎯 Verified Leads (Active Only)", "📧 Raw Active Email List", "🛠️ API Raw Response Inspector"])
        
        with tab1:
            display_df = filtered_df.drop(columns=["Raw Payload"], errors="ignore")
            st.dataframe(display_df, use_container_width=True)
            st.download_button("📥 Export Master Sheet to CSV", display_df.to_csv(index=False).encode('utf-8'), "Master_MC_Log.csv", "text/csv", use_container_width=True)

        with tab2:
            leads_df = filtered_df[
                (filtered_df["Operating Status"].str.startswith("🟢 ACTIVE")) & 
                (filtered_df["Email Address"].str.contains("@", na=False)) &
                (~filtered_df["Email Address"].isin(["N/A", "Not Listed"]))
            ].drop(columns=["Raw Payload"], errors="ignore")
            st.dataframe(leads_df, use_container_width=True)
            st.download_button("📥 Export Clean Active Leads to CSV", leads_df.to_csv(index=False).encode('utf-8'), "Active_Leads.csv", "text/csv", use_container_width=True)

        with tab3:
            emails = filtered_df[
                (filtered_df["Operating Status"].str.startswith("🟢 ACTIVE")) & 
                (filtered_df["Email Address"].str.contains("@", na=False)) &
                (~filtered_df["Email Address"].isin(["N/A", "Not Listed"]))
            ]["Email Address"].drop_duplicates()
            st.text_area("Copy Emails:", value="\n".join(emails.tolist()), height=140)
            st.download_button("📥 Export Emails CSV", pd.DataFrame({"Email Address": emails}).to_csv(index=False).encode('utf-8'), "Active_Emails.csv", "text/csv", use_container_width=True)

        with tab4:
            st.subheader("🔍 Inspect Raw CarrierChk API JSON Payload")
            selected_mc_inspect = st.selectbox("Select MC Record to Inspect:", filtered_df["MC Number"].tolist() if not filtered_df.empty else [])
            if selected_mc_inspect:
                match_row = filtered_df[filtered_df["MC Number"] == selected_mc_inspect]
                if not match_row.empty:
                    raw_p = match_row.iloc[0].get("Raw Payload")
                    st.json(raw_p)
    else:
        st.info("No records collected yet. Click 'Start Live Engine' to begin harvesting.")
