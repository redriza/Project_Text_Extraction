import os
import cv2
import pytesseract
import re
from pdf2image import convert_from_path
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# === Configuration ===
pdf_path = r"C:\Users\divya\Desktop\New folder\pdf2.pdf"
poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
output_text_diacritics = r"C:\Users\divya\Desktop\project\ocr_output_diacritics.txt"
output_text_sanskrit = r"C:\Users\divya\Desktop\project\ocr_output_sanskrit.txt"
output_verses_path = r"C:\Users\divya\Desktop\project\ocr_output_verses.txt"
temp_image_dir = r"C:\Users\divya\Desktop\project\temp_images"

os.makedirs(temp_image_dir, exist_ok=True)
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

# === Dictionary ===
roman_to_iast_dict = {
    "Sri": "śrī", "Krsna": "kṛṣṇa", "Krishna": "kṛṣṇa", "atma": "ātmā", "jnana": "jñāna",
    "sastra": "śāstra", "guru": "guruḥ", "bhagavan": "bhagavān", "paramatma": "paramātmā",
    "purusa": "puruṣa", "karma": "karman", "yoga": "yogaḥ", "veda": "veda", "vedanta": "vedānta",
    "brahman": "brahman", "prana": "prāṇa", "jyotis": "jyotis", "akasa": "ākāśa"
}

# === Text Cleaning ===
def clean_ocr_text(text):
    text = text.replace("I$", "IS").replace("$", "S").replace("0f", "of").replace("0", "o")
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
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)

# === Detect Verse ===
def is_sanskrit_verse(line):
    line = line.strip()
    if not line:
        return False
    if re.search(r"[.?!]$", line):
        return False
    words = line.split()
    matches = sum(1 for w in words if w.lower() in roman_to_iast_dict)
    if matches >= 2:
        return True
    if line == line.upper() and len(words) > 3:
        return True
    return False

# === Per-word Transliteration ===
def transliterate_inline_words(line, mapping):
    def convert_word(word):
        clean = re.sub(r'[^\w]', '', word)
        lower = clean.lower()
        replacement = mapping.get(clean, mapping.get(lower, None))
        return word.replace(clean, replacement) if replacement else word

    return " ".join(convert_word(w) for w in line.split())

def convert_to_devanagari(iast_line):
    return transliterate(iast_line, sanscript.IAST, sanscript.DEVANAGARI)

# === Processing ===
images = convert_from_path(pdf_path, dpi=500, poppler_path=poppler_path, first_page=1, last_page=5)

output_diacritics = ""
output_sanskrit = ""
output_side_by_side = ""

for i, image in enumerate(images):
    print(f"Processing page {i+1}...")
    image_path = os.path.join(temp_image_dir, f"page{i+1}.jpg")
    image.save(image_path, "JPEG")

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (1, 1), 0)
    ocr_text = pytesseract.image_to_string(blur, config="--psm 1")

    text = clean_ocr_text(ocr_text)
    text = remove_ascii_borders(text)
    lines = text.splitlines()

    page_diacritics = []
    page_sanskrit = []
    side_by_side = []

    for line in lines:
        diacritic_line = transliterate_inline_words(line, roman_to_iast_dict)
        dev_line = transliterate_inline_words(diacritic_line, {
            v: convert_to_devanagari(v) for v in roman_to_iast_dict.values()
        })

        page_diacritics.append(diacritic_line)
        page_sanskrit.append(dev_line)

        if is_sanskrit_verse(line):
            side_by_side.append(f"IAST:     {diacritic_line}\nSanskrit: {dev_line}\n")

    output_diacritics += f"\n--- Page {i+1} ---\n" + "\n".join(page_diacritics) + "\n"
    output_sanskrit += f"\n--- Page {i+1} ---\n" + "\n".join(page_sanskrit) + "\n"
    output_side_by_side += f"\n--- Page {i+1} ---\n" + "\n".join(side_by_side) + "\n"

# === Save Files ===
with open(output_text_diacritics, "w", encoding="utf-8") as f:
    f.write(output_diacritics)

with open(output_text_sanskrit, "w", encoding="utf-8") as f:
    f.write(output_sanskrit)

with open(output_verses_path, "w", encoding="utf-8") as f:
    f.write(output_side_by_side)

print("✅ Done: All files saved with inline Sanskrit + side-by-side verses.")
