import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
from scripts.evaluate_income import run_assistant
from streamlit_renderer import render_evaluation
from openai import OpenAI
from dotenv import load_dotenv
from supabase import create_client
import io

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
    st.sidebar.success(f"✅ Welcome, are you ready to review loans? ")

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
    pass

st.title("🧾 AI Underwriter Assistant")

# Initialize chat history and state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "current_analysis" not in st.session_state:
    st.session_state.current_analysis = None

if "applications_list" not in st.session_state:
    st.session_state.applications_list = None

# Initialize application statuses
if "application_statuses" not in st.session_state:
    st.session_state.application_statuses = {}

# Create tabs for different sections
analysis_tab, chat_history_tab = st.tabs(["Current Analysis", "Chat History"])

# Analysis content will go in the first tab
with analysis_tab:
    # Show the current analysis content or applications list
    if st.session_state.current_analysis:
        folder_name = st.session_state.current_analysis["folder_name"]
        
        # Status selection in the sidebar
        st.sidebar.markdown("### Application Status")
        
        # Get current status or default to "Submitted"
        current_status = st.session_state.application_statuses.get(folder_name, "Submitted")
        
        # Status selection widget
        new_status = st.sidebar.selectbox(
            "Select status:",
            ["Submitted", "Approved", "Conditional Approval", "Decline", "Escalate"],
            index=["Submitted", "Approved", "Conditional Approval", "Decline", "Escalate"].index(current_status)
        )
        
        # Update status when changed
        if new_status != current_status:
            st.session_state.application_statuses[folder_name] = new_status
            # Here you would also update the status in Supabase if needed
            try:
                # Example of updating status in a metadata file
                # This is a placeholder - implement according to your data structure
                # supabase.storage.from_(supabase_bucket).update_metadata(f"{folder_name}/metadata.json", {"status": new_status})
                st.sidebar.success(f"Status updated to: {new_status}")
            except Exception as e:
                st.sidebar.error(f"Failed to update status: {str(e)}")
        
        # Display status with appropriate color
        status_colors = {
            "Submitted": "blue",
            "Approved": "green",
            "Conditional Approval": "orange",
            "Decline": "red",
            "Escalate": "purple"
        }
        
        # Display a colored status badge
        st.markdown(f"""
        <div style='
            display: inline-block;
            padding: 0.2em 0.6em;
            border-radius: 0.5em;
            font-weight: bold;
            background-color: {status_colors.get(new_status, "gray")};
            color: white;
            margin-bottom: 1em;'>
            {new_status}
        </div>
        """, unsafe_allow_html=True)
        
        # Display the current analysis
        st.subheader(f"Analysis for: {folder_name}")
        # The render_evaluation function will display the analysis content here
        
    elif st.session_state.applications_list:
        # Display the applications list
        st.subheader("Available Applications")
        st.markdown(st.session_state.applications_list)
    else:
        st.info("No current analysis. Use the chat below to analyze an application.")

# Chat input
user_input = st.chat_input("Ask about available applications...")

# Simple clear button in sidebar
if st.session_state.current_analysis:
    if st.sidebar.button("Clear Current Analysis"):
        st.session_state.current_analysis = None
        st.rerun()

if user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Process user input
    if any(word in user_input.lower() for word in ["show", "list", "available", "applications", "files"]):
        try:
            # List all folders in the Supabase bucket
            with st.spinner("Fetching applications..."):
                response = supabase.storage.from_(supabase_bucket).list()
                
                if response:
                    items_list = []
                    for item in response:
                        # Get status if available
                        status = st.session_state.application_statuses.get(item['name'], "")
                        status_badge = f" [{status}]" if status else ""
                        items_list.append(f"- {item['name']}{status_badge}")
                    
                    # Create formatted response
                    formatted_list = "\n".join(items_list)
                    response_text = f"📋 Here are the list of applications to review for today:\n\n{formatted_list}"
                    response_text += "\n\nTo analyze, type 'analyze' followed by the name (e.g., 'analyze Naga')"
                    
                    # Clear any current analysis and set applications list
                    st.session_state.current_analysis = None
                    st.session_state.applications_list = response_text
                    
                    # For chat history
                    response = response_text
                else:
                    response = "❌ No items found in Supabase storage."
                    st.session_state.applications_list = "No applications found."
                    
                # Force refresh to show in current analysis tab
                st.rerun()
                
        except Exception as e:
            response = f"❌ Error accessing Supabase storage: {str(e)}"
            st.session_state.applications_list = None
    
    elif user_input.lower().startswith("analyze"):
        # Extract name from command without assuming folder structure
        name_to_analyze = user_input.lower().replace("analyze", "").strip()
        
        # Clear applications list when analyzing
        st.session_state.applications_list = None
        
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
                document_contents = []  # Store document contents for rendering
                
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
                        
                        # Extract text for analysis
                        doc_text = "\\n".join(page.extract_text() or "" for page in reader.pages)
                        paystub_text += doc_text
                        
                        # Store document content for rendering
                        document_contents.append({
                            "name": pdf_file,
                            "content": doc_text
                        })
                    except Exception as e:
                        paystub_text += f"\\n[Error reading {pdf_file}: {e}]"

                paystub_data = {"text": paystub_text}

                try:
                    with st.spinner("Running AI analysis..."):
                        result = run_assistant(paystub_data, borrower_data)
                    
                    # Store the current analysis
                    st.session_state.current_analysis = {
                        "folder_name": name_to_analyze,
                        "result": result
                    }
                    
                    # If no status exists for this application, set it to "Submitted"
                    if name_to_analyze not in st.session_state.application_statuses:
                        st.session_state.application_statuses[name_to_analyze] = "Submitted"
                    
                    # Switch to the analysis tab and render the evaluation
                    with analysis_tab:
                        render_evaluation(result, borrower_data, document_contents)
                    
                    # Still provide text response for chat history
                    response = f"✅ Analysis complete for {name_to_analyze}! View results in the Current Analysis tab."
                    
                except Exception as e:
                    response = f"❌ Error analyzing {name_to_analyze}: {str(e)}"
            except Exception as e:
                response = f"❌ Error retrieving data for {name_to_analyze}: {str(e)}"
    
    else:
        response = """👋 Hello! Here are the commands you can use:
- 'show applications' to see available files
- 'analyze Application' to analyze a specific application
"""

    st.session_state.messages.append({"role": "assistant", "content": response})

# Display chat history in the second tab
with chat_history_tab:
    st.subheader("Previous Conversations")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

