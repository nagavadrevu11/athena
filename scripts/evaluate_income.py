from openai import OpenAI
import json
import sys
import os
import pdfplumber
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from openai import OpenAI

# Initialize OpenAI client with API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")
client = None

# Only initialize the client if the API key is available
if api_key:
    client = OpenAI(api_key=api_key)
else:
    print("Warning: OPENAI_API_KEY environment variable not set")

# Function tool schema
tools = [
    {
        "type": "function",
        "function": {
            "name": "underwrite_income",
            "description": "Calculates qualifying income and action items for salaried income based on Fannie Mae rules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "qualifying_income_monthly": {
                        "type": "number",
                        "description": "Calculated monthly qualifying income"
                    },
                    "income_type": {
                        "type": "string",
                        "enum": ["Salaried"]
                    },
                    "action_items": {
                        "type": "array",
                        "items": { "type": "string" },
                        "description": "Items underwriter should follow up on"
                    },
                    "guideline_citations": {
                        "type": "array",
                        "items": { "type": "string" },
                        "description": "Relevant Fannie Mae guideline references"
                    }
                },
                "required": ["qualifying_income_monthly", "income_type", "action_items"]
            }
        }
    }
]

def run_assistant(paystub_data, borrower_data):
    print("Starting analysis...")
    
    # Check if OpenAI client is initialized
    if not client:
        return {
            "qualifying_income_monthly": 0,
            "income_type": "Salaried",
            "action_items": ["Error: OpenAI API key not set. Please set the OPENAI_API_KEY environment variable."],
            "guideline_citations": []
        }
    
    prompt = f"""
You are an expert mortgage underwriting assistant following Fannie Mae guidelines.

Use the following extracted paystub data and borrower application data to determine the qualifying monthly income.

Paystub Data:
{json.dumps(paystub_data, indent=2)}

Borrower Info:
{json.dumps(borrower_data, indent=2)}

Respond with:
- Monthly qualifying income
- Income type (Salaried)
- Action items (e.g., missing docs, clarification needs)
- Guideline references (e.g., B3-3.1-05)
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": "You are a mortgage underwriting assistant."},
                {"role": "user", "content": prompt}
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=1000
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        return json.loads(tool_call.function.arguments)
        
    except Exception as e:
        return {
            "qualifying_income_monthly": 0,
            "income_type": "Salaried",
            "action_items": [f"Error: {str(e)}. Please review manually."],
            "guideline_citations": []
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate borrower income using Fannie Mae guidelines")
    parser.add_argument("--paystub", required=True, help="Path to the PDF file")
    parser.add_argument("--borrower", required=True, help="Path to the borrower metadata JSON")
    
    args = parser.parse_args()

    with open(args.borrower, "r") as f:
        borrower_data = json.load(f)

    # Process the paystub
    with pdfplumber.open(args.paystub) as pdf:
        paystub_text = "\n".join(
            page.extract_text() for page in pdf.pages 
            if page.extract_text()
        )
        paystub_data = {"text": paystub_text.strip()}

    result = run_assistant(paystub_data, borrower_data)
    print(json.dumps(result, indent=2))
