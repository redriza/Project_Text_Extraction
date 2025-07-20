import os
import re
import csv
import unicodedata
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# === CONFIG ===
PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf2.pdf"
OUTPUT_CSV = r"C:\Users\divya\Desktop\project\vedanta_output.csv"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === CLEANING HELPERS ===
def clean_text(text):
    text = text.replace('I$', 'IS').replace('$', 'S').replace('0f', 'of').replace('0', 'o')
    text = re.sub(r'\(\s*\)', '', text)
    return text

def remove_ascii_borders(text):
    return "\n".join([line for line in text.splitlines() if line.count('|') < 5 and len(line.strip()) > 2])

def normalize_unicode(text):
    return unicodedata.normalize("NFC", text)

def fix_iast_ocr_typos(text):
    # Fix common OCR-to-IAST diacritic issues
    return (
        text.replace("ġ", "g")
            .replace("ḻ", "l")
            .replace("ṭ", "t")
            .replace("ṭh", "th")
            .replace("ṭr", "tr")
            .replace("ḍ", "d")
            .replace("ṛ", "r")
            .replace("ṝ", "r̄")
            .replace("ṇ", "n")
            .replace("ṅ", "n")
            .replace("ś", "sh")
            .replace("ṣ", "sh")
            .replace("ḷ", "l")
            .replace("ḥ", "h")
            .replace("ṃ", "m")
            .replace("ṉ", "n")
            .replace("Ḥ", "H")
            .replace("Ḍ", "D")
            .replace("Ṛ", "R")
            .replace("Ṭ", "T")
            .replace("Ḷ", "L")
            .replace("k͟h", "kh")
            .replace("ṡ", "s")
    )

def convert_to_iast(text):
    iast = transliterate(text, sanscript.ITRANS, sanscript.IAST)
    return normalize_unicode(fix_iast_ocr_typos(iast))

def convert_to_devanagari(text):
    dev = transliterate(text, sanscript.ITRANS, sanscript.DEVANAGARI)
    return normalize_unicode(dev)

# === MAIN PARSER ===
def extract_verses(text):
    blocks = []
    current_chapter = ""
    current_subchapter = ""
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line.isupper() and len(line.split()) > 3:
            current_subchapter = line
            i += 1
            continue

        if re.match(r"^\d\.\d+\.\d+", line):
            sutra_no = line.strip()
            i += 1
            roman_lines = []
            synonym_lines = []
            translation_lines = []
            sb_ref = sutra_no

            while i < len(lines) and '--' not in lines[i] and not re.match(r'^\d\.\d+\.\d+', lines[i]):
                roman_lines.append(lines[i].strip())
                i += 1

            while i < len(lines) and ('--' in lines[i] or re.search(r"--", lines[i])):
                synonym_lines.append(lines[i].strip())
                i += 1

            while i < len(lines):
                if re.match(r'^\d\.\d+\.\d+', lines[i]):
                    break
                if lines[i].strip().upper().startswith("TRANSLATION"):
                    i += 1
                    continue
                if lines[i].strip():
                    translation_lines.append(lines[i].strip())
                i += 1

            roman = " ".join(roman_lines).strip()
            synonyms = " ".join(synonym_lines).strip().strip("| ")
            translation = " ".join(translation_lines).strip().strip("| ")
            if not translation:
                translation = "[TODO: Insert translation]"

            # Special fix for known OCR issue
            if 'jijnasa' in roman.lower() and re.match(r"1\.2\.1(?!\d)", sutra_no):
                sutra_no = '1.2.10'

            sutra_parts = re.findall(r"\d\.\d+\.\d+", sutra_no)
            for sutra_id in sutra_parts:
                block = {
                    "Chapter Title": current_chapter,
                    "Sub-Chapter Title": current_subchapter,
                    "sutra_no": sutra_id,
                    "sutra_translation": convert_to_iast(roman),
                    "sb_verse_no": sutra_id,
                    "sb_verse_roman": convert_to_iast(roman),
                    "sb_verse_devanagari": convert_to_devanagari(roman),
                    "sb_verse_synonyms": convert_to_iast(synonyms),
                    "sb_verse_translation": convert_to_iast(translation)
                }
                blocks.append(block)
        else:
            i += 1

    return blocks

# === CSV WRITER ===
def write_csv(rows, out_path):
    headers = [
        "Chapter Title", "Sub-Chapter Title", "sutra_no", "sutra_translation",
        "sb_verse_no", "sb_verse_roman", "sb_verse_devanagari",
        "sb_verse_synonyms", "sb_verse_translation"
    ]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        last_subchapter = ""
        for row in rows:
            if not row["Sub-Chapter Title"] and last_subchapter:
                row["Sub-Chapter Title"] = last_subchapter
            else:
                last_subchapter = row["Sub-Chapter Title"]
            writer.writerow(row)

# === MAIN ===
def main():
    print("Converting first 2 pages of PDF to images...")
    images = convert_from_path(PDF_PATH, dpi=300, first_page=1, last_page=2, poppler_path=POPPLER_PATH)

    all_blocks = []
    for page_num, image in enumerate(images, start=1):
        print(f"Processing Page {page_num}...")
        raw = pytesseract.image_to_string(image, lang="eng+san")
        cleaned = clean_text(remove_ascii_borders(raw))
        blocks = extract_verses(cleaned)
        print(f"  Extracted {len(blocks)} sutra blocks.")
        all_blocks.extend(blocks)

    print("Writing to CSV...")
    write_csv(all_blocks, OUTPUT_CSV)
    print(f"Done. Output written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
