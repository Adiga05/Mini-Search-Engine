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
if 'current_page' not in st.session_state: st.session_state['current_page'] = "search" # search, admin, file_view
if 'selected_file' not in st.session_state: st.session_state['selected_file'] = None

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
            .stButton > button { border-radius: 20px; }
            </style>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); color: black; }
            section[data-testid="stSidebar"] { background-color: #ffffff; box-shadow: 2px 0 5px rgba(0,0,0,0.1); }
            div[data-testid="stExpander"] { background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .stButton > button { border-radius: 20px; background-color: #4b6cb7; color: white; }
            </style>
            """, unsafe_allow_html=True)

# ==========================================
# 3. BACKEND LOGIC
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
# 4. VIEW FUNCTIONS (PAGES)
# ==========================================

def render_login_page():
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

def render_file_view():
    """Displays a single file in a dedicated 'page'."""
    file_data = st.session_state['selected_file']
    
    if st.button("⬅️ Back to Search"):
        st.session_state['selected_file'] = None
        st.session_state['current_page'] = "search"
        st.rerun()
    
    st.markdown(f"# 📄 {file_data['filename']}")
    st.caption(f"Word Count: {file_data['total_words']}")
    st.divider()
    
    # Display Content in a clean box
    st.code(file_data['content'], language='markdown') # Using code block for raw text preservation
    
    st.download_button(
        label="📥 Download File",
        data=file_data['content'],
        file_name=file_data['filename'],
        mime='text/plain'
    )

def render_search_page():
    st.title(f"🔎 DocSearch")
    st.caption("Search Internal Documents")
    
    engine = load_engine()
    query = st.text_input("Keywords:", placeholder="Type to search...")
    
    if query:
        log_search(st.session_state['username'], query)
        results = engine.search(query)
        
        if not results:
            st.warning("No matches found.")
        else:
            st.success(f"Found {len(results)} documents.")
            for res in results:
                # Result Card
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    st.markdown(f"**📄 {res['filename']}** (Relevance: {res['score']:.2f})")
                    # Preview snippet (first 100 chars)
                    snippet = res['content'][:100].replace("\n", " ") + "..."
                    st.caption(snippet)
                with col2:
                    # The "Open" button triggers a page switch
                    if st.button("Open ↗️", key=f"btn_{res['filename']}"):
                        st.session_state['selected_file'] = res
                        st.session_state['current_page'] = "file_view"
                        st.rerun()
                st.divider()

def render_admin_page():
    st.title("🛡️ Admin Dashboard")
    
    if st.button("⬅️ Exit Admin Mode"):
        st.session_state['current_page'] = "search"
        st.rerun()
        
    st.markdown("---")
    
    # Tab 1: Upload (Clean, no list shown)
    st.subheader("📤 Upload Documents")
    uploaded = st.file_uploader("Drop .txt files here", accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            with open(os.path.join(DOCS_DIR, f.name), "wb") as w: w.write(f.getbuffer())
        st.success("Uploaded successfully.")
        st.cache_resource.clear()

    st.markdown("---")
    
    # Tab 2: Delete (Hidden by default as requested)
    with st.expander("🗑️ Delete Files (Click to View Current Files)"):
        st.warning("Warning: Deletions are permanent.")
        for f in os.listdir(DOCS_DIR):
            c1, c2 = st.columns([0.9, 0.1])
            c1.text(f)
            if c2.button("❌", key=f"del_{f}"):
                os.remove(os.path.join(DOCS_DIR, f))
                st.cache_resource.clear()
                st.rerun()

    st.markdown("---")
    
    # Tab 3: Global Logs
    st.subheader("📊 Global Search Logs")
    if os.path.exists(LOG_FILE):
        st.dataframe(pd.read_csv(LOG_FILE), use_container_width=True)

# ==========================================
# 5. MAIN APP CONTROLLER
# ==========================================

apply_theme()

if not st.session_state['logged_in']:
    render_login_page()
else:
    # --- SIDEBAR SETTINGS ---
    with st.sidebar:
        st.write(f"User: **{st.session_state['username']}**")
        
        # SETTINGS MENU
        with st.expander("⚙️ Settings", expanded=False):
            # 1. Theme
            st.markdown("**Theme**")
            theme = st.radio("Mode", ["Light", "Dark"], label_visibility="collapsed", index=0 if st.session_state['theme']=="Light" else 1)
            if theme != st.session_state['theme']:
                st.session_state['theme'] = theme
                st.rerun()
            
            st.divider()
            
            # 2. History
            st.markdown("**User History**")
            if st.checkbox("Show My History"):
                if os.path.exists(LOG_FILE):
                    df = pd.read_csv(LOG_FILE)
                    user_df = df[df['User'] == st.session_state['username']]
                    st.dataframe(user_df[['Timestamp', 'Query']], hide_index=True)
                else:
                    st.caption("No history.")
            
            st.divider()

            # 3. Admin Login
            st.markdown("**Admin Access**")
            if not st.session_state['admin_unlocked']:
                admin_pw = st.text_input("Password", type="password", placeholder="Enter Admin Key")
                if st.button("Unlock Admin"):
                    if admin_pw == "admin123":
                        st.session_state['admin_unlocked'] = True
                        st.session_state['current_page'] = "admin"
                        st.rerun()
                    else:
                        st.error("Invalid")
            else:
                if st.button("Go to Admin Dashboard"):
                    st.session_state['current_page'] = "admin"
                    st.rerun()
                if st.button("Lock Admin"):
                    st.session_state['admin_unlocked'] = False
                    st.session_state['current_page'] = "search"
                    st.rerun()

        st.markdown("---")
        # Explicit Logout Button
        if st.button("🚪 Logout"):
            st.session_state['logged_in'] = False
            st.session_state['admin_unlocked'] = False
            st.session_state['current_page'] = "search"
            st.rerun()

    # --- PAGE ROUTING LOGIC ---
    if st.session_state['current_page'] == "search":
        render_search_page()
    elif st.session_state['current_page'] == "file_view":
        render_file_view()
    elif st.session_state['current_page'] == "admin":
        if st.session_state['admin_unlocked']:
            render_admin_page()
        else:
            st.error("Access Denied. Please unlock in Settings.")
            st.session_state['current_page'] = "search"
