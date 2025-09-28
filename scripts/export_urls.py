#!/usr/bin/env python3
"""
Script to extract URLs from the blacklist_consolidated.csv file
and export them to a new CSV file with only a URL column.
"""
import csv
import os
import sys
import argparse
from datetime import datetime

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def export_urls(input_file, output_file=None):
    """
    Extract URLs from the input CSV file and write them to a new CSV file with only a URL column.
    
    Args:
        input_file: Path to the input CSV file
        output_file: Path to the output CSV file (default: auto-generated based on input file)
    
    Returns:
        Path to the output file
    """
    # Generate output file path if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.dirname(input_file)
        output_base = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(output_dir, f"{output_base}_urls_{timestamp}.csv")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Extract URLs and write to output file
    urls = []
    try:
        # Read URLs from input file
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Skip header
            header = next(reader, None)
            if not header:
                print(f"Error: Input file {input_file} is empty or has no header")
                return None
                
            # Extract URLs (first column)
            for row in reader:
                if row and row[0]:  # Check if row exists and first column is not empty
                    url = row[0].strip()
                    if url and url.startswith(("http://", "https://")):
                        urls.append(url)
        
        # Write URLs to output file
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["URL"])  # Write header
            for url in urls:
                writer.writerow([url])
        
        print(f"Successfully extracted {len(urls)} URLs from {input_file}")
        print(f"Exported to {output_file}")
        return output_file
    
    except Exception as e:
        print(f"Error exporting URLs: {str(e)}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract URLs from a CSV file and export to a new CSV with only URL column")
    parser.add_argument("--input", "-i", default="data/tmp/blacklist_consolidated.csv", 
                       help="Path to input CSV file (default: data/tmp/blacklist_consolidated.csv)")
    parser.add_argument("--output", "-o", 
                       help="Path to output CSV file (default: auto-generated)")
    
    args = parser.parse_args()
    
    # Run the export
    export_urls(args.input, args.output) 