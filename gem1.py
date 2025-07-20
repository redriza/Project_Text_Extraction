import os
from pdf2image import convert_from_path
from PIL import Image # Still used for saving images to temp_image_dir
import pytesseract
import cv2 # For image processing before OCR
import re # For cleaning functions
from llama_cpp import Llama
from indic_transliteration.sanscript import transliterate, IAST, DEVANAGARI, ITRANS # Keep ITRANS just in case, though LLM should output IAST

# === CONFIGURATION ===
pdf_path = r"C:\Users\divya\Desktop\New folder\pdf2.pdf" # Make sure this points to your PDF
poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe" # New: Tesseract executable path
model_path = r"C:\Users\divya\Desktop\models\mistral\mistral-7b-instruct-v0.1.Q4_K_M.gguf"
temp_image_dir = "temp_images"
output_file = "sanskrit_verses_and_english.txt"
sanskrit_only_file = "sanskrit_verses_only.txt"
english_only_file = "english_text_only.txt"

os.makedirs(temp_image_dir, exist_ok=True)

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

# === Cleaning Functions (Copied from new OCR code) ===

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
        # Adjusted this regex to be slightly more robust for mixed characters
        if re.match(r"^[|!¬:;\-_=~]*[|!¬:;\-_=~]+", stripped) and len(re.findall(r"[a-zA-Z0-9]", stripped)) < 10:
            continue
        
        # This part is meant to be selective and keep content-rich lines.
        # It's a heuristic, and might need tuning for your specific document.
        # Original logic:
        # tokens = stripped.split()
        # long_words = [w for w in tokens if len(w) > 3]
        # short_words = [w for w in tokens if len(w) <= 3]
        # if len(set(tokens)) < len(tokens) * 0.5: # Checks for low word uniqueness
        #    continue

        # More generalized check for actual text
        if not stripped: # Skip empty lines after stripping
            continue
        # Basic check to see if it looks like a sentence/word rather than just symbols
        if len(re.findall(r'[a-zA-Z0-9]', stripped)) < 3 and not any(c.isalpha() for c in stripped):
            continue

        # Keywords and structure checks for keeping lines (can be fine-tuned)
        if (
            stripped.isupper() and len(stripped.split()) >= 4 # All uppercase sentences/headings
        ) or (
            any(keyword in stripped.lower() for keyword in [
                "adhikarana", "sastra", "vedanta", "sri", "krsna", "truth", "chapter", "page"
            ]) # Important keywords
        ) or (
            len(stripped.split()) >= 3 and any(c.isalpha() for c in stripped) # At least 3 words and contains letters
        ):
            cleaned_lines.append(stripped)
        # Add a fallback to include lines that are not caught by the above but seem like actual text
        elif len(stripped) > 15 and len(re.findall(r'[a-zA-Z]', stripped)) / len(stripped) > 0.5:
            cleaned_lines.append(stripped)
        
    return "\n".join(cleaned_lines)


# === STEP 1: Convert PDF to Images ===
print("📄 Converting PDF to images with DPI 500...")
# Using dpi=500 as in the new OCR code for better quality
images = convert_from_path(
    pdf_path,
    dpi=500, # Increased DPI for better OCR
    poppler_path=poppler_path,
    first_page=1,
    last_page=5 # Adjust as needed
)
image_paths = []
for i, image in enumerate(images):
    image_path = os.path.join(temp_image_dir, f"page_{i+1}.png")
    image.save(image_path, "PNG") # Save as PNG for potential better quality with OpenCV
    image_paths.append(image_path)
print(f"✅ Saved {len(image_paths)} pages as images.")

# === STEP 2: OCR to Extract Text (Line by Line with Image Preprocessing) ===
print("🔍 Performing OCR on each page with image preprocessing and segmentation...")
ocr_raw_lines_processed = [] # This will store the cleaned OCR lines

for i, img_path in enumerate(image_paths):
    print(f"  Processing image for OCR: {os.path.basename(img_path)}")
    img = cv2.imread(img_path)
    if img is None:
        print(f"  Failed to read image: {os.path.basename(img_path)}. Skipping.")
        continue

    # Image preprocessing as in the new OCR code
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (1, 1), 0) # Apply blur, kernel (1,1) is minimal blur

    # Perform OCR with PSM 1 (automatic page segmentation with OSD)
    # The new OCR code used config="--psm 1".
    # `lang="eng+san"` is crucial for recognizing both English and Sanskrit.
    raw_ocr_text = pytesseract.image_to_string(blur, lang="eng+san", config="--psm 1")

    # Apply cleaning functions
    cleaned_text = clean_ocr_text(raw_ocr_text)
    filtered_text = remove_ascii_borders(cleaned_text) # This might aggressively filter non-Sanskrit/English

    # Extend with lines from the filtered text
    ocr_raw_lines_processed.extend([line.strip() for line in filtered_text.split("\n") if line.strip()])

print("✅ OCR complete and lines extracted/cleaned.")
print(f"Total cleaned OCR lines for LLM processing: {len(ocr_raw_lines_processed)}")


# === STEP 3: Load Mistral (GGUF) ===
print("🧠 Loading Mistral 7B GGUF model...")
llm = Llama(
    model_path=model_path,
    n_ctx=2048,
    n_threads=8,
    verbose=False # Suppress verbose output from Llama
)
print("✅ Mistral model loaded.")

# === STEP 4: Function to Classify and Normalize Text Chunk ===
def process_text_chunk(chunk_text):
    # Sanitize chunk_text for prompt, important for potentially malformed OCR input
    # Limit size to prevent context window overflow for very long lines
    cleaned_chunk = chunk_text.replace("'", "`").replace("\"", "`")[:1000] # Use backticks for safety

    # Prompt to classify and normalize Sanskrit
    prompt_classify_normalize = (
        "You are an expert in Sanskrit and English. Analyze the following text segment. "
        "Your task is to determine if it is a genuine Sanskrit verse (or part of one) "
        "or if it is primarily an English sentence/explanation. "
        "If it is a Sanskrit verse, normalize it into standard IAST transliteration, "
        "correcting any minor OCR errors, ensuring correct diacritics. "
        "If it is primarily English, return 'ENGLISH:'. " # Added colon for easier parsing
        "If it is neither (e.g., garbage, headings, or very mixed), return 'OTHER:'. " # Added colon
        "Do not add any other text before the output.\n\n"
        f"Text Segment: '{cleaned_chunk}'\n\n"
        "Output:" # Expecting "IAST: <transliteration>", "ENGLISH:", or "OTHER:"
    )

    try:
        response = llm(
            prompt_classify_normalize,
            max_tokens=512, # Increased max_tokens to ensure full IAST generation
            stop=["\n", "Output:"], # Stop on newline or "Output:" if LLM repeats it
            temperature=0.1 # Keep it less creative, more factual
        )
        llm_raw_output = response["choices"][0]["text"].strip()
        
        # More robust parsing of LLM output
        llm_output_lower = llm_raw_output.lower()

        if llm_output_lower.startswith("english:"):
            return "ENGLISH", chunk_text # Return original chunk for English
        elif llm_output_lower.startswith("other:"):
            return "OTHER", chunk_text # Return original chunk for Other
        else:
            # Assume it's Sanskrit and try to extract IAST.
            # LLM might just output the IAST directly if instructed.
            # If it starts with "IAST:", remove it.
            if llm_output_lower.startswith("iast:"):
                processed_iast = llm_raw_output[len("iast:"):].strip()
                if processed_iast:
                    return "SANSKRIT", processed_iast
                else: # LLM said IAST but provided empty text
                    return "OTHER", chunk_text 
            elif len(llm_raw_output) > 5 and any(c.isalpha() for c in llm_raw_output): # Basic check for valid Sanskrit-like output
                return "SANSKRIT", llm_raw_output
            else: # If it's not clear IAST, English or Other
                return "OTHER", chunk_text
    except Exception as e:
        print(f"Error during LLM processing of chunk '{cleaned_chunk[:50]}...': {e}")
        return "ERROR", chunk_text # Indicate an error occurred

# === STEP 5: Process Chunks, Transliterate & Save ===
print("🔠 Analyzing lines with Mistral and transliterating Sanskrit verses...")

processed_results = [] # To store (type, original_text, processed_text/IAST)

for i, line in enumerate(ocr_raw_lines_processed):
    if i % 10 == 0: # Print progress every 10 lines
        print(f"Processing chunk {i+1}/{len(ocr_raw_lines_processed)}: '{line[:80]}...'")

    line = line.strip()
    if not line:
        continue # Skip empty lines

    # Use the LLM to classify and potentially normalize
    result_type, processed_content = process_text_chunk(line)
    processed_results.append((result_type, line, processed_content))


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
            except Exception as e:
                print(f"⚠️ Transliteration Error for '{processed_content}': {e}")
                f_all.write(f"TRANSLITERATION_ERROR (Sanskrit): Original OCR: {original_line}\nLLM Output (IAST): {processed_content}\nError: {e}\n\n")
                f_sanskrit.write(f"ERROR: Could not transliterate: {processed_content} (Original: {original_line})\n\n")
        elif result_type == "ENGLISH":
            f_all.write(f"ENGLISH TEXT:\n{original_line}\n\n")
            f_english.write(f"{original_line}\n\n")
        elif result_type == "OTHER":
            f_all.write(f"OTHER/UNCLASSIFIED TEXT:\n{original_line}\n\n")
        elif result_type == "ERROR":
            f_all.write(f"PROCESSING ERROR for line:\n{original_line}\n\n")


print(f"\n📄 Done. Output saved to: {output_file}, {sanskrit_only_file}, and {english_only_file}")

# Optional: Clean up temporary images
# import shutil
# shutil.rmtree(temp_image_dir)
# print(f"Cleaned up {temp_image_dir}")