#!/usr/bin/env python3
"""
Simple test script to verify Streamlit setup and show basic UI
"""
import streamlit as st
import os

# Page configuration
st.set_page_config(
    page_title="DeepResearch2 Test",
    page_icon="📚",
    layout="wide"
)

st.title("📚 DeepResearch2 - Test Interface")
st.markdown("### Testing Streamlit Setup")

# Show environment info
st.subheader("Environment Information")
st.write(f"Python executable: {os.sys.executable}")
st.write(f"Working directory: {os.getcwd()}")
st.write(f"Streamlit version: {st.__version__}")

# Show available modules
st.subheader("Available Dependencies")
try:
    import fastmcp
    st.success(f"✅ FastMCP version: {fastmcp.__version__}")
except ImportError as e:
    st.error(f"❌ FastMCP import error: {e}")

try:
    import openai
    st.success(f"✅ OpenAI version: {openai.__version__}")
except ImportError as e:
    st.error(f"❌ OpenAI import error: {e}")

try:
    import pandas
    st.success(f"✅ Pandas version: {pandas.__version__}")
except ImportError as e:
    st.error(f"❌ Pandas import error: {e}")

# Simple UI test
st.subheader("UI Components Test")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**File Upload Test**")
    uploaded_file = st.file_uploader("Test file upload", type=['txt', 'csv', 'json'])
    if uploaded_file:
        st.success(f"File uploaded: {uploaded_file.name}")

with col2:
    st.markdown("**Form Elements Test**")
    test_text = st.text_input("Test input", placeholder="Type something...")
    test_button = st.button("Test Button")
    if test_button:
        st.info(f"Button clicked! Input: {test_text}")

# Test tabs
st.subheader("Tabs Test")
tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])

with tab1:
    st.write("This is tab 1 content")
    st.metric("Test Metric", value=42, delta=5)

with tab2:
    st.write("This is tab 2 content")
    import pandas as pd
    df = pd.DataFrame({
        'A': [1, 2, 3, 4],
        'B': [10, 20, 30, 40]
    })
    st.dataframe(df)

with tab3:
    st.write("This is tab 3 content")
    st.bar_chart(df.set_index('A'))

# Sidebar test
with st.sidebar:
    st.header("Sidebar Test")
    st.selectbox("Test Select", ["Option 1", "Option 2", "Option 3"])
    st.slider("Test Slider", 0, 100, 50)

st.markdown("---")
st.success("✅ Basic Streamlit interface is working correctly!")