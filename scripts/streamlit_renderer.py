import streamlit as st

def render_evaluation(result: dict, metadata: dict = None, document_list: list = None):
    st.subheader("📋 Borrower Summary")
    if metadata:
        cols = st.columns(2)
        cols[0].markdown(f"**Name:** {metadata.get('name', '-')}")
        cols[1].markdown(f"**Employer:** {metadata.get('employer', '-')}")
        cols[0].markdown(f"**Stated Income:** ${metadata.get('stated_income', '-'):,}")
        cols[1].markdown(f"**Loan Amount:** ${metadata.get('loan_amount', '-'):,}")
        cols[0].markdown(f"**Loan Type:** {metadata.get('loan_type', '-')}")
        cols[1].markdown(f"**Submitted At:** {metadata.get('submitted_at', '-')}")
    else:
        st.info("No metadata provided.")

    st.divider()
    st.subheader("💰 Qualifying Income")
    if result.get("qualifying_income_monthly") is not None:
        st.metric("Monthly Income (Calculated)", f"${result['qualifying_income_monthly']:,.2f}")
    else:
        st.warning("No qualifying income was returned.")

    st.divider()
    st.subheader("📌 Action Items")
    if result.get("action_items"):
        for item in result["action_items"]:
            st.markdown(f"- [ ] {item}")
    else:
        st.success("No action items — everything looks good!")

    if result.get("guideline_citations"):
        st.divider()
        st.subheader("📚 Referenced Guidelines")
        for g in result["guideline_citations"]:
            st.code(g)

    if document_list:
        st.divider()
        st.subheader("📄 Documents Evaluated")
        for doc in document_list:
            st.markdown(f"- {doc.name}")
