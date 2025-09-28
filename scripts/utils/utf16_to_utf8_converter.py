#!/usr/bin/env python3
"""
UTF-16 to UTF-8 CSV File Converter

This script converts CSV files from UTF-16 encoding to UTF-8.
It can handle individual files or process entire directories recursively.

Usage:
    python utf16_to_utf8_converter.py <input_path> [-o OUTPUT] [-r] [-f]

    -o OUTPUT, --output OUTPUT    Output file or directory (default: input_file_utf8.csv)
    -r, --recursive               Process directories recursively
    -f, --force                   Force conversion even if not detected as UTF-16
"""

import os
import sys
import chardet
import codecs
import csv
import argparse
from pathlib import Path


def detect_encoding(file_path):
    """
    Detect the encoding of a file.
    
    Args:
        file_path (str): Path to the file to detect encoding for
        
    Returns:
        str: Detected encoding
    """
    # Check for BOM markers first (more reliable)
    with open(file_path, 'rb') as f:
        raw_data = f.read(4)
        
        # Check for UTF-16 BOM
        if raw_data.startswith(codecs.BOM_UTF16_LE) or raw_data.startswith(codecs.BOM_UTF16_BE):
            return 'utf-16'
        
        # Check for UTF-8 BOM
        if raw_data.startswith(codecs.BOM_UTF8):
            return 'utf-8'
    
    # Use chardet for detection if no BOM found
    # Reading more of the file improves detection accuracy
    with open(file_path, 'rb') as f:
        # Read a sample of the file (up to 1MB)
        raw_data = f.read(min(1024 * 1024, os.path.getsize(file_path)))
        
    result = chardet.detect(raw_data)
    return result['encoding']


def convert_file(input_path, output_path=None, force=False):
    """
    Convert a file from UTF-16 to UTF-8.
    
    Args:
        input_path (str): Path to the input file
        output_path (str, optional): Path to the output file. If None, uses input_path_utf8.csv
        force (bool): Force conversion even if not detected as UTF-16
        
    Returns:
        tuple: (success, message)
    """
    if not os.path.exists(input_path):
        return False, f"File not found: {input_path}"
    
    if not output_path:
        # Generate output filename
        base_path = os.path.splitext(input_path)[0]
        ext = os.path.splitext(input_path)[1]
        output_path = f"{base_path}_utf8{ext}"
    
    # Detect encoding
    try:
        encoding = detect_encoding(input_path)
        
        # Skip if already UTF-8 and not forced
        if encoding and encoding.lower().startswith('utf-8') and not force:
            return False, f"File '{input_path}' is already in UTF-8 format. Skipping."
        
        # Validate if we should convert
        if not encoding or (not encoding.lower().startswith('utf-16') and not force):
            return False, f"File '{input_path}' is not detected as UTF-16 (detected: {encoding}). Use -f to force conversion."
        
        # Read content with detected encoding
        with open(input_path, 'r', encoding=encoding, errors='replace') as infile:
            content = infile.read()
        
        # Write with UTF-8 encoding
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write(content)
        
        return True, f"Converted '{input_path}' to UTF-8: '{output_path}'"
    
    except Exception as e:
        return False, f"Error converting '{input_path}': {str(e)}"


def process_directory(directory_path, output_dir=None, recursive=False, force=False):
    """
    Process all CSV files in a directory.
    
    Args:
        directory_path (str): Path to the directory to process
        output_dir (str, optional): Path to the output directory
        recursive (bool): Process subdirectories recursively
        force (bool): Force conversion even if not detected as UTF-16
        
    Returns:
        tuple: (success_count, error_count, messages)
    """
    success_count = 0
    error_count = 0
    messages = []
    
    if not os.path.exists(directory_path):
        messages.append(f"Directory not found: {directory_path}")
        return 0, 1, messages
    
    # Create output directory if it doesn't exist
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for root, dirs, files in os.walk(directory_path):
        # Process only CSV files
        for file in files:
            if file.lower().endswith('.csv'):
                input_path = os.path.join(root, file)
                
                # Create corresponding output path if output_dir is specified
                if output_dir:
                    # Preserve directory structure
                    rel_path = os.path.relpath(os.path.join(root, file), directory_path)
                    out_path = os.path.join(output_dir, rel_path)
                    
                    # Create parent dirs if needed
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    
                    # Skip creating _utf8 suffix since we're using a different output directory
                    success, message = convert_file(input_path, out_path, force)
                else:
                    success, message = convert_file(input_path, None, force)
                
                messages.append(message)
                if success:
                    success_count += 1
                else:
                    error_count += 1
        
        # Don't recurse if not requested
        if not recursive:
            break
    
    return success_count, error_count, messages


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Convert CSV files from UTF-16 to UTF-8 encoding.')
    parser.add_argument('path', help='Path to the CSV file or directory to process')
    parser.add_argument('-o', '--output', help='Output file or directory path')
    parser.add_argument('-r', '--recursive', action='store_true', 
                        help='Process directories recursively')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Force conversion even if not detected as UTF-16')
    
    args = parser.parse_args()
    
    path = os.path.abspath(args.path)
    
    if os.path.isfile(path):
        # Process single file
        success, message = convert_file(path, args.output, args.force)
        print(message)
        return 0 if success else 1
    
    elif os.path.isdir(path):
        # Process directory
        success_count, error_count, messages = process_directory(
            path, args.output, args.recursive, args.force
        )
        
        # Print all messages
        for message in messages:
            print(message)
        
        # Summary
        print(f"\nSummary: {success_count} files converted, {error_count} errors")
        return 0 if error_count == 0 else 1
    
    else:
        print(f"Error: Path not found: {path}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 