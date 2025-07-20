from pdf2image import convert_from_path
import cv2
import pytesseract
import re
import os
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# === Configuration ===
pdf_path = r"C:\Users\divya\Desktop\New folder\pdf2.pdf"
poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
output_text_diacritics = r"C:\Users\divya\Desktop\project\ocr_output_diacritics.txt"
output_text_sanskrit = r"C:\Users\divya\Desktop\project\ocr_output_sanskrit.txt"
temp_image_dir = r"C:\Users\divya\Desktop\project\temp_images"

# Ensure temp image directory exists
os.makedirs(temp_image_dir, exist_ok=True)

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

# Convert first 5 pages to images
images = convert_from_path(
    pdf_path, dpi=500, poppler_path=poppler_path, first_page=1, last_page=5
)

# === Cleaning Functions ===

def clean_ocr_text(text):
    text = text.replace("I$", "IS").replace("$", "S")
    text = text.replace("0f", "of").replace("0", "o")
    text = re.sub(r"(?<=\w)\)(?=\w)", "", text)
    return text

def remove_ascii_borders(text):
    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        if re.fullmatch(r"[|¦¬\-_=~!.\[\]{}()<>\\/]{4,}", stripped):
            continue
        if re.match(r"^[|!¬:;\-_=~]{2,}", stripped) and len(re.findall(r"[a-zA-Z]", stripped)) < 10:
            continue
        tokens = stripped.split()
        long_words = [w for w in tokens if len(w) > 3]
        short_words = [w for w in tokens if len(w) <= 3]
        if len(set(tokens)) < len(tokens) * 0.5:
            continue
        if (
            stripped.isupper() and len(long_words) >= 4
        ) or (
            any(keyword in stripped.lower() for keyword in [
                "adhikarana", "sastra", "vedanta", "sri", "krsna", "truth"
            ])
        ) or (
            len(long_words) >= 3 and len(tokens) >= 4
        ):
            cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines)

def convert_to_diacritics(text):
    return transliterate(text, sanscript.ITRANS, sanscript.IAST)

def convert_to_devanagari(iast_text):
    return transliterate(iast_text, sanscript.IAST, sanscript.DEVANAGARI)

# === Main OCR Loop ===
output_diacritics = ""
output_sanskrit = ""

print("Starting OCR and transliteration...")

for i, image in enumerate(images):
    print(f"Processing page {i+1}...")

    image_path = os.path.join(temp_image_dir, f"page{i+1}.jpg")
    image.save(image_path, "JPEG")

    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to read image: page {i+1}")
        continue

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (1, 1), 0)

    # OCR
    ocr_text = pytesseract.image_to_string(blur, config="--psm 1")

    # Clean and convert
    text = clean_ocr_text(ocr_text)
    text = remove_ascii_borders(text)
    text_diacritics = convert_to_diacritics(text)
    text_devanagari = convert_to_devanagari(text_diacritics)

    if text.strip():
        output_diacritics += f"\n--- Page {i+1} ---\n{text_diacritics.strip()}\n"
        output_sanskrit += f"\n--- Page {i+1} ---\n{text_devanagari.strip()}\n"
    else:
        print(f"Page {i+1} produced no valid cleaned text.")

# Save final results to two separate files
if output_diacritics.strip():
    with open(output_text_diacritics, "w", encoding="utf-8") as f:
        f.write(output_diacritics)
    print(f"Roman + Diacritics text saved to:\n{output_text_diacritics}")

if output_sanskrit.strip():
    with open(output_text_sanskrit, "w", encoding="utf-8") as f:
        f.write(output_sanskrit)
    print(f"Devanagari Sanskrit text saved to:\n{output_text_sanskrit}")
