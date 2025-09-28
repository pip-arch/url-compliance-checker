#!/usr/bin/env python3
"""Add missing columns to the database for new features."""

import sqlite3
import os
from pathlib import Path

def add_missing_columns():
    """Add analysis_method and match_position columns to url_reports table."""
    
    db_path = Path("data/url_checker.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(url_reports)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add analysis_method column if missing
        if 'analysis_method' not in columns:
            print("Adding analysis_method column...")
            cursor.execute("""
                ALTER TABLE url_reports 
                ADD COLUMN analysis_method TEXT DEFAULT 'unknown'
            """)
            print("✓ Added analysis_method column")
        else:
            print("✓ analysis_method column already exists")
        
        # Add match_position column if missing
        if 'match_position' not in columns:
            print("Adding match_position column...")
            cursor.execute("""
                ALTER TABLE url_reports 
                ADD COLUMN match_position INTEGER DEFAULT NULL
            """)
            print("✓ Added match_position column")
        else:
            print("✓ match_position column already exists")
        
        # Add enrichment_data column if missing
        if 'enrichment_data' not in columns:
            print("Adding enrichment_data column...")
            cursor.execute("""
                ALTER TABLE url_reports 
                ADD COLUMN enrichment_data TEXT DEFAULT NULL
            """)
            print("✓ Added enrichment_data column")
        else:
            print("✓ enrichment_data column already exists")
        
        # Add pattern_matches column if missing
        if 'pattern_matches' not in columns:
            print("Adding pattern_matches column...")
            cursor.execute("""
                ALTER TABLE url_reports 
                ADD COLUMN pattern_matches TEXT DEFAULT NULL
            """)
            print("✓ Added pattern_matches column")
        else:
            print("✓ pattern_matches column already exists")
        
        # Add qa_checked column if missing
        if 'qa_checked' not in columns:
            print("Adding qa_checked column...")
            cursor.execute("""
                ALTER TABLE url_reports 
                ADD COLUMN qa_checked BOOLEAN DEFAULT 0
            """)
            print("✓ Added qa_checked column")
        else:
            print("✓ qa_checked column already exists")
        
        conn.commit()
        print("\n✅ Database schema updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_missing_columns() 