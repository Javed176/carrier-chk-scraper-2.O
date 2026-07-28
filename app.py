import streamlit as st
import requests
import json
import time
import re
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────────────────────
CARRIER_TOKEN = "3243d1219423e4ea"
CARRIER_API_URL = "https://carrierchk.com/api/carrier"

# ─── PAGE SETUP ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Carrier Lookup",
    page_icon="🚛",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─── CUSTOM CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-title {
        font-size: 3rem;
        font-weight: 700;
        color: #1a1a1a;
        text-align: center;
        margin-bottom: 0.5rem;
        line-height: 1.2;
    }

    .subtitle {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }

    .search-container {
        background: #f8f9fa;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        border: 1px solid #e9ecef;
    }

    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .badge-active {
        background-color: #d1fae5;
        color: #065f46;
    }

    .badge-inactive {
        background-color: #fee2e2;
        color: #991b1b;
    }

    .badge-pending {
        background-color: #fef3c7;
        color: #92400e;
    }

    .info-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .info-card h3 {
        margin-top: 0;
        margin-bottom: 1rem;
        color: #1a1a1a;
        font-size: 1.1rem;
        font-weight: 600;
        border-bottom: 2px solid #198754;
        padding-bottom: 0.5rem;
    }

    .info-row {
        display: flex;
        justify-content: space-between;
        padding: 0.6rem 0;
        border-bottom: 1px solid #f3f4f6;
    }

    .info-row:last-child {
        border-bottom: none;
    }

    .info-label {
        color: #6b7280;
        font-weight: 500;
    }

    .info-value {
        color: #1a1a1a;
        font-weight: 600;
        text-align: right;
    }

    .risk-green { color: #059669; font-weight: 700; }
    .risk-orange { color: #d97706; font-weight: 700; }
    .risk-red { color: #dc2626; font-weight: 700; }

    .footer {
        text-align: center;
        color: #9ca3af;
        font-size: 0.85rem;
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 1px solid #e5e7eb;
    }

    .stats-bar {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin: 1.5rem 0;
        flex-wrap: wrap;
    }

    .stat-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #6b7280;
        font-size: 0.9rem;
    }

    .stat-icon { color: #198754; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🚛 Verify any US Carrier</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Search any US carrier by USDOT or MC number. '
    'Instantly verify authority status, insurance, safety ratings, and fleet data.</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="stats-bar">
    <div class="stat-item"><span class="stat-icon">✅</span> Official FMCSA Data</div>
    <div class="stat-item"><span class="stat-icon">🔄</span> Updated Daily</div>
    <div class="stat-item"><span class="stat-icon">🔒</span> 100% Free</div>
</div>
""", unsafe_allow_html=True)

# ─── SEARCH SECTION ────────────────────────────────────────────────────────
with st.container():
    st.markdown('<div class="search-container">', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])

    with col1:
        search_input = st.text_input(
            "",
            placeholder="Enter DOT or MC number — e.g. 3000000 or MC 1700000",
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_clicked = st.button("🔍 Search", use_container_width=True, type="primary")

    st.markdown(
        '<p style="color:#9ca3af; font-size:0.85rem; margin-top:0.5rem;">'
        'Enter a USDOT or MC number.</p>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

# ─── HELPER: DETECT INPUT TYPE ────────────────────────────────────────────
def detect_input_type(query):
    """Detect if input is MC or DOT number."""
    query = query.strip().upper()

    # If starts with MC or has letters, it's MC
    if query.startswith("MC"):
        # Remove "MC" prefix and any spaces
        number = re.sub(r"[^0-9]", "", query)
        return "mc", number

    # If it's all digits
    if query.isdigit():
        # DOT numbers are typically 6-7 digits, MC can vary
        # We'll default to "mc" if user explicitly types MC, else try "dot" first then "mc"
        # For simplicity, if it starts with MC it's MC, otherwise try DOT
        return "dot", query

    # Default fallback
    return "dot", query

# ─── API CALL FUNCTION ─────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_carrier_data(search_type, value):
    """Fetch carrier data from carrierchk.com API with correct query params."""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://carrierchk.com/",
    }

    params = {
        "type": search_type,
        "value": value,
        "token": CARRIER_TOKEN
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(
                CARRIER_API_URL,
                headers=headers,
                params=params,
                timeout=15
            )

            # Handle specific status codes
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"error": f"Invalid JSON response: {response.text[:200]}"}

            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    time.sleep(wait_time)
                    continue
                return {"error": "Rate limited by Cloudflare (429). Please wait a moment and try again."}

            elif response.status_code == 401:
                return {"error": "Unauthorized (401). The API token may be invalid or expired."}

            elif response.status_code == 404:
                return {"error": f"Carrier not found (404). No carrier matches {search_type.upper()} {value}."}

            elif response.status_code in [502, 503, 504]:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"error": f"Server error ({response.status_code}). The API is temporarily unavailable."}

            else:
                return {"error": f"API error {response.status_code}: {response.text[:300]}"}

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"error": "Request timed out. The API server is not responding."}

        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"error": "Connection error. Cannot reach the API server."}

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}

    return {"error": "All retry attempts failed."}

# ─── DISPLAY FUNCTIONS ───────────────────────────────────────────────────
def get_status_badge(status):
    status = str(status).lower() if status else "unknown"
    if "active" in status:
        return '<span class="badge badge-active">● Active</span>'
    elif "inactive" in status or "revoke" in status:
        return '<span class="badge badge-inactive">● Inactive</span>'
    elif "pending" in status:
        return '<span class="badge badge-pending">● Pending</span>'
    else:
        return f'<span class="badge badge-pending">● {status.title()}</span>'

def get_risk_class(authority_status, safety_rating, months_active):
    if not authority_status:
        return "risk-red"
    status = str(authority_status).lower()
    if "inactive" in status or "revoke" in status:
        return "risk-red"
    if safety_rating and "unsatisfactory" in str(safety_rating).lower():
        return "risk-red"
    if months_active is not None and months_active < 6:
        return "risk-orange"
    return "risk-green"

def display_carrier_card(data):
    """Display carrier data in a beautiful card layout."""

    # Extract fields with safe defaults - handle nested structures
    carrier_name = data.get("legal_name") or data.get("dba_name") or data.get("name") or data.get("carrier_name") or "Unknown Carrier"
    dot_number = data.get("dot_number") or data.get("usdot_number") or data.get("dot") or "N/A"
    mc_number = data.get("mc_number") or data.get("mc") or data.get("docket_number") or data.get("mc_docket") or "N/A"

    authority_status = data.get("authority_status") or data.get("operating_status") or data.get("status") or data.get("operating_authority_status") or "Unknown"
    safety_rating = data.get("safety_rating") or data.get("rating") or data.get("fmcsa_safety_rating") or "N/A"

    # Insurance - handle nested dict or flat keys
    insurance = data.get("insurance") or {}
    if isinstance(insurance, dict):
        bi_pd = insurance.get("bi_pd") or insurance.get("liability") or insurance.get("bodily_injury_property_damage") or "N/A"
        cargo = insurance.get("cargo") or insurance.get("cargo_insurance") or "N/A"
    else:
        bi_pd = data.get("bi_pd") or data.get("liability") or "N/A"
        cargo = data.get("cargo") or data.get("cargo_insurance") or "N/A"

    # Fleet
    fleet = data.get("fleet") or {}
    if isinstance(fleet, dict):
        power_units = fleet.get("power_units") or fleet.get("total_power_units") or fleet.get("trucks") or "N/A"
        drivers = fleet.get("drivers") or fleet.get("total_drivers") or fleet.get("cdl_drivers") or "N/A"
    else:
        power_units = data.get("power_units") or data.get("total_power_units") or data.get("trucks") or "N/A"
        drivers = data.get("drivers") or data.get("total_drivers") or data.get("cdl_drivers") or "N/A"

    # Contact
    phone = data.get("phone") or data.get("telephone") or data.get("phone_number") or "N/A"
    email = data.get("email") or data.get("email_address") or data.get("contact_email") or "N/A"
    address = data.get("address") or data.get("physical_address") or data.get("mailing_address") or "N/A"

    # Authority age
    authority_date = data.get("authority_date") or data.get("date_authorized") or data.get("authority_age") or data.get("date_of_authority")
    months_active = None
    if authority_date:
        try:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y"]:
                try:
                    auth_dt = datetime.strptime(str(authority_date)[:20].strip(), fmt)
                    months_active = (datetime.now() - auth_dt).days // 30
                    break
                except:
                    continue
        except:
            pass

    # ─── RISK BANNER ─────────────────────────────────────────────────────
    risk_class = get_risk_class(authority_status, safety_rating, months_active)

    if risk_class == "risk-red":
        risk_msg = "⚠️ HIGH RISK — Do not book with this carrier"
        risk_bg = "#fef2f2"
        risk_border = "#fecaca"
    elif risk_class == "risk-orange":
        risk_msg = "⚡ CAUTION — Carrier is new (< 6 months)"
        risk_bg = "#fffbeb"
        risk_border = "#fcd34d"
    else:
        risk_msg = "✅ LOW RISK — Carrier appears safe to book"
        risk_bg = "#f0fdf4"
        risk_border = "#bbf7d0"

    st.markdown(f"""
    <div style="background:{risk_bg}; border:1px solid {risk_border}; border-radius:12px; padding:1rem; margin-bottom:1.5rem; text-align:center;">
        <span style="font-weight:700; font-size:1.1rem;">{risk_msg}</span>
    </div>
    """, unsafe_allow_html=True)

    # ─── CARRIER HEADER ────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:1.5rem;">
        <h2 style="margin:0; color:#1a1a1a; font-size:1.8rem;">{carrier_name}</h2>
        <p style="color:#6b7280; margin-top:0.3rem;">
            DOT: <strong>{dot_number}</strong> &nbsp;|&nbsp; 
            MC: <strong>{mc_number}</strong> &nbsp;|&nbsp;
            {get_status_badge(authority_status)}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ─── INFO CARDS ────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="info-card">
            <h3>📋 Operating Authority</h3>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="info-row">
            <span class="info-label">Status</span>
            <span class="info-value">{get_status_badge(authority_status)}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Safety Rating</span>
            <span class="info-value">{safety_rating}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Authority Date</span>
            <span class="info-value">{authority_date or 'N/A'}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Time Active</span>
            <span class="info-value">{f"{months_active} months" if months_active else 'N/A'}</span>
        </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="info-card">
            <h3>🛡️ Insurance</h3>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="info-row">
            <span class="info-label">BI & PD</span>
            <span class="info-value">{bi_pd}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Cargo</span>
            <span class="info-value">{cargo}</span>
        </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-card">
            <h3>🚛 Fleet Data</h3>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="info-row">
            <span class="info-label">Power Units</span>
            <span class="info-value">{power_units}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Total Drivers</span>
            <span class="info-value">{drivers}</span>
        </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="info-card">
            <h3>📞 Contact Info</h3>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="info-row">
            <span class="info-label">Phone</span>
            <span class="info-value">{phone}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Email</span>
            <span class="info-value">{email}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Address</span>
            <span class="info-value">{address}</span>
        </div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("🔧 View Raw API Response"):
        st.json(data)

# ─── MAIN LOGIC ──────────────────────────────────────────────────────────
if search_clicked and search_input.strip():
    search_type, search_value = detect_input_type(search_input.strip())

    with st.spinner(f"🔍 Looking up {search_type.upper()} {search_value}..."):
        result = fetch_carrier_data(search_type, search_value)

    if "error" in result:
        st.error(f"❌ {result['error']}")
        st.info("💡 Try entering a valid USDOT number (e.g., 3000000) or MC number (e.g., MC 1700000)")

        with st.expander("🔧 Debug Info"):
            st.write("Search type:", search_type)
            st.write("Search value:", search_value)
            st.write("API URL:", CARRIER_API_URL)
            st.write("Full request would be:", f"{CARRIER_API_URL}?type={search_type}&value={search_value}&token=****")
    else:
        display_carrier_card(result)

elif search_clicked and not search_input.strip():
    st.warning("⚠️ Please enter a DOT number or MC number.")

# ─── FOOTER ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    <p>🔒 Data sourced from official FMCSA records via CarrierChk API</p>
    <p>Built with Streamlit • Verify carriers before booking loads</p>
</div>
""", unsafe_allow_html=True)
