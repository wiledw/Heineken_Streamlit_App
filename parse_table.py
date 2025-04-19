import os
import re
import logging
from pdf2image import convert_from_path
import pytesseract
import fitz  # PyMuPDF
from thefuzz import fuzz

# --- Configuration ---
BASE_DIR = "/Users/wiledw/Downloads/Heneiken/heineken_reports"
OUTPUT_DIR = "./output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Define the target sections ---
SECTIONS = {
    "cash_flows": ["consolidated statement of cash flows"],
    "income_statement": ["consolidated income statement", "heineken n.v. income statement"],
    "balance_sheet": ["heineken n.v. balance sheet"]
}

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Estimate PDF Offset ---
def estimate_pdf_offset(doc, sample_range=20):
    """
    Estimate the offset for page numbers based on the document's first few pages.
    """
    offset_counts = {}
    for i in range(min(sample_range, len(doc))):
        text = doc[i].get_text("text")
        lines = [line.strip() for line in text.splitlines()]
        for line in lines:
            if re.fullmatch(r"\d{1,3}", line):
                reported = int(line)
                offset = i - reported + 1
                offset_counts[offset] = offset_counts.get(offset, 0) + 1
                break
    if offset_counts:
        most_common = max(offset_counts, key=offset_counts.get)
        logger.info(f"[✓] Estimated PDF offset: {most_common}")
        return most_common
    else:
        logger.warning("[!] Could not estimate offset from headers/footers. Using offset = 0")
        return 0

# --- Process all PDFs ---
def process_pdf_for_year(year):
    """
    Process the Heineken financial PDF for a specific year, extract the TOC, and perform OCR.
    """
    pdf_path = os.path.join(BASE_DIR, f"heineken-{year}.pdf")
    if not os.path.exists(pdf_path):
        logger.warning(f"[!] PDF not found: {pdf_path}")
        return

    logger.info(f"\n[→] Processing: {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"[!] Error opening PDF: {e}")
        return

    max_page = len(doc)
    pdf_offset = estimate_pdf_offset(doc)

    # Extract Table of Contents (TOC)
    toc_text = ""
    for i in range(1, 5):  # Checking pages 2–5 for the TOC
        toc_text += doc[i].get_text()

    lines = [line.strip() for line in toc_text.splitlines() if line.strip()]
    found_pages = {}

    # Match sections in the TOC
    for line in lines:
        match_candidates = [
            (line, lines[i+1] if i + 1 < len(lines) else ""),
            (lines[i-1] if i - 1 >= 0 else "", line)
        ]
        for key, variants in SECTIONS.items():
            for variant in variants:
                for title_line, number_line in match_candidates:
                    if fuzz.partial_ratio(variant.lower(), title_line.lower()) > 85:
                        match = re.search(r"\b(\d{1,3})\b", number_line)
                        if match:
                            reported_page = int(match.group(1))
                            actual_page = reported_page + pdf_offset - 1
                            if 0 <= actual_page < max_page:
                                found_pages.setdefault(key, set()).add(actual_page)
                                found_pages[key].update([actual_page - 1, actual_page + 1])

    # OCR matched pages
    for key, page_nums in found_pages.items():
        for page_num in sorted(page_nums):
            if 0 <= page_num < max_page:
                logger.info(f"[+] Extracting: {SECTIONS[key][0]} (PDF page {page_num + 1})")
                try:
                    image = convert_from_path(pdf_path, first_page=page_num + 1, last_page=page_num + 1)[0]
                    ocr_text = pytesseract.image_to_string(image)
                    output_filename = f"{year}_{key}_page_{page_num}.txt"
                    output_path = os.path.join(OUTPUT_DIR, output_filename)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(ocr_text)
                    logger.info(f"    → Saved to {output_path}")
                except Exception as e:
                    logger.error(f"[!] Error extracting page {page_num + 1}: {e}")

    if not found_pages:
        logger.info("[-] No matching sections found in TOC.")

# --- Main Function ---
def main():
    """
    Main function to process Heineken financial PDFs for the years 2014 to 2024.
    """
    for year in range(2014, 2025):
        process_pdf_for_year(year)

if __name__ == "__main__":
    main()
