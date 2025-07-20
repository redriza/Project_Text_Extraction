import os
import re
import csv
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
import pytesseract
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# === CONFIGURATION ===
# Ensure these paths are correct for your system before running.
PDF_PATH = r"C:\Users\divya\Desktop\New folder\pdf2.pdf"
OUTPUT_CSV = r"C:\Users\divya\Desktop\project\vedanta_output_final.csv"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Set the Tesseract command path
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# === DATA CLEANING & CONVERSION ===
def clean_text(text):
    """Cleans raw OCR text by removing artifacts and fixing common errors."""
    # Fix common OCR character mistakes
    text = text.replace('I$', 'IS').replace('$', 'S').replace('0f', 'of').replace('0', 'o')
    text = text.replace('1o|', '10.').replace('o|', '0.')

    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        # Remove artifacts from the OCR process
        line = re.sub(r'\[source: \d+\]', '', line)
        line = line.replace('\\', '')
        line = re.sub(r'-----.*-----', '', line)
        line = re.sub(r'L=+', '', line)
        
        if line.strip() and not line.strip().startswith('--- PAGE'):
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r'\(\s*\)', '', text)
    return text.strip()

def convert_to_iast(text):
    """Transliterates text from ITRANS scheme to IAST."""
    if not text: return ""
    try:
        return transliterate(text, sanscript.ITRANS, sanscript.IAST)
    except Exception:
        return text

def convert_to_devanagari(text):
    """Transliterates text from ITRANS scheme to Devanagari."""
    if not text: return ""
    try:
        return transliterate(text, sanscript.ITRANS, sanscript.DEVANAGARI)
    except Exception:
        return text


# === CORE PARSING LOGIC ===
def extract_structured_data(full_text):
    """
    Parses the full text of the document to extract structured verse data.
    """
    all_rows = []
    
    vs_blocks = re.split(r'(\(Vs\.\s*\d+\.\d+\.\d+\.?\))', full_text)
    
    current_chapter = ""
    current_subchapter = ""

    for i in range(1, len(vs_blocks), 2):
        sutra_no_text = vs_blocks[i]
        content_block = vs_blocks[i+1]
        
        sutra_no_match = re.search(r'(\d+\.\d+\.\d+)', sutra_no_text)
        if not sutra_no_match:
            continue
        sutra_no = sutra_no_match.group(1)

        chapter_match = re.search(r'CHAPTER\s+\w+', content_block, re.IGNORECASE)
        if chapter_match:
            current_chapter = chapter_match.group(0).strip()
            current_subchapter = ""

        adhikarana_match = re.search(r'Adhikarana \d+:(.*)', content_block, re.IGNORECASE)
        if adhikarana_match:
            current_subchapter = adhikarana_match.group(1).strip()
            
        sb_verse_pattern = r'(?m)^(\d{1,2}\.\d{1,2}\.\d{1,2}(?:-\d{1,2})?.*)$'
        sb_blocks = re.split(sb_verse_pattern, content_block)
        
        if len(sb_blocks) < 2:
            continue

        for j in range(1, len(sb_blocks), 2):
            sb_verse_header = sb_blocks[j].strip()
            sb_content = sb_blocks[j+1]

            sb_verse_no_match = re.match(r'(\d{1,2}\.\d{1,2}\.\d{1,2}(?:-\d{1,2})?)', sb_verse_header)
            sb_verse_no = sb_verse_no_match.group(1) if sb_verse_no_match else "N/A"
            
            roman_from_header = re.sub(sb_verse_pattern, '', sb_verse_header, 1).strip()

            synonyms_match = re.search(r'([^\n]+--[^\n]+.*)', sb_content, re.DOTALL)
            translation_match = re.search(r'TRANSLATION\n(.*?)(?=\d{1,2}\.\d{1,2}\.\d{1,2}|$)', sb_content, re.DOTALL | re.IGNORECASE)

            end_of_roman = len(sb_content)
            if synonyms_match:
                end_of_roman = synonyms_match.start()
            elif translation_match:
                end_of_roman = translation_match.start()
            
            full_roman_text = roman_from_header + " " + sb_content[:end_of_roman].strip()

            synonyms_text = synonyms_match.group(1).strip() if synonyms_match else ""
            translation_text = translation_match.group(1).strip() if translation_match else ""
            
            row = {
                "Chapter Title": current_chapter.title(),
                "Sub-Chapter Title": current_subchapter,
                "sutra_no": sutra_no,
                "sb_verse_no": sb_verse_no,
                "sb_verse_roman": convert_to_iast(' '.join(full_roman_text.split())),
                "sb_verse_devanagari": convert_to_devanagari(' '.join(full_roman_text.split())),
                "sb_verse_synonyms": ' '.join(synonyms_text.split()),
                "sb_verse_translation": ' '.join(translation_text.split())
            }
            all_rows.append(row)

    return all_rows


# === CSV WRITING ===
def write_csv(rows, out_path):
    """Writes the extracted data to a CSV file."""
    headers = [
        "Chapter Title", "Sub-Chapter Title", "sutra_no", "sb_verse_no",
        "sb_verse_roman", "sb_verse_devanagari",
        "sb_verse_synonyms", "sb_verse_translation"
    ]
    seen = set()
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        
        for row in rows:
            key = (row["sutra_no"], row["sb_verse_no"], row["sb_verse_roman"])
            if key in seen:
                continue
            seen.add(key)
            writer.writerow(row)


# === MAIN EXECUTION BLOCK (WITH PAGE-BY-PAGE PROGRESS) ===
def main():
    """Main function to orchestrate the PDF processing."""
    
    # First, get the total number of pages to use in our progress counter.
    try:
        print("Getting PDF page count...")
        info = pdfinfo_from_path(PDF_PATH, poppler_path=POPPLER_PATH)
        total_pages = info["Pages"]
        print(f"PDF has {total_pages} pages. Starting conversion and OCR.")
    except Exception as e:
        print(f"FATAL ERROR: Could not get PDF info. Check POPPLER_PATH and PDF_PATH. Details: {e}")
        return

    full_text = ""
    # This loop processes ONE page at a time, showing you progress for each.
    for page_num in range(1, total_pages + 1):
        print(f"--- Processing page {page_num}/{total_pages} ---")
        try:
            # 1. Convert just the current page to an image. This is fast.
            image = convert_from_path(
                PDF_PATH,
                dpi=300,
                poppler_path=POPPLER_PATH,
                first_page=page_num,
                last_page=page_num
            )

            # 2. Perform OCR on that single image. This is the slow part.
            print(f"  - Performing OCR...")
            text = pytesseract.image_to_string(image[0], lang="eng+san")
            full_text += text + "\n"
            print(f"  - Page {page_num} completed.")

        except Exception as e:
            print(f"  - !!! ERROR processing page {page_num}: {e}")
            continue # If a page fails, we'll log the error and continue.

    # Now, process the aggregated text all at once for accuracy.
    print("\n--- All pages processed. Now cleaning and parsing the full text. ---")
    cleaned_text = clean_text(full_text)
    
    print("--- Parsing structured data... ---")
    all_blocks = extract_structured_data(cleaned_text)
    
    print(f"--- Extracted {len(all_blocks)} total entries. Writing to CSV... ---")
    write_csv(all_blocks, OUTPUT_CSV)
    
    print("\nProcessing complete. Output saved to:", OUTPUT_CSV)


if __name__ == "__main__":
    main()
