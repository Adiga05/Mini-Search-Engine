import streamlit as st
import os
import re
import math
import glob
import pandas as pd
from datetime import datetime
from collections import defaultdict, Counter

# ==========================================
# 1. CONFIGURATION & STATE
# ==========================================

st.set_page_config(page_title="Mini Engine", page_icon="🚀", layout="wide")

DOCS_DIR = "docs"
LOG_FILE = "search_logs.csv"
USER_DB_FILE = "users.csv"
LOGIN_ACTIVITY_FILE = "login_logs.csv"

# Ensure directories exist
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

# Initialize Session State
state_defaults = {
    'logged_in': False,
    'username': "",
    'theme': "Light",
    'admin_unlocked': False,
    'current_page': "search",
    'selected_file': None,
    'last_logged_query': None
}

for key, val in state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ==========================================
# 2. UI STYLING (Original Reverted CSS)
# ==========================================
def apply_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }
        
        /* --- 0. POP-UP ANIMATION KEYFRAMES --- */
        @keyframes popUp {
            0% { transform: translateY(40px) scale(0.95); opacity: 0; }
            100% { transform: translateY(0) scale(1); opacity: 1; }
        }

        /* --- 1. MAIN LOGIN CARD (THE FORM ITSELF) --- */
        [data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(20px);
            border-radius: 25px;
            padding: 40px;
            border: 1px solid rgba(255,255,255,0.6);
            box-shadow: 0 20px 50px rgba(0,0,0,0.15);
            max-width: 450px; 
            margin: 20px auto; 
            text-align: center;
            animation: popUp 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }

        /* --- 2. REFINED INPUT FIELDS (FLOATING PILLS) --- */
        div[data-testid="stTextInput"] {
            background: #ffffff; /* Pure white */
            border-radius: 50px; /* Pill shape */
            display: flex; 
            align-items: center; 
            height: 50px; 
            padding: 0px 20px;
            margin-bottom: 15px; /* Spacing between inputs */
            
            /* The "Floating" Look */
            box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
            border: 1px solid rgba(0,0,0,0.02);
            transition: all 0.3s ease;
        }
        
        div[data-testid="stTextInput"]:hover, div[data-testid="stTextInput"]:focus-within {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.1);
            border: 1px solid rgba(0,114,255,0.3); /* Subtle blue glow */
        }
        
        div[data-testid="stTextInput"] > div { width: 100%; display: flex; align-items: center; }
        div[data-testid="stTextInput"] > div > div > input {
            border: none; background: transparent; font-size: 1rem; color: #333; margin: 0; padding: 0;
        }

        /* SPECIFIC: Search Bar Width (NARROWER) */
        .main div[data-testid="stTextInput"] {
            width: 40%; /* Reduced to 40% */
            min-width: 400px;
            margin: 0 auto 30px auto;
        }

        /* SPECIFIC: Sidebar Inputs (Admin Key) */
        section[data-testid="stSidebar"] div[data-testid="stTextInput"] {
            width: 100% !important; 
            min-width: 0;
            margin-bottom: 10px;
        }

        /* --- 3. ANIMATED BUTTONS --- */
        div.stButton > button {
            transition: all 0.3s ease;
            border-radius: 12px;
            font-weight: 600;
            border: none;
            padding: 0.6rem 1.5rem;
            width: 100%; /* Full width buttons in form */
            background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(0,114,255,0.3);
        }
        div.stButton > button:hover {
            transform: translateY(-2px) scale(1.02);
            box-shadow: 0 8px 25px rgba(0,114,255,0.5);
        }
        
        /* --- 4. GLASS CARDS (Results) --- */
        .glass-card {
            background: rgba(255, 255, 255, 0.5);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.4);
            padding: 24px;
            margin-bottom: 20px;
            animation: popUp 0.5s ease-out forwards;
        }

        /* --- 5. TABS --- */
        .stTabs [data-baseweb="tab-list"] {
            justify-content: center;
            gap: 20px;
            background: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-radius: 20px;
            padding: 5px 20px;
            color: #555;
        }
        .stTabs [aria-selected="true"] {
            background-color: rgba(255,255,255,0.8);
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            color: #0072ff;
            font-weight: bold;
        }
        
        /* --- 6. HIDE DEFAULT STREAMLIT FORM HINTS --- */
        [data-testid="InputInstructions"] {
            display: none !important;
        }
        
        .profile-img {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid white;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    # Theme Colors
    if st.session_state['theme'] == "Dark":
        st.markdown("""
            <style>
            .stApp { background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%); color: #ffffff; }
            section[data-testid="stSidebar"] { background-color: rgba(30, 30, 50, 0.85); border-right: 1px solid rgba(255,255,255,0.1); }
            h1, h2, h3, p { color: white !important; }
            
            /* Dark Mode Overrides */
            [data-testid="stForm"] { background: rgba(30, 30, 50, 0.85); border: 1px solid rgba(255,255,255,0.1); }
            div[data-testid="stTextInput"] { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); }
            div[data-testid="stTextInput"] > div > div > input { color: white; }
            div[data-testid="stTextInput"]:hover { border: 1px solid rgba(218, 34, 255, 0.5); }
            div.stButton > button { background: linear-gradient(90deg, #da22ff, #9733ee); }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            .stApp { background: linear-gradient(120deg, #a1c4fd 0%, #c2e9fb 100%); color: #333; }
            section[data-testid="stSidebar"] { background-color: rgba(255, 255, 255, 0.6); backdrop-filter: blur(10px); }
            h1, h2, h3 { color: #2c3e50 !important; }
            </style>
        """, unsafe_allow_html=True)

# ==========================================
# 3. BACKEND LOGIC
# ==========================================

def init_dbs():
    if not os.path.exists(USER_DB_FILE):
        df = pd.DataFrame(columns=["username", "password", "created_at"])
        df.loc[0] = ["Admin", "admin123", datetime.now().strftime("%Y-%m-%d")]
        df.to_csv(USER_DB_FILE, index=False)

def register_user(username, password):
    init_dbs()
    df = pd.read_csv(USER_DB_FILE)
    if username in df['username'].values:
        return False, "Username already taken."
    new_user = pd.DataFrame([[username, password, datetime.now().strftime("%Y-%m-%d")]], 
                            columns=["username", "password", "created_at"])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USER_DB_FILE, index=False)
    return True, "Account created! Please log in."

def authenticate_user(username, password):
    init_dbs()
    df = pd.read_csv(USER_DB_FILE)
    user_row = df[(df['username'] == username) & (df['password'] == password)]
    
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOGIN_ACTIVITY_FILE):
        with open(LOGIN_ACTIVITY_FILE, "w") as f: f.write("Timestamp,User,Status\n")
    
    if not user_row.empty:
        with open(LOGIN_ACTIVITY_FILE, "a") as f: f.write(f"{ts},{username},Success\n")
        
        # --- FIX: SAVE LOGIN TO URL ---
        st.query_params["user"] = username
        return True
    else:
        with open(LOGIN_ACTIVITY_FILE, "a") as f: f.write(f"{ts},{username},Failed\n")
        return False

def log_search(username, query):
    if st.session_state['last_logged_query'] == query:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f: f.write("Timestamp,User,Query\n")
    
    with open(LOG_FILE, "a") as f: f.write(f"{timestamp},{username},{query}\n")
    st.session_state['last_logged_query'] = query

class SearchEngine:
    def __init__(self):
        self.inverted_index = defaultdict(list)
        self.documents = {} 
        self.doc_count = 0

    def _tokenize(self, text):
        return re.findall(r'\b\w+\b', text.lower())

    def add_file(self, filepath):
        if filepath.endswith(".py"): return
        try:
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
        except: return
        
        tokens = self._tokenize(content)
        if not tokens: return
        doc_id = self.doc_count
        self.documents[doc_id] = {"filename": os.path.basename(filepath), "content": content, "total_words": len(tokens)}
        self.doc_count += 1
        for term, count in Counter(tokens).items():
            self.inverted_index[term].append({"doc_id": doc_id, "tf": count})

    def search(self, query):
        tokens = self._tokenize(query)
        if not tokens: return []
        scores = defaultdict(float)
        for token in tokens:
            if token not in self.inverted_index: continue
            postings = self.inverted_index[token]
            idf = math.log(self.doc_count / (len(postings) + 1))
            for post in postings:
                tf = post['tf'] / self.documents[post['doc_id']]['total_words']
                scores[post['doc_id']] += tf * idf
        results = [self.documents[doc_id] | {'score': score} for doc_id, score in scores.items()]
        return sorted(results, key=lambda x: x['score'], reverse=True)

@st.cache_resource
def load_engine():
    engine = SearchEngine()
    files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    if not files:
        with open(os.path.join(DOCS_DIR, "welcome.txt"), "w") as f: f.write("Welcome to the engine.")
        files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    for f in files: engine.add_file(f)
    return engine

# ==========================================
# 4. VIEW FUNCTIONS
# ==========================================

def render_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Create Account"])
        with tab1:
            with st.form("login_form"):
                st.markdown("<h2 style='text-align: center; margin: 0 0 20px 0;'>🚀 Mini Engine</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; opacity: 0.6; margin-bottom: 20px;'>Secure Login</p>", unsafe_allow_html=True)
                user = st.text_input("", placeholder="Enter Username")
                password = st.text_input("", type="password", placeholder="Enter Password")
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("Login"):
                    if authenticate_user(user, password):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = user
                        st.rerun()
                    else: st.error("Invalid Credentials")
        with tab2:
            with st.form("register_form"):
                st.markdown("<h2 style='text-align: center; margin: 0 0 20px 0;'>📝 Join Us</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; opacity: 0.6; margin-bottom: 20px;'>Create Account</p>", unsafe_allow_html=True)
                new_user = st.text_input("New Username", placeholder="Choose Username")
                new_pass = st.text_input("New Password", type="password", placeholder="Choose Password")
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                if st.form_submit_button("Sign Up"):
                    if new_user and new_pass:
                        success, msg = register_user(new_user, new_pass)
                        if success: st.success(msg)
                        else: st.error(msg)
                    else: st.warning("Fields cannot be empty")

def render_file_view():
    file_data = st.session_state['selected_file']
    if st.button("⬅️ Back to Search"):
        st.session_state['selected_file'] = None
        st.session_state['current_page'] = "search"
        st.rerun()
    st.markdown(f"""
        <div class="glass-card">
            <h2 style="margin:0; color:#333;">📄 {file_data['filename']}</h2>
            <p style="margin:0; opacity:0.7;">Word Count: {file_data['total_words']}</p>
        </div>
    """, unsafe_allow_html=True)
    st.text_area("File Content", file_data['content'], height=550)
    st.download_button("📥 Download File", file_data['content'], file_data['filename'])

def render_search_page():
    st.markdown(f"""
        <div class="glass-card" style="margin-bottom: 40px; text-align: center;">
            <h1 style="margin:0;">🔎 Knowledge Hub</h1>
            <p style="margin:0; opacity:0.8;">Welcome, <b>{st.session_state['username']}</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    engine = load_engine()
    query = st.text_input("", placeholder="Search anything (e.g. 'science', 'sports')...")
    
    if query:
        log_search(st.session_state['username'], query)
        results = engine.search(query)
        
        # --- FILTER: HIDE SCORES <= 0 ---
        results = [r for r in results if r['score'] > 0]
        
        st.markdown(f"### Found {len(results)} matches")
        if not results: st.warning("No documents found matching your query.")
        else:
            for res in results:
                # --- CHANGE 1: CLICKABLE BUTTON CARD ---
                button_label = f"📄 {res['filename']}  (Score: {res['score']:.2f})"
                
                if st.button(button_label, key=f"res_{res['filename']}", use_container_width=True):
                    st.session_state['selected_file'] = res
                    st.session_state['current_page'] = "file_view"
                    st.rerun()

def render_admin_page():
    st.markdown("<h1>🛡️ Admin Dashboard</h1>", unsafe_allow_html=True)
    if st.button("⬅️ Exit Admin"):
        st.session_state['current_page'] = "search"
        st.rerun()
    st.markdown("---")
    t1, t2, t3 = st.tabs(["📂 Database Manager", "📊 User Searches", "👥 Login Logs"])
    with t1:
        st.markdown("### Upload New Documents")
        uploaded = st.file_uploader("Drag text files here", accept_multiple_files=True)
        if uploaded:
            for f in uploaded:
                with open(os.path.join(DOCS_DIR, f.name), "wb") as w: w.write(f.getbuffer())
            st.success("Files Uploaded Successfully!")
            st.cache_resource.clear()
            st.rerun()
        st.divider()
        st.markdown("### Existing Files")
        files = os.listdir(DOCS_DIR)
        if not files: st.info("Database is empty.")
        else:
            for f in files:
                with st.container():
                    col_a, col_b = st.columns([0.85, 0.15])
                    with col_a: st.text(f"📄 {f}")
                    with col_b:
                        if st.button("Remove", key=f"del_{f}"):
                            os.remove(os.path.join(DOCS_DIR, f))
                            st.cache_resource.clear()
                            st.rerun()
                    st.markdown("<hr style='margin:5px 0; opacity:0.1'>", unsafe_allow_html=True)
    with t2:
        if os.path.exists(LOG_FILE): st.dataframe(pd.read_csv(LOG_FILE), use_container_width=True)
        else: st.info("No search logs available.")
    with t3:
        if os.path.exists(LOGIN_ACTIVITY_FILE): st.dataframe(pd.read_csv(LOGIN_ACTIVITY_FILE), use_container_width=True)
        else: st.info("No login logs available.")

# ==========================================
# 5. MAIN APP CONTROLLER
# ==========================================

apply_theme()
init_dbs()

if not st.session_state['logged_in']:
    render_login_page()
else:
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align:center; margin-bottom: 20px;">
                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed={st.session_state['username']}" class="profile-img">
                <h3 style="margin: 10px 0 0 0;">{st.session_state['username']}</h3>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("### ⚙️ Settings Portal")
        with st.expander("🎨 Theme"):
            current_theme = st.session_state['theme']
            new_theme = st.radio("Select Mode:", ["Light", "Dark"], index=0 if current_theme == "Light" else 1)
            if new_theme != current_theme:
                st.session_state['theme'] = new_theme
                st.rerun()
                
        # --- CHANGE 2: HIDDEN TIMESTAMP IN HISTORY ---
        with st.expander("🕒 Search History"):
            if os.path.exists(LOG_FILE):
                df = pd.read_csv(LOG_FILE)
                my_logs = df[df['User'] == st.session_state['username']]
                if not my_logs.empty:
                    # Only showing Query column
                    st.dataframe(my_logs[['Query']], hide_index=True)
                else: st.info("No history")
            else: st.info("No history")
            
        with st.expander("🛡️ Admin Page"):
            if not st.session_state['admin_unlocked']:
                pwd = st.text_input("Enter Key", type="password")
                if st.button("Unlock Admin"):
                    if pwd == "admin123":
                        st.session_state['admin_unlocked'] = True
                        st.session_state['current_page'] = "admin"
                        st.rerun()
                    else: st.error("Invalid Key")
            else:
                st.success("Unlocked")
                if st.button("Go to Dashboard"):
                    st.session_state['current_page'] = "admin"
                    st.rerun()
                if st.button("Lock Admin"):
                    st.session_state['admin_unlocked'] = False
                    st.session_state['current_page'] = "search"
                    st.rerun()
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.query_params.clear() # CLEAR URL ON LOGOUT
            st.session_state['logged_in'] = False
            st.session_state['admin_unlocked'] = False
            st.session_state['current_page'] = "search"
            st.rerun()

    if st.session_state['current_page'] == "search": render_search_page()
    elif st.session_state['current_page'] == "file_view": render_file_view()
    elif st.session_state['current_page'] == "admin":
        if st.session_state['admin_unlocked']: render_admin_page()
        else:
            st.session_state['current_page'] = "search"
            st.rerun()
