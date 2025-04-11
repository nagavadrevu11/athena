import pdfplumber
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
import argparse
from openai import OpenAI
import os

def pdf_to_jsonl(pdf_path: str, output_path: str = "guidelines.json"):
    """Convert PDF to JSONL format for OpenAI"""
    print("Reading PDF...")
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(
            page.extract_text() for page in pdf.pages 
            if page.extract_text()
        )
    
    print("Splitting into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=20,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = text_splitter.split_text(text)
    
    print(f"Writing {len(chunks)} chunks to JSON...")
    data = []
    for i, chunk in enumerate(chunks):
        data.append({
            "text": chunk,
            "metadata": {
                "section_id": i
            }
        })
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"JSON file created at: {output_path}")
    
    # Upload to OpenAI
    print("Uploading to OpenAI...")
    api_key = os.getenv("OPENAI_API_KEY").strip()
    client = OpenAI(api_key=api_key)
    
    with open(output_path, "rb") as file:
        response = client.files.create(
            file=file,
            purpose="assistants"
        )
    
    print(f"File uploaded successfully! File ID: {response.id}")
    print("\nFull response:")
    print(json.dumps(response.model_dump(), indent=2))
    return response.id

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF guidelines to JSON format")
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument("--output", default="guidelines.json", help="Output JSON file path")
    args = parser.parse_args()
    
    file_id = pdf_to_jsonl(args.pdf, args.output)


