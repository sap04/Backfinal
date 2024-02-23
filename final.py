import io
import re
from fastapi import FastAPI, UploadFile, File, HTTPException
import google.generativeai as genai
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

app = FastAPI()

# Configure generative model with API key
GOOGLE_API_KEY = "AIzaSyBFmJax_4lJoUYgcMarFzEtIQBRklGVdCU"  # Replace this with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def convert_pdf_to_text(file):
    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    page_no = 1

    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos = set()

    initial_date = None
    expiry_date = None
    contract_owner = None
    signee = None

    for page in PDFPage.get_pages(file, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True):
        retstr.write(f'Page {page_no}: ')
        interpreter.process_page(page)
        text = retstr.getvalue()
        page_no += 1

        if not initial_date:
            initial_date = extract_date(text)

        if not expiry_date:
            expiry_date = extract_date(text)

        match_contract_owner = re.search(r'Contract Owner: (.+)', text)
        if match_contract_owner:
            contract_owner = match_contract_owner.group(1)

        match_signee = re.search(r'Signee: (.+)', text)
        if match_signee:
            signee = match_signee.group(1)

    device.close()
    retstr.close()
    text = text.replace('\n', ' ')

    return {
        "text": text,
        "initial_date": initial_date,
        "expiry_date": expiry_date,
        "contract_owner": contract_owner,
        "signee": signee
    }

def extract_date(text):
    date_regex = r'\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2} [a-zA-Z]{3,9} \d{4})\b'
    match = re.search(date_regex, text)
    if match:
        return match.group()
    return None

@app.post("/generate-contract-summary/")
async def generate_contract_summary(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")

    pdf_data = convert_pdf_to_text(io.BytesIO(await file.read()))
    pdf_text = pdf_data["text"]

    # Define input text for generating content
    input_text = """
    Summarize the key details of this contract including the following:
    - Dates: initial_date, expiry_date
    - Contract Owner
    - Signee
    - Payment terms
    - Term of the contract
    - Termination conditions
    - Confidentiality provisions
    - Intellectual property rights
    - Governing law

    Provide the information in the following format:
    initial_date: <initial_date>
    expiry_date: <expiry_date>
    contract_owner: <contract_owner>
    signee: <signee>
    """

    # Generate content using both PDF text and input text
    response = model.generate_content([input_text, pdf_text])
    generated_text = response.text

    # Parse generated text to get initial_date, expiry_date, contract_owner, and signee if not found in PDF
    initial_date = None
    expiry_date = None
    contract_owner = None
    signee = None
    match = re.search(r'initial_date: (.+)', generated_text)
    if match:
        initial_date = match.group(1)
    match = re.search(r'expiry_date: (.+)', generated_text)
    if match:
        expiry_date = match.group(1)
    match = re.search(r'contract_owner: (.+)', generated_text)
    if match:
        contract_owner = match.group(1)
    match = re.search(r'signee: (.+)', generated_text)
    if match:
        signee = match.group(1)

    # Remove newlines from generated text
    
    
    generated_text = generated_text.replace('\n', ' ')

    return {
        "generated_text": generated_text,
        "pdf_text": pdf_text,
        "initial_date": initial_date,
        "expiry_date": expiry_date,
        "contract_owner": contract_owner,
        "signee": signee
    }


@app.post("/chat/")
async def chat_with_model(input_text: str, pdf_text: str):
    if not input_text:
        raise HTTPException(status_code=400, detail="Input text is required")

    if not pdf_text:
        raise HTTPException(status_code=400, detail="PDF text is required")

    chat=model.start_chat(history=[])
    response = chat.send_message(['refer the contract and respond minimum words: '+input_text, pdf_text])

    reply=response.text
    reply =reply.replace('\n', ' ')

    return {"response_text": reply}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
