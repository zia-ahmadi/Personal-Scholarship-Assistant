import streamlit as st

from src.analyzer import analyze_opportunity_text
from src.scraper import scrape_webpage_text


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
        with st.spinner("Fetching webpage..."):
            scrape_result = scrape_webpage_text(opportunity_url)

        if not scrape_result["ok"]:
            st.error(scrape_result["error"])
        else:
            with st.spinner("Analyzing with local Ollama model..."):
                analysis_result = analyze_opportunity_text(
                    scrape_result["text"],
                    model="llama3.2:3b",
                )

            if not analysis_result["ok"]:
                st.error(analysis_result["error"])
            else:
                st.subheader("Extracted Opportunity Data")
                st.json(analysis_result["data"])

                with st.expander("Cleaned Webpage Text"):
                    st.text(scrape_result["text"][:5000])
