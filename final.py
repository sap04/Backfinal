import io
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

    for page in PDFPage.get_pages(file, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True):
        retstr.write(f'Page {page_no}: ')
        interpreter.process_page(page)
        page_no += 1

    device.close()
    text = retstr.getvalue()
    retstr.close()
    return text

def initiate_chat():
    return model.start_chat(history=[])

def send_message(chat, input_text, pdf_text):
    return chat.send_message([input_text, pdf_text])

@app.post("/generate-contract-summary/")
async def generate_contract_summary(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")

    pdf_text = convert_pdf_to_text(io.BytesIO(await file.read()))
    input_text = "Write a short summary for this contract include: dates, Parties, Payment, Term, Termination, Confidentiality, Intellectual Property, Governing Law"
    response = model.generate_content([input_text, pdf_text])
    generated_text = response.text

    return {"pdf_text": pdf_text, "summary": generated_text}

@app.post("/chat/")
async def chat_with_model(input_text: str, pdf_text: str):
    if not input_text:
        raise HTTPException(status_code=400, detail="Input text is required")

    if not pdf_text:
        raise HTTPException(status_code=400, detail="PDF text is required")

    chat = initiate_chat()
    response = send_message(chat, input_text, pdf_text)
    return {"response_text": response.text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
