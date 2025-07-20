# Script 2: db_correction.py
import re
import csv
import os

# === CONFIGURATION =======================================================
# --- The intermediate file created by Script 1 ---
INPUT_AI_CLEANED_PATH = r"C:\Users\divya\Desktop\project\ai_cleaned_output.txt"

# --- REQUIRED: Path to your Devanagari Sūtra Database ---
SUTRA_DB_PATH = r"C:\Users\divya\Desktop\project\sutras_db_devanagari.csv"

# --- The final, perfected output file ---
FINAL_OUTPUT_PATH = r"C:\Users\divya\Desktop\project\nyaya_final_perfect_output.txt"

# === HELPER FUNCTIONS ====================================================

def load_sutra_database(db_path):
    """Loads the ground truth sūtras from your CSV database file."""
    print(f"-> Loading Sūtra database from: {db_path}")
    sutra_map = {}
    try:
        with open(db_path, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            for row in reader:
                if len(row) == 2:
                    sutra_map[row[0].strip()] = row[1].strip()
        print(f"✅ Successfully loaded {len(sutra_map)} sūtras.")
        return sutra_map
    except Exception as e:
        print(f"❌ CRITICAL ERROR loading database: {e}")
        exit()

def insert_ground_truth_sutras(text, sutra_map):
    """Programmatically inserts correct Devanagari sūtras into the text."""
    print("-> Inserting correct Devanagari sūtras...")
    for sutra_num, sutra_text in sorted(sutra_map.items(), key=lambda item: [int(i) for i in item[0].split('.')], reverse=True):
        display_num = sutra_num.split('.')[-1]
        pattern = re.compile(rf"^\s*{re.escape(display_num)}\.", re.MULTILINE)
        replacement = f"\n{sutra_text}\n\n{display_num}."
        if pattern.search(text):
            text = pattern.sub(replacement, text, count=1)
    return text

# === MAIN WORKFLOW ==========================================================
if __name__ == "__main__":
    print("--- STARTING FINAL DATABASE CORRECTION ---")
    
    try:
        # Load the sūtra database
        SUTRA_GROUND_TRUTH = load_sutra_database(SUTRA_DB_PATH)
        
        # Read the AI-cleaned text from the intermediate file
        print(f"-> Reading AI-cleaned text from: {INPUT_AI_CLEANED_PATH}")
        with open(INPUT_AI_CLEANED_PATH, "r", encoding="utf-8") as f:
            ai_cleaned_text = f.read()
            
        # Perform the final programmatic correction
        final_text = insert_ground_truth_sutras(ai_cleaned_text, SUTRA_GROUND_TRUTH)
        
        # Save the final, perfected text
        with open(FINAL_OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(final_text)
        
        print("\n" + "="*50)
        print(f"✅✅✅ SUCCESS! Final, perfected output saved to: ✅✅✅")
        print(FINAL_OUTPUT_PATH)
        print("="*50)
        
    except FileNotFoundError:
        print(f"❌ ERROR: The input file was not found at '{INPUT_AI_CLEANED_PATH}'.")
        print("Please make sure you have run Script 1 first.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")