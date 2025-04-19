import os
import re
import csv
import logging
from pathlib import Path

# --- Configuration ---
INPUT_DIR = Path("./output")
OUTPUT_CSV = Path("./heineken_financials_2014_2024.csv")

# --- Keywords to match common metrics ---
METRIC_PATTERNS = {
    "revenue": ["revenue", "net revenue", "total revenue"],
    "net_income": ["net income", "profit for the year", "net profit"],
    "total_assets": ["total assets"],
    "total_liabilities": ["total liabilities"],
    "operating_cash_flow": ["net cash from operating activities", "operating activities"],
    "investing_cash_flow": ["net cash from investing activities", "investing activities"],
    "financing_cash_flow": ["net cash from financing activities", "financing activities"]
}

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Normalize text ---
def normalize(text):
    """
    Normalize text by removing unwanted characters and converting to lowercase.
    """
    return re.sub(r"[^a-z0-9 .,-]", "", text.lower())

# --- Extract number from a line ---
def extract_number(line):
    """
    Extract the first number found in a line.
    """
    match = re.search(r"([-\d.,]+)", line.replace(",", ""))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

# --- Collect data entries ---
def collect_data_entries():
    """
    Collect and return all data entries from the text files in the input directory.
    """
    entries = []

    for file in INPUT_DIR.glob("*.txt"):
        try:
            text = file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"[!] Error reading file {file.name}: {e}")
            continue

        lines = text.splitlines()
        year_match = re.match(r"(\d{4})_([a-z_]+)_page_\d+", file.stem)

        if not year_match:
            continue

        year, section = year_match.groups()

        for line in lines:
            norm = normalize(line)

            for metric, patterns in METRIC_PATTERNS.items():
                if any(p in norm for p in patterns):
                    value = extract_number(norm)
                    if value is not None:
                        entries.append({
                            "Year": year,
                            "Section": section,
                            "Metric": metric,
                            "Value": value,
                            "Source File": file.name
                        })
    return entries

# --- Write data to CSV ---
def write_to_csv(entries):
    """
    Write the extracted data entries to a CSV file.
    """
    sorted_data = sorted(entries, key=lambda x: int(x["Year"]))
    fieldnames = ["Year", "Section", "Metric", "Value", "Source File"]

    try:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sorted_data)
        logger.info(f"[✓] Extracted {len(entries)} entries to {OUTPUT_CSV}")
    except Exception as e:
        logger.error(f"[!] Error writing to CSV: {e}")

# --- Main Function ---
def main():
    """
    Main function to collect data from text files and write to CSV.
    """
    logger.info("[→] Starting data extraction from text files.")
    entries = collect_data_entries()

    if entries:
        write_to_csv(entries)
    else:
        logger.info("[-] No data entries found.")

if __name__ == "__main__":
    main()
