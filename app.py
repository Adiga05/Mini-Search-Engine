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

st.set_page_config(page_title="DocSearch Pro", page_icon="🚀", layout="wide")

DOCS_DIR = "docs"
LOG_FILE = "search_logs.csv"
USER_DB_FILE = "users.csv"

# Ensure directories exist
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

# Initialize Session State
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'theme' not in st.session_state: st.session_state['theme'] = "Light"
if 'admin_unlocked' not in st.session_state: st.session_state['admin_unlocked'] = False

# ==========================================
# 2. STYLING & THEMES
# ==========================================
def apply_theme():
    """Injects CSS based on the selected theme."""
    if st.session_state['theme'] == "Dark":
        st.markdown("""
            <style>
            .stApp { background-color: #0E1117; color: #FAFAFA; }
            section[data-testid="stSidebar"] { background-color: #262730; }
            div[data-testid="stExpander"] { background-color: #262730; border: 1px solid #4F4F4F; }
            .stTextInput > div > div > input { background-color: #262730; color: white; }
            </style>
            """, unsafe_allow_html=True)
    else:
        # Colorful Gradient for Light Mode
        st.markdown("""
            <style>
            .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); color: black; }
            section[data-testid="stSidebar"] { background-color: #ffffff; box-shadow: 2px 0 5px rgba(0,0,0,0.1); }
            div[data-testid="stExpander"] { background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            </style>
            """, unsafe_allow_html=True)

# ==========================================
# 3. BACKEND LOGIC (Auth, Search, Logs)
# ==========================================

def init_user_db():
    if not os.path.exists(USER_DB_FILE):
        df = pd.DataFrame(columns=["username", "password", "created_at"])
        df.loc[0] = ["admin", "admin123", datetime.now().strftime("%Y-%m-%d")]
        df.to_csv(USER_DB_FILE, index=False)

def register_user(username, password):
    init_user_db()
    df = pd.read_csv(USER_DB_FILE)
    if username in df['username'].values:
        return False, "Username taken."
    new_user = pd.DataFrame([[username, password, datetime.now().strftime("%Y-%m-%d")]], 
                            columns=["username", "password", "created_at"])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USER_DB_FILE, index=False)
    return True, "Success!"

def authenticate_user(username, password):
    init_user_db()
    df = pd.read_csv(USER_DB_FILE)
    user_row = df[(df['username'] == username) & (df['password'] == password)]
    return not user_row.empty

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
        with open(os.path.join(DOCS_DIR, "welcome.txt"), "w") as f: f.write("Welcome.")
        files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    for f in files: engine.add_file(f)
    return engine

# ==========================================
# 4. PAGES
# ==========================================

# --- PAGE 1: LOGIN ---
def page_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Access Portal</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    if authenticate_user(u, p):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        st.rerun()
                    else: st.error("Failed.")
        with tab2:
            with st.form("register"):
                u = st.text_input("New Username")
                p = st.text_input("New Password", type="password")
                if st.form_submit_button("Create Account"):
                    success, msg = register_user(u, p)
                    if success: st.success(msg)
                    else: st.error(msg)

# --- PAGE 2: SEARCH ENGINE (User View) ---
def page_search_engine():
    st.title(f"🔎 Hello, {st.session_state['username']}")
    
    # Tabs for Search vs History
    tab_search, tab_history = st.tabs(["🔍 Search", "🕒 My History"])
    
    with tab_search:
        engine = load_engine()
        query = st.text_input("Find documents:", placeholder="Keywords...")
        if query:
            log_search(st.session_state['username'], query)
            results = engine.search(query)
            if results:
                st.success(f"Found {len(results)} matches.")
                for res in results:
                    with st.expander(f"📄 {res['filename']} (Score: {res['score']:.2f})"):
                        st.markdown(res['content'])
            else:
                st.warning("No results found.")

    with tab_history:
        st.subheader("Your Search Activity")
        if os.path.exists(LOG_FILE):
            df = pd.read_csv(LOG_FILE)
            user_df = df[df['User'] == st.session_state['username']]
            if not user_df.empty:
                st.dataframe(user_df[['Timestamp', 'Query']], use_container_width=True)
            else:
                st.info("No history yet.")
        else:
            st.info("No logs database.")

# --- PAGE 3: ADMIN DASHBOARD (Separate View) ---
def page_admin_dashboard():
    st.title("🛡️ Admin Command Center")
    
    # Locked State
    if not st.session_state['admin_unlocked']:
        st.markdown("### 🔒 Restricted Area")
        password = st.text_input("Enter Admin Password to Unlock:", type="password")
        if st.button("Unlock"):
            if password == "admin123":
                st.session_state['admin_unlocked'] = True
                st.rerun()
            else:
                st.error("Access Denied.")
        return

    # Unlocked State
    if st.button("Lock Dashboard"):
        st.session_state['admin_unlocked'] = False
        st.rerun()

    t1, t2, t3 = st.tabs(["📂 File Manager", "👥 User DB", "📊 Global Logs"])
    
    with t1:
        st.subheader("Database Management")
        uploaded = st.file_uploader("Upload New Files", accept_multiple_files=True)
        if uploaded:
            for f in uploaded:
                with open(os.path.join(DOCS_DIR, f.name), "wb") as w: w.write(f.getbuffer())
            st.success("Uploaded.")
            st.cache_resource.clear()
        
        st.write("---")
        st.write("**Current Files:**")
        for f in os.listdir(DOCS_DIR):
            c1, c2 = st.columns([0.9, 0.1])
            c1.text(f)
            if c2.button("❌", key=f):
                os.remove(os.path.join(DOCS_DIR, f))
                st.cache_resource.clear()
                st.rerun()

    with t2:
        st.subheader("Registered Users")
        if os.path.exists(USER_DB_FILE):
            st.dataframe(pd.read_csv(USER_DB_FILE), use_container_width=True)

    with t3:
        st.subheader("Global Search Logs")
        if os.path.exists(LOG_FILE):
            st.dataframe(pd.read_csv(LOG_FILE), use_container_width=True)

# ==========================================
# 5. MAIN CONTROLLER
# ==========================================

apply_theme() # Inject CSS

if not st.session_state['logged_in']:
    page_login()
else:
    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=50)
        st.write(f"User: **{st.session_state['username']}**")
        
        st.markdown("---")
        # Navigation Menu
        page_selection = st.radio("Go to:", ["Search Engine", "Admin Dashboard"])
        
        st.markdown("---")
        # Theme Toggle
        st.subheader("Appearance")
        theme = st.radio("Theme", ["Light", "Dark"], index=0 if st.session_state['theme']=="Light" else 1)
        if theme != st.session_state['theme']:
            st.session_state['theme'] = theme
            st.rerun()
            
        st.markdown("---")
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['admin_unlocked'] = False
            st.rerun()

    # --- PAGE ROUTING ---
    if page_selection == "Search Engine":
        page_search_engine()
    elif page_selection == "Admin Dashboard":
        page_admin_dashboard()
