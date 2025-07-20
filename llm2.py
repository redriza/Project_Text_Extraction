import os
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from llama_cpp import Llama
from indic_transliteration.sanscript import transliterate, SLP1, IAST, DEVANAGARI
# from langdetect import detect, DetectorFactory # Uncomment if using language detection
# DetectorFactory.seed = 0 # For reproducible results with langdetect

# === CONFIGURATION ===
pdf_path = r"C:\Users\divya\Desktop\New Folder\pdf2.pdf" # Make sure this points to your PDF
poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
model_path = r"C:\Users\divya\Desktop\models\mistral\mistral-7b-instruct-v0.1.Q4_K_M.gguf"
temp_image_dir = "temp_images"
output_file = "sanskrit_verses_and_english.txt" # Changed output file name
sanskrit_only_file = "sanskrit_verses_only.txt" # New file for Sanskrit only
english_only_file = "english_text_only.txt" # New file for English only

os.makedirs(temp_image_dir, exist_ok=True)

# === STEP 1: Convert PDF to Images (First 5 Pages) ===
print("📄 Converting PDF to images...")
images = convert_from_path(
    pdf_path,
    dpi=300, # High DPI is good for OCR accuracy
    poppler_path=poppler_path,
    first_page=1,
    last_page=5 # Adjust as needed
)
image_paths = []
for i, image in enumerate(images):
    image_path = os.path.join(temp_image_dir, f"page_{i+1}.png")
    image.save(image_path, "PNG")
    image_paths.append(image_path)
print(f"✅ Saved {len(image_paths)} pages as images.")

# === STEP 2: OCR to Extract Text (Line by Line) ===
print("🔍 Performing OCR on each page and segmenting lines...")
# We'll get detailed OCR output with bounding boxes to help with line segmentation
# If you don't need bounding boxes, image_to_string is fine, but you'll rely on newline chars
ocr_raw_lines = []
for img_path in image_paths:
    # Use output_type=pytesseract.Output.DICT for more structured output if needed
    # For now, let's stick to string and then split, assuming newlines are somewhat reliable
    text = pytesseract.image_to_string(Image.open(img_path), lang="eng+san")
    ocr_raw_lines.extend([line.strip() for line in text.split("\n") if line.strip()]) # Get non-empty lines
print("✅ OCR complete and lines extracted.")

# === STEP 3: Load Mistral (GGUF) ===
print("🧠 Loading Mistral 7B GGUF model...")
llm = Llama(
    model_path=model_path,
    n_ctx=2048, # Context window size
    n_threads=8, # Number of threads
    # Consider adding verbose=False if you want less output from Llama
)
print("✅ Mistral model loaded.")

# === STEP 4: Function to Classify Line (Sanskrit Verse or Not) ===
# This function will also try to normalize the Sanskrit if identified
def process_text_chunk(chunk_text):
    # Sanitize chunk_text for prompt
    cleaned_chunk = chunk_text.replace("'", "").replace("\"", "")[:500] # Limit size and remove problematic chars

    # Prompt to classify and normalize Sanskrit
    prompt_classify_normalize = (
        "You are an expert in Sanskrit and English. Analyze the following text segment. "
        "Your task is to determine if it is a genuine Sanskrit verse (or part of one) "
        "or if it is primarily an English sentence/explanation. "
        "If it is a Sanskrit verse, normalize it into standard IAST transliteration, "
        "correcting any minor OCR errors. If it is primarily English, return 'ENGLISH'. "
        "If it is neither (e.g., garbage, headings, or very mixed), return 'OTHER'.\n\n"
        f"Text Segment: '{cleaned_chunk}'\n\n"
        "Output (IAST, ENGLISH, or OTHER):"
    )

    response = llm(
        prompt_classify_normalize,
        max_tokens=256, # Sufficient for IAST conversion or 'ENGLISH'/'OTHER'
        stop=["\n\n", "Output:"], # Stop sequences
        temperature=0.1 # Keep it less creative, more factual
    )
    llm_output = response["choices"][0]["text"].strip()

    # Post-process LLM output
    if llm_output.lower().startswith("english"):
        return "ENGLISH", chunk_text
    elif llm_output.lower().startswith("other"):
        return "OTHER", chunk_text
    else:
        # Assume it's IAST if not 'ENGLISH' or 'OTHER'
        # The LLM might output some preamble before the IAST, so try to extract the IAST directly
        # A more robust parser for LLM output might be needed for complex cases
        if "IAST:" in llm_output: # if LLM is verbose and writes "IAST: "
            return "SANSKRIT", llm_output.split("IAST:")[1].strip()
        elif "Output:" in llm_output: # if LLM is verbose and writes "Output: "
            return "SANSKRIT", llm_output.split("Output:")[1].strip()
        else: # direct IAST
            return "SANSKRIT", llm_output

# === STEP 5: Process Chunks, Transliterate & Save ===
print("🔠 Analyzing chunks with Mistral and processing content...")

processed_results = [] # To store (type, original_text, processed_text/IAST)

for i, line in enumerate(ocr_raw_lines):
    print(f"Processing line {i+1}/{len(ocr_raw_lines)}: '{line[:80]}...'") # Show progress
    line = line.strip()
    if not line:
        continue # Skip empty lines

    # Basic filtering for common non-content lines
    if line.startswith("--- Page") or line.lower().startswith("contents of chapter") or line.lower().startswith("inquiry into brahman"):
        processed_results.append(("OTHER", line, line)) # Mark as other, not to be transliterated
        continue

    # Use the LLM to classify and potentially normalize
    result_type, processed_text = process_text_chunk(line)
    processed_results.append((result_type, line, processed_text))
    print(f"  -> Classified as: {result_type}")


# Now, write to the output files based on classification
with open(output_file, "w", encoding="utf-8") as f_all, \
     open(sanskrit_only_file, "w", encoding="utf-8") as f_sanskrit, \
     open(english_only_file, "w", encoding="utf-8") as f_english:

    f_all.write("=== Full Processed Output ===\n\n")
    f_sanskrit.write("=== Sanskrit Verses (IAST & Devanagari) ===\n\n")
    f_english.write("=== English Sentences ===\n\n")

    for result_type, original_line, processed_content in processed_results:
        if result_type == "SANSKRIT":
            # Attempt transliteration from IAST to Devanagari
            try:
                # Assuming 'processed_content' is now clean IAST from the LLM
                devanagari = transliterate(processed_content, IAST, DEVANAGARI)
                f_all.write(f"SANSKRIT VERSE:\nOriginal OCR: {original_line}\nIAST: {processed_content}\nDevanagari: {devanagari}\n\n")
                f_sanskrit.write(f"{processed_content}\n{devanagari}\n\n")
                print(f"✅ Sanskrit - IAST: {processed_content}\n   Devanagari: {devanagari}")
            except Exception as e:
                print(f"⚠️ Transliteration Error for '{processed_content}': {e}")
                f_all.write(f"TRANSLITERATION_ERROR (Sanskrit): Original OCR: {original_line}\nLLM Output: {processed_content}\nError: {e}\n\n")
                f_sanskrit.write(f"ERROR: Could not transliterate: {processed_content} (Original: {original_line})\n\n")
        elif result_type == "ENGLISH":
            f_all.write(f"ENGLISH TEXT:\n{original_line}\n\n")
            f_english.write(f"{original_line}\n\n")
            print(f"➡️ English: {original_line}")
        else: # "OTHER" or unclassified
            f_all.write(f"OTHER/UNCLASSIFIED:\n{original_line}\n\n")
            print(f"❓ Other: {original_line}")

print(f"\n📄 Done. Output saved to: {output_file}, {sanskrit_only_file}, and {english_only_file}")

