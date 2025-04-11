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

# Load environment variables from .env file
load_dotenv()

# Get the root directory and ensure data folder exists
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(ROOT_DIR, "data")

# Create data directory if it doesn't exist
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

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
        applications = [d for d in os.listdir(DATA_FOLDER) if os.path.isdir(os.path.join(DATA_FOLDER, d))]
        
        if applications:
            response = "📋 Here are the available applications:\n\n" + "\n".join(f"- {app}" for app in applications)
            response += "\n\nTo analyze an application, type 'analyze' followed by the folder name (e.g., 'analyze jane')"
        else:
            response = "❌ No applications found in the data folder."
    
    elif user_input.lower().startswith("analyze"):
        # Extract folder name from command
        folder_name = user_input.lower().replace("analyze", "").strip()
        folder_path = os.path.join(DATA_FOLDER, folder_name)
        metadata_path = os.path.join(folder_path, "metadata.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                borrower_data = json.load(f)

            documents = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
            paystub_text = ""
            for doc in documents:
                try:
                    with open(os.path.join(folder_path, doc), "rb") as file:
                        from PyPDF2 import PdfReader
                        reader = PdfReader(file)
                        paystub_text += "\\n".join(page.extract_text() or "" for page in reader.pages)
                except Exception as e:
                    paystub_text += f"\\n[Error reading {doc}: {e}]"

            paystub_data = {"text": paystub_text}

            try:
                result = run_assistant(paystub_data, borrower_data)
                response = f"📊 Analysis for {folder_name}:\n```json\n{json.dumps(result, indent=2)}\n```"
                
                # Store the current analysis for potential email
                st.session_state.current_analysis = {
                    "folder_name": folder_name,
                    "result": result
                }
                
                response += "\n\n✉️ Analysis complete! Use the sidebar to send these results via email."
                
            except Exception as e:
                response = f"❌ Error analyzing {folder_name}: {str(e)}"
        else:
            response = f"❌ Folder {folder_name} not found or missing metadata.json."
    
    else:
        response = """👋 Hello! Here are the commands you can use:
- 'show applications' to see available files
- 'analyze folder_name' to analyze a specific application"""

    st.session_state.messages.append({"role": "assistant", "content": response})

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
