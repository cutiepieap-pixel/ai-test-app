# app.py
from pathlib import Path
import streamlit as st
import bedrock as glib  # Local library (bedrock.py)

# ======================
# Basic Settings
# ======================
st.set_page_config(page_title="PrepPro", page_icon="💬", layout="wide")
APP_TITLE = "PrepPro: Your AI Amazon Interview Companion"

# ======================
# Banner Path (repo-relative)
# ======================
# 👉 App Runner 컨테이너에서도 동작하도록, 현재 파일 기준 상대경로로 배너를 읽습니다.
BASE_DIR = Path(__file__).parent
BANNER_PNG = BASE_DIR / "banner.png"   # 반드시 레포에 banner.png를 커밋하세요

# ======================
# Disclaimer Text (English)
# ======================
DISCLAIMER_TEXT = """
I'm an AI assistant unaffiliated with Amazon. 
My responses are for practice only, not reflecting Amazon's actual interviews. 
Amazon isn't responsible for interview outcomes based on my information. 
Verify through official Amazon resources. 
Use this exercise cautiously and do not solely rely on my responses for Amazon or other interviews. 
Please do not share any personal or confidential data with the chatbot to ensure your data privacy.
"""

# ======================
# Display Banner (scale down to 150px height, keep aspect ratio)
# ======================
# 모든 <img>에 영향을 주지 않도록 'max-height'을 사용 → 잘리지 않고 축소만 됨
if BANNER_PNG.exists():
    st.image(str(BANNER_PNG), use_container_width=True)
    st.markdown(
        """
        <style>
        /* 이미지가 너무 커 보이는 것을 방지 - 비율 유지, 높이만 제한 */
        img {
            max-height: 150px !important;
            height: auto !important;
            object-fit: contain !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
else:
    st.warning("Banner image not found in the app folder. Please add 'banner.png' to the repo root.")

# ======================
# Title & Disclaimer
# ======================
st.title(APP_TITLE)

# 노란 박스에 전체 디스클레이머 텍스트 표기
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
# Tabs: Chat / Introduction / FAQ
# ======================
tab_chat, tab_intro, tab_faq = st.tabs(["💬 Chat", "📘 Introduction", "❓ FAQs"])

# --- Chat Tab ---
with tab_chat:
    st.header("💬 Chat with PrepPro")

    # 채팅 상태
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 입력창 + 엔터로 전송
    input_text = st.chat_input("Please type in any questions you may have.")

    # 메시지 전송 시 KB 호출
    if input_text:
        with st.spinner("Thinking with Knowledge Base..."):
            try:
                glib.chat_with_kb(message_history=st.session_state.chat_history, new_text=input_text)
            except Exception as e:
                # 런타임 오류를 UI에 보여줘서 디버깅이 쉬움
                st.error(f"Chat error: {type(e).__name__}: {e}")

    # 채팅 렌더
    for message in st.session_state.chat_history:
        with st.chat_message(message.role):
            st.markdown(message.text)

    # 유틸 버튼
    col1, col2, _ = st.columns([1,1,6])
    with col1:
        if st.button("🧹 Clear chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    with col2:
        if st.button("🐞 Debug KB/Identity", use_container_width=True):
            # bedrock.debug_* 함수를 직접 출력 대신 UI에 안내
            st.info("Check CloudWatch > Application logs for identity/KB diagnostics if enabled.\n"
                    "Or run debug_print_identity_and_kbs() locally.")

# --- Introduction Tab ---
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
