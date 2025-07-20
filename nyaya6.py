import os
import cv2
import pytesseract
import re
import time
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import google.generativeai as genai

# === CONFIGURATION =======================================================
PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf3.pdf"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
START_PAGE = 26
END_PAGE = 30 
OUTPUT_TXT_PATH = r"C:\Users\divya\Desktop\project\nyaya_fully_automated_output.txt"
GOOGLE_API_KEY = "AIzaSyCEarEwXeDYL1FUh0ym47fjtl8qPKT2cB0"

# === GROUND TRUTH TEXT ===================================================
CANONICAL_SUTRA = "प्रमाणप्रमेयसंशयप्रयोजनदृष्टान्तसिद्धान्तावयवतर्कनिर्णयवादजल्पवितण्डाहेत्वाभासच्छलजातिनिग्रहस्थानानां तत्त्वज्ञानान्निःश्रेयसाधिगमः ॥१।१।१॥"
CANONICAL_VATSAYANA_FOOTNOTE = """*The English equivalent for “tarka” is variously given as “confutation,” “argumentation,” “reductio ad absurdum,” “hypothetical reasoning,” etc.
† Vātsyāyana observes:—
त्रिविधा चास्य शास्त्रस्य प्रवृत्तिः । उद्देशो लक्षणं परीक्षा चेति ।
—(Nyāyabhāṣya)"""

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === HELPER FUNCTIONS ====================================================

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
        raise Exception(f"Failed to load PDF page {page_no}.")
    processed_image = preprocess_image(images[0])
    config = '--psm 4'
    text = pytesseract.image_to_string(processed_image, lang='eng+san', config=config)
    print(f"-> Raw text extracted successfully for page {page_no}.")
    return text

def get_general_correction(raw_text, genai_model):
    """(PASS 1) Uses Gemini API for general cleanup."""
    print(" -> AI Pass 1: Performing general cleanup...")
    prompt = f"""You are an editor cleaning up raw OCR text. Correct spelling, formatting, and remove garbage characters. Do not attempt to add scholarly diacritics.

**Raw OCR text to clean:**
---
{raw_text}
---

**Cleaned Text:**
"""
    try:
        response = genai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"   ❌ AI Pass 1 Failed: {e}")
        return raw_text

def add_diacritics_with_ai(cleaned_text, genai_model):
    """(PASS 2) Uses Gemini API for the specific task of adding diacritics."""
    print(" -> AI Pass 2: Adding scholarly diacritics...")
    prompt = f"""Your single task is to find every Sanskrit word inside parentheses in the provided text and add the correct IAST diacritics and formatting.

**Rule:** Convert any term like `(samsaya)` into `(*saṁśaya*)`.
**Rule:** Do not change any other part of the text.

**Text to process:**
---
{cleaned_text}
---

**Text with diacritics:**
"""
    try:
        response = genai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"   ❌ AI Pass 2 Failed: {e}")
        return cleaned_text

# === MAIN WORKFLOW ==========================================================
if __name__ == "__main__":
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY":
        print("❌ CRITICAL ERROR: GOOGLE_API_KEY is not set. Please add your key to the script.")
        exit()
        
    # Configure the Gemini client once
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    try:
        with open(OUTPUT_TXT_PATH, "w", encoding="utf-8") as f:
            print(f"✅ Opened output file for writing: {OUTPUT_TXT_PATH}")
            for page_num in range(START_PAGE, END_PAGE + 1):
                print("\n" + "="*70)
                print(f"PROCESSING PAGE {page_num}")
                print("="*70)
                
                try:
                    # Stage 1: Extraction
                    raw_text = extract_raw_text_from_page(PDF_PATH, page_num)
                    
                    # Stage 2: Two-Pass AI Correction
                    general_text = get_general_correction(raw_text, model)
                    polished_text = add_diacritics_with_ai(general_text, model)
                    
                    # Stage 3: Programmatic Override
                    print("-> Performing final programmatic override for canonical text...")
                    text_with_sutras = re.sub(r'प्रमाण.*॥१।१।१॥', CANONICAL_SUTRA, polished_text, flags=re.DOTALL)
                    perfect_text = re.sub(r'\*The English equivalent for “tarka”.*', CANONICAL_VATSAYANA_FOOTNOTE, text_with_sutras, flags=re.DOTALL | re.IGNORECASE)
                    
                    # Write to the consolidated file
                    f.write(f"\n\n{'='*25} START OF PAGE {page_num} {'='*25}\n\n")
                    f.write(perfect_text)
                    print(f"✅ Successfully processed and wrote page {page_num} to the file.")

                except Exception as e:
                    error_message = f"❌❌❌ An error occurred while processing page {page_num}: {e} ❌❌❌"
                    print(error_message)
                    f.write(f"\n\n{error_message}\n")
                    continue
                
                # Add a delay between processing each page
                if page_num < END_PAGE:
                    print("Waiting for 2 seconds before the next page...")
                    time.sleep(2)
        
        print("\n" + "="*70)
        print(f"ALL PAGES PROCESSED. Final consolidated file saved to:\n{OUTPUT_TXT_PATH}")
        print("="*70)

    except Exception as e:
        print(f"\n❌ A critical error occurred: {e}")