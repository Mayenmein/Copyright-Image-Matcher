import os
import cv2
import shutil
import sqlite3
import pytesseract
import pandas as pd
from PIL import Image
from rapidfuzz import fuzz
import re

class CopyrightMatcher:
    def __init__(self,
                 image_dir="sample copyright",
                 spreadsheet_path="copyright_records.csv",
                 ocr_db_path="image_text_index.db",
                 ocr_output_dir="ocr_output",
                 match_output_csv="matched_results.csv",
                 matched_image_dir="matched_output",
                 tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe"):

        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        self.IMAGE_DIR = image_dir
        self.SPREADSHEET_PATH = spreadsheet_path
        self.OCR_DB_PATH = ocr_db_path
        self.OCR_OUTPUT_DIR = ocr_output_dir
        self.MATCH_OUTPUT_CSV = match_output_csv
        self.MATCHED_IMAGE_DIR = matched_image_dir

        os.makedirs(self.OCR_OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.MATCHED_IMAGE_DIR, exist_ok=True)

    def preprocess_image(self, image_path):
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    def extract_ocr(self, image_path):
        preprocessed = self.preprocess_image(image_path)
        pil_img = Image.fromarray(preprocessed)
        return pytesseract.image_to_string(pil_img)

    def format_reg_number(self, raw):
        match = re.match(r'^([A-Z]{2})(\d{10})$', raw)
        if match:
            prefix, digits = match.groups()
            part1 = int(digits[3])           # 1 digit
            part2 = int(digits[4:7])         # 3 digits
            part3 = int(digits[7:])          # 5 digits
            return f"{prefix} {part1}-{part2}-{part3}"
        return raw

    def format_date_us_style(self, raw_date):
        try:
            dt = pd.to_datetime(raw_date)
            return dt.strftime("%B %d, %Y")
        except:
            return raw_date

    def clean_term(self, term):
        term = str(term)
        term = re.sub(r"[^a-zA-Z0-9\s:,]", " ", term)
        return re.sub(r"\s+", " ", term).strip()

    def build_ocr_index(self):
        conn = sqlite3.connect(self.OCR_DB_PATH)
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS ocr_index")
        c.execute("CREATE VIRTUAL TABLE ocr_index USING fts5(filename, content)")

        for fname in os.listdir(self.IMAGE_DIR):
            if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".tiff")):
                continue
            path = os.path.join(self.IMAGE_DIR, fname)
            text = self.extract_ocr(path)
            with open(os.path.join(self.OCR_OUTPUT_DIR, fname + ".txt"), "w", encoding="utf-8") as f:
                f.write(text)
            c.execute("INSERT INTO ocr_index (filename, content) VALUES (?, ?)", (fname, text))

        conn.commit()
        conn.close()

    def match_entries(self):
        df = pd.read_csv(self.SPREADSHEET_PATH)
        conn = sqlite3.connect(self.OCR_DB_PATH)
        c = conn.cursor()

        matched = []

        for _, row in df.iterrows():
            reg_date_raw = str(row['Registration Number / Date']).strip()
            title = str(row['Title']).strip()

            parts = [p.strip() for p in reg_date_raw.split("/")]
            reg_number_raw = parts[0] if len(parts) > 0 else ""
            reg_number_formatted = self.format_reg_number(reg_number_raw)
            date_raw = parts[1] if len(parts) > 1 else ""
            date_formatted = self.format_date_us_style(date_raw)

            search_terms = [reg_number_raw, reg_number_formatted, date_raw, date_formatted, title]
            best_match = None
            best_score = 0
            matched_files = set()

            for term in search_terms:
                if not term or term.lower() == "nan":
                    continue
                clean = self.clean_term(term)
                try:
                    c.execute("SELECT filename, content FROM ocr_index WHERE ocr_index MATCH ?", (f'"{clean}"',))
                    results = c.fetchall()
                except sqlite3.OperationalError:
                    c.execute("SELECT filename, content FROM ocr_index WHERE content LIKE ?", (f"%{term}%",))
                    results = c.fetchall()

                for filename, content in results:
                    score = fuzz.partial_ratio(term.lower(), content.lower())
                    if score > 80:
                        matched_files.add(filename)
                        if score > best_score:
                            best_score = score
                            best_match = filename

            if best_match:
                src_path = os.path.join(self.IMAGE_DIR, best_match)
                dst_name = f"{reg_number_raw}_{title[:50].replace(' ', '_')}.webp"
                dst_path = os.path.join(self.MATCHED_IMAGE_DIR, dst_name)
                try:
                    shutil.copy2(src_path, dst_path)
                except FileNotFoundError:
                    pass

            matched.append({
                'Registration Number': reg_number_raw,
                'Formatted Registration': reg_number_formatted,
                'Date': date_raw,
                'Formatted Date': date_formatted,
                'Title': title,
                'Best Match Image': best_match,
                'All Matched Files': "; ".join(matched_files)
            })

        pd.DataFrame(matched).to_csv(self.MATCH_OUTPUT_CSV, index=False)
        conn.close()

    def run(self):
        print("[1/3] Extracting OCR and building index...")
        self.build_ocr_index()
        print("[2/3] Matching spreadsheet entries to images...")
        self.match_entries()
        print(f"[3/3] Done. Results saved to {self.MATCH_OUTPUT_CSV} and {self.MATCHED_IMAGE_DIR}/")

# Main script usage
if __name__ == "__main__":

    matcher = CopyrightMatcher(spreadsheet_path="simulated_records.csv")
    matcher.run()
