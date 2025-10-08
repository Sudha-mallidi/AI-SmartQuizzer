import fitz  # PyMuPDF
import re
from .models import MCQ

def extract_mcqs_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)   # open using path, not .read()
    text = ""
    for page in doc:
        text += page.get_text()
        text = re.sub(r'\r\n|\r', '\n', text)        # Convert CRLF or CR to LF
    text = re.sub(r'\n\s*\n', '\n', text)       # Remove multiple blank lines
    text = re.sub(r'[ \t]+', ' ', text)

    # Regex pattern for MCQs
    pattern = re.compile(
        r"(\d+)\.\s*(.*?)\n\s*A[\)\.]?\s*(.*?)\n\s*B[\)\.]?\s*(.*?)\n\s*C[\)\.]?\s*(.*?)\n\s*D[\)\.]?\s*(.*?)\n\s*Answer[:\s]*([A-D])",
        re.DOTALL | re.IGNORECASE
    )

    matches = pattern.findall(text)
    mcqs = []

    for match in matches:
        q_no, question, a, b, c, d, ans = match
        mcqs.append({
            "question_no": int(q_no.strip()),
            "question": question.strip().replace("\n", " "),
            "option_a": a.strip().replace("\n", " "),
            "option_b": b.strip().replace("\n", " "),
            "option_c": c.strip().replace("\n", " "),
            "option_d": d.strip().replace("\n", " "),
            "correct_answer": ans.strip().upper()
        })

    print(f"Extracted {len(mcqs)} MCQs from PDF: {pdf_path}")    
    return mcqs