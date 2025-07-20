import cv2
import pytesseract
import re

# File paths
image_path = r"C:\Users\divya\Desktop\project\pg1.png"
raw_output_path = r"C:\Users\divya\Desktop\project\ocr_output_raw.txt"
cleaned_output_path = r"C:\Users\divya\Desktop\project\ocr_output_cleaned.txt"

# Optional: Set Tesseract path if not in system PATH
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Step 1: Read and preprocess the image
image = cv2.imread(image_path)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
thresh = cv2.adaptiveThreshold(
    gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10
)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
cleaned_img = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

# Step 2: OCR
text = pytesseract.image_to_string(cleaned_img)

# Step 3: Save raw output
with open(raw_output_path, "w", encoding="utf-8") as f:
    f.write(text)

# Step 4: Define cleaning function
def clean_ocr_text(text):
    # Replace commonly misread characters
    text = text.replace("I$", "IS")
    text = text.replace("$", "S")
    text = text.replace("0f", "of")
    text = text.replace("0", "o")

    # Fix misread brackets or layout splits
    text = text.replace("Le\nvedante-sutra", "[Vedanta-sutra")

    # Remove stray hyphenated lines
    text = re.sub(r"-\s*sutras,?", "", text)

    # Fix characters in words like prayo)itah → prayojitah
    text = re.sub(r"(?<=\w)\)(?=\w)", "", text)

    return text

# Step 5: Clean the text
cleaned_text = clean_ocr_text(text)

# Step 6: Save cleaned output
with open(cleaned_output_path, "w", encoding="utf-8") as f:
    f.write(cleaned_text)

print("✅ OCR completed and outputs saved.")
print(f"Raw text: {raw_output_path}")
print(f"Cleaned text: {cleaned_output_path}")
