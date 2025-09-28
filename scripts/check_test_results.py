#!/usr/bin/env python3
"""Check test results from the database."""

import sqlite3
import datetime
from pathlib import Path

def check_test_results():
    """Check recent test results from the database."""
    db_path = Path("data/url_checker.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get recent batches
    cursor.execute('''
    SELECT id, created_at, url_count, processed_count, status 
    FROM url_batches 
    ORDER BY created_at DESC 
    LIMIT 5
    ''')
    print('Recent batches:')
    for row in cursor.fetchall():
        print(f'  {row}')
    
    # Get URL report counts by category from recent batch
    cursor.execute('''
    SELECT category, COUNT(*) 
    FROM url_reports 
    WHERE created_at > datetime('now', '-30 minutes')
    GROUP BY category
    ''')
    print('\nRecent URL categorization (last 30 min):')
    total = 0
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')
        total += row[1]
    print(f'  Total: {total}')
    
    # Get analysis method distribution
    cursor.execute('''
    SELECT analysis_method, COUNT(*) 
    FROM url_reports 
    WHERE created_at > datetime('now', '-30 minutes')
    GROUP BY analysis_method
    ''')
    print('\nAnalysis methods used:')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')
    
    # Get some example URLs
    cursor.execute('''
    SELECT url, category, analysis_method, created_at
    FROM url_reports 
    WHERE created_at > datetime('now', '-30 minutes')
    ORDER BY created_at DESC
    LIMIT 10
    ''')
    print('\nExample recent URLs:')
    for row in cursor.fetchall():
        print(f'  {row[0][:60]}... -> {row[1]} ({row[2]}) at {row[3]}')
    
    # Check for domain violations
    cursor.execute('''
    SELECT COUNT(DISTINCT url) 
    FROM url_reports 
    WHERE category = 'blacklist' 
    AND created_at > datetime('now', '-30 minutes')
    ''')
    blacklist_count = cursor.fetchone()[0]
    print(f'\nBlacklisted URLs in test: {blacklist_count}')
    
    conn.close()

if __name__ == "__main__":
    check_test_results() 