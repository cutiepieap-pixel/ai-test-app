# app.py
from pathlib import Path
import traceback
import streamlit as st

# ===== Basic Settings =====
st.set_page_config(page_title="PrepPro", page_icon="💬", layout="wide")
APP_TITLE = "PrepPro: Your AI Amazon Interview Companion"

# ===== Safe import for bedrock helper (show warning if missing) =====
glib = None
bedrock_import_error = None
try:
    import bedrock as glib  # must exist as bedrock.py in repo root
except Exception as e:
    bedrock_import_error = f"{type(e).__name__}: {e}"

# ===== Paths (container-friendly) =====
# In App Runner, your app code is under /app. We resolve banner relative to this file.
HERE = Path(__file__).parent
CANDIDATE_BANNERS = [
    HERE / "banner.png",              # repo root
    HERE / "assets" / "banner.png",   # optionally assets/banner.png
]

def find_banner():
    for p in CANDIDATE_BANNERS:
        if p.exists():
            return p
    return None

BANNER_PNG = find_banner()

# ===== Disclaimer =====
DISCLAIMER_TEXT = (
    "I'm an AI assistant unaffiliated with Amazon. "
    "My responses are for practice only, not reflecting Amazon's actual interviews. "
    "Amazon isn't responsible for interview outcomes based on my information. "
    "Verify through official Amazon resources. "
    "Use this exercise cautiously and do not solely rely on my responses for Amazon or other interviews. "
    "Please do not share any personal or confidential data with the chatbot to ensure your data privacy."
)

# ===== UI: Banner (keeps aspect ratio, caps height via wrapper only) =====
st.markdown("<div id='banner-wrap'>", unsafe_allow_html=True)
if BANNER_PNG:
    st.image(str(BANNER_PNG), use_container_width=True)
else:
    st.warning("Banner image not found. Place `banner.png` at repo root (same folder as app.py) "
               "or under `assets/banner.png`.")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
      /* Only affect the banner image inside our wrapper */
      #banner-wrap img {
        max-height: 150px !important;   /* cap height */
        width: 100% !important;          /* fit width */
        object-fit: contain !important;  /* keep aspect ratio without cropping */
      }
    </style>
    """,
    unsafe_allow_html=True
)

# ===== Title & Disclaimer =====
st.title(APP_TITLE)
st.markdown(
    f"""
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
        {DISCLAIMER_TEXT}
    </div>
    """,
    unsafe_allow_html=True
)

# ===== Tabs =====
tab_chat, tab_intro, tab_faq, tab_diag = st.tabs(["💬 Chat", "📘 Introduction", "❓ FAQs", "🛠 Diagnostics"])

# --- Chat Tab ---
with tab_chat:
    st.header("💬 Chat with PrepPro")
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # If bedrock helper failed to import, show an inline error so page still renders
    if bedrock_import_error:
        st.error(
            "Bedrock module import failed. Chat will be disabled.\n\n"
            f"Details: {bedrock_import_error}"
        )
    else:
        user_text = st.chat_input("Please type in any questions you may have.")
        if user_text:
            try:
                glib.chat_with_kb(message_history=st.session_state.chat_history, new_text=user_text)
            except Exception as e:
                st.error(f"Chat backend error: {type(e).__name__}: {e}")

    for m in st.session_state.get('chat_history', []):
        with st.chat_message(m.role):
            st.markdown(m.text)

# --- Intro Tab ---
with tab_intro:
    st.subheader("What is PrepPro?")
    st.markdown(
        """
        PrepPro is an **AI-powered interview companion** that helps you prepare for interviews effectively.  
        You can practice answering real-world interview questions and receive **instant feedback** to improve your responses.
        """
    )

    st.subheader("How to Use")
    st.markdown(
        """
        1. Type your question or let AI generate one for you in the **chat box**.  
        2. Write your answer, and AI will provide **specific feedback** and improvement tips.  
        3. **Repeat practice** to refine your answers and boost your confidence.  
        4. Optionally, specify an industry or role to receive **tailored interview questions**.
        """
    )

# --- FAQ Tab ---
with tab_faq:
    st.subheader("Frequently Asked Questions")
    st.markdown(
        """
        - **Q: Where do the questions come from?**  
          → They are based on AI models trained on public data and interview trends.  

        - **Q: Are my answers saved?**  
          → No, all conversations remain **only in the current session** and are not stored.  
        """
    )

# --- Diagnostics Tab (to quickly verify in App Runner) ---
with tab_diag:
    st.write("### Environment")
    st.code(
        f"""
CWD: {Path.cwd()}
__file__: {__file__}
HERE: {HERE}
banner candidates:
- {CANDIDATE_BANNERS[0]}
- {CANDIDATE_BANNERS[1]}
resolved banner: {BANNER_PNG if BANNER_PNG else 'NOT FOUND'}
bedrock import error: {bedrock_import_error or 'None'}
        """.strip()
    )
    st.caption("If banner shows NOT FOUND, ensure banner.png is committed to the repo root and redeploy.")

