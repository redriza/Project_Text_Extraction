import os
import cv2
import pytesseract
import re
import csv
import time
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import google.generativeai as genai

# === CONFIGURATION =======================================================
PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf3.pdf"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
SUTRA_DB_PATH = r"C:\Users\divya\Desktop\project\sutras_db.csv"
FINAL_OUTPUT_PATH = r"C:\Users\divya\Desktop\project\nyaya_final_output.txt"
PAGE_RANGE = (26, 30)

# --- Define a precise crop zone to isolate the main text block ---
# This is the best way to prevent stray text from being read by the OCR.
CROP_ZONE = (200, 250, 2350, 3100) 

GOOGLE_API_KEY = "AIzaSyCEarEwXeDYL1FUh0ym47fjtl8qPKT2cB0"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === HELPER FUNCTIONS ====================================================

def load_sutra_database(db_path):
    """Loads the ground truth sūtras from your CSV file."""
    print(f"-> Loading Sūtra database from: {db_path}")
    sutra_map = {}
    try:
        with open(db_path, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            for row in reader:
                if len(row) == 2: sutra_map[row[0].strip()] = row[1].strip()
        print(f"✅ Successfully loaded {len(sutra_map)} sūtras.")
        return sutra_map
    except Exception as e:
        print(f"❌ CRITICAL ERROR loading database: {e}"); exit()

def preprocess_image(pil_image):
    """Applies cleaning filters to an image."""
    print("-> Preprocessing image...")
    img = np.array(pil_image.convert("L"))
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def get_ai_cleanup(raw_text):
    """Uses the powerful prompt to remove stray text and clean English."""
    print("-> Using AI to remove stray text and clean English...")
    
    # This prompt explicitly tells the AI to delete the unwanted lines.
    prompt = f"""You are an expert editor. Your task is to restore raw OCR text. The input is a mix of main English commentary and unwanted "stray text" (isolated lines of transliterated Sanskrit).

**Your Instructions:**
1.  **DELETE** all of the stray transliterated Sanskrit lines completely.
2.  Correct the spelling and grammar of the remaining English prose.
3.  Do not alter or remove the main Devanagari sūtras.
4.  Provide ONLY the cleaned main text as your output.

**Raw OCR text to restore:**
---
{raw_text}
---

**Restored and Cleaned Text:**
"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        print("-> AI cleanup complete.")
        return response.text
    except Exception as e:
        print(f"   ❌ AI Cleanup Failed: {e}")
        return raw_text

def insert_ground_truth_sutras(text, sutra_map):
    """Programmatically inserts the correct Devanagari sūtras."""
    print("-> Inserting correct Devanagari sūtras...")
    for sutra_num, sutra_text in sorted(sutra_map.items(), key=lambda item: [int(i) for i in item[0].split('.')], reverse=True):
        display_num = sutra_num.split('.')[-1]
        pattern = re.compile(rf"^\s*{re.escape(display_num)}\.", re.MULTILINE)
        replacement = f"\n{sutra_text}\n\n{display_num}."
        if pattern.search(text):
            text = pattern.sub(replacement, text, count=1)
    return text

# === MAIN WORKFLOW ==========================================================
if __name__ == "__main__":
    
    SUTRA_GROUND_TRUTH = load_sutra_database(SUTRA_DB_PATH)
    
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY":
        print("❌ CRITICAL ERROR: GOOGLE_API_KEY is not set."); exit()
    genai.configure(api_key=GOOGLE_API_KEY)

    try:
        with open(FINAL_OUTPUT_PATH, "w", encoding="utf-8") as f:
            start_page, end_page = PAGE_RANGE
            for page_num in range(start_page, end_page + 1):
                print(f"\nPROCESSING PAGE {page_num}...")
                try:
                    page_image = convert_from_path(PDF_PATH, poppler_path=POPPLER_PATH, dpi=300, first_page=page_num, last_page=page_num)[0]
                    
                    print("-> Cropping and OCRing...")
                    main_text_image = page_image.crop(CROP_ZONE)
                    processed_image = preprocess_image(main_text_image)
                    raw_text = pytesseract.image_to_string(processed_image, lang='eng+san', config='--psm 3')
                    
                    ai_cleaned_text = get_ai_cleanup(raw_text)
                    final_text = insert_ground_truth_sutras(ai_cleaned_text, SUTRA_GROUND_TRUTH)
                    
                    f.write(f"\n\n{'='*25} START OF PAGE {page_num} {'='*25}\n\n")
                    f.write(final_text)
                    print(f"✅ Successfully processed page {page_num}.")
                except Exception as e:
                    print(f"❌ An error occurred on page {page_num}: {e}")
                    f.write(f"\n\n--- ERROR ON PAGE {page_num}: {e} ---\n")
                    continue
                if page_num < end_page:
                    print("Waiting 2 seconds...")
                    time.sleep(2)
        print(f"\nALL PAGES PROCESSED. Output saved to {FINAL_OUTPUT_PATH}")
    except Exception as e:
        print(f"\n❌ A critical error occurred: {e}")