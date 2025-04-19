import os
import re
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from thefuzz import fuzz

# --- Configuration ---
base_dir = "/Users/wiledw/Downloads/Heneiken/heineken_reports"
output_dir = "./output"
os.makedirs(output_dir, exist_ok=True)

# --- Define the target sections ---
sections = {
    "cash_flows": ["consolidated statement of cash flows"],
    "income_statement": ["consolidated income statement", "heineken n.v. income statement"],
    "balance_sheet": ["heineken n.v. balance sheet"]
}

# --- Estimate offset ---
def estimate_pdf_offset(doc, sample_range=20):
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
        print(f"[✓] Estimated PDF offset: {most_common}")
        return most_common
    else:
        print("[!] Could not estimate offset from headers/footers. Using offset = 0")
        return 0

# --- Process all PDFs ---
for year in range(2014, 2025):
    pdf_path = os.path.join(base_dir, f"heineken-{year}.pdf")
    if not os.path.exists(pdf_path):
        print(f"[!] PDF not found: {pdf_path}")
        continue

    print(f"\n[→] Processing: {pdf_path}")
    doc = fitz.open(pdf_path)
    max_page = len(doc)
    pdf_offset = estimate_pdf_offset(doc)

    # Extract TOC
    toc_text = ""
    for i in range(1, 5):
        toc_text += doc[i].get_text()

    lines = [line.strip() for line in toc_text.splitlines() if line.strip()]
    found_pages = {}

    for i in range(len(lines)):
        current = lines[i]
        match_candidates = [(current, lines[i+1] if i+1 < len(lines) else ""),
                            (lines[i-1] if i-1 >= 0 else "", current)]

        for key, variants in sections.items():
            for variant in variants:
                for title_line, number_line in match_candidates:
                    if fuzz.partial_ratio(variant.lower(), title_line.lower()) > 85:
                        match = re.search(r"\b(\d{1,3})\b", number_line)
                        if match:
                            reported_page = int(match.group(1))
                            actual_page = reported_page + pdf_offset - 1
                            if 0 <= actual_page < max_page:
                                found_pages.setdefault(key, set()).add(actual_page)
                                found_pages[key].add(actual_page - 1)
                                found_pages[key].add(actual_page + 1)

    # OCR matched pages
    for key, page_nums in found_pages.items():
        for page_num in sorted(page_nums):
            if 0 <= page_num < max_page:
                print(f"[+] Extracting: {sections[key][0]} (PDF page {page_num + 1})")
                try:
                    image = convert_from_path(pdf_path, first_page=page_num + 1, last_page=page_num + 1)[0]
                    ocr_text = pytesseract.image_to_string(image)
                    output_filename = f"{year}_{key}_page_{page_num}.txt"
                    output_path = os.path.join(output_dir, output_filename)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(ocr_text)
                    print(f"    → Saved to {output_path}")
                except Exception as e:
                    print(f"[!] Error extracting page {page_num + 1}: {e}")

    if not found_pages:
        print("[-] No matching sections found in TOC.")
