import streamlit as st
import os
import json
from datetime import datetime
from PyPDF2 import PdfReader

st.set_page_config(page_title="Borrower Intake", layout="centered")
st.title("📥 Borrower Income Submission")

st.markdown("Please complete the form and upload your income documents (max 5 PDFs).")

# Borrower Form
with st.form("borrower_submission_form"):
    name = st.text_input("Full Name")
    employer = st.text_input("Employer Name")
    stated_income = st.number_input("Stated Annual Income ($)", min_value=0)
    loan_amount = st.number_input("Loan Amount ($)", min_value=0)
    loan_type = st.selectbox("Loan Type", ["Conventional", "FHA", "VA", "Other"])
    uploaded_files = st.file_uploader("Upload income documents (up to 5 PDFs)", type=["pdf"], accept_multiple_files=True)

    submitted = st.form_submit_button("Submit")

if submitted:
    if not name or not employer or not uploaded_files:
        st.error("Please fill in all required fields and upload at least one document.")
    elif len(uploaded_files) > 5:
        st.error("You may upload up to 5 documents only.")
    else:
        # Create folder under /data/<name>/ and save metadata + files
        folder_name = name.lower().replace(" ", "_")
        # Get the root directory (parent of scripts)
        ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Update folder path to be from root
        folder_path = os.path.join(ROOT_DIR, "data", folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Save metadata
        metadata = {
            "name": name,
            "employer": employer,
            "stated_income": stated_income,
            "loan_amount": loan_amount,
            "loan_type": loan_type,
            "submitted_at": datetime.now().isoformat()
        }
        with open(os.path.join(folder_path, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        # Save uploaded PDFs
        for i, file in enumerate(uploaded_files):
            file_path = os.path.join(folder_path, f"document_{i+1}.pdf")
            with open(file_path, "wb") as out:
                out.write(file.read())

        st.success(f"Thank you, {name}! Your information and documents have been submitted.")
