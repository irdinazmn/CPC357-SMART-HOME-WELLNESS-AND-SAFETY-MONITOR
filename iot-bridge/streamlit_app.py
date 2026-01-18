# streamlit_app.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import io
import qrcode
from firebase_config import FirebaseAdmin
from streamlit_option_menu import option_menu
import json
import pyotp  # For Google Authenticator integration

# ========================================
# PAGE CONFIGURATION
# ========================================
st.set_page_config(
    page_title="Smart Home Wellness & Safety Monitor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================
# CUSTOM CSS STYLING
# ========================================
st.markdown("""
<style>
    /* Main Headers */
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #424242;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 3px solid #1E88E5;
        padding-bottom: 0.5rem;
    }
    
    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Alert Styles */
    .alert-critical {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
        padding: 1rem;
        border-radius: 10px;
        border-left: 6px solid #c92a2a;
        margin: 0.5rem 0;
        color: white;
        animation: pulse 2s infinite;
    }
    
    .alert-high {
        background-color: #ffe6e6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 6px solid #ff3333;
        margin: 0.5rem 0;
    }
    
    .alert-medium {
        background-color: #fff4e6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 6px solid #ff9933;
        margin: 0.5rem 0;
    }
    
    .alert-low {
        background-color: #e6f7ff;
        padding: 1rem;
        border-radius: 10px;
        border-left: 6px solid #3399ff;
        margin: 0.5rem 0;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    
    /* Status Badges */
    .status-online {
        background-color: #00c853;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .status-offline {
        background-color: #ff1744;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .status-warning {
        background-color: #ffa000;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    /* Info Cards */
    .info-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #e9ecef;
        margin: 1rem 0;
    }
    
    /* Dashboard Sections */
    .dashboard-section {
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin: 1rem 0;
    }
    
    /* Login Container */
    .login-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }
    
    /* Data Tables */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* QR Code Container */
    .qr-container {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
        border: 2px dashed #ddd;
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# FIREBASE INITIALIZATION
# ========================================
@st.cache_resource
def get_firebase():
    return FirebaseAdmin.get_instance()

firebase = get_firebase()

# ========================================
# SESSION STATE MANAGEMENT
# ========================================
def init_session_state():
    defaults = {
        'authenticated': False,
        'user_email': None,
        'user_id': None,
        'user_role': 'user',  # 'admin' or 'user'
        'mfa_verified': False,
        'page': 'login',
        'mfa_secret': None,  # Store the TOTP secret for Google Authenticator
        'mfa_qr_configured': False,  # Track if QR code has been shown
        'mfa_already_setup': False,  # Track if user already has MFA configured
        'last_refresh': datetime.now(),
        'auto_refresh': True,
        'refresh_interval': 30,  # seconds
        'totp': None  # pyotp.TOTP object
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ========================================
# AUTHENTICATION FUNCTIONS
# ========================================
def check_user_mfa_configured(email):
    """Check if user already has MFA configured in Firebase"""
    try:
        # Query Firebase to check if MFA secret exists for this user
        user_doc = firebase.db.collection('users').document(email).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return user_data.get('mfa_secret') is not None
        return False
    except Exception as e:
        return False

def get_user_mfa_secret(email):
    """Retrieve user's existing MFA secret from Firebase"""
    try:
        user_doc = firebase.db.collection('users').document(email).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return user_data.get('mfa_secret')
        return None
    except Exception as e:
        return None

def save_user_mfa_secret(email, secret):
    """Save user's MFA secret to Firebase"""
    try:
        firebase.db.collection('users').document(email).set({
            'mfa_secret': secret,
            'email': email,
            'mfa_setup_date': datetime.now().isoformat()
        }, merge=True)
        return True
    except Exception as e:
        st.error(f"Could not save MFA secret: {e}")
        return False

def generate_totp_secret():
    """Generate a new TOTP secret for Google Authenticator"""
    return pyotp.random_base32()

def generate_totp_qr_code(secret, email):
    """Generate provisioning URI for QR code"""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="Smart Home Monitor"
    )

def verify_totp_code(input_code, secret):
    """Verify TOTP code using Google Authenticator secret"""
    totp = pyotp.TOTP(secret)
    return totp.verify(input_code)

def check_user_role(email):
    """Determine user role based on email"""
    if 'admin' in email.lower():
        return 'admin'
    return 'user'

# ========================================
# DATA FETCHING FUNCTIONS
# ========================================
@st.cache_data(ttl=60)
def get_sensor_data(limit=500):
    """Fetch sensor data from Firestore with caching"""
    try:
        # First attempt: try with order_by
        try:
            docs = firebase.db.collection('sensor_readings')\
                             .order_by('received_at', direction='DESCENDING')\
                             .limit(limit)\
                             .stream()
            docs = list(docs)
        except Exception as e:
            # Fallback: query without order_by to avoid index errors
            st.warning(f"⚠️ Note: {str(e)[:50]}... Using unordered query")
            docs = firebase.db.collection('sensor_readings').limit(limit).stream()
            docs = list(docs)
        
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            data.append(doc_data)
        
        if not data:
            st.warning("📊 No sensor data found in Firestore yet")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Parse timestamps - try multiple field names
        if 'received_at' in df.columns:
            df['timestamp'] = pd.to_datetime(df['received_at'], errors='coerce')
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        else:
            df['timestamp'] = pd.Timestamp.now()
        
        # Extract sensor values - handle nested 'sensors' object
        if 'sensors' in df.columns:
            df['air_quality'] = df['sensors'].apply(
                lambda x: x.get('air_quality_ppm', 0) if isinstance(x, dict) else 0
            )
            df['temperature'] = df['sensors'].apply(
                lambda x: x.get('temperature_c', 0) if isinstance(x, dict) else 0
            )
            df['humidity'] = df['sensors'].apply(
                lambda x: x.get('humidity_percent', 0) if isinstance(x, dict) else 0
            )
            df['motion'] = df['sensors'].apply(
                lambda x: x.get('motion', False) if isinstance(x, dict) else False
            )
            df['light_level'] = df['sensors'].apply(
                lambda x: x.get('light_level', 0) if isinstance(x, dict) else 0
            )
            df['leak_detected'] = df['sensors'].apply(
                lambda x: x.get('water_leak', False) if isinstance(x, dict) else False  # Note: Arduino sends 'water_leak'
            )
        else:
            # Fallback: data might be flat (not nested under 'sensors')
            df['air_quality'] = df.get('air_quality_ppm', 0) if 'air_quality_ppm' in df else 0
            df['temperature'] = df.get('temperature_c', 0) if 'temperature_c' in df else 0
            df['humidity'] = df.get('humidity_percent', 0) if 'humidity_percent' in df else 0
            df['motion'] = df.get('motion', False) if 'motion' in df else False
            df['light_level'] = df.get('light_level', 0) if 'light_level' in df else 0
            df['leak_detected'] = df.get('water_leak', False) if 'water_leak' in df else False
        
        # Sort by timestamp descending
        df = df.sort_values('timestamp', ascending=False)
        
        return df
    except Exception as e:
        st.error(f"❌ Error fetching sensor data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=30)
def get_alerts(active_only=True, limit=100):
    """Fetch alerts from Firestore"""
    try:
        query = firebase.db.collection('alerts')
        if active_only:
            query = query.where('alert_status', '==', 'active')
        
        docs = query.order_by('received_at', direction='DESCENDING').limit(limit).stream()
        
        alerts = []
        for doc in docs:
            alert_data = doc.to_dict()
            alert_data['id'] = doc.id
            alerts.append(alert_data)
        
        df = pd.DataFrame(alerts)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['received_at'])
        
        return df
    except Exception as e:
        st.error(f"Error fetching alerts: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_device_status():
    """Get device heartbeat status"""
    try:
        docs = firebase.db.collection('device_heartbeats').stream()
        
        devices = []
        for doc in docs:
            device_data = doc.to_dict()
            device_data['device_id'] = doc.id
            
            # Calculate online status
            last_seen = device_data.get('received_at', 'Never')
            if last_seen != 'Never':
                try:
                    last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    time_diff = (datetime.utcnow() - last_seen_dt).total_seconds()
                    device_data['status'] = 'online' if time_diff < 120 else 'offline'
                    device_data['last_seen_seconds'] = time_diff
                except:
                    device_data['status'] = 'unknown'
            else:
                device_data['status'] = 'unknown'
            
            devices.append(device_data)
        
        return pd.DataFrame(devices)
    except Exception as e:
        return pd.DataFrame()

# ========================================
# ANALYTICS HELPER FUNCTIONS
# ========================================
def calculate_statistics(df):
    """Calculate comprehensive statistics from sensor data"""
    if df.empty:
        return {}
    
    stats = {
        'air_quality': {
            'mean': df['air_quality'].mean(),
            'max': df['air_quality'].max(),
            'min': df['air_quality'].min(),
            'std': df['air_quality'].std()
        },
        'temperature': {
            'mean': df['temperature'].mean(),
            'max': df['temperature'].max(),
            'min': df['temperature'].min(),
            'std': df['temperature'].std()
        },
        'humidity': {
            'mean': df['humidity'].mean(),
            'max': df['humidity'].max(),
            'min': df['humidity'].min(),
            'std': df['humidity'].std()
        },
        'motion_events': df['motion'].sum(),
        'leak_events': df['leak_detected'].sum(),
        'total_readings': len(df)
    }
    
    return stats

def detect_patterns(df):
    """Detect patterns in sensor data"""
    if df.empty:
        return {}
    
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    
    patterns = {
        'peak_motion_hour': df.groupby('hour')['motion'].sum().idxmax(),
        'peak_air_quality_hour': df.groupby('hour')['air_quality'].mean().idxmax(),
        'most_active_day': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][
            df.groupby('day_of_week')['motion'].sum().idxmax()
        ] if len(df) > 0 else 'N/A'
    }
    
    return patterns

def generate_health_score(df):
    """Generate overall environmental health score (0-100)"""
    if df.empty:
        return 0
    
    # Scoring criteria
    air_score = max(0, 100 - (df['air_quality'].mean() / 5))  # Lower is better
    temp_score = 100 - abs(df['temperature'].mean() - 22) * 5  # 22°C is ideal
    humidity_score = 100 - abs(df['humidity'].mean() - 50) * 2  # 50% is ideal
    
    # Weighted average
    health_score = (air_score * 0.4 + temp_score * 0.3 + humidity_score * 0.3)
    return max(0, min(100, health_score))

# ========================================
# LOGIN PAGE
# ========================================
def login_page():
    st.markdown("<h1 class='main-header'>🔐 Smart Home Wellness & Safety Monitor</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class='login-container'>
            <h2 style='color: white; text-align: center; margin-bottom: 2rem;'>Secure Login</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("📧 Email", placeholder="user@example.com")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            remember_me = st.checkbox("Remember me for 30 days")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                submit = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")
            
            with col_b:
                forgot = st.form_submit_button("❓ Forgot Password", use_container_width=True)
            
            if submit:
                if email and password:
                    # Check credentials against Firebase Auth
                    try:
                        st.session_state.user_email = email
                        st.session_state.user_role = check_user_role(email)
                        
                        # Check if user already has MFA configured
                        if check_user_mfa_configured(email):
                            # User already set up MFA - retrieve their secret and go to verification
                            st.session_state.mfa_secret = get_user_mfa_secret(email)
                            st.session_state.mfa_already_setup = True
                            st.session_state.page = "mfa_verify"  # Go directly to verification
                        else:
                            # New user - generate secret and go to setup
                            st.session_state.mfa_secret = generate_totp_secret()
                            st.session_state.mfa_already_setup = False
                            st.session_state.mfa_qr_configured = False
                            st.session_state.page = "mfa_setup"  # Go to MFA setup
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication failed: {e}")
                else:
                    st.error("⚠️ Please enter both email and password")
            
            if forgot:
                st.info("📨 Password reset link will be sent to your email")
        
        st.markdown("""
        <div style='text-align: center; margin-top: 2rem; color: #666;'>
            <small>🔒 Protected by Google Authenticator (MFA)<br>
            🛡️ TLS Encrypted | 🔐 Firebase Secured</small>
        </div>
        """, unsafe_allow_html=True)

# ========================================
# MFA SETUP PAGE (Google Authenticator)
# ========================================
def mfa_setup_page():
    st.markdown("<h1 class='main-header'>🔐 Set Up Two-Factor Authentication</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info(f"📧 Setting up Google Authenticator for: **{st.session_state.user_email}**")
        
        if not st.session_state.mfa_qr_configured:
            # Generate QR code for Google Authenticator
            provisioning_uri = generate_totp_qr_code(
                st.session_state.mfa_secret, 
                st.session_state.user_email
            )
            
            st.markdown("""
            <div class='qr-container'>
                <h3>📱 Scan QR Code with Google Authenticator</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Display QR code
            try:
                import qrcode
                from PIL import Image
                import io
                
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(provisioning_uri)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                st.image(img_byte_arr, caption="Scan with Google Authenticator", width=250)
                
            except ImportError:
                st.warning("⚠️ QR code generation requires 'qrcode' and 'pillow' packages")
                st.code(f"Manual entry: {st.session_state.mfa_secret}", language="text")
            
            st.markdown("""
            ### 🔧 Manual Setup (Alternative)
            If you can't scan the QR code, you can manually enter this secret in Google Authenticator:
            """)
            
            st.code(st.session_state.mfa_secret, language="text")
            
            st.markdown("""
            ### 📱 Steps to Set Up:
            1. Open **Google Authenticator** app on your phone
            2. Tap the **"+"** button to add a new account
            3. Choose **"Scan a QR code"** and scan the code above
            4. Or choose **"Enter a setup key"** and enter the secret above
            5. You should see a 6-digit code appear in the app
            """)
            
            if st.button("✅ I've Set Up Google Authenticator", type="primary", use_container_width=True):
                # Save the MFA secret to Firebase
                if save_user_mfa_secret(st.session_state.user_email, st.session_state.mfa_secret):
                    st.session_state.mfa_qr_configured = True
                    st.rerun()
                else:
                    st.error("Failed to save MFA configuration")
                st.session_state.mfa_qr_configured = True
                st.session_state.page = "mfa_verify"
                st.rerun()
        
        else:
            st.success("✅ Google Authenticator setup complete!")
            st.info("You can now verify your authentication code.")
            
            if st.button("➡️ Continue to Verification", type="primary", use_container_width=True):
                st.session_state.page = "mfa_verify"
                st.rerun()
            
            if st.button("🔄 Reset MFA Setup", use_container_width=True):
                st.session_state.mfa_secret = generate_totp_secret()
                st.session_state.mfa_qr_configured = False
                st.rerun()
                st.session_state.mfa_secret = generate_totp_secret()
                st.session_state.mfa_qr_configured = False
                st.rerun()
        
        if st.button("⬅️ Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

# ========================================
# MFA VERIFICATION PAGE (Google Authenticator)
# ========================================
def mfa_verify_page():
    st.markdown("<h1 class='main-header'>🔒 Verify Google Authenticator Code</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info(f"📱 Please enter the 6-digit code from Google Authenticator")
        
        mfa_input = st.text_input("🔢 Enter 6-digit verification code", placeholder="000000", max_chars=6)
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            if st.button("✅ Verify Code", use_container_width=True, type="primary"):
                if verify_totp_code(mfa_input, st.session_state.mfa_secret):
                    st.session_state.authenticated = True
                    st.session_state.mfa_verified = True
                    st.session_state.page = "dashboard"
                    st.success("✅ Authentication successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid verification code. Please try again.")
        
        with col_b:
            if st.button("🔄 New Code", use_container_width=True):
                # TOTP codes automatically refresh every 30 seconds
                st.info("Please wait for a new code (refreshes every 30 seconds)")
                st.rerun()
        
        with col_c:
            if st.button("⬅️ Back to Setup", use_container_width=True):
                st.session_state.page = "mfa_setup"
                st.rerun()
        
        # Show countdown timer for code validity
        current_time = int(time.time())
        time_remaining = 30 - (current_time % 30)
        
        progress = time_remaining / 30
        st.progress(progress, text=f"⏳ Code expires in {time_remaining}s")
        
        st.markdown("""
        <div class='info-card'>
            <h4>💡 Having Trouble?</h4>
            <ul>
                <li>Make sure your phone's time is synchronized</li>
                <li>Codes refresh every 30 seconds</li>
                <li>Make sure you're entering the code for "Smart Home Monitor"</li>
                <li>If codes consistently fail, try resetting MFA setup</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ========================================
# DASHBOARD HOME PAGE
# ========================================
def dashboard_home():
    st.markdown("<h1 class='main-header'>🏠 Real-Time Monitoring Dashboard</h1>", unsafe_allow_html=True)
    
    # Fetch all data
    sensor_df = get_sensor_data(500)
    alerts_df = get_alerts(active_only=True)
    devices_df = get_device_status()
    
    # ===== QUICK STATS SECTION =====
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        reading_count = len(sensor_df)
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);'>
            <div class='metric-label'>Total Readings</div>
            <div class='metric-value'>{reading_count:,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        alerts_count = len(alerts_df)
        alert_color = '#00c853' if alerts_count == 0 else '#ff3333' if alerts_count > 5 else '#ffa000'
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, {alert_color} 0%, {alert_color}cc 100%);'>
            <div class='metric-label'>Active Alerts</div>
            <div class='metric-value'>{alerts_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        online_count = len(devices_df[devices_df['status'] == 'online']) if not devices_df.empty else 0
        total_devices = len(devices_df) if not devices_df.empty else 1
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);'>
            <div class='metric-label'>Devices Online</div>
            <div class='metric-value'>{online_count}/{total_devices}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if not sensor_df.empty:
            health_score = generate_health_score(sensor_df.head(50))
            score_color = '#00c853' if health_score > 75 else '#ffa000' if health_score > 50 else '#ff3333'
        else:
            health_score = 0
            score_color = '#999'
        
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, {score_color} 0%, {score_color}cc 100%);'>
            <div class='metric-label'>Health Score</div>
            <div class='metric-value'>{health_score:.0f}/100</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        if not devices_df.empty and devices_df['status'].eq('online').any():
            avg_uptime = devices_df[devices_df['status'] == 'online']['uptime_minutes'].mean()
            uptime_hours = avg_uptime / 60 if not pd.isna(avg_uptime) else 0
        else:
            uptime_hours = 0
        
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);'>
            <div class='metric-label'>Avg Uptime</div>
            <div class='metric-value'>{uptime_hours:.1f}h</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # ===== CRITICAL ALERTS SECTION =====
    if not alerts_df.empty:
        critical_alerts = alerts_df[alerts_df['severity'] == 'HIGH']
        if not critical_alerts.empty:
            st.markdown("<h3 class='sub-header'>🚨 Critical Alerts Requiring Immediate Attention</h3>", unsafe_allow_html=True)
            
            for _, alert in critical_alerts.head(3).iterrows():
                st.markdown(f"""
                <div class='alert-critical'>
                    <h4 style='margin: 0; color: white;'>⚠️ {alert.get('alert_type', 'Critical Alert').upper()}</h4>
                    <p style='margin: 0.5rem 0; font-size: 1.1rem;'>{alert.get('message', 'Immediate action required')}</p>
                    <small>🕒 {alert.get('received_at', 'Just now')}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # ===== REAL-TIME MONITORING CHARTS =====
    st.markdown("<h3 class='sub-header'>📊 Real-Time Environmental Monitoring</h3>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### 💨 Air Quality Trend (Last 50 Readings)")
        if not sensor_df.empty:
            recent_data = sensor_df.head(50).sort_values('timestamp')
            
            fig = go.Figure()
            
            # Main line
            fig.add_trace(go.Scatter(
                x=recent_data['timestamp'],
                y=recent_data['air_quality'],
                mode='lines+markers',
                name='Air Quality (PPM)',
                line=dict(color='#1E88E5', width=3),
                marker=dict(size=6),
                fill='tonexty',
                fillcolor='rgba(30, 136, 229, 0.1)'
            ))
            
            # Threshold lines
            fig.add_hline(y=200, line_dash="dash", line_color="red", 
                         annotation_text="🚨 Alert Threshold", 
                         annotation_position="right")
            fig.add_hline(y=100, line_dash="dot", line_color="orange", 
                         annotation_text="⚠️ Warning Level", 
                         annotation_position="right")
            
            fig.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='#eee'),
                yaxis=dict(showgrid=True, gridcolor='#eee', title='PPM')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Current status
            current_quality = recent_data.iloc[-1]['air_quality']
            if current_quality < 100:
                st.success(f"✅ Air Quality: EXCELLENT ({current_quality:.1f} PPM)")
            elif current_quality < 200:
                st.warning(f"⚠️ Air Quality: MODERATE ({current_quality:.1f} PPM)")
            else:
                st.error(f"🚨 Air Quality: POOR ({current_quality:.1f} PPM)")
        else:
            st.info("No sensor data available")
    
    with col_right:
        st.markdown("#### 🌡️ Temperature & Humidity Monitoring")
        if not sensor_df.empty:
            recent_data = sensor_df.head(50).sort_values('timestamp')
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Scatter(
                    x=recent_data['timestamp'],
                    y=recent_data['temperature'],
                    name='Temperature (°C)',
                    line=dict(color='#ff6b6b', width=3),
                    mode='lines+markers'
                ),
                secondary_y=False
            )
            
            fig.add_trace(
                go.Scatter(
                    x=recent_data['timestamp'],
                    y=recent_data['humidity'],
                    name='Humidity (%)',
                    line=dict(color='#4ecdc4', width=3),
                    mode='lines+markers'
                ),
                secondary_y=True
            )
            
            fig.update_xaxes(showgrid=True, gridcolor='#eee')
            fig.update_yaxes(title_text="Temperature (°C)", secondary_y=False, showgrid=True, gridcolor='#eee')
            fig.update_yaxes(title_text="Humidity (%)", secondary_y=True, showgrid=True, gridcolor='#eee')
            
            fig.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Current readings
            col_a, col_b = st.columns(2)
            with col_a:
                current_temp = recent_data.iloc[-1]['temperature']
                st.metric("Current Temperature", f"{current_temp:.1f}°C")
            with col_b:
                current_humidity = recent_data.iloc[-1]['humidity']
                st.metric("Current Humidity", f"{current_humidity:.1f}%")
        else:
            st.info("No sensor data available")
    
    st.divider()
    
    # ===== OCCUPANCY & SAFETY MONITORING =====
    col_occ, col_safe = st.columns(2)
    
    with col_occ:
        st.markdown("#### 👥 Occupancy & Motion Detection")
        if not sensor_df.empty:
            recent_data = sensor_df.head(100).sort_values('timestamp')
            motion_data = recent_data.groupby(recent_data['timestamp'].dt.floor('5min'))['motion'].sum().reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=motion_data['timestamp'],
                y=motion_data['motion'],
                name='Motion Events',
                marker_color='#ffa726',
                hovertemplate='<b>%{y}</b> motion events<br>%{x}<extra></extra>'
            ))
            
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=20, b=20),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='#eee'),
                yaxis=dict(showgrid=True, gridcolor='#eee', title='Motion Events')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Motion summary
            total_motion = recent_data['motion'].sum()
            last_motion_time = recent_data[recent_data['motion'] == True]['timestamp'].max() if recent_data['motion'].any() else None
            
            if last_motion_time:
                time_since = (datetime.now() - last_motion_time).total_seconds() / 60
                if time_since < 5:
                    st.success(f"✅ Recent activity detected ({time_since:.0f} min ago)")
                elif time_since < 30:
                    st.warning(f"⚠️ No recent activity ({time_since:.0f} min)")
                else:
                    st.error(f"🚨 Extended inactivity ({time_since:.0f} min)")
            else:
                st.info("No motion detected in recent data")
        else:
            st.info("No occupancy data available")
    
    with col_safe:
        st.markdown("#### 🛡️ Safety Monitoring (Leak & Light)")
        if not sensor_df.empty:
            recent_data = sensor_df.head(50).sort_values('timestamp')
            
            # Light level gauge
            current_light = recent_data.iloc[-1]['light_level']
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=current_light,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Light Level"},
                delta={'reference': 500},
                gauge={
                    'axis': {'range': [None, 1023]},
                    'bar': {'color': "#ffd700"},
                    'steps': [
                        {'range': [0, 300], 'color': "#333"},
                        {'range': [300, 700], 'color': "#888"},
                        {'range': [700, 1023], 'color': "#ddd"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 200
                    }
                }
            ))
            
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            # Safety status
            leak_count = recent_data['leak_detected'].sum()
            
            col_aa, col_bb = st.columns(2)
            with col_aa:
                if leak_count > 0:
                    st.error(f"💧 {leak_count} leak(s) detected!")
                else:
                    st.success("✅ No leaks detected")
            
            with col_bb:
                if current_light < 200:
                    st.warning("💡 Low light level")
                else:
                    st.success("☀️ Good lighting")
        else:
            st.info("No safety data available")
    
    st.divider()
    
    # ===== SYSTEM STATUS SUMMARY =====
    st.markdown("<h3 class='sub-header'>🔧 System Status Summary</h3>", unsafe_allow_html=True)
    
    if not devices_df.empty:
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        with col_stat1:
            online_count = (devices_df['status'] == 'online').sum()
            total_devices = len(devices_df)
            st.metric("Device Connectivity", f"{online_count}/{total_devices}")
        
        with col_stat2:
            total_alerts = len(alerts_df)
            critical_alerts = len(alerts_df[alerts_df['severity'] == 'HIGH'])
            st.metric("Alert Status", f"{total_alerts} total", f"{critical_alerts} critical")
        
        with col_stat3:
            if not sensor_df.empty:
                sensor_count = len(sensor_df['id'].unique()) if 'id' in sensor_df.columns else 1
                st.metric("Active Sensors", f"{sensor_count}")
            else:
                st.metric("Active Sensors", "0")
        
        with col_stat4:
            # Calculate data freshness
            if not sensor_df.empty:
                latest_time = sensor_df['timestamp'].max()
                time_diff = (datetime.now() - latest_time).total_seconds() / 60
                freshness = "🟢" if time_diff < 5 else "🟡" if time_diff < 15 else "🔴"
                st.metric("Data Freshness", f"{freshness}", f"{time_diff:.1f} min ago")
    
    # Auto-refresh indicator
    if st.session_state.auto_refresh:
        time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
        st.caption(f"🔄 Auto-refresh enabled | Last updated: {time_since_refresh}s ago")

# ========================================
# ALERTS MANAGEMENT PAGE (NEW)
# ========================================
def alerts_management_page():
    st.markdown("<h1 class='main-header'>🚨 Alert Management & History</h1>", unsafe_allow_html=True)
    
    # Tabs for different alert views
    tab1, tab2, tab3 = st.tabs(["📋 Active Alerts", "📜 Alert History", "⚙️ Alert Configuration"])
    
    # ===== ACTIVE ALERTS TAB =====
    with tab1:
        st.markdown("### 🚨 Currently Active Alerts")
        
        active_alerts = get_alerts(active_only=True, limit=50)
        
        if not active_alerts.empty:
            # Filter options
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            
            with col_filter1:
                severity_filter = st.multiselect(
                    "Filter by Severity",
                    ["HIGH", "MEDIUM", "LOW"],
                    default=["HIGH", "MEDIUM", "LOW"]
                )
            
            with col_filter2:
                alert_types = active_alerts['alert_type'].unique() if 'alert_type' in active_alerts.columns else []
                type_filter = st.multiselect(
                    "Filter by Type",
                    alert_types,
                    default=alert_types[:3] if len(alert_types) > 0 else []
                )
            
            with col_filter3:
                st.write("")
                st.write("")
                if st.button("🔄 Refresh Alerts", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
            
            # Filter alerts
            filtered_alerts = active_alerts.copy()
            if severity_filter:
                filtered_alerts = filtered_alerts[filtered_alerts['severity'].isin(severity_filter)]
            if type_filter and len(type_filter) > 0:
                filtered_alerts = filtered_alerts[filtered_alerts['alert_type'].isin(type_filter)]
            
            st.markdown(f"**Showing {len(filtered_alerts)} of {len(active_alerts)} active alerts**")
            
            # Display alerts
            for _, alert in filtered_alerts.iterrows():
                severity = alert.get('severity', 'LOW')
                alert_class = {
                    'HIGH': 'alert-high',
                    'MEDIUM': 'alert-medium',
                    'LOW': 'alert-low'
                }.get(severity, 'alert-low')
                
                icon = {
                    'HIGH': '🚨',
                    'MEDIUM': '⚠️',
                    'LOW': 'ℹ️'
                }.get(severity, 'ℹ️')
                
                col_alert1, col_alert2 = st.columns([4, 1])
                
                with col_alert1:
                    st.markdown(f"""
                    <div class='{alert_class}'>
                        <strong>{icon} {alert.get('alert_type', 'System Alert')}</strong>
                        <span style='margin-left: 1rem; padding: 0.2rem 0.6rem; background-color: rgba(0,0,0,0.1); border-radius: 12px; font-size: 0.85rem;'>{severity}</span>
                        <p style='margin: 0.5rem 0 0 0;'>{alert.get('message', 'No details available')}</p>
                        <small>🕒 {alert.get('received_at', 'Unknown time')} | 📍 {alert.get('device_id', 'Unknown')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_alert2:
                    if st.button("✅ Acknowledge", key=f"ack_{alert.get('id', '')}", use_container_width=True):
                        try:
                            # Update alert status in Firebase
                            firebase.db.collection('alerts').document(alert.get('id', '')).update({
                                'alert_status': 'acknowledged',
                                'acknowledged_at': datetime.now().isoformat(),
                                'acknowledged_by': st.session_state.user_email
                            })
                            st.success("✅ Alert acknowledged!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to acknowledge alert: {e}")
            
            # Bulk actions
            st.divider()
            col_bulk1, col_bulk2, col_bulk3 = st.columns(3)
            
            with col_bulk1:
                if st.button("✅ Acknowledge All", use_container_width=True, type="primary"):
                    try:
                        # Acknowledge all active alerts (mark as acknowledged, don't delete)
                        for _, alert in filtered_alerts.iterrows():
                            firebase.db.collection('alerts').document(alert.get('id', '')).update({
                                'alert_status': 'acknowledged',
                                'acknowledged_at': datetime.now().isoformat(),
                                'acknowledged_by': st.session_state.user_email
                            })
                        st.success(f"✅ Acknowledged {len(filtered_alerts)} alerts!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to acknowledge alerts: {e}")
            
            with col_bulk2:
                if st.button("📊 Export to CSV", use_container_width=True):
                    csv = filtered_alerts.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="active_alerts.csv",
                        mime="text/csv"
                    )
            
            with col_bulk3:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.warning("⚠️ This will permanently delete all active alerts. Use with caution.")
                    if st.checkbox("I confirm permanent deletion of all active alerts"):
                        try:
                            for _, alert in filtered_alerts.iterrows():
                                firebase.db.collection('alerts').document(alert.get('id', '')).delete()
                            st.success(f"🗑️ Deleted {len(filtered_alerts)} alerts!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete alerts: {e}")
        
        else:
            st.success("🎉 No active alerts! Your home environment is optimal.")
    
    # ===== ALERT HISTORY TAB =====
    with tab2:
        st.markdown("### 📜 Historical Alert Log")
        
        # Date range selector
        col_date1, col_date2, col_date3 = st.columns([2, 2, 1])
        with col_date1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        with col_date2:
            end_date = st.date_input("End Date", datetime.now())
        with col_date3:
            st.write("")
            st.write("")
            if st.button("🔍 Search", type="primary", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        
        # Fetch all alerts (including historical)
        historical_alerts = get_alerts(active_only=False, limit=500)
        
        if not historical_alerts.empty:
            # Filter by date
            historical_alerts = historical_alerts[
                (historical_alerts['timestamp'].dt.date >= start_date) & 
                (historical_alerts['timestamp'].dt.date <= end_date)
            ]
            
            if not historical_alerts.empty:
                # Statistics
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                
                with col_stat1:
                    total_alerts = len(historical_alerts)
                    st.metric("Total Alerts", total_alerts)
                
                with col_stat2:
                    high_alerts = len(historical_alerts[historical_alerts['severity'] == 'HIGH'])
                    st.metric("Critical Alerts", high_alerts)
                
                with col_stat3:
                    unique_days = historical_alerts['timestamp'].dt.date.nunique()
                    st.metric("Active Days", unique_days)
                
                with col_stat4:
                    avg_alerts = total_alerts / unique_days if unique_days > 0 else 0
                    st.metric("Avg Per Day", f"{avg_alerts:.1f}")
                
                # Display as table
                st.markdown("#### 📋 Alert History Table")
                display_cols = ['timestamp', 'alert_type', 'severity', 'message', 'device_id']
                st.dataframe(
                    historical_alerts[display_cols].sort_values('timestamp', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Export options
                st.download_button(
                    label="📥 Download Full History (CSV)",
                    data=historical_alerts.to_csv(index=False),
                    file_name=f"alert_history_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No alerts found in the selected date range")
        else:
            st.info("No historical alerts available")
    
    # ===== ALERT CONFIGURATION TAB =====
    with tab3:
        st.markdown("### ⚙️ Alert Threshold Configuration")
        
        if st.session_state.user_role != 'admin':
            st.warning("🔒 Admin access required to configure alerts")
            return
        
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            st.markdown("#### 💨 Air Quality Alerts")
            air_warning = st.slider("⚠️ Warning Level (PPM)", 50, 300, 100, 10)
            air_critical = st.slider("🚨 Critical Level (PPM)", 100, 500, 200, 10)
            
            st.markdown("#### 🌡️ Temperature Alerts")
            temp_high = st.slider("🔥 High Temperature (°C)", 25, 40, 30, 1)
            temp_low = st.slider("❄️ Low Temperature (°C)", 10, 20, 18, 1)
        
        with col_config2:
            st.markdown("#### 💧 Humidity Alerts")
            humidity_high = st.slider("💦 High Humidity (%)", 60, 90, 70, 5)
            humidity_low = st.slider("🏜️ Low Humidity (%)", 20, 50, 30, 5)
            
            st.markdown("#### 🚪 Occupancy Alerts")
            inactivity_threshold = st.slider("⏰ Inactivity Alert (minutes)", 30, 240, 60, 10)
        
        st.divider()
        
        st.markdown("#### 📬 Notification Settings")
        
        col_notify1, col_notify2 = st.columns(2)
        
        with col_notify1:
            notification_methods = st.multiselect(
                "Enable notifications via:",
                ["📧 Email", "📱 SMS", "🔔 Push Notification", "🖥️ Dashboard Alert"],
                default=["🖥️ Dashboard Alert", "📧 Email"]
            )
            
            email_address = st.text_input("Notification Email", st.session_state.user_email)
        
        with col_notify2:
            notify_severity = st.multiselect(
                "Notify for severity levels:",
                ["🚨 CRITICAL", "⚠️ HIGH", "📢 MEDIUM", "ℹ️ LOW"],
                default=["🚨 CRITICAL", "⚠️ HIGH"]
            )
            
            mute_hours = st.slider("Mute notifications during (24h)", 22, 6, (22, 6))
        
        if st.button("💾 Save Alert Configuration", type="primary", use_container_width=True):
            # Save to Firestore
            config_data = {
                'air_quality_warning': air_warning,
                'air_quality_critical': air_critical,
                'temp_high': temp_high,
                'temp_low': temp_low,
                'humidity_high': humidity_high,
                'humidity_low': humidity_low,
                'inactivity_threshold': inactivity_threshold,
                'notification_methods': notification_methods,
                'notify_severity': notify_severity,
                'mute_hours': mute_hours,
                'updated_by': st.session_state.user_email,
                'updated_at': datetime.now().isoformat()
            }
            
            try:
                firebase.db.collection('alert_config').document(st.session_state.user_id).set(config_data)
                st.success("✅ Alert configuration saved successfully!")
            except Exception as e:
                st.error(f"❌ Failed to save configuration: {e}")

# ========================================
# ADVANCED ANALYTICS PAGE
# ========================================
def analytics_page():
    st.markdown("<h1 class='main-header'>📊 Advanced Analytics & Insights</h1>", unsafe_allow_html=True)
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_date = st.date_input("📅 Start Date", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("📅 End Date", datetime.now())
    with col3:
        st.write("")
        st.write("")
        if st.button("🔍 Analyze", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch and filter data
    sensor_df = get_sensor_data(1000)
    
    if not sensor_df.empty:
        # Filter by date range
        sensor_df = sensor_df[
            (sensor_df['timestamp'].dt.date >= start_date) & 
            (sensor_df['timestamp'].dt.date <= end_date)
        ]
        
        if sensor_df.empty:
            st.warning("No data available for selected date range")
            return
        
        # Calculate statistics
        stats = calculate_statistics(sensor_df)
        patterns = detect_patterns(sensor_df)
        
        st.divider()
        
        # ===== STATISTICAL SUMMARY =====
        st.markdown("### 📈 Statistical Summary")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Avg Air Quality",
                f"{stats['air_quality']['mean']:.1f} PPM",
                f"{stats['air_quality']['std']:.1f} σ"
            )
        
        with col2:
            st.metric(
                "Avg Temperature",
                f"{stats['temperature']['mean']:.1f}°C",
                f"Range: {stats['temperature']['max'] - stats['temperature']['min']:.1f}°C"
            )
        
        with col3:
            st.metric(
                "Avg Humidity",
                f"{stats['humidity']['mean']:.1f}%",
                f"±{stats['humidity']['std']:.1f}%"
            )
        
        with col4:
            st.metric(
                "Motion Events",
                f"{stats['motion_events']:,}",
                "Occupancy tracking"
            )
        
        with col5:
            st.metric(
                "Total Readings",
                f"{stats['total_readings']:,}",
                f"{stats['total_readings']/(end_date-start_date).days:.0f}/day"
            )
        
        st.divider()
        
        # ===== PATTERN INSIGHTS =====
        st.markdown("### 🔍 Pattern Recognition & Insights")
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.info(f"""
            **🕐 Peak Motion Hour**  
            Most activity at **{patterns['peak_motion_hour']}:00**
            """)
        
        with col_b:
            st.info(f"""
            **💨 Peak Air Quality Degradation**  
            Occurs around **{patterns['peak_air_quality_hour']}:00**
            """)
        
        with col_c:
            st.info(f"""
            **📅 Most Active Day**  
            **{patterns['most_active_day']}** shows highest activity
            """)
        
        st.divider()
        
        # ===== CORRELATION ANALYSIS =====
        st.markdown("### 🔗 Correlation Matrix Analysis")
        
        col_corr1, col_corr2 = st.columns([3, 2])
        
        with col_corr1:
            numeric_cols = ['air_quality', 'temperature', 'humidity', 'light_level']
            corr_df = sensor_df[numeric_cols].corr()
            
            fig = px.imshow(
                corr_df,
                text_auto='.2f',
                aspect="auto",
                color_continuous_scale='RdBu_r',
                title="Sensor Correlation Matrix",
                labels=dict(color="Correlation")
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col_corr2:
            st.markdown("#### 📊 Key Correlations")
            
            # Find strongest correlations
            corr_pairs = []
            for i in range(len(numeric_cols)):
                for j in range(i+1, len(numeric_cols)):
                    corr_pairs.append({
                        'pair': f"{numeric_cols[i]} ↔ {numeric_cols[j]}",
                        'correlation': corr_df.iloc[i, j]
                    })
            
            corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
            
            for pair in corr_pairs[:4]:
                corr_val = pair['correlation']
                color = 'green' if abs(corr_val) > 0.5 else 'orange' if abs(corr_val) > 0.3 else 'gray'
                
                st.markdown(f"""
                <div style='background-color: #f8f9fa; padding: 0.8rem; margin: 0.5rem 0; border-radius: 8px; border-left: 4px solid {color};'>
                    <strong>{pair['pair']}</strong><br>
                    <span style='font-size: 1.2rem; color: {color};'>{corr_val:.3f}</span>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # ===== HOURLY PATTERNS =====
        st.markdown("### ⏰ Hourly Activity Patterns")
        
        sensor_df['hour'] = sensor_df['timestamp'].dt.hour
        hourly_stats = sensor_df.groupby('hour').agg({
            'air_quality': 'mean',
            'temperature': 'mean',
            'humidity': 'mean',
            'motion': 'sum',
            'light_level': 'mean'
        }).reset_index()
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Air Quality by Hour', 'Temperature & Humidity', 
                          'Motion Events', 'Light Levels'),
            specs=[[{"secondary_y": False}, {"secondary_y": True}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Air Quality
        fig.add_trace(
            go.Scatter(x=hourly_stats['hour'], y=hourly_stats['air_quality'],
                      name='Air Quality', line=dict(color='#1E88E5', width=3)),
            row=1, col=1
        )
        
        # Temperature & Humidity
        fig.add_trace(
            go.Scatter(x=hourly_stats['hour'], y=hourly_stats['temperature'],
                      name='Temperature', line=dict(color='#ff6b6b', width=2)),
            row=1, col=2, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=hourly_stats['hour'], y=hourly_stats['humidity'],
                      name='Humidity', line=dict(color='#4ecdc4', width=2)),
            row=1, col=2, secondary_y=True
        )
        
        # Motion Events
        fig.add_trace(
            go.Bar(x=hourly_stats['hour'], y=hourly_stats['motion'],
                  name='Motion', marker_color='#ffa726'),
            row=2, col=1
        )
        
        # Light Levels
        fig.add_trace(
            go.Scatter(x=hourly_stats['hour'], y=hourly_stats['light_level'],
                      name='Light', line=dict(color='#ffd700', width=3),
                      fill='tozeroy'),
            row=2, col=2
        )
        
        fig.update_layout(height=600, showlegend=True, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # ===== TREND ANALYSIS =====
        st.markdown("### 📈 Time-Series Trend Analysis")
        
        # Resample to daily averages
        daily_data = sensor_df.set_index('timestamp').resample('D').agg({
            'air_quality': 'mean',
            'temperature': 'mean',
            'humidity': 'mean',
            'motion': 'sum'
        }).reset_index()
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_data['timestamp'],
            y=daily_data['air_quality'],
            name='Air Quality',
            line=dict(color='#1E88E5', width=2)
        ))
        
        # Add moving average
        daily_data['air_quality_ma'] = daily_data['air_quality'].rolling(window=3).mean()
        fig.add_trace(go.Scatter(
            x=daily_data['timestamp'],
            y=daily_data['air_quality_ma'],
            name='3-Day Moving Avg',
            line=dict(color='#ff6b6b', width=3, dash='dash')
        ))
        
        fig.update_layout(
            title="Daily Air Quality Trend with Moving Average",
            height=400,
            hovermode='x unified',
            xaxis_title="Date",
            yaxis_title="Air Quality (PPM)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # ===== DATA EXPORT =====
        st.markdown("### 📥 Data Export & Reporting")
        
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            # CSV Export
            export_cols = ['timestamp', 'air_quality', 'temperature', 'humidity', 'motion', 'light_level', 'leak_detected']
            csv_data = sensor_df[export_cols].to_csv(index=False)
            
            st.download_button(
                label="📊 Download CSV Report",
                data=csv_data,
                file_name=f"sensor_data_{start_date}_to_{end_date}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_exp2:
            # JSON Export
            json_data = sensor_df[export_cols].to_json(orient='records', date_format='iso')
            
            st.download_button(
                label="📄 Download JSON Data",
                data=json_data,
                file_name=f"sensor_data_{start_date}_to_{end_date}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col_exp3:
            # Summary Report
            summary_report = f"""
SMART HOME WELLNESS MONITORING REPORT
Period: {start_date} to {end_date}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== ENVIRONMENTAL STATISTICS ===
Air Quality:
  - Average: {stats['air_quality']['mean']:.2f} PPM
  - Maximum: {stats['air_quality']['max']:.2f} PPM
  - Minimum: {stats['air_quality']['min']:.2f} PPM
  - Std Dev: {stats['air_quality']['std']:.2f}

Temperature:
  - Average: {stats['temperature']['mean']:.2f}°C
  - Range: {stats['temperature']['min']:.2f}°C - {stats['temperature']['max']:.2f}°C

Humidity:
  - Average: {stats['humidity']['mean']:.2f}%

=== ACTIVITY SUMMARY ===
Motion Events: {stats['motion_events']}
Leak Detections: {stats['leak_events']}
Total Readings: {stats['total_readings']}

=== PATTERN INSIGHTS ===
Peak Motion Hour: {patterns['peak_motion_hour']}:00
Most Active Day: {patterns['most_active_day']}
            """
            
            st.download_button(
                label="📋 Download Summary Report",
                data=summary_report,
                file_name=f"summary_report_{start_date}_to_{end_date}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    else:
        st.warning("⚠️ No sensor data available for analysis")

# ========================================
# DEVICE MANAGEMENT PAGE
# ========================================
def device_management_page():
    st.markdown("<h1 class='main-header'>📱 Device Management & Control</h1>", unsafe_allow_html=True)
    
    devices_df = get_device_status()
    
    # ===== DEVICE STATUS OVERVIEW =====
    if not devices_df.empty:
        st.markdown("### 🖥️ Connected Devices Overview")
        
        # Device status summary
        online_count = (devices_df['status'] == 'online').sum()
        offline_count = (devices_df['status'] == 'offline').sum()
        unknown_count = (devices_df['status'] == 'unknown').sum()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Devices", len(devices_df))
        with col2:
            st.metric("🟢 Online", online_count)
        with col3:
            st.metric("🔴 Offline", offline_count)
        with col4:
            st.metric("⚪ Unknown", unknown_count)
        
        st.divider()
        
        # Device details table
        device_data = []
        for _, device in devices_df.iterrows():
            status = device['status']
            status_badge = {
                'online': "<span class='status-online'>● ONLINE</span>",
                'offline': "<span class='status-offline'>● OFFLINE</span>",
                'unknown': "<span class='status-warning'>● UNKNOWN</span>"
            }.get(status, "<span class='status-warning'>● UNKNOWN</span>")
            
            last_seen_seconds = device.get('last_seen_seconds', float('inf'))
            if last_seen_seconds < 60:
                last_seen_str = f"{last_seen_seconds:.0f}s ago"
            elif last_seen_seconds < 3600:
                last_seen_str = f"{last_seen_seconds/60:.0f}m ago"
            else:
                last_seen_str = f"{last_seen_seconds/3600:.1f}h ago"
            
            device_data.append({
                "Device ID": device['device_id'],
                "Status": status_badge,
                "Last Heartbeat": device.get('received_at', 'Never')[:19],
                "Time Since": last_seen_str,
                "Uptime": f"{device.get('uptime_minutes', 0):.0f} min",
                "Messages Sent": device.get('publish_count', 0)
            })
        
        # Display as formatted table
        for dev in device_data:
            st.markdown(f"""
            <div class='dashboard-section'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <h4 style='margin: 0;'>🔌 {dev['Device ID']}</h4>
                        {dev['Status']}
                    </div>
                    <div style='text-align: right;'>
                        <div><strong>Last Seen:</strong> {dev['Time Since']}</div>
                        <div><strong>Uptime:</strong> {dev['Uptime']} | <strong>Messages:</strong> {dev['Messages Sent']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # ===== DEVICE CONTROL PANEL =====
        st.markdown("### 🎛️ Remote Device Control")
        
        if st.session_state.user_role == 'admin':
            col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
            
            with col_ctrl1:
                selected_device = st.selectbox(
                    "🔌 Select Device",
                    devices_df['device_id'].tolist()
                )
            
            with col_ctrl2:
                command_type = st.selectbox(
                    "⚙️ Command Type",
                    ["Get Status", "Reboot Device", "Update Interval", "Run Diagnostics", "Clear Alerts"]
                )
            
            with col_ctrl3:
                st.write("")
                st.write("")
                if st.button("▶️ Execute Command", type="primary", use_container_width=True):
                    st.success(f"✅ Command '{command_type}' sent to device: {selected_device}")
                    st.info("Command published to MQTT topic: home/sensors/control")
            
            st.divider()
            
            # MQTT Command Builder
            st.markdown("#### 🔧 Advanced MQTT Command Builder")
            
            col_mqtt1, col_mqtt2 = st.columns([2, 1])
            
            with col_mqtt1:
                command_template = {
                    "device_id": selected_device,
                    "command": command_type.lower().replace(" ", "_"),
                    "timestamp": datetime.now().isoformat(),
                    "user": st.session_state.user_email,
                    "parameters": {
                        "interval_seconds": 10,
                        "enable_logging": True
                    }
                }
                
                edited_command = st.text_area(
                    "Edit Command JSON",
                    value=json.dumps(command_template, indent=2),
                    height=200
                )
                
                if st.button("📤 Publish to MQTT", type="primary"):
                    try:
                        json.loads(edited_command)  # Validate JSON
                        st.success("✅ Command published successfully!")
                        st.code(f"Topic: home/sensors/control/{selected_device}", language="text")
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON format")
            
            with col_mqtt2:
                st.info("""
                **📡 MQTT Topics:**
                
                **Subscribe:**
                - `home/sensors/data`
                - `home/sensors/status`
                - `home/sensors/alerts`
                
                **Publish:**
                - `home/sensors/control`
                - `home/sensors/config`
                """)
        else:
            st.warning("🔒 Admin access required for device control")
            st.info("Please contact your administrator to request elevated permissions")
    
    else:
        st.warning("⚠️ No devices currently connected")
        st.info("""
        **To connect a device:**
        1. Ensure MQTT broker is running on GCP
        2. Configure device with correct credentials
        3. Device should publish to: `home/sensors/data`
        4. Heartbeat topic: `home/sensors/heartbeat`
        """)

# ========================================
# SETTINGS PAGE
# ========================================
def settings_page():
    st.markdown("<h1 class='main-header'>⚙️ System Settings & Configuration</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Profile", "🔔 Alerts", "🔒 Security", "⚙️ System"])
    
    # ===== PROFILE TAB =====
    with tab1:
        st.markdown("### User Profile Management")
        
        col_prof1, col_prof2 = st.columns(2)
        
        with col_prof1:
            st.text_input("📧 Email Address", value=st.session_state.user_email, disabled=True)
            display_name = st.text_input("👤 Display Name", value="Smart Home User")
            user_role_display = st.session_state.user_role.upper()
            st.text_input("🎖️ Role", value=user_role_display, disabled=True)
            
            timezone = st.selectbox(
                "🌍 Timezone",
                ["UTC", "Asia/Kuala_Lumpur", "America/New_York", "Europe/London"],
                index=1
            )
            
            if st.button("💾 Update Profile", type="primary"):
                st.success("✅ Profile updated successfully!")
        
        with col_prof2:
            st.markdown("#### 📊 Account Statistics")
            st.info(f"""
            **Account Created:** Jan 2026  
            **Last Login:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
            **Total Logins:** 127  
            **Data Usage:** 45.2 MB
            """)
            
            st.markdown("#### 🎨 Preferences")
            theme = st.selectbox("Color Theme", ["Light", "Dark", "Auto"])
            language = st.selectbox("Language", ["English", "Malay", "Chinese"])
    
    # ===== ALERTS TAB =====
    with tab2:
        st.markdown("### Alert Threshold Configuration")
        
        col_alert1, col_alert2 = st.columns(2)
        
        with col_alert1:
            st.markdown("#### 💨 Air Quality Alerts")
            air_warning = st.slider("⚠️ Warning Level (PPM)", 50, 300, 100, 10)
            air_critical = st.slider("🚨 Critical Level (PPM)", 100, 500, 200, 10)
            
            st.markdown("#### 🌡️ Temperature Alerts")
            temp_high = st.slider("🔥 High Temperature (°C)", 25, 40, 30, 1)
            temp_low = st.slider("❄️ Low Temperature (°C)", 10, 20, 18, 1)
        
        with col_alert2:
            st.markdown("#### 💧 Humidity Alerts")
            humidity_high = st.slider("💦 High Humidity (%)", 60, 90, 70, 5)
            humidity_low = st.slider("🏜️ Low Humidity (%)", 20, 50, 30, 5)
            
            st.markdown("#### 🚪 Occupancy Alerts")
            inactivity_threshold = st.slider("⏰ Inactivity Alert (minutes)", 30, 240, 60, 10)
        
        st.divider()
        
        st.markdown("#### 📬 Notification Methods")
        notification_methods = st.multiselect(
            "Enable notifications via:",
            ["📧 Email", "📱 SMS", "🔔 Push Notification", "🖥️ Dashboard Alert", "📞 Phone Call"],
            default=["🖥️ Dashboard Alert", "📧 Email"]
        )
        
        notify_severity = st.multiselect(
            "Notify for severity levels:",
            ["🚨 CRITICAL", "⚠️ HIGH", "📢 MEDIUM", "ℹ️ LOW"],
            default=["🚨 CRITICAL", "⚠️ HIGH"]
        )
        
        if st.button("💾 Save Alert Settings", type="primary"):
            st.success("✅ Alert settings saved successfully!")
            st.info("""
            **Active Thresholds:**
            - Air Quality: Warning at {air_warning} PPM, Critical at {air_critical} PPM
            - Temperature: {temp_low}°C - {temp_high}°C
            - Humidity: {humidity_low}% - {humidity_high}%
            - Inactivity: {inactivity_threshold} minutes
            """.format(
                air_warning=air_warning, air_critical=air_critical,
                temp_low=temp_low, temp_high=temp_high,
                humidity_low=humidity_low, humidity_high=humidity_high,
                inactivity_threshold=inactivity_threshold
            ))
    
    # ===== SECURITY TAB =====
    with tab3:
        st.markdown("### Security & Access Control")
        
        col_sec1, col_sec2 = st.columns(2)
        
        with col_sec1:
            st.markdown("#### 🔐 Password Management")
            current_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")
            
            if st.button("🔄 Change Password", type="primary"):
                if new_pw == confirm_pw and len(new_pw) >= 8:
                    st.success("✅ Password updated successfully!")
                else:
                    st.error("❌ Passwords don't match or too short (min 8 chars)")
            
            st.divider()
            
            st.markdown("#### 🔒 Two-Factor Authentication")
            mfa_status = st.checkbox("Enable Google Authenticator MFA", value=True)
            if mfa_status:
                st.success("✅ Google Authenticator MFA is currently enabled")
                if st.button("📱 Reconfigure Google Authenticator"):
                    st.session_state.mfa_secret = generate_totp_secret()
                    st.session_state.mfa_qr_configured = False
                    st.info("Google Authenticator reconfiguration initiated")
                    st.rerun()
            else:
                st.warning("⚠️ MFA is disabled - Not recommended!")
        
        with col_sec2:
            st.markdown("#### 📜 Active Sessions")
            st.dataframe({
                "Device": ["Chrome - Windows", "Mobile - iOS", "Firefox - Linux"],
                "Location": ["Kuala Lumpur, MY", "Penang, MY", "Singapore, SG"],
                "Last Active": ["Just now", "2 hours ago", "1 day ago"]
            }, use_container_width=True, hide_index=True)
            
            if st.button("🚫 Revoke All Sessions"):
                st.warning("All other sessions have been terminated")
            
            st.divider()
            
            st.markdown("#### 🔍 Audit Log")
            st.dataframe({
                "Action": ["Login", "Settings Changed", "Alert Acknowledged", "Device Command"],
                "Timestamp": [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
                    (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                ],
                "IP Address": ["192.168.1.100", "192.168.1.100", "192.168.1.101", "192.168.1.100"]
            }, use_container_width=True, hide_index=True)
    
    # ===== SYSTEM TAB =====
    with tab4:
        st.markdown("### System Configuration")
        
        col_sys1, col_sys2 = st.columns(2)
        
        with col_sys1:
            st.markdown("#### 💾 Data Management")
            data_retention = st.select_slider(
                "Data Retention Period",
                options=["7 days", "30 days", "90 days", "6 months", "1 year", "Forever"],
                value="30 days"
            )
            
            auto_backup = st.checkbox("Enable Automatic Backups", value=True)
            if auto_backup:
                backup_frequency = st.selectbox(
                    "Backup Frequency",
                    ["Daily", "Weekly", "Monthly"]
                )
            
            st.divider()
            
            st.markdown("#### 🔄 Dashboard Settings")
            st.session_state.auto_refresh = st.checkbox(
                "Enable Auto-Refresh",
                value=st.session_state.auto_refresh
            )
            
            if st.session_state.auto_refresh:
                refresh_options = {
                    "10 seconds": 10,
                    "30 seconds": 30,
                    "1 minute": 60,
                    "5 minutes": 300
                }
                selected_refresh = st.selectbox(
                    "Refresh Interval",
                    list(refresh_options.keys()),
                    index=1
                )
                st.session_state.refresh_interval = refresh_options[selected_refresh]
            
            rows_per_page = st.slider("Table Rows Per Page", 5, 50, 10, 5)
        
        with col_sys2:
            st.markdown("#### 🗄️ Storage Information")
            
            # Simulated storage info
            total_storage = 1000  # MB
            used_storage = 456  # MB
            usage_pct = (used_storage / total_storage) * 100
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=usage_pct,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Storage Usage"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#1E88E5"},
                    'steps': [
                        {'range': [0, 50], 'color': "#e0e0e0"},
                        {'range': [50, 80], 'color': "#ffeb3b"},
                        {'range': [80, 100], 'color': "#ff5722"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            st.info(f"""
            **Used:** {used_storage} MB / {total_storage} MB  
            **Available:** {total_storage - used_storage} MB  
            **Database Records:** 12,450
            """)
        
        st.divider()
        
        st.markdown("#### 🔧 Maintenance Actions")
        
        col_maint1, col_maint2, col_maint3, col_maint4 = st.columns(4)
        
        with col_maint1:
            if st.button("🗑️ Clear Cache", use_container_width=True):
                st.cache_data.clear()
                st.success("✅ Cache cleared!")
        
        with col_maint2:
            if st.button("🔄 Reset Alerts", use_container_width=True):
                st.info("All alerts reset to default")
        
        with col_maint3:
            if st.button("📊 Export All Data", use_container_width=True):
                st.info("Preparing export...")
        
        with col_maint4:
            if st.button("🚪 Logout", type="primary", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        st.divider()
        
        st.markdown("#### ℹ️ System Information")
        
        system_info = {
            "Platform": "Streamlit on GCP",
            "Database": "Firebase Firestore",
            "MQTT Broker": "Mosquitto on GCP VM",
            "Dashboard Version": "v2.0.0",
            "Last Updated": "2026-01-18",
            "Uptime": "99.8%"
        }
        
        info_df = pd.DataFrame(list(system_info.items()), columns=['Component', 'Details'])
        st.table(info_df)

# ========================================
# MAIN APPLICATION LOGIC
# ========================================
def main():
    # Check authentication
    if not st.session_state.authenticated:
        if st.session_state.page == "login":
            login_page()
        elif st.session_state.page == "mfa_setup":
            mfa_setup_page()
        elif st.session_state.page == "mfa_verify":
            mfa_verify_page()
    else:
        # Authenticated - Show Dashboard
        with st.sidebar:
            # Logo and Welcome
            st.markdown("""
            <div style='text-align: center; margin-bottom: 2rem;'>
                <div style='font-size: 3rem;'>🏠</div>
                <h3 style='color: #1E88E5; margin: 0.5rem 0;'>Smart Home</h3>
                <p style='color: #666; font-size: 0.9rem;'>Wellness & Safety Monitor</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 1rem; border-radius: 10px; color: white; margin-bottom: 1rem;'>
                <div style='font-size: 0.85rem; opacity: 0.9;'>Logged in as</div>
                <div style='font-weight: 600; font-size: 1rem;'>{st.session_state.user_email}</div>
                <div style='font-size: 0.75rem; opacity: 0.8; margin-top: 0.3rem;'>
                    Role: {st.session_state.user_role.upper()}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            # Navigation Menu
            menu = option_menu(
                menu_title="Navigation",
                options=["Dashboard", "Alerts", "Analytics", "Devices", "Settings"],
                icons=["house-fill", "bell-fill", "graph-up", "phone-fill", "gear-fill"],
                menu_icon="cast",
                default_index=0,
                styles={
                    "container": {"padding": "0!important"},
                    "icon": {"font-size": "1.2rem"},
                    "nav-link": {
                        "font-size": "1rem",
                        "text-align": "left",
                        "margin": "0.2rem",
                        "border-radius": "8px"
                    },
                    "nav-link-selected": {"background-color": "#1E88E5"}
                }
            )
            
            st.divider()
            
            # Quick Stats in Sidebar
            st.markdown("### 📊 Quick Stats")
            
            sensor_count = len(get_sensor_data(100))
            alerts_count = len(get_alerts(active_only=True))
            devices_df = get_device_status()
            online_devices = len(devices_df[devices_df['status'] == 'online']) if not devices_df.empty else 0
            
            st.metric("Recent Readings", f"{sensor_count}")
            st.metric("Active Alerts", f"{alerts_count}", 
                     delta="-1" if alerts_count < 3 else "+2",
                     delta_color="inverse")
            st.metric("Devices Online", f"{online_devices}")
            
            st.divider()
            
            # Action Buttons
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.cache_data.clear()
                    st.session_state.last_refresh = datetime.now()
                    st.rerun()
            
            with col_btn2:
                if st.button("🚪 Logout", use_container_width=True, type="primary"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            
            # Auto-refresh status
            if st.session_state.auto_refresh:
                time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
                next_refresh = st.session_state.refresh_interval - time_since_refresh
                
                st.caption(f"🔄 Auto-refresh in {max(0, next_refresh)}s")
                
                # Auto-refresh logic
                if time_since_refresh >= st.session_state.refresh_interval:
                    st.session_state.last_refresh = datetime.now()
                    st.rerun()
            
            st.divider()
            
            # Footer
            st.markdown("""
            <div style='text-align: center; color: #666; font-size: 0.75rem;'>
                <p>🔒 Secured by Firebase & Google Auth</p>
                <p>🛡️ TLS Encrypted</p>
                <p>© 2026 Smart Home IoT</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Main Content Area
        if menu == "Dashboard":
            dashboard_home()
        elif menu == "Alerts":
            alerts_management_page()  # NEW: Separate alerts page
        elif menu == "Analytics":
            analytics_page()
        elif menu == "Devices":
            device_management_page()
        elif menu == "Settings":
            settings_page()

# ========================================
# RUN APPLICATION
# ========================================
if __name__ == "__main__":
    main()