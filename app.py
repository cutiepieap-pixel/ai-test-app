# app.py — minimal chat-first Streamlit app (no banner)

import streamlit as st

st.set_page_config(page_title="PrepPro", page_icon="💬", layout="wide")

APP_TITLE = "PrepPro: Your Amazon Interview Assistant"
APP_DESC = (
    "THIS WAS CREATED JUST FOR LEARNING PURPOSES, DO NOT USE FOR ANY SENSITIVE OR CONFIDENTIAL DATA THAT CANNOT BE SHARED WITH THE PUBLIC. "
    "Responses are generated via AWS Bedrock RAG."
    "My name is PrepPro, your AI assistant designed to help you succeed at Amazon Web Services Loop Interviews."
    "I understand that the Loop interview process at AWS can be quite challenging, which is why I'm here to provide you with guidance and support. My goal is to ensure you are well-prepared and confident going into your interviews."
    "I have in-depth knowledge of the core Leadership Principles that Amazon looks for. I can help you craft compelling Situation, Task, Action, Result (STAR) examples that demonstrate how you embody these principles through real-life experiences."
    "Additionally, I'm well-versed in the different question types you may encounter, such as behavioral, situational, and case study questions. I can provide tips on how to structure your responses, what to emphasize, and how to effectively communicate your thought process."
    "So let's get started! I'm excited to work with you and help you put your best foot forward. Don't hesitate to ask me any questions you may have."
    "DISCLAIMER: I'm an AI assistant unaffiliated with Amazon. My responses are for practice only, not reflecting Amazon's actual interviews. Amazon isn't responsible for interview outcomes based on my information. Verify through official AWS resources. Use this exercise cautiously and do not solely rely on my responses for Amazon or other interviews. Please do not share any personal or confidential data with the chatbot to ensure your data privacy."
)

# ---- Safe import of bedrock helper (doesn't block page render)
glib = None
bedrock_import_error = None
try:
    import bedrock as glib  # your bedrock.py helper (must live next to app.py)
except Exception as e:
    bedrock_import_error = f"{type(e).__name__}: {e}"

# ---- Page header
st.title(APP_TITLE)
st.caption(APP_DESC)

# ---- Error handling for bedrock import
if bedrock_import_error:
    st.error("❌ Failed to import bedrock.py")
    st.code(bedrock_import_error)
else:
    st.success("✅ Bedrock module loaded successfully")

# ---- Chat area
st.subheader("💬 Chat")

# session state for history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# render existing messages
for msg in st.session_state.chat_history:
    # both glib.ChatMessage and simple objects with .role/.text are supported
    role = getattr(msg, "role", "assistant")
    text = getattr(msg, "text", "")
    with st.chat_message(role):
        st.markdown(text)

# chat input (sticks to the bottom)
user_text = st.chat_input("Type your question here…")

if user_text:
    # DO NOT pre-append user message here to avoid duplicates.
    # bedrock.chat_with_kb() appends the user and assistant messages itself.
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        if glib is None or bedrock_import_error:
            reply = f"(Bedrock unavailable) I received: {user_text}"
            st.markdown(reply)
            # keep UI coherent
            st.session_state.chat_history.append(type("Msg", (), {"role": "user", "text": user_text}))
            st.session_state.chat_history.append(type("Msg", (), {"role": "assistant", "text": reply}))
        else:
            try:
                with st.spinner("Thinking with Knowledge Base…"):
                    reply = glib.chat_with_kb(
                        message_history=st.session_state.chat_history,
                        new_text=user_text
                    )
                st.markdown(reply)
            except Exception as e:
                err = f"Error calling Knowledge Base: {type(e).__name__}: {e}"
                st.error(err)
                # Store user + error so the transcript remains consistent
                st.session_state.chat_history.append(type("Msg", (), {"role": "user", "text": user_text}))
                st.session_state.chat_history.append(type("Msg", (), {"role": "assistant", "text": err}))

