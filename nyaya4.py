import os
import cv2
import pytesseract
import re
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import google.generativeai as genai

# === CONFIGURATION =======================================================
# Ensure all these paths and your API key are correct.

PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf3.pdf"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
PAGE_NO = 26

# --- IMPORTANT: Replace with your actual key from Google AI Studio ---
GOOGLE_API_KEY = "AIzaSyCEarEwXeDYL1FUh0ym47fjtl8qPKT2cB0"

# --- Define the path for the final, perfect output text file ---
OUTPUT_TXT_PATH = r"C:\Users\divya\Desktop\project\nyaya_PERFECT_output.txt"

# === GROUND TRUTH TEXT ===================================================
# We store the 100% correct versions of the text to ensure final accuracy.

CANONICAL_SUTRA = "प्रमाणप्रमेयसंशयप्रयोजनदृष्टान्तसिद्धान्तावयवतर्कनिर्णयवादजल्पवितण्डाहेत्वाभासच्छलजातिनिग्रहस्थानानां तत्त्वज्ञानान्निःश्रेयसाधिगमः ॥१।१।१॥"

CANONICAL_VATSAYANA_FOOTNOTE = """*The English equivalent for “tarka” is variously given as “confutation,” “argumentation,” “reductio ad absurdum,” “hypothetical reasoning,” etc.
† Vātsyāyana observes:—
त्रिविधा चास्य शास्त्रस्य प्रवृत्तिः । उद्देशो लक्षणं परीक्षा चेति ।
—(Nyāyabhāṣya)"""

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# === STAGE 1: OCR EXTRACTION ===============================================
def preprocess_image(pil_image):
    """Applies cleaning filters to an image to improve OCR accuracy."""
    print("-> Preprocessing image for OCR...")
    img = np.array(pil_image.convert("L"))
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    denoised = cv2.medianBlur(thresh, 3)
    return denoised

def extract_raw_text_from_page(pdf_path, page_no):
    """Converts a PDF page to a preprocessed image and extracts raw text."""
    print(f"-> Extracting raw text from page {page_no}...")
    images = convert_from_path(pdf_path, dpi=300, first_page=page_no, last_page=page_no, poppler_path=POPPLER_PATH)
    if not images:
        raise Exception("Failed to load PDF page.")
    processed_image = preprocess_image(images[0])
    config = '--psm 4'
    text = pytesseract.image_to_string(processed_image, lang='eng+san', config=config)
    print("-> Raw text extracted successfully.")
    return text


# === STAGE 2: GENERAL AI CORRECTION =========================================
def get_ai_correction(raw_text):
    """Uses the Gemini API for a general cleanup of the raw text."""
    print("\n-> Sending text to Gemini API for general cleanup...")
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY":
        print("❌ ERROR: GOOGLE_API_KEY is not set.")
        return raw_text

    prompt = """**System Instruction:**
You are a meticulous archivist correcting a text transcription from a scanned document. Your absolute priority is to be faithful to the original source text. Your task is to restore the raw OCR text provided below.

**Rules:**
1. Correct obvious OCR errors (misread letters, formatting).
2. Remove garbage characters not part of the text.
3. Do not re-interpret or philosophically change the text. Your goal is faithful restoration, not creative editing.
4. Provide ONLY the restored text as your final output. Do not add any commentary or introductory phrases.

**Raw OCR text to restore:**
---
{}
---
""".format(raw_text)

    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        safety_settings = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        response = model.generate_content(prompt, safety_settings=safety_settings)
        print("-> AI has returned the generally corrected text.")
        return response.text
    except Exception as e:
        print(f"❌ The API call failed: {e}")
        return raw_text


# === STAGE 4: FINAL POLISHING ==============================================
def final_polish(text):
    """Applies final deterministic cleaning rules for a perfect output."""
    print("-> Applying final polishing rules...")
    
    # Remove any lingering noise at the beginning of the file, case-insensitive
    if text.lstrip().lower().startswith("n * nr"):
        text = re.sub(r'^\s*N \* nr\s*', '', text, flags=re.IGNORECASE)

    # Add diacritics to parenthetical terms
    replacements = {
        "(pramana)": "(*pramāṇa*)",
        "(pra- meya)": "(*prameya*)", # Handles space
        "(prameya)": "(*prameya*)",
        "(samsaya)": "(*saṁśaya*)",
        "(prayojana)": "(*prayojana*)",
        "(drstanta)": "(*dṛṣṭānta*)",
        "(siddhanta)": "(*siddhānta*)",
        "(avayava)": "(*avayava*)",
        "(tarka*)": "(*tarka*)*", # Keep the asterisk outside
        "(nirnaya)": "(*nirṇaya*)",
        "(vada)": "(*vāda*)",
        "(jalpa)": "(*jalpa*)",
        "(vitanda)": "(*vitaṇḍā*)",
        "(hetvabhasa)": "(*hetvābhāsa*)",
        "(chala)": "(*chala*)",
        "(jati)": "(*jāti*)",
        "(nigrahasthana)": "(*nigrahasthāna*)"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


# === MAIN WORKFLOW ==========================================================
if __name__ == "__main__":
    
    # Run Stage 1
    raw_text = extract_raw_text_from_page(PDF_PATH, PAGE_NO)
    
    # Run Stage 2
    ai_corrected_text = get_ai_correction(raw_text)
    
    # Run Stage 3: Programmatic Override for canonical text
    print("-> Performing programmatic corrections for 100% accuracy...")
    text_with_sutras = re.sub(r'प्रमाण.*॥१।१।१॥', CANONICAL_SUTRA, ai_corrected_text, flags=re.DOTALL)
    text_with_footnotes = re.sub(r'\*The English equivalent for “tarka”.*', CANONICAL_VATSAYANA_FOOTNOTE, text_with_sutras, flags=re.DOTALL | re.IGNORECASE)

    # Run Stage 4
    perfect_text = final_polish(text_with_footnotes)
    
    # Save the final, perfect result
    try:
        with open(OUTPUT_TXT_PATH, "w", encoding="utf-8") as f:
            f.write(perfect_text)
            
        print("\n" + "="*50)
        print("✅✅✅ Success! Perfect output has been saved to: ✅✅✅")
        print(OUTPUT_TXT_PATH)
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ An error occurred while saving the file: {e}")