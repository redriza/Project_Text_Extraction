import os
import csv
import re
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract

# ------------------ Config ------------------
PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf2.pdf"
OUTPUT_CSV = r"C:\Users\divya\Desktop\project\vedanta_output.csv"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# ------------------ Utility Functions ------------------

def clean_text(text):
    text = text.replace('|', ' | ').replace('।', ' । ')
    text = re.sub(r'[^a-zA-Z0-9\s\|.,;:!?\'"-–—()\[\]{}<>\n\r]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def remove_ascii_borders(text):
    lines = text.splitlines()
    filtered = []
    for line in lines:
        if len(line.strip()) < 3:
            continue
        if re.match(r'^[\s\W_]*$', line):
            continue
        filtered.append(line)
    return '\n'.join(filtered)

def postprocess_translation(text):
    corrections = {
        'khrsna': 'kṛṣṇa',
        'knovledge': 'knowledge',
        'detacment': 'detachment',
        'vhat': 'what',
        'vhic': 'which',
        'vorld': 'world',
        'vorks': 'works',
        'ekshactly': 'exactly',
        'āll': 'all',
        'tOdO:': '[TODO]',
        'īnsert': 'insert',
        'smrtah': 'smṛtaḥ',
        'svrat': 'svarāṭ',
        'abhijnah': 'abhijñaḥ',
        'adhikavaye': 'ādi-kavaye',
    }
    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
    return text.strip()

def detect_chapter_title(text_lines):
    for line in text_lines:
        if line.strip().isupper() and ("CHAPTER" in line or "ADHYAYA" in line):
            return line.strip().title()
    return ""

def generate_translation(verse_roman):
    return f"[Auto-translated] Meaning of: {verse_roman[:40]}..."

# ------------------ Main Pipeline ------------------

def extract_text_from_pdf(pdf_path):
    images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
    full_text = []
    for img in images:
        text = pytesseract.image_to_string(img, lang='eng+san')
        text = remove_ascii_borders(text)
        full_text.append(text)
    return '\n'.join(full_text)

def parse_sections(raw_text):
    sections = []
    lines = raw_text.split('\n')
    current_chapter = detect_chapter_title(lines)
    subchapter = ""
    current = {}
    
    for line in lines:
        line = line.strip()
        if not line: continue

        # Chapter detection
        if detect_chapter_title([line]):
            current_chapter = line.title()
            continue

        # Sub-Chapter detection (simple assumption)
        if line.istitle() and len(line.split()) < 10:
            subchapter = line

        if re.match(r'^\d+\.\d+\.\d+', line):
            if current: sections.append(current)
            current = {
                "Chapter Title": current_chapter,
                "Sub-Chapter Title": subchapter,
                "sutra_no": line,
                "sutra_translation": "",
                "sb_verse_no": line,
                "sb_verse_roman": "",
                "sb_verse_devanagari": "",
                "sb_verse_synonyms": "",
                "sb_verse_translation": ""
            }
        elif "॥" in line or re.search(r'\b(vasudeve|dharmah|om)\b', line.lower()):
            current["sb_verse_roman"] += " " + line
        elif re.search(r'[\u0900-\u097F]', line):  # Devanagari
            current["sb_verse_devanagari"] += " " + line
        elif '--' in line:  # Synonyms
            current["sb_verse_synonyms"] += " " + line
        elif 'translation' in line.lower() or 'meaning' in line.lower() or 'rendering' in line.lower():
            current["sb_verse_translation"] += " " + line
        else:
            current["sutra_translation"] += " " + line

    if current:
        sections.append(current)

    return sections

def clean_and_export_csv(sections, output_csv):
    fields = ["Chapter Title","Sub-Chapter Title","sutra_no","sutra_translation",
              "sb_verse_no","sb_verse_roman","sb_verse_devanagari",
              "sb_verse_synonyms","sb_verse_translation"]
    
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for sec in sections:
            sec["sutra_translation"] = postprocess_translation(sec["sutra_translation"])
            sec["sb_verse_roman"] = clean_text(sec["sb_verse_roman"])
            sec["sb_verse_devanagari"] = clean_text(sec["sb_verse_devanagari"])
            sec["sb_verse_synonyms"] = postprocess_translation(sec["sb_verse_synonyms"])
            sec["sb_verse_translation"] = postprocess_translation(sec["sb_verse_translation"])
            
            if not sec["sb_verse_translation"] or "[TODO]" in sec["sb_verse_translation"]:
                sec["sb_verse_translation"] = generate_translation(sec["sb_verse_roman"])
            
            writer.writerow(sec)

# ------------------ Entry ------------------

if __name__ == "__main__":
    print("[1/3] Extracting OCR from PDF...")
    text = extract_text_from_pdf(PDF_PATH)

    print("[2/3] Parsing verse sections...")
    sections = parse_sections(text)

    print("[3/3] Writing structured CSV...")
    clean_and_export_csv(sections, OUTPUT_CSV)

    print(f"✅ Done! Output saved to {OUTPUT_CSV}")
