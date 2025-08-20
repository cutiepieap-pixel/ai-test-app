# app.py
from pathlib import Path
import streamlit as st
import bedrock as glib  # Local library

# ======================
# Basic Settings
# ======================
st.set_page_config(page_title="PrepPro", page_icon="💬", layout="wide")
APP_TITLE = "PrepPro: Your AI Amazon Interview Companion"

# Banner Path
BASE_DIR = Path(r"C:\Users\jeeinp\ai test")
BANNER_PNG = BASE_DIR / "banner.png"

# Disclaimer Text (English)
DISCLAIMER_TEXT = """
I'm an AI assistant unaffiliated with Amazon. 
My responses are for practice only, not reflecting Amazon's actual interviews. 
Amazon isn't responsible for interview outcomes based on my information. 
Verify through official Amazon resources. 
Use this exercise cautiously and do not solely rely on my responses for Amazon or other interviews. 
Please do not share any personal or confidential data with the chatbot to ensure your data privacy.
"""

# ======================
# Display Banner (150px height, maintain aspect ratio)
# ======================
if BANNER_PNG.exists():
    st.image(str(BANNER_PNG), use_container_width=True, output_format="PNG")
    # Limit only banner height (note: this targets all <img>; if you add images later and don't want them resized,
    # we can scope this CSS to a wrapper. For now, kept simple as requested.)
    st.markdown(
        """
        <style>
        img {
            height: 150px !important;
            object-fit: contain;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
else:
    st.warning("Banner image not found. Please check banner.png in the folder.")

# ======================
# Title & Disclaimer
# ======================
st.title(APP_TITLE)

disclaimer_html = f"""
<div style="
    background:#fff3cd;
    border:1px solid #ffe69c;
    color:#664d03;
    padding:12px 14px;
    border-radius:8px;
    margin:10px 0 6px 0;
    font-size:14px;
    line-height:1.5;">
    <strong>Disclaimer:</strong><br>
    {DISCLAIMER_TEXT.replace("\n", "<br>")}
</div>
"""
st.markdown(disclaimer_html, unsafe_allow_html=True)

# ======================
# Tabs: Chat / Introduction / FAQ (FAQ separated)
# ======================
tab_chat, tab_intro, tab_faq = st.tabs(["💬 Chat", "📘 Introduction", "❓ FAQs"])

# --- Chat Tab ---
with tab_chat:
    st.header("💬 Chat with PrepPro")

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    input_text = st.chat_input("Please type in any questions you may have.")
    if input_text:
        glib.chat_with_kb(message_history=st.session_state.chat_history, new_text=input_text)

    for message in st.session_state.chat_history:
        with st.chat_message(message.role):
            st.markdown(message.text)

# --- Introduction Tab ---
with tab_intro:
    st.subheader("What is PrepPro?")
    st.markdown("""
    PrepPro is an **AI-powered interview companion** that helps you prepare for interviews effectively.  
    You can practice answering real-world interview questions and receive **instant feedback** to improve your responses.
    """)

    st.subheader("How to Use")
    st.markdown("""
    1. Type your question or let AI generate one for you in the **chat box**.  
    2. Write your answer, and AI will provide **specific feedback** and improvement tips.  
    3. **Repeat practice** to refine your answers and boost your confidence.  
    4. Optionally, specify an industry or role to receive **tailored interview questions**.
    """)

# --- FAQ Tab (separated) ---
with tab_faq:
    st.subheader("Frequently Asked Questions")
    st.markdown("""
    - **Q: Where do the questions come from?**  
      → They are based on AI models trained on public data and interview trends.  

    - **Q: Are my answers saved?**  
      → No, all conversations remain **only in the current session** and are not stored.  
    """)
