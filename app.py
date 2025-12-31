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
    """Injects Advanced CSS with Gradients and Glassmorphism."""
    
    # Common CSS for Fonts and Transitions
    base_css = """
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }
        
        /* Smooth transitions */
        .stButton > button, div[data-testid="stExpander"], input {
            transition: all 0.3s ease-in-out;
        }

        /* Card Styling for Search Results */
        .result-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Profile Image */
        .profile-img {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            object-fit: cover;
            margin-bottom: 15px;
            border: 4px solid white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
    </style>
    """

    if st.session_state['theme'] == "Dark":
        st.markdown(f"""
            {base_css}
            <style>
            /* Dark Mode Gradient */
            .stApp {{
                background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
                color: #ffffff;
            }}
            
            /* Sidebar Dark */
            section[data-testid="stSidebar"] {{
                background-color: rgba(15, 32, 39, 0.95);
                border-right: 1px solid #2c5364;
            }}

            /* Inputs Dark */
            .stTextInput > div > div > input {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid #2c5364;
                border-radius: 10px;
            }}
            
            /* Buttons Dark */
            .stButton > button {{
                background: linear-gradient(90deg, #8E2DE2, #4A00E0);
                color: white;
                border: none;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(74, 0, 224, 0.4);
            }}
            .stButton > button:hover {{
                transform: scale(1.02);
                box-shadow: 0 6px 20px rgba(74, 0, 224, 0.6);
            }}

            /* Expanders Dark */
            div[data-testid="stExpander"] {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }}
            </style>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            {base_css}
            <style>
            /* Light Mode Gradient */
            .stApp {{
                background: linear-gradient(120deg, #a1c4fd 0%, #c2e9fb 100%);
                color: #2c3e50;
            }}
            
            /* Sidebar Light */
            section[data-testid="stSidebar"] {{
                background-color: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(10px);
                box-shadow: 5px 0 15px rgba(0,0,0,0.05);
            }}

            /* Inputs Light */
            .stTextInput > div > div > input {{
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid #a1c4fd;
                border-radius: 10px;
                color: #333;
            }}
            
            /* Buttons Light - Vibrant Gradients */
            .stButton > button {{
                background: linear-gradient(90deg, #00c6ff, #0072ff);
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 600;
                box-shadow: 0 4px 15px rgba(0, 114, 255, 0.3);
            }}
            .stButton > button:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(0, 114, 255, 0.5);
            }}

            /* Expanders Light */
            div[data-testid="stExpander"] {{
                background: white;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                border: none;
            }}
            
            /* Result Cards specific for Light Mode */
            .result-card {{
                background: white;
                color: #333;
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
    # Centered Glass Card for Login
    st.markdown("""
        <style>
        .login-container {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(15px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center;
            border: 1px solid rgba(255,255,255,0.5);
            margin-top: 50px;
        }
        h1 { color: #0072ff; font-weight: 700; }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
            <div class='login-container'>
                <h1>🚀 Mini Engine</h1>
                <p>Secure Internal Document Search</p>
            </div>
            <br>
        """, unsafe_allow_html=True)
        
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
    
    # Header with styling
    c1, c2 = st.columns([0.2, 0.8])
    with c1:
        if st.button("⬅️ Back"):
            st.session_state['selected_file'] = None
            st.session_state['current_page'] = "search"
            st.rerun()
    with c2:
        st.markdown(f"<h2 style='color: #0072ff;'>📄 {file_data['filename']}</h2>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # File Content Display in a clean box
    st.info(f"📊 Word Count: {file_data['total_words']}")
    st.text_area("Content Preview", file_data['content'], height=500)
    
    # Download Button with custom logic
    st.download_button(
        label="📥 Download Original File",
        data=file_data['content'],
        file_name=file_data['filename'],
        mime='text/plain',
        use_container_width=True
    )

def render_search_page():
    st.markdown(f"""
        <div style="background: rgba(255,255,255,0.2); padding: 20px; border-radius: 15px; margin-bottom: 20px;">
            <h1 style="margin:0;">🔎 Knowledge Base</h1>
            <p style="margin:0; opacity: 0.8;">Searching as: <b>{st.session_state['username']}</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    engine = load_engine()
    
    # Search Bar
    query = st.text_input("", placeholder="Type keywords here (e.g. project, data, finance)...")
    
    if query:
        log_search(st.session_state['username'], query)
        results = engine.search(query)
        
        st.markdown(f"### Found {len(results)} Matches")
        
        if not results:
            st.warning("No matches found.")
        else:
            for res in results:
                # Custom HTML Card for visuals
                st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(255,255,255,0.9), rgba(255,255,255,0.6));
                        padding: 20px;
                        border-radius: 15px;
                        margin-bottom: 10px;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
                        border-left: 5px solid #0072ff;
                    ">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h3 style="margin:0; color: #333;">📄 {res['filename']}</h3>
                            <span style="
                                background: #0072ff; 
                                color: white; 
                                padding: 5px 10px; 
                                border-radius: 15px; 
                                font-size: 0.8rem;
                                font-weight: bold;
                            ">Score: {res['score']:.2f}</span>
                        </div>
                        <p style="color: #666; font-style: italic; margin-top: 10px;">
                            "{res['content'][:120].replace(chr(10), ' ')}..."
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
                # The Action Button (Native Streamlit)
                col1, col2 = st.columns([0.85, 0.15])
                with col2:
                    if st.button("Open File ↗", key=f"btn_{res['filename']}"):
                        st.session_state['selected_file'] = res
                        st.session_state['current_page'] = "file_view"
                        st.rerun()

def render_admin_page():
    st.markdown("<h1 style='color: #d946ef;'>🛡️ Admin Dashboard</h1>", unsafe_allow_html=True)
    if st.button("⬅️ Exit Admin Mode"):
        st.session_state['current_page'] = "search"
        st.rerun()
    
    st.markdown("---")
    
    # Admin Tabs with Icons
    t1, t2, t3, t4 = st.tabs(["📤 Uploads", "🗑️ Delete", "📊 Logs", "👥 Logins"])
    
    with t1:
        st.subheader("Add Documents")
        uploaded = st.file_uploader("Drop text files here", accept_multiple_files=True)
        if uploaded:
            for f in uploaded:
                with open(os.path.join(DOCS_DIR, f.name), "wb") as w: w.write(f.getbuffer())
            st.success("Uploaded successfully!")
            st.cache_resource.clear()

    with t2:
        st.subheader("Manage Database")
        if st.checkbox("Unlock Deletion Mode"):
            for f in os.listdir(DOCS_DIR):
                c1, c2 = st.columns([0.9, 0.1])
                c1.markdown(f"**{f}**")
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
                <h3 style="margin-top:0;">{}</h3>
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
