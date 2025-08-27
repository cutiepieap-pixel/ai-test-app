# app.py
from pathlib import Path
import os
import sys
import streamlit as st

# ============ Page basics ============
st.set_page_config(page_title="PrepPro", page_icon="💬", layout="wide")
APP_TITLE = "PrepPro: Your AI Amazon Interview Companion"

# ============ Robust import of backend ============
HAVE_BACKEND = True
IMPORT_ERROR = None
try:
    import bedrock as glib  # your backend module
except Exception as e:
    HAVE_BACKEND = False
    IMPORT_ERROR = f"{type(e).__name__}: {e}"

# ============ Banner finder ============
def find_banner() -> Path | None:
    # priority: env var -> ./banner.png -> ./static/banner.png
    env_path = os.getenv("BANNER_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    here = Path(__file__).resolve().parent
    candidates += [here / "banner.png", here / "static" / "banner.png"]
    for p in candidates:
        if p.exists():
            return p
    return None

BANNER_PNG = find_banner()

# ============ Disclaimer ============
DISCLAIMER_TEXT = (
    "I'm an AI assistant unaffiliated with Amazon. "
    "My responses are for practice only, not reflecting Amazon's actual interviews. "
    "Amazon isn't responsible for interview outcomes based on my information. "
    "Verify through official Amazon resources. "
    "Use this exercise cautiously and do not solely rely on my responses for Amazon or other interviews. "
    "Please do not share any personal or confidential data with the chatbot to ensure your data privacy."
)

# ============ UI: Banner ============
if BANNER_PNG:
    # 가로폭에 맞추고, 원본 비율 유지
    st.image(str(BANNER_PNG), use_container_width=True)
else:
    st.info("Banner image not found (looked for `banner.png` or `static/banner.png`).")

# ============ UI: Title & Disclaimer ============
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
        {DISCLAIMER_TEXT.replace("\n","<br>")}
    </div>
    """,
    unsafe_allow_html=True
)

# ============ Tabs ============
tab_chat, tab_intro, tab_faq = st.tabs(["💬 Chat", "📘 Introduction", "❓ FAQs"])

# --- Chat Tab ---
with tab_chat:
    st.header("💬 Chat with PrepPro")

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # 안내: 백엔드 임포트 실패 시 사용자에게 알려주되, UI는 유지
    if not HAVE_BACKEND:
        st.warning(
            "Backend module (`bedrock.py`) import failed, so responses will not use the KB right now.\n\n"
            f"Details: {IMPORT_ERROR}"
        )

    input_text = st.chat_input("Please type in any questions you may have.")
    if input_text:
        # 사용자 메시지 먼저 쌓아주면 UI 즉시 갱신
        st.session_state.chat_history.append(type("ChatMessage",(object,),{})())
        st.session_state.chat_history[-1].role = "user"
        st.session_state.chat_history[-1].text = input_text

        if HAVE_BACKEND:
            try:
                # glib.chat_with_kb가 내부에서 history에 assistant 답변을 append 하는 구조라면
                glib.chat_with_kb(message_history=st.session_state.chat_history, new_text=input_text)
            except Exception as e:
                err = f"Backend error: {type(e).__name__}: {e}"
                st.session_state.chat_history.append(type("ChatMessage",(object,),{})())
                st.session_state.chat_history[-1].role = "assistant"
                st.session_state.chat_history[-1].text = err
        else:
            # 임시 에코 답변
            st.session_state.chat_history.append(type("ChatMessage",(object,),{})())
            st.session_state.chat_history[-1].role = "assistant"
            st.session_state.chat_history[-1].text = "⚠️ Backend unavailable. (Echo) You said: " + input_text

    # 대화 렌더
    for message in st.session_state.chat_history:
        role = getattr(message, "role", "assistant")
        text = getattr(message, "text", "")
        with st.chat_message(role):
            st.markdown(text)

# --- Introduction Tab ---
with tab_intro:
    st.subheader("What is PrepPro?")
    st.markdown(
        "PrepPro is an **AI-powered interview companion** that helps you prepare for interviews effectively.  "
        "You can practice answering real-world interview questions and receive **instant feedback** to improve your responses."
    )

    st.subheader("How to Use")
    st.markdown(
        "1. Type your question or let AI generate one for you in the **chat box**.  \n"
        "2. Write your answer, and AI will provide **specific feedback** and improvement tips.  \n"
        "3. **Repeat practice** to refine your answers and boost your confidence.  \n"
        "4. Optionally, specify an industry or role to receive **tailored interview questions**."
    )

# --- FAQ Tab ---
with tab_faq:
    st.subheader("Frequently Asked Questions")
    st.markdown(
        "- **Q: Where do the questions come from?**  \n"
        "  → They are based on AI models trained on public data and interview trends.  \n\n"
        "- **Q: Are my answers saved?**  \n"
        "  → No, all conversations remain **only in the current session** and are not stored."
    )

# ============ Debug Sidebar (helps on App Runner) ============
with st.sidebar:
    st.header("🔧 Debug Info")
    st.write("**Python**:", sys.version)
    st.write("**Streamlit**:", st.__version__)
    cwd = Path.cwd()
    st.write("**CWD**:", cwd)
    try:
        st.write("**Files in CWD**:", [p.name for p in cwd.iterdir()])
    except Exception as e:
        st.write("List dir error:", f"{type(e).__name__}: {e}")

    st.subheader("Env")
    for key in ["AWS_REGION", "KB_ID", "MODEL_ID", "BANNER_PATH"]:
        st.write(f"{key} =", os.getenv(key))

    st.subheader("Banner")
    st.write("Resolved path:", str(BANNER_PNG) if BANNER_PNG else "(not found)")
    st.write("Exists?:", bool(BANNER_PNG and Path(BANNER_PNG).exists()))

    st.subheader("Backend")
    st.write("bedrock import ok?:", HAVE_BACKEND)
    if IMPORT_ERROR:
        st.code(IMPORT_ERROR)
