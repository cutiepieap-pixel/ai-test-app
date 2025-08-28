import streamlit as st
import os

print("Starting Streamlit app...")  # This will show in logs

st.set_page_config(
    page_title="Test App", 
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Test App")
st.write("If you can see this, the basic Streamlit app is working!")

st.success("✅ App is running successfully")

# Test environment variables
st.subheader("Environment Check")
aws_region = os.getenv('AWS_REGION', 'Not set')
kb_id = os.getenv('KB_ID', 'Not set')

st.write(f"**AWS_REGION:** {aws_region}")
st.write(f"**KB_ID:** {kb_id}")

# Simple interaction test
if st.button("Test Button"):
    st.balloons()
    st.write("✅ Button works!")

st.write("---")
st.write("If you can see this entire page, Streamlit is working correctly!")