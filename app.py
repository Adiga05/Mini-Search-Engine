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
# 2. CSS STYLING (THEMES & ANIMATIONS)
# ==========================================
def apply_theme():
    # Base CSS: Fonts and Button Animations
    # We use unsafe_allow_html=True to make sure this renders as style, not text.
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }
        
        /* POP-UP BUTTON ANIMATION */
        div.stButton > button {
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 600;
        }
        div.stButton > button:hover {
            transform: translateY(-5px) scale(1.02) !important;
            box-shadow: 0 10px 20px rgba(0,0,0,0.15) !important;
            z-index: 999;
        }
        div.stButton > button:active {
            transform: translateY(-2px) scale(0.98) !important;
        }

        /* CARD STYLING */
        .doc-card {
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: 0.3s;
        }
        .doc-card:hover {
            box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        }

        /* PROFILE IMAGE */
        .profile-img {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            margin-bottom: 10px;
            border: 4px solid rgba(255,255,255,0.8);
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    # Theme Specific Colors
    if st.session_state['theme'] == "Dark":
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: #ffffff;
            }
            section[data-testid="stSidebar"] {
                background-color: rgba(30, 60, 114, 0.95);
                border-right: 1px solid rgba(255,255,255,0.1);
            }
            div[data-testid="stExpander"] {
                background-color: rgba(255,255,255,0.1);
                border-radius: 10px;
            }
            .stTextInput > div > div > input {
                background-color: rgba(255,255,255,0.15);
                color: white;
                border: 1px solid rgba(255,255,255,0.2);
            }
            /* Dark Mode Button */
            div.stButton > button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .doc-card {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
            }
            h1, h2, h3, p { color: white !important; }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
                color: #333;
            }
            section[data-testid="stSidebar"] {
                background-color: #ffffff;
                box-shadow: 2px 0 15px rgba(0,0,0,0.05);
            }
            div[data-testid="stExpander"] {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #eee;
            }
            .stTextInput > div > div > input {
                background-color: #ffffff;
                border: 1px solid #ddd;
                color: #333;
            }
            /* Light Mode Button */
            div.stButton > button {
                background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%);
                color: white;
            }
            .doc-card {
                background: #ffffff;
                border-left: 5px solid #0072ff;
            }
            </style>
        """, unsafe_allow_html=True)

# ==========================================
# 3. BACKEND LOGIC
# ==========================================

def init_dbs():
    if not os.path.exists(USER_DB_FILE):
        df = pd.DataFrame(columns=["username", "password", "created_at"])
        df.loc[0] = ["admin", "admin123", datetime.now().strftime("%Y-%m-%d")]
        df.to_csv(USER_DB_FILE, index=False)

def log_login_activity(username, status="Success"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOGIN_ACTIVITY_FILE):
        with open(LOGIN_ACTIVITY_FILE, "w") as f: f.write("Timestamp,User,Status\n")
    with open(LOGIN_ACTIVITY_FILE, "a") as f: f.write(f"{timestamp},{username},{status}\n")

def register_user(username, password):
    init_dbs()
    df = pd.read_csv(USER_DB_FILE)
    if username in df['username'].values:
        return False, "Username taken."
    new_user = pd.DataFrame([[username, password, datetime.now().strftime("%Y-%m-%d")]], 
                            columns=["username", "password", "created_at"])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USER_DB_FILE, index=False)
    return True, "Success!"

def authenticate_user(username, password):
    init_dbs()
    df = pd.read_csv(USER_DB_FILE)
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
        # Safety: Don't index script files if user dragged them in by mistake
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
    # Ensure we only load .txt files
    files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    if not files:
        with open(os.path.join(DOCS_DIR, "welcome.txt"), "w") as f: f.write("Welcome. Please upload files in Admin panel.")
        files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    for f in files: engine.add_file(f)
    return engine

# ==========================================
# 4. VIEW FUNCTIONS
# ==========================================

def render_login_page():
    # Styled Login Box
    st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            max-width: 500px;
            margin: 50px auto;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        ">
            <h1 style="color: #0072ff; margin-bottom: 0;">🚀 Mini Engine</h1>
            <p style="color: #666;">Secure Access Portal</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Log In", use_container_width=True):
                    if authenticate_user(u, p):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        st.rerun()
                    else: st.error("Wrong credentials")
        with tab2:
            with st.form("register"):
                u = st.text_input("New Username")
                p = st.text_input("New Password", type="password")
                if st.form_submit_button("Sign Up", use_container_width=True):
                    success, msg = register_user(u, p)
                    if success: st.success(msg)
                    else: st.error(msg)

def render_file_view():
    file_data = st.session_state['selected_file']
    
    # Back button
    if st.button("⬅️ Back to Search"):
        st.session_state['selected_file'] = None
        st.session_state['current_page'] = "search"
        st.rerun()
    
    # File Header
    st.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; margin: 20px 0;">
            <h2 style="margin:0;">📄 {file_data['filename']}</h2>
            <p style="margin:0; opacity: 0.7;">Word Count: {file_data['total_words']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Content
    st.text_area("File Content", file_data['content'], height=500)
    
    st.download_button("📥 Download File", file_data['content'], file_data['filename'])

def render_search_page():
    # Welcome Banner
    st.markdown(f"""
        <div style="padding: 20px; border-radius: 15px; margin-bottom: 30px; background: rgba(255,255,255,0.1);">
            <h1 style="margin:0;">🔎 Knowledge Base</h1>
            <p style="margin:0; opacity:0.8;">Welcome back, <b>{st.session_state['username']}</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    engine = load_engine()
    query = st.text_input("", placeholder="🔍 Search documents (e.g. 'invoice', 'plan')...")
    
    if query:
        log_search(st.session_state['username'], query)
        results = engine.search(query)
        
        st.markdown(f"### Found {len(results)} matches")
        
        if not results:
            st.warning("No documents found.")
        else:
            for res in results:
                # Card HTML
                st.markdown(f"""
                    <div class="doc-card">
                        <div style="display:flex; justify-content:space-between;">
                            <h3 style="margin:0;">📄 {res['filename']}</h3>
                            <span style="background:#0072ff; color:white; padding:2px 10px; border-radius:10px; font-size:0.8em;">
                                Score: {res['score']:.2f}
                            </span>
                        </div>
                        <p style="font-style:italic; opacity:0.7; margin-top:10px;">
                            "{res['content'][:150].replace(chr(10), ' ')}..."
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Button Logic
                col1, col2 = st.columns([0.85, 0.15])
                with col2:
                    if st.button("Open ↗", key=f"btn_{res['filename']}"):
                        st.session_state['selected_file'] = res
                        st.session_state['current_page'] = "file_view"
                        st.rerun()

def render_admin_page():
    st.markdown("<h1>🛡️ Admin Dashboard</h1>", unsafe_allow_html=True)
    
    if st.button("⬅️ Exit"):
        st.session_state['current_page'] = "search"
        st.rerun()
    
    st.markdown("---")
    
    # Tabs
    t1, t2, t3 = st.tabs(["📂 Manage Files", "📊 Logs", "👥 Activity"])
    
    # MERGED UPLOAD & DELETE SECTION
    with t1:
        st.info("Upload new files or delete existing ones.")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 📤 Upload")
            uploaded = st.file_uploader("Drag & Drop Text Files", accept_multiple_files=True)
            if uploaded:
                for f in uploaded:
                    with open(os.path.join(DOCS_DIR, f.name), "wb") as w: w.write(f.getbuffer())
                st.success("Files uploaded successfully!")
                st.cache_resource.clear()
                st.rerun()

        with col_right:
            st.markdown("### 🗑️ Database Content")
            files = os.listdir(DOCS_DIR)
            if not files:
                st.caption("No files in database.")
            else:
                for f in files:
                    # Clean layout for delete button
                    c1, c2 = st.columns([0.8, 0.2])
                    c1.text(f)
                    if c2.button("❌", key=f"del_{f}"):
                        os.remove(os.path.join(DOCS_DIR, f))
                        st.cache_resource.clear()
                        st.rerun()

    with t2:
        st.subheader("User Searches")
        if os.path.exists(LOG_FILE):
            st.dataframe(pd.read_csv(LOG_FILE), use_container_width=True)
        else: st.caption("No logs yet.")

    with t3:
        st.subheader("Login History")
        if os.path.exists(LOGIN_ACTIVITY_FILE):
            st.dataframe(pd.read_csv(LOGIN_ACTIVITY_FILE), use_container_width=True)
        else: st.caption("No login history.")

# ==========================================
# 5. MAIN APP CONTROLLER
# ==========================================

apply_theme()
init_dbs()

if not st.session_state['logged_in']:
    render_login_page()
else:
    with st.sidebar:
        # Profile
        st.markdown(f"""
            <div style="text-align:center">
                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed={st.session_state['username']}" class="profile-img">
                <h3 style="margin:0">{st.session_state['username']}</h3>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Settings
        with st.expander("⚙️ Settings"):
            # Theme
            st.caption("Theme")
            new_theme = st.selectbox("Mode", ["Light", "Dark"], label_visibility="collapsed",
                                   index=0 if st.session_state['theme']=="Light" else 1)
            if new_theme != st.session_state['theme']:
                st.session_state['theme'] = new_theme
                st.rerun()
            
            st.divider()
            
            # History
            st.caption("My History")
            if os.path.exists(LOG_FILE):
                df = pd.read_csv(LOG_FILE)
                my_logs = df[df['User'] == st.session_state['username']]
                if not my_logs.empty:
                    st.dataframe(my_logs[['Timestamp', 'Query']], hide_index=True)
                else: st.markdown("*No searches yet*")
            
            st.divider()
            
            # Admin Unlock
            st.caption("Admin Access")
            if not st.session_state['admin_unlocked']:
                pwd = st.text_input("Key", type="password", label_visibility="collapsed")
                if st.button("Unlock"):
                    if pwd == "admin123":
                        st.session_state['admin_unlocked'] = True
                        st.session_state['current_page'] = "admin"
                        st.rerun()
                    else: st.error("Invalid")
            else:
                if st.button("Go to Admin"):
                    st.session_state['current_page'] = "admin"
                    st.rerun()
                if st.button("Lock Admin"):
                    st.session_state['admin_unlocked'] = False
                    st.session_state['current_page'] = "search"
                    st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state['logged_in'] = False
            st.session_state['admin_unlocked'] = False
            st.session_state['current_page'] = "search"
            st.rerun()

    # Routing
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
