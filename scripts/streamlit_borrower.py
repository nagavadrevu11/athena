import streamlit as st
import os
import json
from datetime import datetime
from PyPDF2 import PdfReader
import dotenv
from supabase import create_client
import io

# Load environment variables
dotenv.load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase_bucket = os.environ.get("SUPABASE_BUCKET")

supabase = create_client(supabase_url, supabase_key)

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
        try:
            # Create a folder path in Supabase storage
            folder_name = name.lower().replace(" ", "_")
            
            # Prepare metadata
            metadata = {
                "name": name,
                "employer": employer,
                "stated_income": stated_income,
                "loan_amount": loan_amount,
                "loan_type": loan_type,
                "submitted_at": datetime.now().isoformat()
            }
            
            # Upload metadata.json to Supabase
            metadata_path = f"{folder_name}/metadata.json"
            metadata_bytes = json.dumps(metadata, indent=2).encode('utf-8')
            supabase.storage.from_(supabase_bucket).upload(
                metadata_path,
                metadata_bytes,
                {"content-type": "application/json"}
            )
            
            # Upload PDF files to Supabase
            for i, file in enumerate(uploaded_files):
                file_path = f"{folder_name}/document_{i+1}.pdf"
                file_bytes = file.read()
                supabase.storage.from_(supabase_bucket).upload(
                    file_path,
                    file_bytes,
                    {"content-type": "application/pdf"}
                )
            
            st.success(f"Thank you, {name}! Your information and documents have been uploaded to Supabase.")
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.info("Please check your Supabase credentials in the .env file.")
