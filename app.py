"""
app.py — CarrierChk Pro (FMCSA MC Scraper)
Merged: Original UI + Direct API Integration + Fixed Status Parser
"""

import io
import os
import sys
import time
import json
import uuid
from typing import List
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Try importing local modules; fall back to built-ins ──────────────────────
try:
    from db_manager import db
except ImportError:
    class DummyDB:
        def authenticate_and_login(self, u, p):
            return True, "OK", {"username": u, "is_admin": True, "session_duration_hours": 3.0, "session_token": "dummy", "delay_ms": 500}
        def verify_active_session(self, u, s): return True
        def log_activity(self, u, a, d=""): pass
        def get_activity_logs(self, limit=200): return pd.DataFrame()
        def get_all_users(self): return []
        def create_user(self, *a, **k): return False, "db_manager.py missing."
        def update_user_config(self, *a, **k): return False, "db_manager.py missing."
    db = DummyDB()

try:
    from scraper import scrape_mc
except ImportError:
    # Built-in scraper using carrierchk API
    CARRIER_TOKEN = os.environ.get("CARRIER_TOKEN", "")
    CARRIER_API_URL = os.environ.get("CARRIER_API_URL", "https://carrierchk.com/api/carrier")

    http_session = requests.Session()


    def _find_val(d, keys):
        """Find first matching key in dict or nested dicts."""
        if not isinstance(d, dict):
            return None
        for k in keys:
            if k in d:
                return d[k]
        for v in d.values():
            if isinstance(v, dict):
                found = _find_val(v, keys)
                if found is not None:
                    return found
        return None

    def _find_by_key_part(d, part, depth=0):
        """Recursively find ANY key containing 'part' substring. Returns first match."""
        if depth > 5 or not isinstance(d, dict):
            return None
        for k, v in d.items():
            if part in k.lower():
                return v
            if isinstance(v, dict):
                found = _find_by_key_part(v, part, depth + 1)
                if found is not None:
                    return found
            elif isinstance(v, list):
                for item in v:
                    found = _find_by_key_part(item, part, depth + 1)
                    if found is not None:
                        return found
        return None

    def _collect_all_by_key_part(d, part, depth=0):
        """Recursively collect ALL values from keys containing 'part'."""
        results = []
        if depth > 5 or not isinstance(d, dict):
            return results
        for k, v in d.items():
            if part in k.lower():
                results.append(v)
            if isinstance(v, dict):
                results.extend(_collect_all_by_key_part(v, part, depth + 1))
            elif isinstance(v, list):
                for item in v:
                    results.extend(_collect_all_by_key_part(item, part, depth + 1))
        return results

    def _normalize_status(data):
        """ROBUST STATUS DETECTION."""
        status_raw = _find_val(data, [
            "operating_status", "status", "authority_status", "carrier_status",
            "operation_status", "active_status", "current_status", "record_status"
        ]) or ""
        s = str(status_raw).upper().strip()

        if s in ["ACTIVE", "AUTHORIZED", "AUTHORISED", "OPERATING", "OPERATIONAL", "A", "Y", "YES", "TRUE", "1"]:
            return "ACTIVE"
        if s in ["INACTIVE", "NOT AUTHORIZED", "NOT AUTHORISED", "REVOKED", "SUSPENDED", "NONE", "PENDING REVOCATION", "I", "N", "NO", "FALSE", "0"]:
            return "INACTIVE"

        common = str(_find_val(data, ["common_authority_status", "commonAuthStatus", "common_status"]) or "").upper().strip()
        contract = str(_find_val(data, ["contract_authority_status", "contractAuthStatus", "contract_status"]) or "").upper().strip()
        broker = str(_find_val(data, ["broker_authority_status", "brokerAuthStatus", "broker_status"]) or "").upper().strip()

        common_active = common in ["A", "ACTIVE", "Y", "YES", "TRUE", "1", "AUTHORIZED"]
        contract_active = contract in ["A", "ACTIVE", "Y", "YES", "TRUE", "1", "AUTHORIZED"]
        broker_active = broker in ["A", "ACTIVE", "Y", "YES", "TRUE", "1", "AUTHORIZED"]

        common_inactive = common in ["I", "INACTIVE", "N", "NONE", "REVOKED", "SUSPENDED"]
        contract_inactive = contract in ["I", "INACTIVE", "N", "NONE", "REVOKED", "SUSPENDED"]
        broker_inactive = broker in ["I", "INACTIVE", "N", "NONE", "REVOKED", "SUSPENDED"]

        if common_active or contract_active or broker_active:
            return "ACTIVE"
        if common_inactive or contract_inactive or broker_inactive:
            return "INACTIVE"

        op = str(_find_val(data, ["carrier_operation_status", "operation_status_code", "status_code"]) or "").upper().strip()
        if op == "A":
            return "ACTIVE"
        if op in ["I", "N"]:
            return "INACTIVE"

        return "INACTIVE"

    def _is_broker(data):
        entity = str(_find_val(data, ["entity_type", "carrier_type", "operation_type", "company_type"]) or "").upper().strip()
        if entity in ["BROKER", "FREIGHT FORWARDER"]:
            return True
        if "BROKER" in entity and "CARRIER" not in entity:
            return True

        broker_auth = str(_find_val(data, ["broker_authority_status", "brokerAuthStatus", "broker_status"]) or "").upper().strip()
        common_auth = str(_find_val(data, ["common_authority_status", "commonAuthStatus", "common_status"]) or "").upper().strip()
        contract_auth = str(_find_val(data, ["contract_authority_status", "contractAuthStatus", "contract_status"]) or "").upper().strip()

        broker_active = broker_auth in ["A", "ACTIVE", "Y", "YES", "TRUE", "1", "AUTHORIZED"]
        common_active = common_auth in ["A", "ACTIVE", "Y", "YES", "TRUE", "1", "AUTHORIZED"]
        contract_active = contract_auth in ["A", "ACTIVE", "Y", "YES", "TRUE", "1", "AUTHORIZED"]

        if broker_active and not common_active and not contract_active:
            return True
        return False

    def scrape_mc(mc):
        """Built-in scraper using carrierchk API with aggressive backoff."""
        token = st.secrets.get("CARRIER_TOKEN", CARRIER_TOKEN)
        api_url = st.secrets.get("CARRIER_API_URL", CARRIER_API_URL)

        if not token or not api_url:
            return {
                "MC Number": f"MC-{mc:07d}",
                "Carrier Name": "Error: No API token configured",
                "Entity Type": "CARRIER",
                "Operating Status": "NOT FOUND",
                "Phone Number": "—",
                "Email Address": "—",
                "Location": "—",
                "_found": False,
                "_raw": {}
            }

        params = {"type": "mc", "value": str(int(mc)).strip(), "token": token}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://carrierchk.com/",
            "Origin": "https://carrierchk.com"
        }

        # Aggressive exponential backoff with jitter
        last_status = None
        for attempt in range(5):
            try:
                r = http_session.get(api_url, params=params, headers=headers, timeout=15)
                last_status = r.status_code
                if r.status_code == 200:
                    break
                elif r.status_code == 429:
                    sleep_time = (2 ** attempt) + random.uniform(0.5, 2.0)
                    time.sleep(sleep_time)
                    continue
                elif r.status_code in [500, 502, 503, 504]:
                    # Server error — might be "not found" or overloaded
                    sleep_time = 1.0 + random.uniform(0.5, 1.5)
                    time.sleep(sleep_time)
                    continue
                else:
                    return {
                        "MC Number": f"MC-{mc:07d}",
                        "Carrier Name": f"HTTP {r.status_code}",
                        "Entity Type": "CARRIER",
                        "Operating Status": "NOT FOUND",
                        "Phone Number": "—",
                        "Email Address": "—",
                        "Location": "—",
                        "_found": False,
                        "_raw": {}
                    }
            except Exception as e:
                if attempt == 4:
                    return {
                        "MC Number": f"MC-{mc:07d}",
                        "Carrier Name": f"Error: {str(e)[:40]}",
                        "Entity Type": "CARRIER",
                        "Operating Status": "NOT FOUND",
                        "Phone Number": "—",
                        "Email Address": "—",
                        "Location": "—",
                        "_found": False,
                        "_raw": {}
                    }
                time.sleep(1 + random.uniform(0.5, 1.0))
        else:
            return {
                "MC Number": f"MC-{mc:07d}",
                "Carrier Name": f"Rate Limited ({last_status})" if last_status == 429 else f"Server Error ({last_status})",
                "Entity Type": "CARRIER",
                "Operating Status": "NOT FOUND",
                "Phone Number": "—",
                "Email Address": "—",
                "Location": "—",
                "_found": False,
                "_raw": {}
            }

        try:
            c = r.json()
        except Exception:
            return {
                "MC Number": f"MC-{mc:07d}",
                "Carrier Name": "Invalid JSON",
                "Entity Type": "CARRIER",
                "Operating Status": "NOT FOUND",
                "Phone Number": "—",
                "Email Address": "—",
                "Location": "—",
                "_found": False,
                "_raw": {}
            }

        data = c.get("carrier") or c.get("data") or c

        # Name
        name = _find_val(data, ["legal_name", "name", "company_name", "carrier_name", "dba_name", "doing_business_as"]) or "Unknown"

        # DOT
        dot = _find_val(data, ["usdot_number", "dot_number", "usdot", "dot"]) or "N/A"

        # Phone — AGGRESSIVE: any key containing "phone" or "tel"
        phone_candidates = _collect_all_by_key_part(data, "phone") + _collect_all_by_key_part(data, "tel")
        phone = "—"
        for p in phone_candidates:
            if p and str(p).strip() and str(p).strip() not in ("—", "", "None", "null"):
                phone = str(p).strip()
                break

        # Email — AGGRESSIVE: any key containing "email" or "mail"
        email_candidates = _collect_all_by_key_part(data, "email") + _collect_all_by_key_part(data, "mail")
        email = "—"
        for e in email_candidates:
            if e and str(e).strip() and "@" in str(e):
                email = str(e).strip()
                break

        # Location — AGGRESSIVE: any key containing "city" or "state"
        city_candidates = _collect_all_by_key_part(data, "city")
        state_candidates = _collect_all_by_key_part(data, "state")

        city = ""
        for c_val in city_candidates:
            if c_val and str(c_val).strip() and str(c_val).strip().lower() not in ("none", "null", "", "—"):
                city = str(c_val).strip()
                break

        state = ""
        for s_val in state_candidates:
            if s_val and str(s_val).strip() and str(s_val).strip().lower() not in ("none", "null", "", "—"):
                state = str(s_val).strip()
                break

        location = f"{city}, {state}".strip(", ") or "—"

        is_broker = _is_broker(data)
        status = _normalize_status(data)

        if is_broker:
            return {
                "MC Number": f"BROKER MC-{mc:07d}",
                "Broker Name": name,
                "Carrier Name": name,
                "Entity Type": "BROKER",
                "Operating Status": status,
                "Phone Number": phone,
                "Email Address": email,
                "Location": location,
                "USDOT": dot,
                "_found": True,
                "_raw": data
            }
        else:
            return {
                "MC Number": f"MC-{mc:07d}",
                "Carrier Name": name,
                "Broker Name": "",
                "Entity Type": "CARRIER",
                "Operating Status": status,
                "Phone Number": phone,
                "Email Address": email,
                "Location": location,
                "USDOT": dot,
                "_found": True,
                "_raw": data
            }


# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CarrierChk Pro",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State Initialization ──────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = []
if "scraping" not in st.session_state:
    st.session_state.scraping = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "current_mc" not in st.session_state:
    st.session_state.current_mc = 1800000
if "start_mc_val" not in st.session_state:
    st.session_state.start_mc_val = 1800000
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "login_time" not in st.session_state:
    st.session_state.login_time = 0.0


# ── Force Logout Helper ───────────────────────────────────────────────────────
def force_logout(reason: str = "Logged out."):
    if st.session_state.get("authenticated") and st.session_state.get("user_info"):
        username = st.session_state.user_info.get("username", "unknown")
        db.log_activity(username, "LOGOUT", f"Session terminated: {reason}")
    st.session_state["authenticated"] = False
    st.session_state["user_info"] = None
    st.session_state["login_time"] = 0.0
    st.session_state["logout_reason"] = reason
    st.rerun()


# ── Login Screen ──────────────────────────────────────────────────────────────
def _render_login_screen() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        """
        <style>
        .login-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(139,92,246,0.35);
            border-radius: 20px;
            padding: 44px 48px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.4);
            text-align: center;
            margin: 40px auto;
        }
        .login-icon  { font-size: 48px; margin-bottom: 8px; }
        .login-title { font-size: 24px; font-weight: 700; color: #f0f0f0; margin-bottom: 4px; }
        .login-sub   { font-size: 13px; color: #718096; margin-bottom: 24px; }
        .login-error {
            background: rgba(239,68,68,0.12);
            border: 1px solid rgba(239,68,68,0.35);
            border-radius: 8px;
            color: #fc8181;
            font-size: 13px;
            padding: 10px 14px;
            margin-top: 14px;
        }
        div[data-testid="stTextInput"] input {
            background: rgba(255,255,255,0.07) !important;
            border: 1px solid rgba(139,92,246,0.4) !important;
            border-radius: 10px !important;
            color: #f0f0f0 !important;
            font-size: 15px !important;
            padding: 12px 16px !important;
        }
        div[data-testid="stButton"] > button {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
            border: none !important; border-radius: 10px !important;
            color: white !important; font-weight: 700 !important;
            font-size: 15px !important; padding: 12px 0 !important;
            width: 100% !important;
            box-shadow: 0 4px 20px rgba(99,102,241,0.45) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 1.8, 1])
    with center:
        st.markdown(
            '<div class="login-card">'
            '<div class="login-icon">🔒</div>'
            '<div class="login-title">CarrierChk Pro Access</div>'
            '<div class="login-sub">Enter your credentials to sign in.</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        if st.session_state.get("logout_reason"):
            st.warning(st.session_state["logout_reason"])

        username = st.text_input("Username / Email", key="login_username", placeholder="Username")
        password = st.text_input("Password", type="password", key="login_password", placeholder="Password")
        login_btn = st.button("🔓 Sign In", key="login_btn")

        if login_btn:
            if not username or not password:
                st.markdown(
                    '<div class="login-error">⚠️ Please enter both username and password.</div>',
                    unsafe_allow_html=True,
                )
            else:
                success, msg, uinfo = db.authenticate_and_login(username, password)
                if success and uinfo:
                    st.session_state["authenticated"] = True
                    st.session_state["user_info"] = uinfo
                    st.session_state["login_time"] = time.time()
                    st.session_state["logout_reason"] = None
                    st.rerun()
                else:
                    st.markdown(
                        f'<div class="login-error">❌ {msg}</div>',
                        unsafe_allow_html=True,
                    )
    return False


if not _render_login_screen():
    st.stop()

# ── Session Lockout & Expiration Checks ───────────────────────────────────────
user_info = st.session_state.get("user_info") or {}
username = user_info.get("username", "User")
session_token = user_info.get("session_token", "")
session_duration_h = float(user_info.get("session_duration_hours", 3.0))

if not db.verify_active_session(username, session_token):
    force_logout("Session terminated: Account logged in from another tab or device.")

elapsed_sec = time.time() - st.session_state.get("login_time", time.time())
max_sec = session_duration_h * 3600.0
remaining_sec = max(0.0, max_sec - elapsed_sec)

if elapsed_sec >= max_sec:
    db.log_activity(username, "SESSION_TIMEOUT", f"Auto-locked after {session_duration_h} hours")
    force_logout(f"Session expired automatically after {session_duration_h:g} hours.")

# ── Global CSS Styling ────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        min-height: 100vh;
    }

    #MainMenu, footer { visibility: hidden; }
    div[data-testid="stHeader"] { background: transparent !important; }

    .header-banner {
        background: linear-gradient(90deg, rgba(99,102,241,0.15) 0%, rgba(139,92,246,0.10) 100%);
        border: 1px solid rgba(139,92,246,0.3);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .header-title {
        font-size: 28px;
        font-weight: 700;
        color: #f0f0f0;
        margin: 0;
    }

    .input-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 24px;
    }

    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] > div {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(139,92,246,0.4) !important;
        border-radius: 8px !important;
        color: #f0f0f0 !important;
        font-family: 'Inter', sans-serif !important;
    }

    div[data-testid="stNumberInput"] label,
    div[data-testid="stTextInput"] label,
    div[data-testid="stSelectbox"] label {
        color: #c0c0d0 !important;
        font-weight: 500 !important;
        font-size: 13px !important;
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        padding: 12px 24px !important;
        width: 100% !important;
        box-shadow: 0 4px 20px rgba(99,102,241,0.4) !important;
    }

    div[data-testid="stButton"] > button[kind="secondary"] {
        background: rgba(239,68,68,0.15) !important;
        border: 1px solid rgba(239,68,68,0.4) !important;
        border-radius: 10px !important;
        color: #fc8181 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 12px 20px !important;
        width: 100% !important;
    }

    div[data-testid="stTabs"] [role="tablist"] {
        background: rgba(255,255,255,0.04);
        border-radius: 12px;
        padding: 6px;
        gap: 4px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    div[data-testid="stTabs"] button[role="tab"] {
        border-radius: 8px !important;
        color: #a0aec0 !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        padding: 8px 18px !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: rgba(99,102,241,0.25) !important;
        color: #c7d2fe !important;
        border-bottom: 2px solid #6366f1 !important;
    }

    .stat-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 18px 20px;
        text-align: center;
    }
    .stat-value { font-size: 28px; font-weight: 700; color: #c7d2fe; }
    .stat-label { font-size: 12px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }

    .table-wrapper {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        overflow: hidden;
        margin-top: 16px;
    }
    .fmcsa-table { width: 100%; border-collapse: collapse; font-size: 13px; color: #e2e8f0; }
    .fmcsa-table thead tr { background: rgba(99,102,241,0.12); border-bottom: 1px solid rgba(99,102,241,0.3); }
    .fmcsa-table thead th { padding: 14px 16px; text-align: left; font-weight: 600; font-size: 12px; color: #a5b4fc; text-transform: uppercase; }
    .fmcsa-table tbody tr { border-bottom: 1px solid rgba(255,255,255,0.04); }
    .fmcsa-table tbody td { padding: 13px 16px; vertical-align: middle; }
    .mc-cell { font-family: monospace; font-weight: 600; color: #a5b4fc; }
    .name-cell { font-weight: 600; color: #f0f0f0; }
    .entity-badge { padding: 3px 10px; border-radius: 20px; font-size: 11px; background: rgba(99,102,241,0.2); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.3); }
    .entity-badge-broker { padding: 3px 10px; border-radius: 20px; font-size: 11px; background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
    .status-active { color: #68d391; font-weight: 600; }
    .status-inactive { color: #f6ad55; font-weight: 600; }
    .status-oos { color: #fc8181; font-weight: 600; }
    .status-dot-green { width:8px;height:8px;border-radius:50%;background:#48bb78;display:inline-block;margin-right:4px;}
    .status-dot-orange { width:8px;height:8px;border-radius:50%;background:#ed8936;display:inline-block;margin-right:4px;}
    .status-dot-red { width:8px;height:8px;border-radius:50%;background:#fc8181;display:inline-block;margin-right:4px;}

    .export-btn-wrap { margin-top: 24px; text-align: center; }
    .stDownloadButton > button {
        background: linear-gradient(135deg, #7c3aed 0%, #ec4899 100%) !important;
        border: none !important; border-radius: 14px !important; color: white !important;
        font-weight: 700 !important; font-size: 16px !important; padding: 16px 48px !important; width: 60% !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar Account & Admin Controls ──────────────────────────────────────────
with st.sidebar:
    st.markdown("### 👤 User Account")
    is_admin = user_info.get("is_admin", False)
    role_badge = "👑 Super Admin" if is_admin else "👤 Standard User"
    st.markdown(f"**User**: `{username}`")
    st.markdown(f"**Role**: `{role_badge}`")

    rem_min = int(remaining_sec // 60)
    st.caption(f"⏳ Session Expires in: **{rem_min} mins**")

    if st.button("🚪 Log Out", key="logout_btn"):
        force_logout("User clicked log out.")

    st.divider()

    if is_admin:
        st.markdown("### 🛡️ Admin Controls")
        admin_mode = st.radio(
            "Admin Actions",
            ["Dashboard", "👥 Manage Users", "⚙️ Rate & Session Limits", "📊 Activity Audit Logs"],
            key="admin_mode_select",
        )

        if admin_mode == "👥 Manage Users":
            st.subheader("Create New User")
            new_u = st.text_input("New Username", key="new_u_input")
            new_p = st.text_input("New Password", type="password", key="new_p_input")
            new_role = st.selectbox("Role", ["Standard User", "Super Admin"], key="new_role_input")
            if st.button("Create Account", key="create_user_btn"):
                is_adm = (new_role == "Super Admin")
                succ, msg = db.create_user(username, new_u, new_p, is_admin=is_adm)
                if succ:
                    st.success(msg)
                else:
                    st.error(msg)

        elif admin_mode == "⚙️ Rate & Session Limits":
            st.subheader("Configure Per-User Speed & Duration")
            all_users = db.get_all_users()
            u_names = [u["username"] for u in all_users]
            if not u_names:
                u_names = [username]
            if username not in u_names:
                u_names.append(username)

            sel_u = st.selectbox("Select User", u_names, key="sel_user_config")
            sel_u_data = next((u for u in all_users if u["username"] == sel_u), {})

            curr_delay = int(sel_u_data.get("delay_ms", user_info.get("delay_ms", 500)))
            curr_dur = float(sel_u_data.get("session_duration_hours", user_info.get("session_duration_hours", 3.0)))

            new_delay = st.number_input("Request Delay (ms)", min_value=0, max_value=10000, value=curr_delay, step=100, key="new_delay_in")
            new_dur = st.number_input("Session Timeout (hours)", min_value=0.5, max_value=72.0, value=curr_dur, step=0.5, key="new_dur_in")

            if st.button("Save User Config", key="save_u_cfg"):
                succ, msg = db.update_user_config(username, sel_u, new_delay, new_dur)
                if succ or sel_u == username:
                    if sel_u == username:
                        st.session_state["user_info"]["session_duration_hours"] = float(new_dur)
                        st.session_state["user_info"]["delay_ms"] = int(new_delay)
                    st.success(f"Updated config for '{sel_u}' successfully.")
                    st.rerun()
                else:
                    st.error(msg)

        elif admin_mode == "📊 Activity Audit Logs":
            st.subheader("Latest Activity Logs (Max 200)")
            logs_df = db.get_activity_logs(limit=200)
            st.dataframe(logs_df, use_container_width=True)


# ── Render Helper HTML Functions ──────────────────────────────────────────────
def status_badge(status: str) -> str:
    s = str(status).upper()
    if "INACTIVE" in s:
        return f'<span class="status-inactive"><span class="status-dot-orange"></span>INACTIVE</span>'
    elif "ACTIVE" in s:
        return f'<span class="status-active"><span class="status-dot-green"></span>ACTIVE</span>'
    elif "OUT" in s or "OOS" in s:
        return f'<span class="status-oos"><span class="status-dot-red"></span>OUT-OF-SERVICE</span>'
    elif "NOT FOUND" in s:
        return f'<span style="color:#4a5568;font-style:italic;">Not Found</span>'
    return f'<span style="color:#a0aec0;">{status}</span>'


def mc_cell_html(mc_str: str) -> str:
    if str(mc_str).startswith("BROKER "):
        parts = str(mc_str).split(" ", 1)
        return f'<span style="color:#fbbf24;font-weight:700;">{parts[0]}</span> <span class="mc-cell">{parts[1]}</span>'
    return f'<span class="mc-cell">{mc_str}</span>'


def email_cell_html(email: str) -> str:
    if email == "—" or not email:
        return '<span style="color:#4a5568;font-style:italic;font-size:12px;">—</span>'
    return f'<span style="color:#76e4f7;font-size:12px;">{email}</span>'


def render_table(rows: List[dict]) -> str:
    if not rows:
        return '<p style="color:#4a5568;text-align:center;padding:32px;">No data to display.</p>'

    header_cols = [
        "MC Number", "Carrier / Broker Name", "Entity Type",
        "Operating Status", "Phone Number", "Email Address", "Location"
    ]
    html = '<div class="table-wrapper"><table class="fmcsa-table"><thead><tr>'
    for col in header_cols:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"

    for row in rows:
        et = row.get("Entity Type", "CARRIER").upper()
        badge_cls = "entity-badge-broker" if "BROKER" in et else "entity-badge"
        name = row.get("Carrier Name", row.get("Broker Name", "—"))

        html += "<tr>"
        html += f'<td>{mc_cell_html(row.get("MC Number","—"))}</td>'
        html += f'<td class="name-cell">{name}</td>'
        html += f'<td><span class="{badge_cls}">{et}</span></td>'
        html += f'<td>{status_badge(row.get("Operating Status","—"))}</td>'
        html += f'<td style="color:#cbd5e0;font-size:13px;">{row.get("Phone Number","—")}</td>'
        html += f'<td>{email_cell_html(row.get("Email Address","—"))}</td>'
        html += f'<td style="color:#e2e8f0;font-size:13px;">{row.get("Location","—")}</td>'
        html += "</tr>"

    html += "</tbody></table></div>"
    return html


def df_from_results(rows: List[dict]) -> pd.DataFrame:
    cols = ["MC Number", "Carrier Name", "Entity Type",
            "Operating Status", "Phone Number", "Email Address", "Location"]
    clean = []
    for r in rows:
        item = {c: r.get(c, "—") for c in cols}
        if "Carrier Name" not in r and "Broker Name" in r:
            item["Carrier Name"] = r["Broker Name"]
        clean.append(item)
    return pd.DataFrame(clean, columns=cols)


def csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD UI
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="header-banner">
        <div style="font-size:40px;">🚛</div>
        <div>
            <p class="header-title">CarrierChk Pro — MC Scraper</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="input-card">', unsafe_allow_html=True)
col1, col_filter, col2, col3, col4 = st.columns([2.0, 1.5, 1.2, 1.0, 1.2])

with col1:
    start_mc = st.number_input(
        "Start MC Number",
        min_value=1,
        max_value=9999999,
        value=int(st.session_state.start_mc_val),
        step=1,
        format="%d",
        key="start_mc_input",
    )

with col_filter:
    entity_filter = st.selectbox(
        "Filter View",
        ["All Records", "Carriers Only", "Brokers Only"],
        key="entity_filter_select"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    scrape_btn = st.button("🔍 Start Scraping", type="primary", key="scrape_btn")

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    stop_btn = st.button("⛔ Stop", type="secondary", key="stop_btn")

with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    clear_btn = st.button("🗑️ Clear History", key="clear_btn")

st.markdown("</div>", unsafe_allow_html=True)

if scrape_btn:
    st.session_state.stop_requested = False
    st.session_state.current_mc = int(start_mc)
    st.session_state.start_mc_val = int(start_mc)
    st.session_state.scraping = True

if stop_btn:
    st.session_state.stop_requested = True
    st.session_state.start_mc_val = int(st.session_state.current_mc)

if clear_btn:
    st.session_state.results = []
    st.session_state.scraping = False
    st.session_state.stop_requested = False
    db.log_activity(username, "CLEAR_HISTORY", "User cleared all scraped history")
    st.rerun()

if st.session_state.scraping:
    status_text = st.empty()
    live_table = st.empty()
    count = len(st.session_state.results)

    while not st.session_state.stop_requested:
        mc = st.session_state.current_mc

        status_text.markdown(
            f'<p style="color:#a0aec0;font-size:13px;text-align:center;">🔄 Fetching <b style="color:#c7d2fe;">MC-{mc:07d}</b> &nbsp;·&nbsp; <b style="color:#68d391;">{count}</b> scraped so far</p>',
            unsafe_allow_html=True,
        )

        result = scrape_mc(mc)
        st.session_state.results.append(result)
        st.session_state.current_mc += 1
        count += 1

        preview = st.session_state.results[-10:]
        live_table.markdown(render_table(preview), unsafe_allow_html=True)

        user_delay = int(user_info.get("delay_ms", 500)) / 1000.0
        if user_delay > 0:
            time.sleep(user_delay)

    st.session_state.start_mc_val = int(st.session_state.current_mc)
    db.log_activity(username, "HARVEST_MC", f"Scraped batch up to MC-{st.session_state.current_mc:07d} ({count} total)")

    status_text.markdown(
        f'<p style="color:#68d391;font-size:13px;text-align:center;">⛔ Stopped at <b>MC-{st.session_state.current_mc:07d}</b> &nbsp;·&nbsp; <b>{count}</b> total scraped</p>',
        unsafe_allow_html=True,
    )
    st.session_state.scraping = False
    st.rerun()

results = st.session_state.results

# Apply entity filter
if entity_filter == "Carriers Only":
    filtered_results = [r for r in results if "BROKER" not in str(r.get("Entity Type", "")).upper() and "BROKER" not in str(r.get("MC Number", "")).upper()]
elif entity_filter == "Brokers Only":
    filtered_results = [r for r in results if "BROKER" in str(r.get("Entity Type", "")).upper() or "BROKER" in str(r.get("MC Number", "")).upper()]
else:
    filtered_results = results

found = [r for r in filtered_results if r.get("_found", False)]
active = [r for r in found if "ACTIVE" in r.get("Operating Status", "").upper() and "IN" not in r.get("Operating Status", "").upper()]
with_email = [r for r in active if r.get("Email Address", "—") not in ("—", "", None)]

if filtered_results:
    sc1, sc2, sc3, sc4 = st.columns(4)
    stats = [
        (len(filtered_results), "Total Scraped", "#c7d2fe"),
        (len(found), "Entities Found", "#68d391"),
        (len(active), "Active Entities", "#48bb78"),
        (len(with_email), "With Email", "#76e4f7"),
    ]
    for col, (val, label, color) in zip([sc1, sc2, sc3, sc4], stats):
        with col:
            st.markdown(
                f'<div class="stat-card">'
                f'<div class="stat-value" style="color:{color};">{val}</div>'
                f'<div class="stat-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋  Complete Master Log",
        "✅  Verified Leads (Active Only)",
        "📧  Raw Active Email List",
        "🔍  Debug API Response",
    ])

    with tab1:
        st.markdown(render_table(found if found else filtered_results), unsafe_allow_html=True)
        df_all = df_from_results(found if found else filtered_results)
        st.markdown('<div class="export-btn-wrap">', unsafe_allow_html=True)
        st.download_button(
            label="📥  Export Master Sheet to CSV",
            data=csv_bytes(df_all),
            file_name="carrierchk_master_log.csv",
            mime="text/csv",
            key="dl_master",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        if active:
            st.markdown(render_table(active), unsafe_allow_html=True)
            df_active = df_from_results(active)
            st.markdown('<div class="export-btn-wrap">', unsafe_allow_html=True)
            st.download_button(
                label="📥  Export Active Leads to CSV",
                data=csv_bytes(df_active),
                file_name="carrierchk_verified_leads.csv",
                mime="text/csv",
                key="dl_active",
            )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="color:#4a5568;text-align:center;padding:48px;font-size:15px;">'
                '🚫 No active records matching current selection. Run the scraper or adjust filters.</p>',
                unsafe_allow_html=True,
            )

    with tab3:
        if with_email:
            st.markdown(
                '<div class="table-wrapper" style="padding:0;">'
                + "".join(
                    f'<div style="padding:10px 16px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;">'
                    f'<div>'
                    f'<div style="color:#76e4f7;font-size:14px;">{r["Email Address"]}</div>'
                    f'<div style="color:#e2e8f0;font-size:12px;">{r.get("Carrier Name", r.get("Broker Name", "—"))} &nbsp;·&nbsp; {r["MC Number"]} &nbsp;·&nbsp; {r.get("Location", "—")}</div>'
                    f'</div>'
                    f'<div style="color:#718096;font-size:11px;">{r.get("Phone Number", "—")}</div>'
                    f'</div>'
                    for r in with_email
                )
                + "</div>",
                unsafe_allow_html=True,
            )
            df_email = df_from_results(with_email)
            st.markdown('<div class="export-btn-wrap">', unsafe_allow_html=True)
            st.download_button(
                label="📥  Export Email List to CSV",
                data=csv_bytes(df_email),
                file_name="carrierchk_email_list.csv",
                mime="text/csv",
                key="dl_email",
            )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="color:#4a5568;text-align:center;padding:48px;font-size:15px;">'
                '📧 No emails found yet. Active entities without emails won\'t appear here.</p>',
                unsafe_allow_html=True,
            )

    with tab4:
        st.markdown("<div class='input-card'>", unsafe_allow_html=True)
        debug_mc = st.text_input("Enter MC Number to Debug", placeholder="e.g. 1800003", key="debug_mc_input")
        if st.button("Fetch & Show Raw JSON", key="debug_btn"):
            if debug_mc:
                with st.spinner("Fetching..."):
                    token = st.secrets.get("CARRIER_TOKEN", CARRIER_TOKEN)
                    api_url = st.secrets.get("CARRIER_API_URL", CARRIER_API_URL)
                    params = {"type": "mc", "value": str(debug_mc).strip(), "token": token}
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Referer": "https://carrierchk.com/"
                    }
                    try:
                        r = http_session.get(api_url, params=params, headers=headers, timeout=15)
                        st.write(f"**Status Code:** {r.status_code}")
                        if r.status_code == 200:
                            data = r.json()
                            st.json(data)
                            # Also show what our parser extracted
                            inner = data.get("carrier") or data.get("data") or data
                            st.write("---")
                            st.write("**Parsed by our scraper:**")
                            cities = _collect_all_by_key_part(inner, "city")
                            states = _collect_all_by_key_part(inner, "state")
                            emails = _collect_all_by_key_part(inner, "email") + _collect_all_by_key_part(inner, "mail")
                            phones = _collect_all_by_key_part(inner, "phone") + _collect_all_by_key_part(inner, "tel")
                            st.write(f"Cities found: {cities}")
                            st.write(f"States found: {states}")
                            st.write(f"Emails found: {emails}")
                            st.write(f"Phones found: {phones}")
                        else:
                            st.error(f"HTTP {r.status_code}: {r.text[:500]}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown(
        """
        <div style="text-align:center;padding:72px 32px;">
            <div style="font-size:64px;margin-bottom:16px;">🚛</div>
            <h3 style="color:#e2e8f0;font-size:20px;margin-bottom:8px;">Ready to Scrape</h3>
            <p style="color:#718096;font-size:14px;max-width:400px;margin:0 auto;">
                Enter a start MC number above, then click <strong style="color:#a5b4fc;">Start Scraping</strong>.<br>
                Results appear in real-time as each carrier or broker is fetched.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
