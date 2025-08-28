# app.py — minimal chat-first Streamlit app (no banner)

import os
import traceback
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="PrepPro Chat", page_icon="💬", layout="wide")

APP_TITLE = "PrepPro: Knowledge Base Chat"
APP_DESC = (
    "Ask anything related to your Knowledge Base. "
    "Responses are generated via AWS Bedrock Retrieve-and-Generate."
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

# ---- Quick runtime/env checks (always visible)
aws_region = os.getenv("AWS_REGION")
kb_id = os.getenv("KB_ID")
model_id = os.getenv("MODEL_ID")

if bedrock_import_error:
    st.error("❌ Failed to import bedrock.py")
    st.code(bedrock_import_error)

if not aws_region:
    st.warning("⚠️ AWS_REGION is not set (App Runner Console → Runtime environment variables).")
if not kb_id:
    st.warning("⚠️ KB_ID is not set (must match your Knowledge Base ID).")
if not model_id:
    st.info("ℹ️ MODEL_ID not set. Using default from bedrock.py if provided.")

with st.expander("Runtime info"):
    st.write({"AWS_REGION": aws_region, "KB_ID": kb_id, "MODEL_ID": model_id})
    if not bedrock_import_error:
        st.write("bedrock.py import: OK ✅")

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

# ---- Tiny debug block at the bottom (optional)
with st.expander("Debug (files & last exception)"):
    try:
        files = "\n".join(sorted(os.listdir(Path(__file__).parent)))
    except Exception as e:
        files = f"(listdir failed: {type(e).__name__}: {e})"
    st.text_area("Files in app dir", value=files, height=160)

# global exception capture to surface in Debug (best-effort)
def _patch_report_exception():
    import sys
    def excepthook(exc_type, exc, tb):
        st.session_state["_last_exception"] = "".join(traceback.format_exception(exc_type, exc, tb))
        raise exc
    sys.excepthook = excepthook

try:
    _patch_report_exception()
except Exception:
    pass