#!/usr/bin/env python3
"""Check test results from the database - simplified version."""

import sqlite3
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
    LIMIT 10
    ''')
    print('Recent batches:')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[2]} URLs, {row[3]} processed, status: {row[4]}')
    
    # Get URL report counts by category
    cursor.execute('''
    SELECT category, COUNT(*) 
    FROM url_reports 
    GROUP BY category
    ''')
    print('\nURL categorization totals:')
    total = 0
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')
        total += row[1]
    print(f'  Total: {total}')
    
    # Get some example URLs
    cursor.execute('''
    SELECT url, category, created_at
    FROM url_reports 
    ORDER BY created_at DESC
    LIMIT 20
    ''')
    print('\nRecent URLs processed:')
    for row in cursor.fetchall():
        print(f'  {row[0][:80]}... -> {row[1]}')
    
    # Check for test batch
    cursor.execute('''
    SELECT id, url_count, processed_count, created_at
    FROM url_batches 
    WHERE filename LIKE '%test_100_urls%'
    ORDER BY created_at DESC
    LIMIT 1
    ''')
    test_batch = cursor.fetchone()
    if test_batch:
        print(f'\nTest batch found: {test_batch[0]}')
        print(f'  URLs: {test_batch[1]}, Processed: {test_batch[2]}')
        print(f'  Created: {test_batch[3]}')
        
        # Get results for this batch
        cursor.execute('''
        SELECT ur.category, COUNT(*) 
        FROM url_reports ur
        JOIN urls u ON ur.url_id = u.id
        WHERE u.batch_id = ?
        GROUP BY ur.category
        ''', (test_batch[0],))
        print(f'\nTest batch results:')
        for row in cursor.fetchall():
            print(f'  {row[0]}: {row[1]}')
    
    conn.close()

if __name__ == "__main__":
    check_test_results() 