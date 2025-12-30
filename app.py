import streamlit as st
import os
import re
import math
import glob
import pandas as pd
from datetime import datetime
from collections import defaultdict, Counter

# ==========================================
# 1. CONFIGURATION & STATE SETUP
# ==========================================

st.set_page_config(page_title="DocSearch Pro", page_icon="🔎", layout="wide")

DOCS_DIR = "docs"
LOG_FILE = "search_logs.csv"

# Create docs folder if missing
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

# Initialize Session State Variables
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'theme' not in st.session_state:
    st.session_state['theme'] = "Light"
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False

# --- DUMMY USER DATABASE ---
# Format: "username": "password"
USERS_DB = {
    "user": "1234",
    "alice": "password",
    "admin": "admin123" # Admin can also log in as a user
}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def log_search(username, query):
    """Logs the search query with the specific username."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("Timestamp,User,Query\n")
    
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp},{username},{query}\n")

def apply_theme():
    """Injects CSS based on the selected theme."""
    if st.session_state['theme'] == "Dark":
        st.markdown("""
            <style>
            .stApp {
                background-color: #0E1117;
                color: #FAFAFA;
            }
            .stTextInput > div > div > input {
                background-color: #262730;
                color: #FAFAFA;
            }
            div[data-testid="stExpander"] {
                background-color: #262730;
                border: 1px solid #4F4F4F;
            }
            </style>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            .stApp {
                background-color: #FFFFFF;
                color: #000000;
            }
            </style>
            """, unsafe_allow_html=True)

# ==========================================
# 3. SEARCH ENGINE LOGIC
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
        # Create dummy file if empty
        with open(os.path.join(DOCS_DIR, "welcome.txt"), "w") as f:
            f.write("Welcome to the system.")
        files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    for f in files:
        engine.add_file(f)
    return engine

# ==========================================
# 4. PAGE: LOGIN SCREEN
# ==========================================
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔒 Secure Login</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Log In")

            if submit:
                if username in USERS_DB and USERS_DB[username] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
    
    st.info("Demo Accounts: user/1234, alice/password")

# ==========================================
# 5. PAGE: MAIN APPLICATION
# ==========================================
def main_app():
    apply_theme() # Apply CSS based on settings
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.write(f"👤 Welcome, **{st.session_state['username'].capitalize()}**")
        
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['is_admin'] = False
            st.rerun()
        
        st.divider()

        # --- SETTINGS MENU ---
        with st.expander("⚙️ Settings"):
            # 1. Theme Toggle
            st.subheader("Appearance")
            theme_choice = st.radio("Theme Mode", ["Light", "Dark"], 
                                    index=0 if st.session_state['theme']=="Light" else 1)
            if theme_choice != st.session_state['theme']:
                st.session_state['theme'] = theme_choice
                st.rerun()

            st.divider()

            # 2. History Toggle
            st.subheader("Data")
            show_history = st.checkbox("Show My Search History")

            st.divider()

            # 3. Admin Access (Hidden by default)
            st.subheader("Admin Zone")
            enable_admin = st.checkbox("Enable Admin Access")
            
            if enable_admin:
                admin_pass = st.text_input("Admin Password", type="password")
                # Using st.secrets is best, but hardcoded here for demo
                CORRECT_ADMIN_PASS = "admin123" 
                
                if admin_pass == CORRECT_ADMIN_PASS:
                    st.session_state['is_admin'] = True
                    st.success("Admin Unlocked!")
                elif admin_pass:
                    st.session_state['is_admin'] = False
                    st.error("Wrong Password")
            else:
                st.session_state['is_admin'] = False

    # --- ADMIN DASHBOARD (Only visible if unlocked) ---
    if st.session_state['is_admin']:
        st.markdown("### 🛠️ Admin Dashboard")
        tab1, tab2 = st.tabs(["📄 Manage Files", "📊 Global Logs"])
        
        with tab1:
            uploaded_files = st.file_uploader("Upload .txt files to Database", accept_multiple_files=True)
            if uploaded_files:
                for up_file in uploaded_files:
                    with open(os.path.join(DOCS_DIR, up_file.name), "wb") as f:
                        f.write(up_file.getbuffer())
                st.success("Files Uploaded!")
                st.cache_resource.clear()
                st.rerun()
            
            st.write("Existing Files:")
            for file in os.listdir(DOCS_DIR):
                c1, c2 = st.columns([0.8, 0.2])
                c1.text(file)
                if c2.button("🗑️", key=f"del_{file}"):
                    os.remove(os.path.join(DOCS_DIR, file))
                    st.cache_resource.clear()
                    st.rerun()

        with tab2:
            if os.path.exists(LOG_FILE):
                df = pd.read_csv(LOG_FILE)
                st.dataframe(df, use_container_width=True)
                st.download_button("Download CSV", df.to_csv().encode('utf-8'), "logs.csv")
            else:
                st.info("No logs found.")
        
        st.markdown("---") 

    # --- MAIN SEARCH UI ---
    st.title("🔎 DocSearch Pro")
    
    # Show History if toggle is ON
    if show_history:
        st.subheader("🕒 Your Search History")
        if os.path.exists(LOG_FILE):
            df = pd.read_csv(LOG_FILE)
            # Filter logs for current user only
            user_logs = df[df['User'] == st.session_state['username']]
            if not user_logs.empty:
                st.dataframe(user_logs[['Timestamp', 'Query']], hide_index=True)
            else:
                st.info("No history found for you.")
        else:
            st.info("No logs database found.")
        st.markdown("---")

    # Search Bar
    engine = load_engine()
    query = st.text_input("Search Documents:", placeholder="Enter keyword...")

    if query:
        # Log this search
        log_search(st.session_state['username'], query)
        
        results = engine.search(query)
        
        if not results:
            st.warning("No matches found.")
        else:
            st.success(f"Found {len(results)} matches.")
            for res in results:
                with st.expander(f"📄 {res['filename']} (Score: {res['score']:.2f})"):
                    st.markdown(res['content'])

# ==========================================
# 6. APP EXECUTION FLOW
# ==========================================

if not st.session_state['logged_in']:
    login_page()
else:
    main_app()
