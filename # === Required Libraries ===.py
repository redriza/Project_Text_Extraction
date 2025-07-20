# === Required Libraries ===
import os
import re
import cv2
import torch
import pytesseract
from pdf2image import convert_from_path
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# === CONFIGURATION ===
pdf_path = r"C:\Users\divya\Desktop\project\pdf2.pdf"
poppler_path = r"C:/Program Files/poppler-24.08.0/Library/bin"
temp_image_dir = "temp_images"
os.makedirs(temp_image_dir, exist_ok=True)

# === LOAD LLM CLASSIFIER ===
print("Loading classification model...")
model_name = "naver/splade-cocondenser-ensembledistil"  # replace with Sanskrit/English classifier
classifier = pipeline("text-classification", model=model_name, tokenizer=model_name, device=0 if torch.cuda.is_available() else -1)

# === CLEANING UTILS ===
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
        if re.fullmatch(r"[|\u00A6\u00AC\-_=~!\.\[\]{}()<>\\/]{4,}", stripped):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

# === LLM FILTERED TRANSLITERATION ===
def transliterate_if_sanskrit(line):
    pred = classifier(line[:250])[0]  # Use first 250 chars
    if pred['label'].lower() == "sanskrit" and pred['score'] > 0.75:
        iast = transliterate(line, sanscript.ITRANS, sanscript.IAST)
        dev = transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)
        return f"→ {iast}\n→ {dev}"
    return line

# === OCR + PROCESSING LOOP ===
all_output = ""
print("Converting PDF to images and processing...")
images = convert_from_path(pdf_path, dpi=500, poppler_path=poppler_path, first_page=1, last_page=2)

for i, image in enumerate(images):
    image_path = os.path.join(temp_image_dir, f"page{i+1}.jpg")
    image.save(image_path, "JPEG")
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (1, 1), 0)
    ocr_text = pytesseract.image_to_string(blur, config="--psm 1")
    text = clean_ocr_text(ocr_text)
    text = remove_ascii_borders(text)

    lines = text.splitlines()
    processed = [transliterate_if_sanskrit(line.strip()) for line in lines if line.strip()]
    all_output += f"\n--- Page {i+1} ---\n" + "\n".join(processed) + "\n"

# === SAVE FINAL OUTPUT ===
with open("output_llm.txt", "w", encoding="utf-8") as f:
    f.write(all_output)

print("LLM-based transliteration complete. See output_llm.txt")
