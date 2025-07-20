import os
import re
import cv2
import pytesseract
from concurrent.futures import ThreadPoolExecutor
from pdf2image import convert_from_path
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from transformers import pipeline
from functools import lru_cache
import configparser

# === CONFIGURATION HANDLER ===
class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.defaults = {
            'PATHS': {
                'pdf_path': r'C:\Users\divya\Desktop\project\pdf2.pdf',
                'poppler_path': r'C:\Program Files\poppler-24.08.0\Library\bin',
                'temp_image_dir': 'temp_images',
                'output_file': 'sanskrit_analysis.md'
            },
            'PROCESSING': {
                'start_page': '1',
                'end_page': '3',
                'dpi': '500',
                'classifier_threshold': '0.85'
            },
            'OCR': {
                'tesseract_config': '--oem 3 --psm 6',
                'language': 'san+eng'
            }
        }

    def load(self):
        """Load configuration from file or use defaults"""
        if os.path.exists('config.ini'):
            self.config.read('config.ini')
        else:
            self.config.read_dict(self.defaults)
            self._create_config_file()
        return self

    def _create_config_file(self):
        """Create default config file if missing"""
        with open('config.ini', 'w') as f:
            self.config.write(f)

    def get_path(self, key):
        return os.path.normpath(self.config.get('PATHS', key))

    def get_processing(self, key):
        return self.config.get('PROCESSING', key)

    def get_ocr_config(self):
        return self.config.get('OCR', 'tesseract_config')

# === TEXT PROCESSING ===
class TextCleaner:
    @staticmethod
    def clean_ocr_text(text):
        """Multi-stage OCR text cleaning"""
        if not text:
            return ""

        replacements = {
            r'I[\$\|¦]': 'I',
            r'\b0([a-z])': r'o\1',
            r'[¦¬\\]': '',
            r'(?<=\w)[^\w\s](?=\w)': ''
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)

        text = re.sub(r'[^\w\s.,;:!?\'-]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def remove_ascii_art(text):
        lines = [line for line in text.splitlines()
                 if not re.match(r'^[\-=\\+*\\/]{4,}$', line.strip())]
        return '\n'.join(lines)

# === SANSKRIT PROCESSOR ===
class SanskritProcessor:
    def __init__(self):
        self.glossary = {
            'sri': 'auspicious, holy',
            'guru': 'teacher',
            'namaḥ': 'obeisance',
            'shloka': 'verse',
            'bhagavad': 'of the Lord',
        }
        self.classifier = None

    def initialize_classifier(self):
        if not self.classifier:
            self.classifier = pipeline(
                "text-classification",
                model="buddhist-nlp/sanskrit-classification",
                device=-1
            )

    @lru_cache(maxsize=1000)
    def is_sanskrit(self, text):
        self.initialize_classifier()
        try:
            result = self.classifier(text[:512])
            return result[0]['label'] == 'sanskrit' and result[0]['score'] > float(Config().get_processing('classifier_threshold'))
        except Exception as e:
            print(f"Classification error: {e}")
            return False

    @lru_cache(maxsize=2000)
    def translate_term(self, term):
        return self.glossary.get(term.lower(), None)

    def process_line(self, text):
        if not self.is_sanskrit(text):
            return {'type': 'other', 'content': text}

        iast = transliterate(text, sanscript.ITRANS, sanscript.IAST)
        devanagari = transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)

        words = re.findall(r'[\w\']+', text)
        analyzed_words = []
        for word in words:
            translation = self.translate_term(word)
            analyzed_words.append(
                f"{word} ({translation})" if translation else word
            )

        return {
            'type': 'sanskrit',
            'original': text,
            'words': ' '.join(analyzed_words),
            'iast': iast,
            'devanagari': devanagari
        }

# === OCR PROCESSOR ===
class OCRProcessor:
    @staticmethod
    def preprocess_image(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    @staticmethod
    def extract_text(image_path, config):
        try:
            img = cv2.imread(image_path)
            processed = OCRProcessor.preprocess_image(img)
            custom_config = Config().get_ocr_config()
            return pytesseract.image_to_string(
                processed,
                config=custom_config,
                lang=config.get('OCR', 'language')
            )
        except Exception as e:
            print(f"OCR Error on {image_path}: {e}")
            return ""

# === MAIN PROCESS ===
def main():
    config = Config().load()
    sanskrit_processor = SanskritProcessor()

    # Ensure Poppler path is valid
    poppler_dir = config.get_path('poppler_path')
    if not os.path.exists(poppler_dir):
        raise FileNotFoundError(f"Poppler path is invalid: {poppler_dir}")

    print(f"Processing pages {config.get_processing('start_page')}-{config.get_processing('end_page')}...")

    # Convert PDF to images
    images = convert_from_path(
        config.get_path('pdf_path'),
        first_page=int(config.get_processing('start_page')),
        last_page=int(config.get_processing('end_page')),
        dpi=int(config.get_processing('dpi')),
        poppler_path=poppler_dir
    )

    # Ensure temp image directory exists
    image_dir = config.get_path('temp_image_dir')
    os.makedirs(image_dir, exist_ok=True)

    # Save images
    for i, img in enumerate(images):
        img_path = os.path.join(image_dir, f"page_{i+1}.jpg")
        img.save(img_path, 'JPEG')

    # Process images in parallel
    with ThreadPoolExecutor() as executor:
        page_texts = list(executor.map(
            lambda i: OCRProcessor.extract_text(
                os.path.join(image_dir, f"page_{i+1}.jpg"),
                config
            ),
            range(len(images))
        ))

    # Analyze and format results
    output = ["# Sanskrit Text Analysis Report\n"]
    for i, text in enumerate(page_texts):
        cleaned = TextCleaner.clean_ocr_text(TextCleaner.remove_ascii_art(text))
        output.append(f"\n## Page {i+1}\n```\n{cleaned}\n```\n")

        for line in cleaned.splitlines():
            if not line.strip():
                continue

            analysis = sanskrit_processor.process_line(line)
            if analysis['type'] == 'sanskrit':
                output.extend([
                    f"### Sanskrit Analysis\n",
                    f"- **Original**: {analysis['original']}\n",
                    f"- **Word Breakdown**: {analysis['words']}\n",
                    f"- **IAST Transliteration**: {analysis['iast']}\n",
                    f"- **Devanagari**: {analysis['devanagari']}\n\n"
                ])

    # Save output
    with open(config.get_path('output_file'), 'w', encoding='utf-8') as f:
        f.writelines(output)

    print(f"Analysis complete! Results saved to {config.get_path('output_file')}")

if __name__ == "__main__":
    main()
