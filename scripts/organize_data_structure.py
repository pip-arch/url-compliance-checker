#!/usr/bin/env python3
"""
Organize data files into a clean, structured format.
Moves files from /tmp and other locations to appropriate directories.
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
import csv

def create_directory_structure():
    """Create the organized directory structure."""
    directories = [
        "data/inputs/admiral_markets",
        "data/inputs/blacklist_keywords",
        "data/inputs/raw_backlinks",
        "data/outputs/blacklists",
        "data/outputs/whitelists",
        "data/outputs/review",
        "data/outputs/analysis_results",
        "data/outputs/domain_analysis",
        "data/outputs/enrichment",
        "data/outputs/qa_reports",
        "data/archive/tmp_backup",
        "data/archive/old_inputs",
        "data/test_files/archive"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created/verified: {dir_path}")

def organize_tmp_folder():
    """Organize files from data/tmp folder."""
    print("\n📁 Organizing /tmp folder...")
    
    tmp_path = Path("data/tmp")
    if not tmp_path.exists():
        print("  ⚠️  No tmp folder found")
        return
    
    # Move Admiral Markets backlink files to raw_backlinks
    for file in tmp_path.glob("admiralmarkets.com-backlinks-*.csv"):
        dest = Path(f"data/inputs/raw_backlinks/{file.name}")
        if not dest.exists():
            shutil.move(str(file), str(dest))
            print(f"  ✓ Moved {file.name} → raw_backlinks/")
    
    # Move blacklist files to appropriate locations
    blacklist_files = {
        "blacklist_consolidated.csv": "data/outputs/blacklists/blacklist_consolidated_master.csv",
        "blacklist_consolidated.csv.bak": "data/archive/tmp_backup/blacklist_consolidated.csv.bak",
        "blacklist_consolidated_backup.csv": "data/archive/tmp_backup/blacklist_consolidated_backup.csv",
        "blacklist_direct.csv": "data/outputs/blacklists/blacklist_direct.csv",
        "review_needed.csv": "data/outputs/review/review_needed_tmp.csv"
    }
    
    for src_file, dest_path in blacklist_files.items():
        src = tmp_path / src_file
        if src.exists():
            dest = Path(dest_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            print(f"  ✓ Moved {src_file} → {dest_path}")
    
    # Move any remaining CSV files to archive
    for file in tmp_path.glob("*.csv"):
        dest = Path(f"data/archive/tmp_backup/{file.name}")
        shutil.move(str(file), str(dest))
        print(f"  ✓ Archived {file.name}")
    
    # Move backups folder
    if (tmp_path / "backups").exists():
        shutil.move(str(tmp_path / "backups"), "data/archive/tmp_backup/backups")
        print("  ✓ Moved backups folder to archive")

def organize_input_files():
    """Organize files from data/inputs folder."""
    print("\n📁 Organizing input files...")
    
    inputs_path = Path("data/inputs")
    
    # Move Admiral Markets processed files
    admiral_files = [
        "admiralmarkets_latest_utf8.csv",
        "admiralmarkets_clean.csv",
        "admiralmarkets_fixed.csv",
        "admiralmarkets_utf8.csv"
    ]
    
    for file_name in admiral_files:
        src = inputs_path / file_name
        if src.exists():
            dest = Path(f"data/inputs/admiral_markets/{file_name}")
            shutil.move(str(src), str(dest))
            print(f"  ✓ Moved {file_name} → admiral_markets/")
    
    # Move raw backlinks file
    raw_backlink = inputs_path / "admiralmarkets.com-backlinks-subdomains_2025-04-16_13-31-57.csv"
    if raw_backlink.exists():
        dest = Path("data/inputs/raw_backlinks/admiralmarkets.com-backlinks-subdomains_2025-04-16_13-31-57.csv")
        if not dest.exists():
            shutil.move(str(raw_backlink), str(dest))
            print(f"  ✓ Moved raw backlinks file → raw_backlinks/")
    
    # Move blacklist keywords files
    for xlsx_file in inputs_path.glob("*.xlsx"):
        dest = Path(f"data/inputs/blacklist_keywords/{xlsx_file.name}")
        shutil.move(str(xlsx_file), str(dest))
        print(f"  ✓ Moved {xlsx_file.name} → blacklist_keywords/")
    
    # Move referring URLs
    if (inputs_path / "referring_urls.txt").exists():
        shutil.move(str(inputs_path / "referring_urls.txt"), 
                   "data/inputs/admiral_markets/referring_urls.txt")
        print("  ✓ Moved referring_urls.txt → admiral_markets/")

def organize_root_files():
    """Organize blacklist keywords files from root directory."""
    print("\n📁 Organizing root directory files...")
    
    # Move Blacklist keywords files
    blacklist_files = [
        "Blacklist keywords.csv",
        "Blacklist keywords (1).xlsx"
    ]
    
    for file_name in blacklist_files:
        if Path(file_name).exists():
            dest = Path(f"data/inputs/blacklist_keywords/{file_name}")
            shutil.move(file_name, str(dest))
            print(f"  ✓ Moved {file_name} → blacklist_keywords/")

def organize_test_files():
    """Clean up test files."""
    print("\n📁 Organizing test files...")
    
    test_path = Path("data/test_files")
    
    # Keep only the important test files
    important_files = [
        "all_admiral_urls.csv",
        "test_100_urls.csv",
        "test_10_urls.csv"
    ]
    
    # Archive old test files
    for file in test_path.glob("*.csv"):
        if file.name not in important_files:
            dest = Path(f"data/test_files/archive/{file.name}")
            shutil.move(str(file), str(dest))
            print(f"  ✓ Archived {file.name}")

def create_readme_files():
    """Create README files to explain the structure."""
    print("\n📝 Creating README files...")
    
    readme_content = {
        "data/inputs/README.md": """# Input Files Directory

## Structure:
- `admiral_markets/` - Processed Admiral Markets CSV files ready for analysis
- `blacklist_keywords/` - Blacklist keyword files (CSV and XLSX formats)
- `raw_backlinks/` - Original raw backlink export files from Admiral Markets

## Files:
### admiral_markets/
- `admiralmarkets_latest_utf8.csv` - Latest UTF-8 encoded version
- `admiralmarkets_clean.csv` - Cleaned version
- `referring_urls.txt` - Extracted referring URLs

### blacklist_keywords/
- `Blacklist keywords.csv` - Current active keywords
- `Blacklist keywords (1).xlsx` - Original Excel version
- `Blacklist keywords.xlsx` - Backup version

### raw_backlinks/
- Raw export files with timestamps (UTF-16 encoded)
""",
        "data/outputs/README.md": """# Output Files Directory

## Structure:
- `blacklists/` - Blacklisted URLs and domains
- `whitelists/` - Verified whitelist URLs
- `review/` - URLs requiring manual review
- `analysis_results/` - Batch processing results
- `domain_analysis/` - Domain-level analysis reports
- `enrichment/` - Enriched URL data (WHOIS, SSL, etc.)
- `qa_reports/` - Quality assurance reports
- `screenshots/` - URL screenshots
- `organized/` - Organized batch outputs

## Key Files:
- `blacklists/blacklist_consolidated_master.csv` - Master blacklist
- `domain_analysis_results.json` - Domain violation tracking
""",
        "data/archive/README.md": """# Archive Directory

## Structure:
- `tmp_backup/` - Backup of files from data/tmp
- `old_inputs/` - Archived input files
- Previous versions and backups

## Note:
Files here are kept for reference but not actively used.
"""
    }
    
    for file_path, content in readme_content.items():
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✓ Created {file_path}")

def generate_file_inventory():
    """Generate an inventory of all organized files."""
    print("\n📊 Generating file inventory...")
    
    inventory = {
        "timestamp": datetime.now().isoformat(),
        "directories": {}
    }
    
    # Scan key directories
    scan_dirs = [
        "data/inputs",
        "data/outputs",
        "data/test_files",
        "data/archive"
    ]
    
    for dir_path in scan_dirs:
        path = Path(dir_path)
        if path.exists():
            inventory["directories"][dir_path] = scan_directory(path)
    
    # Write inventory
    inventory_file = "data/FILE_INVENTORY.json"
    import json
    with open(inventory_file, 'w') as f:
        json.dump(inventory, f, indent=2)
    print(f"  ✓ Created {inventory_file}")
    
    # Also create a simple text version
    with open("data/FILE_INVENTORY.txt", 'w') as f:
        f.write(f"File Inventory - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for dir_name, dir_info in inventory["directories"].items():
            f.write(f"{dir_name}/\n")
            write_directory_tree(f, dir_info, indent="  ")
            f.write("\n")
    
    print("  ✓ Created data/FILE_INVENTORY.txt")

def scan_directory(path: Path, max_depth=3, current_depth=0):
    """Recursively scan directory structure."""
    if current_depth >= max_depth:
        return {"type": "directory", "truncated": True}
    
    result = {
        "type": "directory",
        "files": [],
        "subdirs": {}
    }
    
    try:
        for item in sorted(path.iterdir()):
            if item.is_file():
                size = item.stat().st_size
                result["files"].append({
                    "name": item.name,
                    "size": format_size(size)
                })
            elif item.is_dir() and not item.name.startswith('.'):
                result["subdirs"][item.name] = scan_directory(
                    item, max_depth, current_depth + 1
                )
    except PermissionError:
        result["error"] = "Permission denied"
    
    return result

def write_directory_tree(f, dir_info, indent=""):
    """Write directory tree to file."""
    if "files" in dir_info:
        for file_info in dir_info["files"]:
            f.write(f"{indent}📄 {file_info['name']} ({file_info['size']})\n")
    
    if "subdirs" in dir_info:
        for subdir_name, subdir_info in dir_info["subdirs"].items():
            f.write(f"{indent}📁 {subdir_name}/\n")
            if "truncated" in subdir_info and subdir_info["truncated"]:
                f.write(f"{indent}  ...\n")
            else:
                write_directory_tree(f, subdir_info, indent + "  ")

def format_size(size):
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"

def main():
    """Main organization function."""
    print("🚀 Starting data organization process...\n")
    
    # Create directory structure
    create_directory_structure()
    
    # Organize files
    organize_tmp_folder()
    organize_input_files()
    organize_root_files()
    organize_test_files()
    
    # Create documentation
    create_readme_files()
    generate_file_inventory()
    
    print("\n✅ Data organization complete!")
    print("\n📋 Summary:")
    print("  - Input files organized in data/inputs/")
    print("  - Output files organized in data/outputs/")
    print("  - Test files cleaned up in data/test_files/")
    print("  - Old files archived in data/archive/")
    print("  - README files created for documentation")
    print("  - File inventory generated in data/")

if __name__ == "__main__":
    main() 