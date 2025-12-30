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
state_keys = {
    'logged_in': False,
    'username': "",
    'theme': "Light",
    'admin_unlocked': False,
    'current_page': "search",
    'selected_file': None
}

for key, val in state_keys.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ==========================================
# 2. ADVANCED STYLING (CSS)
# ==========================================
def apply_theme():
    """Injects CSS based on the selected theme."""
    
    # 1. Hide Streamlit Defaults (Menu, Footer, Header)
    hide_streamlit_style = """
        <style>
        /* Hides the top right hamburger menu */
        #MainMenu {visibility: hidden;}
        
        /* Hides the 'Make with Streamlit' footer and 'Manage App' button */
        footer {visibility: hidden;}
        
        /* Hides the header line at the top */
        header {visibility: hidden;}
        
        /* Hides the 'Deploy' button if visible */
        .stDeployButton {display:none;}
        </style>
        """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    # 2. Your Custom Theme CSS
    common_css = """
        /* Rounded Buttons */
        .stButton > button {
            border-radius: 12px;
            padding: 8px 16px;
            font-weight: 600;
        }
        /* Profile Image Styling */
        .profile-img {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            margin-bottom: 10px;
            border: 3px solid #4b6cb7;
        }
    """
    
    if st.session_state['theme'] == "Dark":
        st.markdown(f"""
            <style>
            {common_css}
            .stApp {{ background-color: #0E1117; color: #E6E6E6; }}
            section[data-testid="stSidebar"] {{ background-color: #1A1C24; border-right: 1px solid #2D2D2D; }}
            div[data-testid="stExpander"] {{ background-color: #262730; border: 1px solid #4F4F4F; border-radius: 8px; }}
            .stTextInput > div > div > input {{ background-color: #262730; color: white; border-radius: 10px; }}
            </style>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <style>
            {common_css}
            .stApp {{ background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); color: #1a1a1a; }}
            section[data-testid="stSidebar"] {{ background-color: #ffffff; box-shadow: 4px 0 10px rgba(0,0,0,0.05); }}
            div[data-testid="stExpander"] {{ background: white; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: none; }}
            .stTextInput > div > div > input {{ border-radius: 10px; border: 1px solid #ddd; }}
            
            div.stButton > button {{
                background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
                color: white;
                border: none;
            }}
            div.stButton > button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }}
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
    """Logs every login attempt."""
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
# 4. VIEW FUNCTIONS
# ==========================================

def render_login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #4b6cb7;'>🔒 DocSearch Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Internal Document Retrieval System</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Access Dashboard", use_container_width=True):
                    if authenticate_user(u, p):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        st.rerun()
                    else: st.error("Invalid Credentials")
        with tab2:
            with st.form("register"):
                u = st.text_input("Choose Username")
                p = st.text_input("Choose Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    success, msg = register_user(u, p)
                    if success: st.success(msg)
                    else: st.error(msg)

def render_file_view():
    file_data = st.session_state['selected_file']
    
    # Header
    c1, c2 = st.columns([0.2, 0.8])
    with c1:
        if st.button("⬅️ Back"):
            st.session_state['selected_file'] = None
            st.session_state['current_page'] = "search"
            st.rerun()
    with c2:
        st.title(f"📄 {file_data['filename']}")
    
    st.markdown("---")
    
    # File Content Display
    st.info(f"Word Count: {file_data['total_words']}")
    st.text_area("Content Preview", file_data['content'], height=400)
    
    # Download
    st.download_button(
        label="📥 Download Original File",
        data=file_data['content'],
        file_name=file_data['filename'],
        mime='text/plain',
        use_container_width=True
    )

def render_search_page():
    st.markdown("## 🔎 Document Search")
    st.caption(f"Searching database as: {st.session_state['username']}")
    
    engine = load_engine()
    
    # Search Bar
    query = st.text_input("", placeholder="Type keywords here (e.g. invoice, report)...")
    
    if query:
        log_search(st.session_state['username'], query)
        results = engine.search(query)
        
        st.markdown("### Results")
        if not results:
            st.warning("No matches found.")
        else:
            for res in results:
                with st.container():
                    # Card Layout
                    c1, c2 = st.columns([0.85, 0.15])
                    with c1:
                        st.markdown(f"**{res['filename']}**")
                        st.caption(f"Relevance Score: {res['score']:.2f}")
                        st.markdown(f"*{res['content'][:80].replace(chr(10), ' ')}...*")
                    with c2:
                        if st.button("Open", key=f"btn_{res['filename']}"):
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
    
    # Admin Tabs
    t1, t2, t3, t4 = st.tabs(["📤 Uploads", "🗑️ Delete", "📊 Logs", "👥 Logins"])
    
    with t1:
        st.subheader("Add Documents")
        uploaded = st.file_uploader("Drop files", accept_multiple_files=True)
        if uploaded:
            for f in uploaded:
                with open(os.path.join(DOCS_DIR, f.name), "wb") as w: w.write(f.getbuffer())
            st.success("Uploaded!")
            st.cache_resource.clear()

    with t2:
        st.subheader("Manage Database")
        if st.checkbox("Show Files for Deletion"):
            for f in os.listdir(DOCS_DIR):
                c1, c2 = st.columns([0.9, 0.1])
                c1.text(f)
                if c2.button("❌", key=f"del_{f}"):
                    os.remove(os.path.join(DOCS_DIR, f))
                    st.cache_resource.clear()
                    st.rerun()

    with t3:
        st.subheader("Search Queries")
        if os.path.exists(LOG_FILE):
            st.dataframe(pd.read_csv(LOG_FILE), use_container_width=True)

    with t4:
        st.subheader("Login Activity")
        if os.path.exists(LOGIN_ACTIVITY_FILE):
            st.dataframe(pd.read_csv(LOGIN_ACTIVITY_FILE), use_container_width=True)
        else:
            st.info("No login activity recorded yet.")

# ==========================================
# 5. MAIN APP CONTROLLER
# ==========================================

apply_theme()
init_dbs()

if not st.session_state['logged_in']:
    render_login_page()
else:
    # --- SIDEBAR SETTINGS ---
    with st.sidebar:
        # Profile Section
        st.markdown("""
            <div style="text-align: center;">
                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed={}" class="profile-img">
                <h3>{}</h3>
            </div>
        """.format(st.session_state['username'], st.session_state['username']), unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("**⚙️ Settings Menu**")

        # 1. THEME
        with st.expander("🎨 Appearance"):
            theme = st.selectbox("Choose Theme", ["Light", "Dark"], 
                               index=0 if st.session_state['theme']=="Light" else 1)
            if theme != st.session_state['theme']:
                st.session_state['theme'] = theme
                st.rerun()

        # 2. HISTORY
        with st.expander("🕒 My History"):
            if os.path.exists(LOG_FILE):
                df = pd.read_csv(LOG_FILE)
                user_df = df[df['User'] == st.session_state['username']]
                if not user_df.empty:
                    st.dataframe(user_df[['Timestamp', 'Query']], hide_index=True)
                else:
                    st.caption("No recent searches.")

        # 3. ADMIN
        with st.expander("🛡️ Admin Zone"):
            if not st.session_state['admin_unlocked']:
                admin_pw = st.text_input("Admin Key", type="password")
                if st.button("Unlock"):
                    if admin_pw == "admin123":
                        st.session_state['admin_unlocked'] = True
                        st.session_state['current_page'] = "admin"
                        st.rerun()
                    else: st.error("Invalid")
            else:
                st.success("Admin Unlocked")
                if st.button("Go to Dashboard"):
                    st.session_state['current_page'] = "admin"
                    st.rerun()
                if st.button("Lock Dashboard"):
                    st.session_state['admin_unlocked'] = False
                    st.session_state['current_page'] = "search"
                    st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['admin_unlocked'] = False
            st.session_state['current_page'] = "search"
            st.rerun()

    # --- PAGE ROUTING ---
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
