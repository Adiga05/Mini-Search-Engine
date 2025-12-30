import streamlit as st
import os
import re
import math
import glob
import pandas as pd
from datetime import datetime
from collections import defaultdict, Counter

# --- CONFIGURATION ---
DOCS_DIR = "docs"
LOG_FILE = "search_logs.csv"

# Ensure directories exist
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

# --- LOGGING ---
def log_search(query):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("Timestamp,Query\n")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp},{query}\n")

# --- SEARCH ENGINE LOGIC ---
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
    # Check if files exist
    files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    if not files:
        # Create a dummy file if empty to prevent errors
        dummy_path = os.path.join(DOCS_DIR, "welcome.txt")
        with open(dummy_path, "w") as f:
            f.write("Welcome to your new search engine! Add files in the Admin panel.")
        files = [dummy_path]
        
    for f in files:
        engine.add_file(f)
    return engine

# --- UI SETUP ---
st.set_page_config(page_title="DocSearch Pro", page_icon="🔎", layout="wide")

# --- ADMIN AUTH ---
with st.sidebar:
    st.title("⚙️ Settings")
    password = st.text_input("Admin Password", type="password")
    
    # Check against Streamlit Secrets (Secure) or fallback to 'admin123'
    correct_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
    
    is_admin = (password == correct_password)
    if is_admin:
        st.success("✅ Owner Access Granted")

# --- ADMIN DASHBOARD ---
if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.header("Admin Dashboard")
    tab1, tab2 = st.sidebar.tabs(["📄 Files", "📊 Logs"])
    
    with tab1:
        uploaded_files = st.file_uploader("Upload .txt files", accept_multiple_files=True)
        if uploaded_files:
            for up_file in uploaded_files:
                with open(os.path.join(DOCS_DIR, up_file.name), "wb") as f:
                    f.write(up_file.getbuffer())
            st.success("Uploaded!")
            st.cache_resource.clear()
            st.rerun()
            
        st.write("---")
        st.write("Existing Files:")
        for file in os.listdir(DOCS_DIR):
            col1, col2 = st.columns([0.8, 0.2])
            col1.text(file)
            if col2.button("🗑️", key=file):
                os.remove(os.path.join(DOCS_DIR, file))
                st.cache_resource.clear()
                st.rerun()

    with tab2:
        if os.path.exists(LOG_FILE):
            df = pd.read_csv(LOG_FILE)
            st.dataframe(df)
        else:
            st.info("No logs yet.")

# --- MAIN SEARCH ---
st.title("🔎 Document Search Engine")
engine = load_engine()

query = st.text_input("Search Database:", placeholder="Enter keyword...")

if query:
    log_search(query)
    results = engine.search(query)
    
    if not results:
        st.warning("No matches found.")
    else:
        st.success(f"Found {len(results)} matches.")
        for res in results:
            with st.expander(f"📄 {res['filename']} (Score: {res['score']:.2f})"):
                st.markdown(res['content'])
