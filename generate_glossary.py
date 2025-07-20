import os
import re
import csv
from pdf2image import convert_from_path
import pytesseract

# === CONFIGURATION =======================================================
PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf3.pdf"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- NEW: Define the specific page range to process ---
START_PAGE = 26
END_PAGE = 30

# The location where this script will save the generated glossary file
GLOSSARY_DB_PATH = r"C:\Users\divya\Desktop\project\glossary_db_26_to_30.csv"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === MAIN SCRIPT =========================================================
if __name__ == "__main__":
    print(f"Starting glossary generation for pages {START_PAGE}-{END_PAGE}...")
    try:
        # --- MODIFIED: Use the page range to load only the necessary pages ---
        images = convert_from_path(
            PDF_PATH,
            dpi=300,
            poppler_path=POPPLER_PATH,
            first_page=START_PAGE,
            last_page=END_PAGE
        )
        
        all_text = ""
        print(f"Found {len(images)} pages to process. Performing OCR...")
        
        for i, image in enumerate(images):
            page_num = START_PAGE + i
            print(f"  - Reading page {page_num}...")
            all_text += pytesseract.image_to_string(image, lang='eng+san') + "\n"
        
        print("\nOCR complete. Finding all unique parenthetical terms...")
        
        # This pattern finds all text inside parentheses
        found_terms = re.findall(r'\(([^)]+)\)', all_text)
        
        # Clean up the found terms to get a unique set
        cleaned_terms = set()
        for term in found_terms:
            clean_term = term.replace('-\n', '').replace('\n', ' ').replace('*', '').strip().lower()
            if ' ' not in clean_term and len(clean_term) > 1 and clean_term.isalpha():
                cleaned_terms.add(clean_term)
        
        unique_sorted_terms = sorted(list(cleaned_terms))
        
        # Save the unique glossary to a CSV file, ready for you to edit
        with open(GLOSSARY_DB_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Original", "Corrected IAST"]) # Write a header row
            for term in unique_sorted_terms:
                writer.writerow([term, ""]) # Write the term in the first column, leaving the second empty

        print("\n" + "="*50)
        print(f"✅✅✅ Success! Glossary file has been created at: ✅✅✅")
        print(GLOSSARY_DB_PATH)
        print("="*50)
        print("\n--> NEXT STEP: Open this CSV file and fill in the 'Corrected IAST' column.")

    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")