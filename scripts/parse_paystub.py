import pdfplumber
import sys
import json
from datetime import datetime

def extract_fields_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    fields = {
        "gross_pay_per_period": None,
        "ytd_income": None,
        "pay_frequency": "Biweekly",  # default assumption
        "pay_period_start": None,
        "pay_period_end": None,
        "employer_name": None,
        "raw_text": text[:1000]  # helpful for GPT context
    }

    # Basic regex-free parsing (real implementation would be more robust)
    lines = text.splitlines()
    for line in lines:
        if "gross" in line.lower() and "$" in line:
            try:
                fields["gross_pay_per_period"] = float(line.replace("$", "").split()[-1].replace(",", ""))
            except:
                pass
        if "ytd" in line.lower() and "$" in line:
            try:
                fields["ytd_income"] = float(line.replace("$", "").split()[-1].replace(",", ""))
            except:
                pass
        if "period" in line.lower() and "-" in line:
            parts = line.split()
            for part in parts:
                if "/" in part:
                    try:
                        if fields["pay_period_start"] is None:
                            fields["pay_period_start"] = str(datetime.strptime(part, "%m/%d/%Y").date())
                        elif fields["pay_period_end"] is None:
                            fields["pay_period_end"] = str(datetime.strptime(part, "%m/%d/%Y").date())
                    except:
                        continue
        if "employer" in line.lower():
            fields["employer_name"] = line.split(":")[-1].strip()

    return fields

if __name__ == "__main__":
    pdf_path = sys.argv[1]
    fields = extract_fields_from_pdf(pdf_path)
    print(json.dumps(fields, indent=2))
