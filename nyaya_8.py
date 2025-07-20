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

# --- Define the final output file ---
FINAL_OUTPUT_PATH = r"C:\Users\divya\Desktop\project\nyaya_ai_only_output.txt"

# --- Gemini API Key ---
GOOGLE_API_KEY = "AIzaSyCG8Zu2vpLLs-ZW4xaDQIE_-IQIxercCzQ"

# --- Set the page range to process ---
PAGE_RANGE = (26, 30)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === HELPER FUNCTIONS ====================================================

def preprocess_image(pil_image):
    """Applies cleaning filters to an image for better OCR accuracy."""
    print("-> Preprocessing image...")
    img = np.array(pil_image.convert("L"))
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def get_full_ai_correction(raw_text):
    """
    Uses a single, advanced Gemini prompt to perform all corrections.
    """
    print("-> Sending text to Gemini API for full correction...")
    
    # This advanced prompt asks the AI to handle all tasks at once.
    prompt = f"""**System Instruction:**
You are a meticulous archivist and an expert scholar of Sanskrit philosophy, correcting a text transcription from a scanned document. Your absolute priority is to be faithful to the original source text.

**Your Instructions:**
1.  The input text is a mix of main commentary and unwanted "stray text" (isolated lines of transliterated Sanskrit). **You must identify and DELETE all of this stray text completely.**
2.  Find any broken or incorrect Devanagari sūtras within the main text and replace them with their correct, canonical versions.
3.  Correct all spelling and grammar errors in the English prose.
4.  Find all Sanskrit terms in parentheses, like `(pramana)`, and format them with proper academic IAST diacritics and italics, like `(*pramāṇa*)`.
5.  Provide ONLY the restored and perfectly formatted text as your final output.

**Raw OCR text to restore:**
---
{raw_text}
---

**Restored and Perfected Text:**
"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        print("-> AI has returned the corrected text.")
        return response.text
    except Exception as e:
        print(f"   ❌ AI Correction Failed: {e}")
        return raw_text

# === MAIN WORKFLOW ==========================================================
if __name__ == "__main__":
    
    # Configure Gemini client
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY":
        print("❌ CRITICAL ERROR: GOOGLE_API_KEY is not set.")
        exit()
    genai.configure(api_key=GOOGLE_API_KEY)

    try:
        with open(FINAL_OUTPUT_PATH, "w", encoding="utf-8") as f:
            start_page, end_page = PAGE_RANGE
            
            for page_num in range(start_page, end_page + 1):
                print("\n" + "="*70)
                print(f"PROCESSING PAGE {page_num} of {end_page}")
                print("="*70)
                
                try:
                    # 1. Get the image for the current page
                    page_image = convert_from_path(PDF_PATH, poppler_path=POPPLER_PATH, dpi=300, first_page=page_num, last_page=page_num)[0]
                    
                    # 2. Preprocess and OCR the ENTIRE page
                    processed_image = preprocess_image(page_image)
                    print("-> Performing OCR on full page...")
                    raw_text = pytesseract.image_to_string(processed_image, lang='eng+san', config='--psm 3')
                    
                    # 3. Get the final, corrected text from the AI
                    final_text = get_full_ai_correction(raw_text)
                    
                    # 4. Write to File
                    f.write(f"\n\n{'='*25} START OF PAGE {page_num} {'='*25}\n\n")
                    f.write(final_text)
                    print(f"✅ Successfully processed and wrote page {page_num} to the file.")

                except Exception as e:
                    error_message = f"❌ An error occurred while processing page {page_num}: {e}"
                    print(error_message)
                    f.write(f"\n\n{error_message}\n")
                    continue
                
                # Add a polite delay between API calls
                if page_num < end_page:
                    print("Waiting for 2 seconds before the next API call...")
                    time.sleep(2)
        
        print("\n" + "="*70)
        print(f"ALL PAGES PROCESSED. Final output saved to:\n{FINAL_OUTPUT_PATH}")
        print("="*70)

    except Exception as e:
        print(f"\n❌ A critical error occurred during the process: {e}")