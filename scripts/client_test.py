import requests
import argparse
import json

def main(pdf_path, borrower_json_path):
    url = "http://localhost:8000/underwrite/"

    with open(pdf_path, "rb") as f:
        files = {"file": ("paystub.pdf", f, "application/pdf")}

        with open(borrower_json_path, "r") as meta_file:
            metadata = meta_file.read()
            data = {"borrower_json": metadata}

        print(f"Sending request to {url}...")
        response = requests.post(url, files=files, data=data)

        if response.status_code == 200:
            print("✅ Underwriting report:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("❌ Error:")
            print(response.status_code)
            print(response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test local underwriting API client.")
    parser.add_argument("--paystub", required=True, help="Path to the PDF file.")
    parser.add_argument("--borrower", required=True, help="Path to the borrower metadata JSON.")
    args = parser.parse_args()
    main(args.paystub, args.borrower)
