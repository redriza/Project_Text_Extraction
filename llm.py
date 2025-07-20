import os
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from llama_cpp import Llama
from indic_transliteration.sanscript import transliterate, SLP1, IAST, DEVANAGARI

# === CONFIGURATION ===
pdf_path = r"C:\Users\divya\Desktop\New Folder\pdf2.pdf"
poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
model_path = r"C:\Users\divya\Desktop\models\mistral\mistral-7b-instruct-v0.1.Q4_K_M.gguf"
temp_image_dir = "temp_images"
output_file = "sanskrit_verses.txt"

os.makedirs(temp_image_dir, exist_ok=True)

# === STEP 1: Convert PDF to Images (First 5 Pages) ===
print("📄 Converting PDF to images...")
images = convert_from_path(
    pdf_path,
    dpi=300,
    poppler_path=poppler_path,
    first_page=1,
    last_page=5
)
image_paths = []
for i, image in enumerate(images):
    image_path = os.path.join(temp_image_dir, f"page_{i+1}.png")
    image.save(image_path, "PNG")
    image_paths.append(image_path)
print(f"✅ Saved {len(image_paths)} pages as images.")

# === STEP 2: OCR to Extract Text ===
print("🔍 Performing OCR on each page...")
ocr_texts = []
for img_path in image_paths:
    text = pytesseract.image_to_string(Image.open(img_path), lang="eng+san")
    ocr_texts.append(text)
full_text = "\n".join(ocr_texts)
print("✅ OCR complete.")

# === STEP 3: Load Mistral (GGUF) ===
print("🧠 Loading Mistral 7B GGUF model...")
llm = Llama(
    model_path=model_path,
    n_ctx=2048,
    n_threads=8
)

# === STEP 4: Function to Classify Line ===
def is_sanskrit_verse(line):
    prompt = (
        "You are a Sanskrit scholar. Determine whether the following line is a Sanskrit verse. "
        "Answer only Yes or No.\n"
        f"Line: '{line}'\nAnswer:"
    )
    response = llm(prompt, max_tokens=10, stop=["\n"])
    return response["choices"][0]["text"].strip()

# === STEP 5: Transliterate & Save Sanskrit Verses ===
print("🔠 Analyzing lines with Mistral and transliterating Sanskrit verses...")
with open(output_file, "w", encoding="utf-8") as f:
    lines = full_text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        result = is_sanskrit_verse(line)
        if result.lower() == "yes":
            try:
                # First convert to IAST (assume OCR is in SLP1 or near-SLP1 form)
                # Here, we assume the OCR is close to IAST already. If it's SLP1 or Devanagari, convert appropriately.
                iast = line
                dev = transliterate(iast, IAST, DEVANAGARI)
                f.write(f"{iast}\n{dev}\n\n")
                print(f"✅ {iast}\n   {dev}")
            except Exception as e:
                print(f"⚠️ Could not transliterate line: {line} — {e}")

print(f"📄 Done. Sanskrit verses saved to: {output_file}")
