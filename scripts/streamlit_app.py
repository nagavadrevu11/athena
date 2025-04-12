import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
from scripts.evaluate_income import run_assistant
import webbrowser
import urllib.parse
from openai import OpenAI
from dotenv import load_dotenv
from supabase import create_client
import io
import base64

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase_bucket = os.environ.get("SUPABASE_BUCKET")

supabase = create_client(supabase_url, supabase_key)

# Set page config early
st.set_page_config(page_title="Underwriter Assistant", layout="centered")

# Setup OpenAI API key from Streamlit secrets or environment variables
api_key_source = "None"
try:
    if st.secrets and "openai" in st.secrets and "api_key" in st.secrets["openai"]:
        os.environ["OPENAI_API_KEY"] = st.secrets["openai"]["api_key"]
        api_key_source = "Streamlit Secrets"
except Exception as e:
    st.sidebar.error(f"Error accessing Streamlit secrets: {str(e)}")

# If we still don't have an API key, check the environment variable
if not os.getenv("OPENAI_API_KEY"):
    if os.path.exists(".env"):
        api_key_source = "Environment (.env file)"
    else:
        st.error("""
        ⚠️ **OpenAI API Key Not Found**
        
        Please set your OpenAI API key using one of these methods:
        
        1. **For local development**: Create a `.env` file with your API key:
           ```
           OPENAI_API_KEY=your_key_here
           ```
           
        2. **For Streamlit Cloud**: Add your API key to the Streamlit secrets:
           ```
           [openai]
           api_key = "your_key_here"
           ```
        """)
else:
    st.sidebar.success(f"✅ API Key loaded from: {api_key_source}")

# Check Supabase credentials
if not supabase_url or not supabase_key or not supabase_bucket:
    st.error("""
    ⚠️ **Supabase Configuration Not Found**
    
    Please set your Supabase credentials in the `.env` file:
    ```
    SUPABASE_URL=your_supabase_url_here
    SUPABASE_KEY=your_supabase_key_here
    SUPABASE_BUCKET=your_bucket_name_here
    ```
    """)
else:
    st.sidebar.success("✅ Supabase configuration loaded")

st.title("🧾 AI Underwriter Assistant")


# Initialize chat history and email state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "current_analysis" not in st.session_state:
    st.session_state.current_analysis = None

# Chat input
user_input = st.chat_input("Ask about available applications...")

# Email functionality
if st.session_state.current_analysis:
    folder_name = st.session_state.current_analysis["folder_name"]
    analysis_result = st.session_state.current_analysis["result"]
    
    st.sidebar.markdown("### Send Results via Email")
    email_to = st.sidebar.text_input("Recipient Email:", key="email_to")
    email_subject = st.sidebar.text_input("Subject:", value=f"Application Analysis: {folder_name}", key="email_subject")
    
    if st.sidebar.button("Send Email"):
        # Prepare the email body with the analysis results
        email_body = f"Analysis results for {folder_name}:\n\n"
        email_body += json.dumps(analysis_result, indent=2)
        
        # Create a mailto link
        mailto_link = f"mailto:{email_to}?subject={urllib.parse.quote(email_subject)}&body={urllib.parse.quote(email_body)}"
        
        # Open the default email client
        webbrowser.open(mailto_link)
        
        st.sidebar.success("Email client opened!")
        
    if st.sidebar.button("Clear Current Analysis"):
        st.session_state.current_analysis = None
        st.experimental_rerun()

if user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Process user input
    if any(word in user_input.lower() for word in ["show", "list", "available", "applications", "files"]):
        try:
            # List all folders in the Supabase bucket
            with st.spinner("Fetching applications..."):
                response = supabase.storage.from_(supabase_bucket).list()
                
                # Don't make assumptions about the folder structure
                # Just show the raw files/folders
                if response:
                    items_list = []
                    for item in response:
                        items_list.append(f"- {item['name']}")
                    
                    response = "📋 Here are the available items in storage:\n\n" + "\n".join(items_list)
                    response += "\n\nTo analyze, type 'analyze' followed by the name (e.g., 'analyze Applicant Name')"
                else:
                    response = "❌ No items found in Supabase storage."
        except Exception as e:
            response = f"❌ Error accessing Supabase storage: {str(e)}"
    
    elif user_input.lower().startswith("analyze"):
        # Extract name from command without assuming folder structure
        name_to_analyze = user_input.lower().replace("analyze", "").strip()
        
        with st.spinner(f"Analyzing {name_to_analyze}..."):
            try:
                # First try a direct match
                direct_match = False
                
                # List all items and look for matches
                all_items = supabase.storage.from_(supabase_bucket).list()
                
                # Check for a matching metadata file
                for item in all_items:
                    if item['name'].endswith('metadata.json') and name_to_analyze in item['name']:
                        metadata_path = item['name']
                        direct_match = True
                        break
                
                if not direct_match:
                    # Try with path construction
                    metadata_path = f"{name_to_analyze}/metadata.json"
                
                # Get metadata.json from Supabase
                metadata_response = supabase.storage.from_(supabase_bucket).download(metadata_path)
                borrower_data = json.loads(metadata_response.decode('utf-8'))

                # Get list of related files - try both approaches
                try:
                    # Try to list contents as if name_to_analyze is a folder
                    file_list = supabase.storage.from_(supabase_bucket).list(name_to_analyze)
                except Exception:
                    # If that fails, search for matching filenames
                    file_list = []
                    for item in all_items:
                        if name_to_analyze in item['name'] and item['name'].endswith('.pdf'):
                            file_list.append(item)
                
                pdf_files = [item['name'] for item in file_list if item['name'].endswith('.pdf')]
                
                paystub_text = ""
                for pdf_file in pdf_files:
                    try:
                        # Download the PDF file - adjust path as needed
                        if '/' in pdf_file:
                            # If pdf_file already has path
                            file_path = pdf_file
                        else:
                            # Construct path
                            file_path = f"{name_to_analyze}/{pdf_file}"
                        
                        pdf_content = supabase.storage.from_(supabase_bucket).download(file_path)
                        
                        # Read the PDF content
                        from PyPDF2 import PdfReader
                        reader = PdfReader(io.BytesIO(pdf_content))
                        paystub_text += "\\n".join(page.extract_text() or "" for page in reader.pages)
                    except Exception as e:
                        paystub_text += f"\\n[Error reading {pdf_file}: {e}]"

                paystub_data = {"text": paystub_text}

                try:
                    with st.spinner("Running AI analysis..."):
                        result = run_assistant(paystub_data, borrower_data)
                    response = f"📊 Analysis for {name_to_analyze}:\n```json\n{json.dumps(result, indent=2)}\n```"
                    
                    # Store the current analysis for potential email
                    st.session_state.current_analysis = {
                        "folder_name": name_to_analyze,
                        "result": result
                    }
                    
                    response += "\n\n✉️ Analysis complete! Use the sidebar to send these results via email."
                    
                except Exception as e:
                    response = f"❌ Error analyzing {name_to_analyze}: {str(e)}"
            except Exception as e:
                response = f"❌ Error retrieving data for {name_to_analyze}: {str(e)}"
    
    else:
        response = """👋 Hello! Here are the commands you can use:
- 'show applications' to see available files
- 'analyze item_name' to analyze a specific application

Tip: Use the "Storage Settings" section to check your Supabase connection."""

    st.session_state.messages.append({"role": "assistant", "content": response})

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
