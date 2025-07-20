import os
import cv2
import pytesseract
import re
import time
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import google.generativeai as genai
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# === CONFIGURATION (No changes) =========================================
PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf3.pdf"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
START_PAGE = 26
END_PAGE = 30 
OUTPUT_TXT_PATH = r"C:\Users\divya\Desktop\project\nyaya_consolidated_output_final.txt"
GOOGLE_API_KEY = "AIzaSyCEarEwXeDYL1FUh0ym47fjtl8qPKT2cB0"

# === GROUND TRUTH TEXT (No changes) =====================================
CANONICAL_SUTRA = "प्रमाणप्रमेयसंशयप्रयोजनदृष्टान्तसिद्धान्तावयवतर्कनिर्णयवादजल्पवितण्डाहेत्वाभासच्छलजातिनिग्रहस्थानानां तत्त्वज्ञानान्निःश्रेयसाधिगमः ॥१।१।१॥"
CANONICAL_VATSAYANA_FOOTNOTE = """*The English equivalent for “tarka” is variously given as “confutation,” “argumentation,” “reductio ad absurdum,” “hypothetical reasoning,” etc.
† Vātsyāyana observes:—
त्रिविधा चास्य शास्त्रस्य प्रवृत्तिः । उद्देशो लक्षणं परीक्षा चेति ।
—(Nyāyabhāṣya)"""

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === HELPER FUNCTIONS (No changes) =======================================
# All helper functions (preprocess_image, extract_raw_text_from_page, 
# final_polish_scalable) are the same.

def preprocess_image(pil_image):
    # ... (code is the same)
    print("-> Preprocessing image for OCR...")
    img = np.array(pil_image.convert("L"))
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    denoised = cv2.medianBlur(thresh, 3)
    return denoised

def extract_raw_text_from_page(pdf_path, page_no):
    # ... (code is the same)
    print(f"-> Extracting raw text from page {page_no}...")
    images = convert_from_path(pdf_path, dpi=300, first_page=page_no, last_page=page_no, poppler_path=POPPLER_PATH)
    if not images: raise Exception(f"Failed to load PDF page {page_no}.")
    processed_image = preprocess_image(images[0])
    config = '--psm 4'
    text = pytesseract.image_to_string(processed_image, lang='eng+san', config=config)
    print(f"-> Raw text extracted successfully for page {page_no}.")
    return text

def final_polish_scalable(text):
    # ... (code is the same)
    print("-> Applying final scalable polishing rules...")
    text = re.sub(r'^\s*N \* nr\s*', '', text, flags=re.IGNORECASE)
    def transliterate_match(match):
        original_word = match.group(1).replace('-\n', '').replace(' ', '')
        transliterated_word = transliterate(original_word, sanscript.ITRANS, sanscript.IAST)
        return f"(*{transliterated_word}*)"
    text = re.sub(r'\((\S+?)\)', transliterate_match, text)
    return text

# === AI CORRECTION FUNCTION (Updated with Few-Shot Prompt) ===============
def get_gemini_correction(raw_text):
    """Uses the Gemini API with a few-shot prompt for high accuracy."""
    print("\n-> Sending text to Gemini API with a few-shot prompt...")
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY":
        print("❌ ERROR: GOOGLE_API_KEY is not set.")
        return raw_text

    # --- NEW: FEW-SHOT PROMPT ---
    # We show the AI exactly what we want by giving it a clear example.
    prompt = f"""Your task is to correct OCR errors in the provided text. Be faithful to the original source. Follow the example below.

### EXAMPLE ###

RAW OCR TEXT:
---
Book 1L.—Cuarrer 1.
Supreme लकि is attained by the knowledge...
---

CORRECTED TEXT:
---
Book I.—Chapter 1.
Supreme felicity is attained by the knowledge...
---

### TASK ###

RAW OCR TEXT:
---
{raw_text}
---

CORRECTED TEXT:
---
"""

    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        # We can increase the temperature slightly to encourage completion
        generation_config = genai.types.GenerationConfig(temperature=0.2)
        
        print("-> Sending request to Gemini API...")
        response = model.generate_content(prompt, generation_config=generation_config)
        
        print("-> AI has returned the generally corrected text.")
        return response.text
    except Exception as e:
        print(f"❌ The API call failed: {e}")
        return raw_text

# === MAIN WORKFLOW (No changes) ==========================================
if __name__ == "__main__":
    try:
        with open(OUTPUT_TXT_PATH, "w", encoding="utf-8") as f:
            print(f"✅ Opened output file for writing: {OUTPUT_TXT_PATH}")
            for page_num in range(START_PAGE, END_PAGE + 1):
                print("\n" + "="*70)
                print(f"PROCESSING PAGE {page_num}")
                print("="*70)
                try:
                    raw_text = extract_raw_text_from_page(PDF_PATH, page_num)
                    ai_corrected_text = get_gemini_correction(raw_text)
                    text_with_sutras = re.sub(r'प्रमाण.*॥१।१।१॥', CANONICAL_SUTRA, ai_corrected_text, flags=re.DOTALL)
                    text_with_footnotes = re.sub(r'\*The English equivalent for “tarka”.*', CANONICAL_VATSAYANA_FOOTNOTE, text_with_sutras, flags=re.DOTALL | re.IGNORECASE)
                    perfect_text = final_polish_scalable(text_with_footnotes)
                    
                    f.write(f"\n\n{'='*25} START OF PAGE {page_num} {'='*25}\n\n")
                    f.write(perfect_text)
                    print(f"✅ Successfully processed and wrote page {page_num} to the file.")
                except Exception as e:
                    error_message = f"❌❌❌ An error occurred while processing page {page_num}: {e} ❌❌❌"
                    print(error_message)
                    f.write(f"\n\n{error_message}\n")
                    continue
                if page_num < END_PAGE:
                    print("Waiting for 2 seconds before processing the next page...")
                    time.sleep(2)
        print("\n" + "="*70)
        print("ALL PAGES PROCESSED. Consolidated file has been saved.")
        print("="*70)
    except Exception as e:
        print(f"\n❌ A critical error occurred trying to open the output file: {e}")