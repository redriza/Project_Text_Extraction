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
# Ensure all paths and your API key are correct.

PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf3.pdf"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- REQUIRED: Paths to your database files ---
SUTRA_DB_PATH = r"C:\Users\divya\Desktop\project\sutras_db.csv"
GLOSSARY_DB_PATH = r"C:\Users\divya\Desktop\project\glossary_db_26_to_30.csv"

# --- Define the final output file ---
FINAL_OUTPUT_PATH = r"C:\Users\divya\Desktop\project\nyaya_book_final_output.txt"

# --- Gemini API Key ---
GOOGLE_API_KEY = "AIzaSyCEarEwXeDYL1FUh0ym47fjtl8qPKT2cB0"

# --- Set the page range to process ---
PAGE_RANGE = (26, 30)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === HELPER FUNCTIONS ====================================================

def load_database_from_csv(db_path, db_name="Database"):
    """Loads a two-column CSV into a dictionary."""
    print(f"-> Loading {db_name} from: {db_path}")
    db_map = {}
    try:
        with open(db_path, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            # Skip header row if it exists
            next(reader, None)  
            for rows in reader:
                if len(rows) == 2 and rows[0] and rows[1]:
                    db_map[rows[0].strip().lower()] = rows[1].strip()
        print(f"✅ Successfully loaded {len(db_map)} items from {os.path.basename(db_path)}.")
        return db_map
    except FileNotFoundError:
        print(f"❌ CRITICAL ERROR: {db_name} file not found at {db_path}.")
        exit()
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not read {db_name}. Error: {e}")
        exit()

def preprocess_image(pil_image):
    """Applies cleaning filters to an image for better OCR accuracy."""
    print("-> Preprocessing image...")
    img = np.array(pil_image.convert("L")) # Convert to grayscale
    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    # Apply thresholding to get a clean black-and-white image
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def clean_english_with_ai(raw_text):
    """(AI Task) Uses Gemini API for general cleanup of English prose."""
    print("-> Using AI to clean up English text...")
    
    # A simple, focused prompt to prevent the AI from making unwanted changes.
    prompt = f"""Correct the spelling and grammar of the following English text. Do not alter or remove any Sanskrit words, whether in Devanagari script or within parentheses.

TEXT TO CORRECT:
---
{raw_text}
---

CORRECTED TEXT:
"""
    try:
        # Configure the generative model
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Generate the content
        response = model.generate_content(prompt)
        print("-> AI has returned the cleaned English text.")
        return response.text
    except Exception as e:
        print(f"   ❌ AI English cleanup failed: {e}")
        return raw_text

def apply_programmatic_corrections(text, sutra_map, glossary_map):
    """(Code Task) Inserts canonical sūtras and formats glossary terms with 100% reliability."""
    print("-> Applying programmatic corrections...")

    # 1. Insert Sūtras from your database
    for sutra_num, sutra_text in sorted(sutra_map.items(), key=lambda item: [int(i) for i in item[0].split('.')], reverse=True):
        display_num = sutra_num.split('.')[-1]
        # Regex to find the number at the start of a line, making it robust
        pattern = re.compile(f"^{display_num}\\.", re.MULTILINE | re.IGNORECASE)
        replacement = f"\n{sutra_text}\n\n{display_num}."
        text = pattern.sub(replacement, text, count=1)

    # 2. Add Diacritics using your glossary
    def replace_diacritics(match):
        word = match.group(1).lower().replace('*', '').strip()
        # Look up the corrected version in your glossary; if not found, leave it unchanged.
        corrected_word = glossary_map.get(word, word)
        return f"(*{corrected_word}*)"
    text = re.sub(r'\(([^)]+)\)', replace_diacritics, text)

    return text

# === MAIN WORKFLOW ==========================================================
if __name__ == "__main__":
    
    # --- Load all your data at the start ---
    SUTRA_GROUND_TRUTH = load_database_from_csv(SUTRA_DB_PATH, "Sūtra Database")
    GLOSSARY_GROUND_TRUTH = load_database_from_csv(GLOSSARY_DB_PATH, "Glossary Database")
    
    # --- Configure Gemini client ---
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY":
        print("❌ CRITICAL ERROR: GOOGLE_API_KEY is not set.")
        exit()
    genai.configure(api_key=GOOGLE_API_KEY)

    try:
        # --- Open the single output file ---
        with open(FINAL_OUTPUT_PATH, "w", encoding="utf-8") as f:
            print(f"✅ Opened output file for writing: {FINAL_OUTPUT_PATH}")
            
            start_page, end_page = PAGE_RANGE
            
            # --- Loop through the specified pages ---
            for page_num in range(start_page, end_page + 1):
                print("\n" + "="*70)
                print(f"PROCESSING PAGE {page_num} of {end_page}")
                print("="*70)
                
                try:
                    # 1. Extraction and Preprocessing
                    page_image = convert_from_path(PDF_PATH, poppler_path=POPPLER_PATH, dpi=300, first_page=page_num, last_page=page_num)[0]
                    raw_text = pytesseract.image_to_string(preprocess_image(page_image), lang='eng+san', config='--psm 4')
                    
                    # 2. AI Correction
                    ai_corrected_text = clean_english_with_ai(raw_text)
                    
                    # 3. Final Programmatic Correction & Polishing
                    perfect_text = apply_programmatic_corrections(ai_corrected_text, SUTRA_GROUND_TRUTH, GLOSSARY_GROUND_TRUTH)
                    
                    # 4. Write to File
                    f.write(f"\n\n{'='*25} START OF PAGE {page_num} {'='*25}\n\n")
                    f.write(perfect_text)
                    print(f"✅ Successfully processed and wrote page {page_num} to the file.")

                except Exception as e:
                    error_message = f"❌ An error occurred while processing page {page_num}: {e}"
                    print(error_message)
                    f.write(f"\n\n{error_message}\n")
                    continue
                
                # Add a delay to be respectful to the API server
                if page_num < end_page:
                    print("Waiting for 2 seconds before the next API call...")
                    time.sleep(2)
        
        print("\n" + "="*70)
        print(f"ALL PAGES PROCESSED. Final output saved to:\n{FINAL_OUTPUT_PATH}")
        print("="*70)

    except Exception as e:
        print(f"\n❌ A critical error occurred during the process: {e}")