import os
import cv2
import re
import csv
import subprocess
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# === CONFIGURATION ===
PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf3.pdf"
OUTPUT_CSV = r"C:\Users\divya\Desktop\project\nyaya_output_llama.csv"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
MISTRAL_PATH = r"C:\Users\divya\Desktop\models\mistral\mistral-7b-instruct-v0.1.Q4_K_M.gguf"
LLAMA_CPP_BIN = r"C:\path\to\llama-run.exe"  # replace with actual path

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === FUNCTION TO USE MISTRAL VIA LLAMA-CPP FOR SANSKRIT DETECTION ===
def is_sanskrit(text):
    prompt = f"Is the following text Sanskrit? Reply with only 'yes' or 'no'.\n\n{text.strip()}"
    try:
        result = subprocess.run([
            LLAMA_CPP_BIN,
            MISTRAL_PATH,
            prompt,
            "--temp", "0.1",
            "--threads", "4",
            "--n", "1",
        ], capture_output=True, text=True, timeout=30)

        output = result.stdout.lower()
        return 'yes' in output and 'no' not in output
    except Exception as e:
        print(f"[ERROR] Llama inference failed: {e}")
        return False

# === OCR, CLASSIFICATION, AND TRANSLITERATION ===
def process_page(page_num):
    print(f"Processing page {page_num}...")
    image = convert_from_path(PDF_PATH, dpi=300, poppler_path=POPPLER_PATH, first_page=page_num, last_page=page_num)[0]

    # Image preprocessing
    img_cv = np.array(image)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    blur = cv2.bilateralFilter(gray, 9, 75, 75)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    img_pil = Image.fromarray(thresh)

    ocr_text = pytesseract.image_to_string(img_pil, lang="eng+san")
    lines = ocr_text.splitlines()

    output_lines = []
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue

        if is_sanskrit(clean_line):
            # Convert Roman to IAST (diacritics) → LLM should handle this ideally, mocked for now
            iast = clean_line  # In real case, use LLM API to convert
            devanagari = transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)
            output_lines.append(devanagari)
        else:
            output_lines.append(clean_line)

    return "\n".join(output_lines)

# === MAIN ===
def main():
    pages = [10, 11]  # Add more as needed
    rows = []
    index = 1

    for pg in pages:
        combined_text = process_page(pg)
        row = {
            "book_no": 0,
            "chapter_no": 0,
            "chapter_title": "Introduction",
            "sutra_no": f"0.0.{index}",
            "sutra_devanagari": "",
            "sutra_roman": "",
            "sutra_translation": combined_text,
            "sutra_commentary": ""
        }
        rows.append(row)
        index += 1

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ CSV written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()