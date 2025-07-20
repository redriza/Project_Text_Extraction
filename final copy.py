from pdf2image import convert_from_path
import cv2
import pytesseract
import re
import os

# === Configuration ===
pdf_path = r"C:\Users\divya\Desktop\New folder\pdf2.pdf"
poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
output_text_path = r"C:\Users\divya\Desktop\project\ocr_output_cleaned.txt"
temp_image_dir = r"C:\Users\divya\Desktop\project\temp_images"

# Create temp image directory if it doesn't exist
os.makedirs(temp_image_dir, exist_ok=True)

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

# Convert first 5 pages to images
images = convert_from_path(
    pdf_path, dpi=500, poppler_path=poppler_path, first_page=1, last_page=5
)

# === Cleaning Functions ===

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

        # Remove lines made entirely of decorative characters
        if re.fullmatch(r"[|¦¬\-_=~!.\[\]{}()<>\\/]{4,}", stripped):
            continue

        # Remove symbol-started lines with few letters
        if re.match(r"^[|!¬:;\-_=~]{2,}", stripped) and len(re.findall(r"[a-zA-Z]", stripped)) < 10:
            continue

        # Token-based gibberish filtering
        tokens = stripped.split()
        real_words = [w for w in tokens if len(w) >= 4 and re.match(r"[a-zA-Z]{3,}", w)]

        # Remove if too few real words among many tokens
        if len(real_words) < 2 and len(tokens) > 4:
            continue

        # Remove if majority tokens are short gibberish
        short_words = [w for w in tokens if len(w) <= 3]
        if len(tokens) > 5 and len(short_words) / len(tokens) > 0.7:
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)

# === Main OCR Loop ===
all_cleaned_text = ""

for i, image in enumerate(images):
    image_path = os.path.join(temp_image_dir, f"page{i+1}.jpg")
    image.save(image_path, "JPEG")

    # Read and convert to grayscale
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Light denoising
    blur = cv2.GaussianBlur(gray, (1, 1), 0)

    # OCR with layout-preserving config
    ocr_text = pytesseract.image_to_string(blur, config="--psm 1")

    # Clean text
    text = clean_ocr_text(ocr_text)
    text = remove_ascii_borders(text)

    all_cleaned_text += f"\n--- Page {i+1} ---\n{text.strip()}\n"

# Save final cleaned output
with open(output_text_path, "w", encoding="utf-8") as f:
    f.write(all_cleaned_text)

print("OCR completed and cleaned text saved to:")
print(output_text_path)
