import streamlit as st
import os
import re
import math
import glob
import pandas as pd
from datetime import datetime
from collections import defaultdict, Counter

# ==========================================
# 1. CONFIGURATION & CSS STYLING
# ==========================================

st.set_page_config(page_title="DocSearch Pro", page_icon="🌈", layout="wide")

DOCS_DIR = "docs"
LOG_FILE = "search_logs.csv"
USER_DB_FILE = "users.csv"

# Ensure directories exist
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

# --- CUSTOM COLORFUL UI (CSS) ---
def apply_custom_style():
    st.markdown("""
        <style>
        /* Main Background Gradient */
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            box-shadow: 2px 0 5px rgba(0,0,0,0.1);
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #2c3e50;
            font-family: 'Helvetica Neue', sans-serif;
        }
        
        /* Card-like containers for results */
        div[data-testid="stExpander"] {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border: none;
            margin-bottom: 10px;
        }
        
        /* Custom Buttons */
        div.stButton > button {
            background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 20px;
            transition: all 0.3s;
        }
        div.stButton > button:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        /* Input Fields */
        div[data-baseweb="input"] {
            border-radius: 8px;
            border: 1px solid #ced4da;
            background: white;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. USER MANAGEMENT SYSTEM
# ==========================================

def init_user_db():
    """Creates the user database if it doesn't exist."""
    if not os.path.exists(USER_DB_FILE):
        df = pd.DataFrame(columns=["username", "password", "created_at"])
        # Add default admin
        df.loc[0] = ["admin", "admin123", datetime.now().strftime("%Y-%m-%d")]
        df.to_csv(USER_DB_FILE, index=False)

def register_user(username, password):
    """Adds a new user to the CSV."""
    init_user_db()
    df = pd.read_csv(USER_DB_FILE)
    
    if username in df['username'].values:
        return False, "Username already taken!"
    
    new_user = pd.DataFrame([[username, password, datetime.now().strftime("%Y-%m-%d")]], 
                            columns=["username", "password", "created_at"])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USER_DB_FILE, index=False)
    return True, "Account created successfully! Please log in."

def authenticate_user(username, password):
    """Checks credentials against CSV."""
    init_user_db()
    df = pd.read_csv(USER_DB_FILE)
    user_row = df[(df['username'] == username) & (df['password'] == password)]
    return not user_row.empty

# ==========================================
# 3. SEARCH ENGINE LOGIC (Same as before)
# ==========================================
class SearchEngine:
    def __init__(self):
        self.inverted_index = defaultdict(list)
        self.documents = {} 
        self.doc_count = 0

    def _tokenize(self, text):
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens

    def add_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return 

        tokens = self._tokenize(content)
        if not tokens: return

        doc_id = self.doc_count
        self.documents[doc_id] = {
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "total_words": len(tokens),
            "content": content
        }
        self.doc_count += 1
        term_counts = Counter(tokens)
        for term, count in term_counts.items():
            self.inverted_index[term].append({"doc_id": doc_id, "tf": count})

    def search(self, query):
        query_tokens = self._tokenize(query)
        if not query_tokens: return []
        doc_scores = defaultdict(float)
        for token in query_tokens:
            if token not in self.inverted_index: continue
            postings = self.inverted_index[token]
            idf = math.log(self.doc_count / (len(postings) + 1))
            for post in postings:
                doc_id = post['doc_id']
                tf = post['tf'] / self.documents[doc_id]['total_words']
                doc_scores[doc_id] += tf * idf
        results = []
        for doc_id, score in doc_scores.items():
            results.append(self.documents[doc_id])
            results[-1]['score'] = score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

@st.cache_resource
def load_engine():
    engine = SearchEngine()
    files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    if not files:
        with open(os.path.join(DOCS_DIR, "welcome.txt"), "w") as f:
            f.write("Welcome to the system.")
        files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    for f in files:
        engine.add_file(f)
    return engine

def log_search(username, query):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("Timestamp,User,Query\n")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp},{username},{query}\n")

# ==========================================
# 4. INITIALIZATION
# ==========================================

# Initialize Session State
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False

init_user_db() # Ensure user DB exists

# ==========================================
# 5. AUTHENTICATION PAGE
# ==========================================
def auth_page():
    apply_custom_style()
    
    st.markdown("<h1 style='text-align: center; color: #4b6cb7;'>Mini Engine</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Secure Access Point</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Create Tabs for Login and Register
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        # --- LOGIN TAB ---
        with tab1:
            with st.form("login_form"):
                user = st.text_input("Username")
                pw = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Access Dashboard")
                
                if submitted:
                    if authenticate_user(user, pw):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = user
                        st.success("Login Successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
        
        # --- REGISTER TAB ---
        with tab2:
            with st.form("register_form"):
                new_user = st.text_input("Choose Username")
                new_pw = st.text_input("Choose Password", type="password")
                reg_submitted = st.form_submit_button("Sign Up")
                
                if reg_submitted:
                    if new_user and new_pw:
                        success, msg = register_user(new_user, new_pw)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.warning("Please fill all fields.")

# ==========================================
# 6. MAIN APPLICATION
# ==========================================
def main_app():
    apply_custom_style()
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.title(f"Hi, {st.session_state['username']}")
        
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['is_admin'] = False
            st.rerun()
            
        st.markdown("---")
        
        # Admin Access
        with st.expander("🛠️ Admin Tools"):
            admin_pass = st.text_input("Admin Key", type="password")
            # Secret key is 'admin123'
            if admin_pass == "admin123":
                st.session_state['is_admin'] = True
                st.success("Unlocked!")
            elif admin_pass:
                st.session_state['is_admin'] = False
                st.error("Access Denied")

    # --- ADMIN DASHBOARD ---
    if st.session_state['is_admin']:
        st.markdown("### 🛡️ Admin Command Center")
        
        # Admin Tabs
        t1, t2, t3 = st.tabs(["📂 File Manager", "👥 User Database", "📊 Search Logs"])
        
        with t1:
            st.info("Manage database documents here.")
            uploaded = st.file_uploader("Upload .txt files", accept_multiple_files=True)
            if uploaded:
                for f in uploaded:
                    with open(os.path.join(DOCS_DIR, f.name), "wb") as w:
                        w.write(f.getbuffer())
                st.success("Files uploaded!")
                st.cache_resource.clear()
            
            # Delete interface
            st.write("**Existing Files:**")
            for f in os.listdir(DOCS_DIR):
                c1, c2 = st.columns([0.8, 0.2])
                c1.text(f)
                if c2.button("Remove", key=f):
                    os.remove(os.path.join(DOCS_DIR, f))
                    st.cache_resource.clear()
                    st.rerun()

        with t2:
            st.warning("⚠️ Confidential: Registered Users")
            if os.path.exists(USER_DB_FILE):
                users_df = pd.read_csv(USER_DB_FILE)
                st.dataframe(users_df, use_container_width=True)
            else:
                st.info("No users found.")

        with t3:
            st.info("Tracking user activity.")
            if os.path.exists(LOG_FILE):
                log_df = pd.read_csv(LOG_FILE)
                st.dataframe(log_df, use_container_width=True)
            else:
                st.info("No logs yet.")
        
        st.divider()

    # --- SEARCH UI ---
    st.title("🔍 Mini Search Engine")
    st.markdown("Enter a keyword below to retrieve internal documents.")
    
    engine = load_engine()
    
    # Custom styled search bar
    query = st.text_input("Search Query", placeholder="e.g. invoice, report, project...")

    if query:
        log_search(st.session_state['username'], query)
        results = engine.search(query)
        
        if not results:
            st.warning("🚫 No documents matched your query.")
        else:
            st.markdown(f"**Found {len(results)} matches:**")
            for res in results:
                # Colorful result card
                with st.expander(f"📄 {res['filename']} (Relevance: {res['score']:.2f})"):
                    st.markdown(f"""
                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
                            <p style="color: #333;">{res['content']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    st.download_button("Download", res['content'], res['filename'])

# --- APP FLOW ---
if not st.session_state['logged_in']:
    auth_page()
else:
    main_app()
