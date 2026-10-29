
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/analyze_risk/"

st.set_page_config(
    page_title="ScamShield FinFraud",
    page_icon="🛡️",
    layout="centered",
)

st.title("🛡️ ScamShield FinFraud")
st.subheader("AI-Based Financial Scam Risk Analysis")
st.write("Upload a suspicious text file to analyze potential financial scam indicators.")

uploaded_file = st.file_uploader("Upload a text file", type=["txt"])

if uploaded_file:
    st.info(f"Selected file: {uploaded_file.name}")

    if st.button("Analyze Risk", type="primary"):
        try:
            with st.spinner("Analyzing..."):
                response = requests.post(
                    API_URL,
                    files={
                        "files": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "text/plain",
                        )
                    },
                    timeout=180,
                )

            if response.status_code != 200:
                st.error(f"API error: HTTP {response.status_code}")
                st.code(response.text[:1000])
            else:
                data = response.json()
                verdict = data.get("final_verdict", {})
                risk_level = verdict.get("risk_level", "Unknown")
                analysis = verdict.get("analysis", "")

                if risk_level == "Unknown" or analysis.startswith("AI reasoning failed:"):
                    st.error("AI analysis failed. Please try again later.")
                    st.write(analysis)
                else:
                    probability = verdict.get("probability", 0)

                    st.header("Analysis Results")
                    st.metric("Estimated Scam Probability", f"{probability * 100:.1f}%")

                    if risk_level == "High":
                        st.error(f"Risk Level: {risk_level}")
                    elif risk_level == "Medium":
                        st.warning(f"Risk Level: {risk_level}")
                    else:
                        st.success(f"Risk Level: {risk_level}")

                    st.subheader("Explanation")
                    st.write(analysis)

                    st.subheader("Safety Recommendations")
                    for item in verdict.get("recommendations", []):
                        st.markdown(f"- {item}")

                    matches = data.get("detailed_evidence", {}).get("text_matches", [])
                    if matches:
                        with st.expander("View Similar Database Cases"):
                            for i, match in enumerate(matches, 1):
                                st.markdown(f"**Case {i} — {match.get('risk_label', 'Unknown')}**")
                                st.write(match.get("text_snippet", ""))
                                st.write(f"Similarity score: {match.get('score', 0):.3f}")
                                st.divider()

                    st.caption(
                        "Educational demonstration only. This tool does not provide "
                        "definitive fraud determinations or professional financial advice."
                    )

        except requests.RequestException as exc:
            st.error(f"Could not connect to the API: {exc}")
            st.info("Ensure FastAPI is running on port 8000.")
