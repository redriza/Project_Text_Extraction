import os
import re
import csv
import numpy as np
import kenlm
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
import cv2
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from llama_cpp import Llama

# === CONFIGURATION ===
PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf3.pdf"
OUTPUT_CSV = r"C:\Users\divya\Desktop\project\nyaya_output_pages26to30.csv"
DATA_TXT_PATH = r"C:\Users\divya\Desktop\project\data.txt"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
LLAMA_PATH = r"C:\Users\divya\Desktop\models\mistral\mistral-7b-instruct-v0.1.Q4_K_M.gguf"
KENLM_MODEL_PATH = r"C:\Users\divya\Desktop\project\sanskrit.binary"  # ✅ Your KenLM binary path

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === LOAD MODELS ===
llm = Llama(model_path=LLAMA_PATH, n_ctx=2048, n_threads=6, n_gpu_layers=30, verbose=False)
lm = kenlm.Model(KENLM_MODEL_PATH)
classification_cache = {}

# === LANGUAGE CLASSIFICATION ===
def classify_sanskrit(line):
    if line in classification_cache:
        return classification_cache[line]
    prompt = f"Classify this text as Sanskrit or English: '{line}'\nAnswer:"
    output = llm(prompt=prompt, max_tokens=1, stop=["\n"])
    is_sanskrit = "sanskrit" in output["choices"][0]["text"].lower()
    classification_cache[line] = is_sanskrit
    return is_sanskrit

# === OCR CLEANUP ===
def is_likely_reference(line):
    return re.search(r'(Chapter|verse|Rigveda|Upanishad|Purana|Br[āa]hma[nm]a)', line, re.IGNORECASE)

def clean_text_block(lines):
    return ' '.join([line.strip() for line in lines if line.strip()])

# === TRANSLITERATION ===
def transliterate_line(line):
    iast = transliterate(line, sanscript.ITRANS, sanscript.IAST)
    devanagari = transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)
    return iast, devanagari

# === KENLM CORRECTION ===
def correct_with_kenlm(text):
    # Placeholder: currently just returns original — replace with actual candidate search + scoring
    return text.strip()

# === OCR IMAGE ENHANCEMENT ===
def preprocess_image(image_pil):
    img = np.array(image_pil.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)
    denoised = cv2.fastNlMeansDenoising(contrast, h=30)
    coords = np.column_stack(np.where(denoised < 255))
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    (h, w) = denoised.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    deskewed = cv2.warpAffine(denoised, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    thresh = cv2.adaptiveThreshold(deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    return Image.fromarray(thresh)

# === BLOCK EXTRACTOR ===
def extract_and_classify(page_image):
    processed = preprocess_image(page_image)
    raw_text = pytesseract.image_to_string(processed, lang='eng+san')
    lines = raw_text.splitlines()
    blocks = []
    buffer = []
    reference = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if is_likely_reference(line):
            if buffer:
                blocks.append((reference, buffer))
                buffer = []
            reference = line
        else:
            buffer.append(line)
    if buffer:
        blocks.append((reference, buffer))
    return blocks, raw_text

# === BOOK/CHAPTER DETECTION ===
def detect_chapter_metadata(text):
    book_match = re.search(r'BOOK\s+([IVXLC]+)', text, re.IGNORECASE)
    chapter_match = re.search(r'CHAPTER\s+([IVXLC]+)', text, re.IGNORECASE)

    def roman_to_int(roman):
        roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        result = 0
        prev = 0
        for char in reversed(roman.upper()):
            curr = roman_map.get(char, 0)
            if curr < prev:
                result -= curr
            else:
                result += curr
                prev = curr
        return str(result)

    book_no = roman_to_int(book_match.group(1)) if book_match else ""
    chapter_no = roman_to_int(chapter_match.group(1)) if chapter_match else ""
    title = f"Book {book_match.group(1)} — Chapter {chapter_match.group(1)}" if book_match and chapter_match else ""
    return book_no, chapter_no, title

# === CSV OUTPUT ===
def write_csv(rows, output_path):
    headers = ["book_no", "chapter_no", "chapter_title", "sutra_no",
               "sutra_devanagari", "sutra_roman", "sutra_translation", "sutra_commentary"]
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

# === MAIN WORKFLOW ===
def main():
    pages = list(range(26, 31))  # ✅ Pages 26–30
    output_rows = []

    with open(DATA_TXT_PATH, "w", encoding="utf-8") as f:
        f.write("")

    for page_num in pages:
        print(f"Processing page {page_num}...")
        try:
            image = convert_from_path(PDF_PATH, dpi=300, poppler_path=POPPLER_PATH,
                                      first_page=page_num, last_page=page_num)[0]
            blocks, raw_text = extract_and_classify(image)
            book_no, chapter_no, chapter_title = detect_chapter_metadata(raw_text)

            for ref, lines in blocks:
                classified_lines = [(line, classify_sanskrit(line)) for line in lines]
                sanskrit_lines = [line for line, is_san in classified_lines if is_san]
                english_lines = [line for line, is_san in classified_lines if not is_san]

                roman = devanagari = ""
                if sanskrit_lines:
                    sanskrit_block = clean_text_block(sanskrit_lines)
                    corrected = correct_with_kenlm(sanskrit_block)
                    roman, devanagari = transliterate_line(corrected)

                    with open(DATA_TXT_PATH, "a", encoding="utf-8") as f:
                        f.write(roman.strip() + "\n")

                row = {
                    "book_no": book_no,
                    "chapter_no": chapter_no,
                    "chapter_title": chapter_title,
                    "sutra_no": ref.strip() if ref else "",
                    "sutra_devanagari": devanagari.strip(),
                    "sutra_roman": roman.strip(),
                    "sutra_translation": clean_text_block(english_lines),
                    "sutra_commentary": ""
                }
                output_rows.append(row)

        except Exception as e:
            print(f"❌ Error on page {page_num}: {e}")
            continue

    write_csv(output_rows, OUTPUT_CSV)
    print(f"✅ Output written to {OUTPUT_CSV}")
    print(f"✅ KenLM training data saved to {DATA_TXT_PATH}")

if __name__ == "__main__":
    main()
