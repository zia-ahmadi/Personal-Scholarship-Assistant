import streamlit as st

from src.analyzer import analyze_opportunity_text
from src.matcher import load_profile, match_opportunity
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

                try:
                    profile = load_profile()
                    match_result = match_opportunity(analysis_result["data"], profile)
                except (OSError, ValueError) as error:
                    st.error(f"Could not load profile: {error}")
                else:
                    st.subheader("My Match")
                    st.write(
                        f"Eligibility status: **{match_result['eligibility_status']}**"
                    )
                    if match_result["eligibility_status"] == "Uncertain":
                        st.info("Some requirements could not be confirmed from the available information.")
                    st.write(f"Match score: **{match_result['match_score']} / 100**")

                    st.write("**Reasons**")
                    st.write(match_result["reasons"] or "None")

                    st.write("**Missing requirements**")
                    st.write(match_result["missing_requirements"] or "None")

                    st.write("**Uncertain requirements**")
                    st.write(match_result["uncertain_requirements"] or "None")

                with st.expander("Cleaned Webpage Text"):
                    st.text(scrape_result["text"][:5000])
