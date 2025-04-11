from fastapi import FastAPI, File, UploadFile, Form
import json
import os
from scripts.parse_paystub import extract_fields_from_pdf
import tempfile
from scripts.evaluate_income import run_assistant
app = FastAPI()



@app.post("/underwrite/")
async def underwrite(
    file: UploadFile = File(...),
    borrower_json: str = Form(...)
):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp.write(await file.read())
    temp.close()

    paystub_data = extract_fields_from_pdf(temp.name)
    borrower_data = json.loads(borrower_json)
    result = run_assistant(paystub_data, borrower_data)
    return result
