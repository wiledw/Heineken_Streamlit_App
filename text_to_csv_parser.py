# text_to_csv_parser.py
import os
import re
import csv
from pathlib import Path

# Input directory with txt files
input_dir = Path("./output")
output_csv = Path("./heineken_financials_2014_2024.csv")

# Keywords to match common metrics
metric_patterns = {
    "revenue": ["revenue", "net revenue", "total revenue"],
    "net_income": ["net income", "profit for the year", "net profit"],
    "total_assets": ["total assets"],
    "total_liabilities": ["total liabilities"],
    "operating_cash_flow": ["net cash from operating activities", "operating activities"],
    "investing_cash_flow": ["net cash from investing activities", "investing activities"],
    "financing_cash_flow": ["net cash from financing activities", "financing activities"]
}

# Normalize text
def normalize(text):
    return re.sub(r"[^a-z0-9 .,-]", "", text.lower())

# Try to extract the first number found in a line
def extract_number(line):
    match = re.search(r"([-\d.,]+)", line.replace(",", ""))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

# Collect data entries
entries = []

for file in input_dir.glob("*.txt"):
    text = file.read_text(encoding="utf-8")
    lines = text.splitlines()
    year_match = re.match(r"(\d{4})_([a-z_]+)_page_\d+", file.stem)

    if not year_match:
        continue

    year, section = year_match.groups()
    
    for line in lines:
        norm = normalize(line)

        for metric, patterns in metric_patterns.items():
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

# Sort the data by year before writing to CSV
sorted_data = sorted(entries, key=lambda x: int(x["Year"]))
fieldnames = ["Year", "Section", "Metric", "Value", "Source File"]
with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(sorted_data)

print(f"[✓] Extracted {len(entries)} entries to {output_csv}")
