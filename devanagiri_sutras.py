# convert_db_to_devanagari.py

import csv
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# === CONFIGURATION =======================================================

# 1. The path to your CURRENT database file with Romanized/English text
INPUT_ROMAN_DB_PATH = r"C:\Users\divya\Desktop\project\sutras_db.csv"

# 2. The path where the NEW, corrected Devanagari database will be saved
OUTPUT_DEVANAGARI_DB_PATH = r"C:\Users\divya\Desktop\project\sutras_db_devanagari.csv"

# === MAIN SCRIPT =========================================================
if __name__ == "__main__":
    print(f"Starting conversion of: {INPUT_ROMAN_DB_PATH}")
    
    converted_sutras = []
    try:
        # Read the original file with Romanized text
        with open(INPUT_ROMAN_DB_PATH, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            for row in reader:
                if len(row) == 2:
                    sutra_number = row[0].strip()
                    roman_text = row[1].strip()
                    
                    # Convert the Roman text to Devanagari
                    # We assume the input is in IAST (standard for academic texts with diacritics)
                    devanagari_text = transliterate(roman_text, sanscript.IAST, sanscript.DEVANAGARI)
                    
                    converted_sutras.append([sutra_number, devanagari_text])

        if not converted_sutras:
            print("❌ No data found or read from the input file.")
            exit()
            
        print(f"Successfully transliterated {len(converted_sutras)} sūtras. Saving to new file...")

        # Write the new file with the Devanagari text
        with open(OUTPUT_DEVANAGARI_DB_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(converted_sutras)
            
        print("\n" + "="*50)
        print(f"✅✅✅ Success! New Devanagari database has been created at: ✅✅✅")
        print(OUTPUT_DEVANAGARI_DB_PATH)
        print("="*50)

    except FileNotFoundError:
        print(f"❌ ERROR: The input file was not found at '{INPUT_ROMAN_DB_PATH}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")