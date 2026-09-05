import streamlit as st


st.set_page_config(
    page_title="Personal Opportunity Analyzer",
    layout="centered",
)


st.title("Personal Opportunity Analyzer")

opportunity_url = st.text_input("Paste opportunity URL:")

if st.button("Analyze Opportunity", type="primary"):
    if not opportunity_url.strip():
        st.warning("Please paste an opportunity URL first.")
    else:
        st.info("URL analysis will be added in the next step.")
        st.write(opportunity_url.strip())
