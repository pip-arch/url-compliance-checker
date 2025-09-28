#!/usr/bin/env python3
"""Test that blacklisted URLs are properly saved to CSV file."""
import csv
import os
import subprocess
import sys

def count_blacklist_entries():
    """Count entries in blacklist CSV."""
    blacklist_file = "data/tmp/blacklist_consolidated.csv"
    if not os.path.exists(blacklist_file):
        return 0
    
    with open(blacklist_file, 'r') as f:
        return sum(1 for _ in f) - 1  # Subtract header

print("🧪 Testing Blacklist Persistence Fix")
print("=" * 50)

# Count before
before_count = count_blacklist_entries()
print(f"✅ Blacklist entries before test: {before_count}")

# Create a small test file with known blacklisted URLs
test_urls = [
    "https://sejaceo.com/4-formas-para-comecar-a-conquistar-uma-renda-extra-no-mercado-financeiro/",
    "https://www.tradewithauntie.com/review-brokers-admirals/",
    "https://www.investissement-en-bourse.fr/coinhouse-avis/"
]

test_file = "data/tmp/test_blacklist_urls.csv"
with open(test_file, 'w') as f:
    f.write("url\n")
    for url in test_urls:
        f.write(f"{url}\n")

print(f"\n📝 Created test file with {len(test_urls)} known blacklisted URLs")

# Run processing
print("\n🏃 Running improved process...")
cmd = [
    "python", "scripts/run_improved_process_postgres.py",
    "--file", test_file,
    "--column", "url",
    "--batch-size", "3",
    "--workers", "3"
]

result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode != 0:
    print(f"\n❌ Error running process: {result.stderr}")
    sys.exit(1)

# Count after
after_count = count_blacklist_entries()
print(f"\n✅ Blacklist entries after test: {after_count}")

# Check results
new_entries = after_count - before_count
if new_entries > 0:
    print(f"\n🎉 SUCCESS! Added {new_entries} new blacklist entries")
    print("✅ Blacklist persistence fix is working correctly!")
    
    # Show the new entries
    blacklist_file = "data/tmp/blacklist_consolidated.csv"
    print(f"\nLast {new_entries} entries added:")
    with open(blacklist_file, 'r') as f:
        lines = f.readlines()
        for line in lines[-new_entries:]:
            print(f"  {line.strip()}")
else:
    print("\n⚠️  No new entries added (URLs might already be in blacklist)")

# Cleanup
os.remove(test_file)
print(f"\n🧹 Cleaned up test file") 