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
    'selected_file': None
}

for key, val in state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ==========================================
# 2. COLORFUL & ATTRACTIVE UI (CSS)
# ==========================================
def apply_theme():
    # Base CSS: Fonts, Gradients, and Glassmorphism
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }
        
        /* 1. ANIMATED BUTTONS */
        div.stButton > button {
            transition: all 0.3s ease;
            border-radius: 12px;
            font-weight: 600;
            border: none;
            padding: 0.5rem 1rem;
        }
        div.stButton > button:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
            z-index: 99;
        }
        
        /* 2. FLOATING ISLAND LOGIN CARD */
        .floating-island {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.6);
            margin: 50px auto; /* Centers it vertically/horizontally in column */
            text-align: center;
        }

        /* 3. GLASS CARDS (General) */
        .glass-card {
            background: rgba(255, 255, 255, 0.25);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            padding: 24px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
            margin-bottom: 20px;
        }

        /* 4. SETTINGS DROPDOWNS */
        div[data-testid="stExpander"] {
            background-color: rgba(255, 255, 255, 0.4);
            border-radius: 10px;
            border: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 10px;
        }
        
        /* 5. PROFILE IMAGE */
        .profile-img {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            object-fit: cover;
            border: 4px solid white;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    # Dynamic Theme Colors
    if st.session_state['theme'] == "Dark":
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
                color: #ffffff;
            }
            section[data-testid="stSidebar"] {
                background-color: rgba(30, 30, 50, 0.85);
                border-right: 1px solid rgba(255,255,255,0.1);
            }
            .stTextInput > div > div > input {
                background-color: rgba(0,0,0,0.3);
                color: white;
                border: 1px solid rgba(255,255,255,0.2);
            }
            div.stButton > button {
                background: linear-gradient(90deg, #da22ff, #9733ee);
                color: white;
            }
            h1, h2, h3, p { color: white !important; }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(120deg, #a1c4fd 0%, #c2e9fb 100%);
                color: #333;
            }
            section[data-testid="stSidebar"] {
                background-color: rgba(255, 255, 255, 0.6);
                backdrop-filter: blur(10px);
            }
            .stTextInput > div > div > input {
                background-color: rgba(255,255,255,0.8);
                color: #333;
                border: 1px solid #a1c4fd;
            }
            div.stButton > button {
                background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%);
                color: white;
            }
            h1, h2, h3 { color: #2c3e50 !important; }
            </style>
        """, unsafe_allow_html=True)

# ==========================================
# 3. BACKEND LOGIC (Database & Auth)
# ==========================================

def init_dbs():
    # REMOVED email column, reverted to username
    if not os.path.exists(USER_DB_FILE):
        df = pd.DataFrame(columns=["username", "password", "created_at"])
        # Default Admin Account
        df.loc[0] = ["Admin", "admin123", datetime.now().strftime("%Y-%m-%d")]
        df.to_csv(USER_DB_FILE, index=False)

def log_login_activity(username, status="Success"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOGIN_ACTIVITY_FILE):
        with open(LOGIN_ACTIVITY_FILE, "w") as f: f.write("Timestamp,User,Status\n")
    with open(LOGIN_ACTIVITY_FILE, "a") as f: f.write(f"{timestamp},{username},{status}\n")

def register_user(username, password):
    init_dbs()
    df = pd.read_csv(USER_DB_FILE)
    
    # Check if username exists
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
    # Match Username and Password
    user_row = df[(df['username'] == username) & (df['password'] == password)]
    
    if not user_row.empty:
        log_login_activity(username, "Success")
        return True
    else:
        log_login_activity(username, "Failed")
        return False

def log_search(username, query):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f: f.write("Timestamp,User,Query\n")
    with open(LOG_FILE, "a") as f: f.write(f"{timestamp},{username},{query}\n")

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
# 4. VIEW FUNCTIONS (UI Pages)
# ==========================================

def render_login_page():
    # Floating Island CSS applied via markdown
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="floating-island">
                <h1 style="color: #0072ff; font-weight: 800; margin-bottom: 5px;">🚀 Mini Engine</h1>
                <p style="color: #555; font-size: 1.1em;">Secure Document Intelligence</p>
                <hr style="opacity: 0.2; margin: 20px 0;">
            </div>
        """, unsafe_allow_html=True)
        
        # Tabs for Login/Register inside the island context
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        with tab1:
            with st.form("login_form"):
                user = st.text_input("Username")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Log In", use_container_width=True):
                    if authenticate_user(user, password):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = user
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password")
        
        with tab2:
            with st.form("register_form"):
                new_user = st.text_input("Choose Username")
                new_pass = st.text_input("Create Password", type="password")
                
                if st.form_submit_button("Sign Up", use_container_width=True):
                    if new_user and new_pass:
                        success, msg = register_user(new_user, new_pass)
                        if success: st.success(msg)
                        else: st.error(msg)
                    else:
                        st.warning("All fields are required.")

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
    # Welcome Header
    st.markdown(f"""
        <div class="glass-card" style="margin-bottom: 30px;">
            <h1 style="margin:0;">🔎 Knowledge Hub</h1>
            <p style="margin:0; opacity:0.8;">Logged in as: <b>{st.session_state['username']}</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    engine = load_engine()
    query = st.text_input("", placeholder="Type keywords (e.g., 'contract', 'finance')...")
    
    if query:
        log_search(st.session_state['username'], query)
        results = engine.search(query)
        
        st.markdown(f"### Found {len(results)} matches")
        
        if not results:
            st.warning("No documents found matching your query.")
        else:
            for res in results:
                # Custom Card HTML
                st.markdown(f"""
                    <div style="
                        background: rgba(255,255,255,0.8);
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 15px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                        border-left: 5px solid #0072ff;
                    ">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h3 style="margin:0; color:#333;">📄 {res['filename']}</h3>
                            <span style="background:#0072ff; color:white; padding:3px 10px; border-radius:20px; font-size:0.8em;">
                                Score: {res['score']:.2f}
                            </span>
                        </div>
                        <p style="color:#666; font-style:italic; margin-top:10px;">
                            "{res['content'][:150].replace(chr(10), ' ')}..."
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Open Button
                col1, col2 = st.columns([0.88, 0.12])
                with col2:
                    if st.button("Open ↗", key=f"btn_{res['filename']}"):
                        st.session_state['selected_file'] = res
                        st.session_state['current_page'] = "file_view"
                        st.rerun()

def render_admin_page():
    st.markdown("<h1>🛡️ Admin Dashboard</h1>", unsafe_allow_html=True)
    
    if st.button("⬅️ Exit Admin"):
        st.session_state['current_page'] = "search"
        st.rerun()
    
    st.markdown("---")
    
    t1, t2, t3 = st.tabs(["📂 Database Manager", "📊 User Searches", "👥 Logins"])
    
    with t1:
        # Changed Layout: Upload first, then files below it (Stacked)
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
        
        if not files:
            st.info("Database is empty.")
        else:
            for f in files:
                # Use a clean container for each file row
                with st.container():
                    col_a, col_b = st.columns([0.85, 0.15])
                    with col_a:
                        st.text(f"📄 {f}")
                    with col_b:
                        if st.button("Remove", key=f"del_{f}"):
                            os.remove(os.path.join(DOCS_DIR, f))
                            st.cache_resource.clear()
                            st.rerun()
                    st.divider()

    with t2:
        if os.path.exists(LOG_FILE):
            st.dataframe(pd.read_csv(LOG_FILE), use_container_width=True)
        else: st.info("No search logs available.")

    with t3:
        if os.path.exists(LOGIN_ACTIVITY_FILE):
            st.dataframe(pd.read_csv(LOGIN_ACTIVITY_FILE), use_container_width=True)
        else: st.info("No login logs available.")

# ==========================================
# 5. MAIN APP CONTROLLER
# ==========================================

apply_theme()
init_dbs()

if not st.session_state['logged_in']:
    render_login_page()
else:
    # --- SIDEBAR (Refined Settings Portal) ---
    with st.sidebar:
        # Profile Picture & Name
        st.markdown(f"""
            <div style="text-align:center; margin-bottom: 20px;">
                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed={st.session_state['username']}" class="profile-img">
                <h3 style="margin: 10px 0 0 0;">{st.session_state['username']}</h3>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### ⚙️ Settings Portal")

        # 1. THEME DROPDOWN
        with st.expander("🎨 Theme"):
            current_theme = st.session_state['theme']
            new_theme = st.radio("Select Mode:", ["Light", "Dark"], 
                                 index=0 if current_theme == "Light" else 1)
            if new_theme != current_theme:
                st.session_state['theme'] = new_theme
                st.rerun()

        # 2. SEARCH HISTORY DROPDOWN
        with st.expander("🕒 Search History"):
            if os.path.exists(LOG_FILE):
                df = pd.read_csv(LOG_FILE)
                # Filter by logged-in username
                my_logs = df[df['User'] == st.session_state['username']]
                
                if not my_logs.empty:
                    st.dataframe(my_logs[['Timestamp', 'Query']], hide_index=True)
                else:
                    st.info("No history")
            else:
                st.info("No history")

        # 3. ADMIN DROPDOWN
        with st.expander("🛡️ Admin Page"):
            if not st.session_state['admin_unlocked']:
                pwd = st.text_input("Enter Key", type="password")
                if st.button("Unlock Admin"):
                    if pwd == "admin123":
                        st.session_state['admin_unlocked'] = True
                        st.session_state['current_page'] = "admin"
                        st.rerun()
                    else:
                        st.error("Invalid Key")
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
            st.session_state['logged_in'] = False
            st.session_state['admin_unlocked'] = False
            st.session_state['current_page'] = "search"
            st.rerun()

    # --- ROUTING ---
    if st.session_state['current_page'] == "search":
        render_search_page()
    elif st.session_state['current_page'] == "file_view":
        render_file_view()
    elif st.session_state['current_page'] == "admin":
        if st.session_state['admin_unlocked']:
            render_admin_page()
        else:
            st.session_state['current_page'] = "search"
            st.rerun()
