import os
import re
import cv2
import pytesseract
from pdf2image import convert_from_path
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# === CONFIGURATION ===
pdf_path = r'C:\Users\divya\Desktop\project\pdf2.pdf'

poppler_path = r"C:/Program Files/poppler-24.08.0/Library/bin"
temp_image_dir = "temp_images"
os.makedirs(temp_image_dir, exist_ok=True)

# === CONVERT PDF TO IMAGES (FIRST 2 PAGES ONLY) ===
print("\U0001F4C4 Converting PDF to images with DPI 500...")
images = convert_from_path(pdf_path, dpi=500, poppler_path=poppler_path, first_page=1, last_page=2)

# === CLEAN OCR TEXT ===
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
        if re.fullmatch(r"[|¦¬\-_=~!\.\[\]{}()<>\\/]{4,}", stripped):
            continue
        if re.match(r"^[|!¬:;\-_=~]{2,}", stripped) and len(re.findall(r"[a-zA-Z]", stripped)) < 10:
            continue
        tokens = stripped.split()
        real_words = [w for w in tokens if len(w) >= 4 and re.match(r"[a-zA-Z]{3,}", w)]
        if len(real_words) < 2 and len(tokens) > 4:
            continue
        short_words = [w for w in tokens if len(w) <= 3]
        if len(tokens) > 5 and len(short_words) / len(tokens) > 0.7:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

# === SANITIZE AND TRANSLITERATE ===
def transliterate_gloss(line):
    segments = re.split(r"\s*--\s*", line)
    output = []
    for seg in segments:
        words = seg.strip().split()
        trans_words = []
        for w in words:
            if re.match(r"^[a-zA-Zāīūṛṅñṭḍṇśṣḥḷṃ\-]+$", w):
                try:
                    dev = transliterate(transliterate(w, sanscript.ITRANS, sanscript.IAST), sanscript.IAST, sanscript.DEVANAGARI)
                    trans_words.append(dev)
                except:
                    trans_words.append(w)
            else:
                trans_words.append(w)
        output.append(" ".join(trans_words))
    return " — ".join(output)

# === MAIN OCR LOOP ===
all_cleaned_text = ""

for i, image in enumerate(images):
    image_path = os.path.join(temp_image_dir, f"page{i+1}.jpg")
    image.save(image_path, "JPEG")
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (1, 1), 0)
    ocr_text = pytesseract.image_to_string(blur, config="--psm 1")
    text = clean_ocr_text(ocr_text)
    text = remove_ascii_borders(text)
    processed_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        processed_lines.append(transliterate_gloss(line))
    all_cleaned_text += f"\n--- Page {i+1} ---\n" + "\n".join(processed_lines) + "\n"

# === OUTPUT RESULT ===
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(all_cleaned_text)

print("\u2705 Done. Output written to output.txt")