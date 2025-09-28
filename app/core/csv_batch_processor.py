import os
from dotenv import load_dotenv
load_dotenv()
import csv
import chardet
import sys
import asyncio
from app.core.url_processor import process_urls

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw = f.read(4096)
    return chardet.detect(raw)['encoding']

def get_up_to_1000_urls(csv_path):
    encoding = detect_encoding(csv_path)
    urls = []
    with open(csv_path, encoding=encoding, newline='') as f:
        # Try to auto-detect delimiter (tab or comma)
        sample = f.read(4096)
        f.seek(0)
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
        except Exception:
            dialect = csv.excel # fallback to default (comma)
        reader = csv.DictReader(f, dialect=dialect)
        url_field = None
        # Robustly find the correct field for URLs (case-insensitive, trimmed)
        for field in reader.fieldnames:
            if field and field.strip().lower() == 'referring page url':
                url_field = field
                break
        if not url_field:
            print('Could not find a "Referring page URL" column in CSV header. Available columns:', reader.fieldnames)
            return []
        for row in reader:
            url = row.get(url_field, '').strip()
            if url.startswith('http'):
                urls.append(url)
            if len(urls) >= 1000:
                break
    return urls

def process_csv_in_batches(csv_path, batch_size=100, max_urls=1000):
    urls = get_up_to_1000_urls(csv_path)
    if not urls:
        print(f"No URLs found in {csv_path}. File will NOT be deleted. Please check the column name and content.")
        return
    print(f"Found {len(urls)} URLs in {csv_path}. Processing in batches of {batch_size}...")
    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i:i+batch_size]
        batch_id = f"{os.path.splitext(os.path.basename(csv_path))[0]}_batch{i//batch_size+1}"
        print(f"Processing batch {i//batch_size+1}: {len(batch_urls)} URLs (batch_id={batch_id})...")
        asyncio.run(process_urls(batch_urls, batch_id))
        print(f"Finished batch {i//batch_size+1}.")
    print(f"All batches complete. File was NOT deleted.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.core.csv_batch_processor <csv_path>")
        sys.exit(1)
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        sys.exit(1)
    process_csv_in_batches(csv_path) 