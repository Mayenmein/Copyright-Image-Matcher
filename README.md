# Copyright Image Matcher

This project matches copyright registration records from a spreadsheet (CSV) to corresponding scanned image files using OCR and fuzzy search. It builds an index of extracted text from images and finds the best match for each record based on registration number, date, and title.

---

## Features

- OCR text extraction from scanned copyright registration **reference images** using Tesseract.
- Fuzzy matching (with `rapidfuzz`) between OCR text and spreadsheet metadata.
- Automatic renaming and copying of matched image files to a results directory.
- Flexible search using formatted/unformatted registration numbers and dates.
- Implemented in a clean, class-based design for easy reuse and extension.

---

## Data Sources

- **Reference Images:** Scanned copyright registration images (JPEG, PNG, WEBP, TIFF, etc.) stored in the `sample copyright/` directory.
- **Reference Spreadsheet:** Metadata about registrations stored in `simulated_records.csv`.
- **Given Spreadsheet** Metadata about registrations stored in `copyright_records.csv`.

---

## Dependencies

Install dependencies using pip:

```bash
pip install opencv-python-headless pytesseract pandas pillow rapidfuzz
```
 
Also ensure you have Tesseract OCR installed on your system:

- Tesseract GitHub Page

- On Windows, set the correct path in the script (default is):
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```
## Directory Structure
project/
│
├── sample copyright/          # Input images (JPEG, PNG, WEBP, etc.)
├── copyright_records.csv      # Input spreadsheet of records
├── ocr_output/                # OCR text output (auto-created)
├── matched_output/            # Matched images with new names (auto-created)
├── image_text_index.db        # SQLite FTS index (auto-generated)
├── matched_results.csv        # CSV of match results (auto-generated)
├── matcher.py                 # Main Python script (class-based)
└── README.md

## Spreadsheet Format
The CSV file should contain at least the following columns:

- Registration Number / Date → e.g., VA0002335524 / 2023-05-07

- Title → e.g., Midnight Melodies

## OCR and Matching Strategy
Each row is matched using: 
- Raw registration number (e.g., VA0002335524) 
- Formatted registration number (e.g., VA 0-233-5524) 
- Raw and formatted dates (e.g., 2023-05-07 → May 07, 2023) 
- Title

Matches are performed using: 
- FTS5 full-text search in SQLite 
- Fuzzy matching with rapidfuzz.partial_ratio

Only matches scoring above a threshold (default ≥ 80%) are accepted.

## How to Run
Run the script from the command line:

```bash
python matcher.py
```
You’ll see logs like:
```bash 
[1/3] Extracting OCR and building index...
[2/3] Matching spreadsheet entries to images...
[3/3] Done. Results saved to matched_results.csv and matched_output/
```
## Output
matched_results.csv
Contains:

- Registration Number and Formatted Registration 
- Date and Formatted Date 
- Title 
- Best Match Image (single best match) 
- All Matched Files (any image matching the entry)

matched_output/
Contains copies of matched images, renamed with the convention:

REGNO_TitleExcerpt.webp
e.g., VA0002335524_Midnight_Melodies.webp

## Customization
You can configure:

- Image folder paths 
- CSV path 
- OCR output location 
- Thresholds 
-Match criteria

...by editing the ` __init__()` config in the `matcher.py` class.

## Cleaning / Resetting
To reset generated output:
```bash
rm image_text_index.db
rm -rf ocr_output/ matched_output/
rm matched_results.csv
```