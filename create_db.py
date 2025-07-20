import re
import csv

# === CONFIGURATION =======================================================
# The raw text file you created by copying from the website
RAW_TEXT_INPUT_PATH = r"C:\Users\divya\Desktop\raw_sutras.txt"

# The final, perfectly formatted CSV database file this script will create
SUTRA_DB_OUTPUT_PATH = r"C:\Users\divya\Desktop\project\sutras_db.csv"

# === MAIN SCRIPT =========================================================
if __name__ == "__main__":
    print(f"Reading raw text from: {RAW_TEXT_INPUT_PATH}")
    
    try:
        with open(RAW_TEXT_INPUT_PATH, "r", encoding="utf-8") as f:
            raw_content = f.read()

        # This regular expression finds all lines that start with a sūtra number
        # like "1.1.1:" followed by the Sanskrit text.
        # It captures the number in group 1 and the text in group 2.
        pattern = re.compile(r"(\d+\.\d+\.\d+):\s+(.*)")
        
        matches = pattern.findall(raw_content)
        
        if not matches:
            print("❌ ERROR: No sūtras found. Please make sure the raw text file contains lines like '1.1.1: प्रमाण...'.")
            exit()
            
        print(f"Found {len(matches)} sūtras. Creating CSV database...")

        # Write the found sūtras into the CSV file
        with open(SUTRA_DB_OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for match in matches:
                sutra_number = match[0]
                sutra_text = match[1].strip()
                writer.writerow([sutra_number, sutra_text])
                
        print("\n" + "="*50)
        print(f"✅✅✅ Success! Sūtra database has been automatically created at: ✅✅✅")
        print(SUTRA_DB_OUTPUT_PATH)
        print("="*50)

    except FileNotFoundError:
        print(f"❌ ERROR: The raw text file was not found at '{RAW_TEXT_INPUT_PATH}'.")
        print("Please make sure the file exists and the path is correct.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")