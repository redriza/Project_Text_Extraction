import os
import re
import pytesseract
from pdf2image import convert_from_path
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Set up paths
pdf_path = r"C:\Users\divya\Desktop\New folder\pdf2.pdf"
output_folder = r"C:\Users\divya\Desktop\project"
poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
mistral_model_path = r"C:\Users\divya\Desktop\models\mistral\mistral-7b-instruct-v0.1.Q4_K_M.gguf"

# --- CLEANING FUNCTIONS ---
def clean_ocr_text(text):
    text = text.replace("I$", "IS").replace("$", "S").replace("0f", "of").replace("0", "o")
    text = re.sub(r"(?<=\w)\)(?=\w)", "", text)
    return text

def remove_ascii_borders(text):
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if re.fullmatch(r"[|\u00a6\xac\-=~!\.\[\]{}()<>\\/]{4,}", stripped):
            continue
        if re.match(r"^[|!\u00ac:;\-=~]{2,}", stripped) and len(re.findall(r"[a-zA-Z]", stripped)) < 10:
            continue
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)

# --- STEP 1: OCR from PDF pages ---
def extract_text_from_pdf(pdf_path, poppler_path):
    images = convert_from_path(pdf_path, 500, poppler_path=poppler_path)
    full_text = ""
    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image, lang="eng+san")
        text = clean_ocr_text(text)
        text = remove_ascii_borders(text)
        full_text += text + "\n"
    return full_text.strip()

# --- STEP 2: IAST transliteration ---
def convert_to_diacritics(text):
    return transliterate(text, sanscript.HK, sanscript.IAST)

# --- STEP 3: Devanagari conversion ---
def convert_to_devanagari(text):
    return transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)

# --- STEP 4: Classify and Translate Sanskrit words only ---
def load_mistral_model():
    from llama_cpp import Llama
    return Llama(model_path=mistral_model_path, n_ctx=2048)

def is_sanskrit_line(llm, line):
    prompt = f"Classify this line as Sanskrit or English: '{line.strip()}'"
    output = llm(prompt, max_tokens=5, stop=["\n"])
    return "Sanskrit" in output["choices"][0]["text"]

def final_replace_sanskrit_words(llm, original_text):
    output_lines = []
    for line in original_text.splitlines():
        if line.strip() == "":
            output_lines.append("")
            continue
        if is_sanskrit_line(llm, line):
            iast = transliterate(line, sanscript.HK, sanscript.IAST)
            dev = transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)
            output_lines.append(dev)
        else:
            output_lines.append(line)
    return "\n".join(output_lines)

# --- MAIN PIPELINE ---
def main():
    # Step 1: OCR
    raw_text = extract_text_from_pdf(pdf_path, poppler_path)
    with open(os.path.join(output_folder, "01_raw_text.txt"), "w", encoding="utf-8") as f:
        f.write(raw_text)

    # Step 2: IAST
    iast_text = convert_to_diacritics(raw_text)
    with open(os.path.join(output_folder, "02_diacritic_text.txt"), "w", encoding="utf-8") as f:
        f.write(iast_text)

    # Step 3: Devanagari
    dev_text = convert_to_devanagari(iast_text)
    with open(os.path.join(output_folder, "03_devanagari_text.txt"), "w", encoding="utf-8") as f:
        f.write(dev_text)

    # Step 4: Final replacement
    llm = load_mistral_model()
    final_output = final_replace_sanskrit_words(llm, raw_text)
    with open(os.path.join(output_folder, "04_final_output.txt"), "w", encoding="utf-8") as f:
        f.write(final_output)

if __name__ == "__main__":
    main()
