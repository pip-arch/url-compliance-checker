# UTF-16 to UTF-8 CSV Converter Utility

## Overview

This document provides instructions for using the UTF-16 to UTF-8
converter utility that helps resolve encoding-related issues with CSV files
in the URL-checker project.

## Problem

CSV files exported from various sources (like Excel, Ahrefs, or SEMrush) 
are sometimes encoded in UTF-16 format. When these files are processed by 
the URL-checker application, they can cause errors such as:

- Incorrect character rendering
- Parsing failures
- Empty or corrupted output
- Python `UnicodeDecodeError` exceptions

These issues occur because many of our scripts expect UTF-8 encoded files
by default.

## Solution

The `utf16_to_utf8_converter.py` script detects and converts UTF-16 encoded
CSV files to UTF-8 format. It provides both single-file and batch conversion
capabilities and can operate recursively across directories.

## Basic Usage

To convert a single CSV file:

1. Activate your virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Run the script with the file path:
   ```bash
   python scripts/utils/utf16_to_utf8_converter.py data/inputs/your_file.csv
   ```

This will create a new file with the same name plus a `_utf8` suffix in the 
same directory.

## Advanced Usage

### Convert with a specific output path:
```bash
python scripts/utils/utf16_to_utf8_converter.py data/inputs/your_file.csv -o data/inputs/converted.csv
```

### Process all CSV files in a directory:
```bash
python scripts/utils/utf16_to_utf8_converter.py data/inputs/ -o data/inputs/converted/
```

### Process directories recursively:
```bash
python scripts/utils/utf16_to_utf8_converter.py data/inputs/ -r
```

### Force conversion regardless of detected encoding:
```bash
python scripts/utils/utf16_to_utf8_converter.py data/inputs/your_file.csv -f
```

## Features

- **Automatic encoding detection**: Using both BOM (Byte Order Mark) detection and content analysis
- **Safe operation**: Creates new files without modifying originals
- **Batch processing**: Can convert multiple files at once
- **Directory structure preservation**: Maintains folder hierarchy when processing directories
- **Detailed logging**: Provides information about each file's conversion status
- **Error handling**: Gracefully handles errors while processing multiple files

## Integration with CSV Batch Processor

After converting your files to UTF-8, you can process them with the CSV batch processor:

```bash
python scripts/utils/batch_processor.py data/inputs/converted/
```

## Troubleshooting

### Encoding Error: "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff"

This error indicates that a file is likely in UTF-16 format but is being read as UTF-8. Use the converter script on the file.

### File Still Has Encoding Issues After Conversion

Use the `-f` (force) flag to override the encoding detection:

```bash
python scripts/utils/utf16_to_utf8_converter.py data/inputs/your_file.csv -f
```

### Alternative Manual Conversion

If the script doesn't work, try using the `iconv` command-line tool:

```bash
iconv -f UTF-16LE -t UTF-8 data/inputs/your_file.csv > data/inputs/your_file_utf8.csv
```

### Memory Error with Large Files

For very large files, try processing them in smaller chunks or use the system's `split` command to break them into smaller files.

### Missing Dependencies

If you encounter module import errors, ensure you've installed all required dependencies:

```bash
pip install chardet
``` 