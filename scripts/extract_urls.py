#!/usr/bin/env python3
"""
Script to extract URLs from the backlinks CSV file and save them to a clean CSV format
"""
import csv
import sys
import os

def extract_urls(input_file, output_file, limit=None):
    """Extract URLs from the input file and save them to the output file"""
    urls = []
    
    # Try different encodings
    encodings = ['utf-8-sig', 'latin-1', 'utf-16', 'cp1252']
    
    for encoding in encodings:
        try:
            print(f"Trying to read CSV with encoding: {encoding}")
            with open(input_file, 'r', encoding=encoding, errors='replace') as f:
                # Read the first few lines to detect the delimiter
                header = f.readline()
                
                # Reset file pointer
                f.seek(0)
                
                # Try different delimiters
                for delimiter in [',', '\t', ';']:
                    try:
                        f.seek(0)  # Reset file pointer
                        reader = csv.DictReader(f, delimiter=delimiter)
                        
                        # Check if 'Referring page URL' is in the fieldnames
                        if 'Referring page URL' not in reader.fieldnames:
                            continue
                        
                        print(f"Found 'Referring page URL' column with delimiter: {delimiter}")
                        
                        # Extract URLs
                        for i, row in enumerate(reader):
                            if limit and i >= limit:
                                break
                                
                            url = row.get('Referring page URL', '').strip()
                            if url.startswith('http'):
                                urls.append([url])
                        
                        if urls:
                            print(f"Successfully extracted {len(urls)} URLs")
                            break
                    except Exception as e:
                        print(f"Error with delimiter {delimiter}: {str(e)}")
                        continue
                
                if urls:
                    break
        except Exception as e:
            print(f"Error with encoding {encoding}: {str(e)}")
            continue
    
    if not urls:
        print("Failed to extract any URLs from the file")
        return False
    
    # Write URLs to output file
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['URL'])
        writer.writerows(urls)
    
    print(f"Successfully wrote {len(urls)} URLs to {output_file}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_urls.py <input_file> <output_file> [limit]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist")
        sys.exit(1)
    
    success = extract_urls(input_file, output_file, limit)
    sys.exit(0 if success else 1) 