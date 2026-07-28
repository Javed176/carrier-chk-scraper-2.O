import streamlit as st
import requests
import json
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

    .search-btn {
        background-color: #198754 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        cursor: pointer !important;
        transition: all 0.2s !important;
    }

    .search-btn:hover {
        background-color: #157347 !important;
        transform: translateY(-1px);
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

    .risk-green {
        color: #059669;
        font-weight: 700;
    }

    .risk-orange {
        color: #d97706;
        font-weight: 700;
    }

    .risk-red {
        color: #dc2626;
        font-weight: 700;
    }

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

    .stat-icon {
        color: #198754;
    }
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
            placeholder="Enter DOT, MC, phone or email — e.g. 3000000 or MC 1700000",
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_clicked = st.button("🔍 Search", use_container_width=True, type="primary")

    st.markdown(
        '<p style="color:#9ca3af; font-size:0.85rem; margin-top:0.5rem;">'
        'Enter a USDOT or MC number, a phone number, or an email.</p>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

# ─── API CALL FUNCTION ─────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_carrier_data(query):
    """Fetch carrier data from carrierchk.com API."""
    headers = {
        "Authorization": f"Bearer {CARRIER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "CarrierLookup-Streamlit/1.0"
    }

    # Try multiple common API patterns
    patterns = [
        {"url": f"{CARRIER_API_URL}", "params": {"q": query}, "method": "GET"},
        {"url": f"{CARRIER_API_URL}", "params": {"query": query}, "method": "GET"},
        {"url": f"{CARRIER_API_URL}", "params": {"dot": query}, "method": "GET"},
        {"url": f"{CARRIER_API_URL}", "params": {"mc": query}, "method": "GET"},
        {"url": f"{CARRIER_API_URL}", "params": {"search": query}, "method": "GET"},
        {"url": f"{CARRIER_API_URL}/{query}", "params": {}, "method": "GET"},
    ]

    last_error = None

    for pattern in patterns:
        try:
            if pattern["method"] == "GET":
                response = requests.get(
                    pattern["url"],
                    headers=headers,
                    params=pattern["params"],
                    timeout=15
                )

            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return {"raw_text": response.text}

            last_error = f"Status {response.status_code}: {response.text[:200]}"

        except requests.exceptions.RequestException as e:
            last_error = str(e)
            continue

    return {"error": f"Could not fetch data. Last attempt: {last_error}"}

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

    # Extract fields with safe defaults
    carrier_name = data.get("legal_name") or data.get("dba_name") or data.get("name") or "Unknown Carrier"
    dot_number = data.get("dot_number") or data.get("usdot_number") or data.get("dot") or "N/A"
    mc_number = data.get("mc_number") or data.get("mc") or data.get("docket_number") or "N/A"

    authority_status = data.get("authority_status") or data.get("operating_status") or data.get("status") or "Unknown"
    safety_rating = data.get("safety_rating") or data.get("rating") or "N/A"

    # Insurance
    insurance = data.get("insurance") or {}
    if isinstance(insurance, dict):
        bi_pd = insurance.get("bi_pd") or insurance.get("liability") or "N/A"
        cargo = insurance.get("cargo") or "N/A"
    else:
        bi_pd = cargo = "N/A"

    # Fleet
    fleet = data.get("fleet") or {}
    if isinstance(fleet, dict):
        power_units = fleet.get("power_units") or fleet.get("total_power_units") or "N/A"
        drivers = fleet.get("drivers") or fleet.get("total_drivers") or "N/A"
    else:
        power_units = data.get("power_units") or "N/A"
        drivers = data.get("drivers") or "N/A"

    # Contact
    phone = data.get("phone") or data.get("telephone") or "N/A"
    email = data.get("email") or data.get("email_address") or "N/A"
    address = data.get("address") or data.get("physical_address") or "N/A"

    # Authority age
    authority_date = data.get("authority_date") or data.get("date_authorized") or data.get("authority_age")
    months_active = None
    if authority_date:
        try:
            # Try parsing various date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]:
                try:
                    auth_dt = datetime.strptime(str(authority_date)[:10], fmt)
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
        # Operating Authority
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

        # Insurance
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
        # Fleet
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

        # Contact
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

    # ─── RAW JSON (expandable) ───────────────────────────────────────────
    with st.expander("🔧 View Raw API Response"):
        st.json(data)

# ─── MAIN LOGIC ──────────────────────────────────────────────────────────
if search_clicked and search_input.strip():
    with st.spinner("🔍 Looking up carrier..."):
        result = fetch_carrier_data(search_input.strip())

    if "error" in result:
        st.error(f"❌ {result['error']}")
        st.info("💡 Try entering a valid USDOT number (e.g., 3000000) or MC number (e.g., MC 1700000)")
    else:
        display_carrier_card(result)

elif search_clicked and not search_input.strip():
    st.warning("⚠️ Please enter a DOT number, MC number, or search term.")

# ─── FOOTER ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    <p>🔒 Data sourced from official FMCSA records via CarrierChk API</p>
    <p>Built with Streamlit • Verify carriers before booking loads</p>
</div>
""", unsafe_allow_html=True)
