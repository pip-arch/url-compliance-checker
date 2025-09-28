#!/usr/bin/env python3
"""
Script to initialize the database for the URL Checker application.
"""
import os
import sys
import sqlite3
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Get database path from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/url_checker.db")

# Extract file path from SQLite URL
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_path = Path(db_path)
    db_dir = db_path.parent
else:
    print("Only SQLite databases are supported for initialization")
    sys.exit(1)

def initialize_database():
    """Initialize the database with tables and indexes."""
    # Create directory if it doesn't exist
    if not db_dir.exists():
        print(f"Creating directory: {db_dir}")
        db_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Initializing database at: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create URL batches table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS url_batches (
        id TEXT PRIMARY KEY,
        description TEXT,
        filename TEXT,
        url_count INTEGER NOT NULL,
        processed_count INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    # Create URLs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        batch_id TEXT NOT NULL,
        status TEXT NOT NULL,
        filter_reason TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        error TEXT,
        FOREIGN KEY (batch_id) REFERENCES url_batches (id)
    )
    """)
    
    # Create URL contents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS url_contents (
        url_id TEXT PRIMARY KEY,
        title TEXT,
        full_text TEXT,
        crawled_at TEXT NOT NULL,
        metadata TEXT,
        FOREIGN KEY (url_id) REFERENCES urls (id)
    )
    """)
    
    # Create URL content matches table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS url_content_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url_id TEXT NOT NULL,
        text TEXT NOT NULL,
        position INTEGER NOT NULL,
        context_before TEXT NOT NULL,
        context_after TEXT NOT NULL,
        embedding_id TEXT,
        FOREIGN KEY (url_id) REFERENCES urls (id)
    )
    """)
    
    # Create compliance reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compliance_reports (
        id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL,
        status TEXT NOT NULL,
        blacklist_count INTEGER NOT NULL DEFAULT 0,
        whitelist_count INTEGER NOT NULL DEFAULT 0,
        review_count INTEGER NOT NULL DEFAULT 0,
        total_urls INTEGER NOT NULL,
        processed_urls INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (batch_id) REFERENCES url_batches (id)
    )
    """)
    
    # Create URL reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS url_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url_id TEXT NOT NULL,
        report_id TEXT NOT NULL,
        url TEXT NOT NULL,
        category TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (url_id) REFERENCES urls (id),
        FOREIGN KEY (report_id) REFERENCES compliance_reports (id)
    )
    """)
    
    # Create rule matches table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rule_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url_report_id INTEGER NOT NULL,
        rule_id TEXT NOT NULL,
        rule_name TEXT NOT NULL,
        rule_description TEXT,
        severity TEXT NOT NULL,
        match_text TEXT NOT NULL,
        context TEXT NOT NULL,
        confidence REAL NOT NULL DEFAULT 1.0,
        FOREIGN KEY (url_report_id) REFERENCES url_reports (id)
    )
    """)
    
    # Create AI analysis results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_analysis_results (
        url_report_id INTEGER PRIMARY KEY,
        model TEXT NOT NULL,
        category TEXT NOT NULL,
        confidence REAL NOT NULL,
        explanation TEXT NOT NULL,
        compliance_issues TEXT NOT NULL,
        raw_response TEXT,
        FOREIGN KEY (url_report_id) REFERENCES url_reports (id)
    )
    """)
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_urls_batch_id ON urls (batch_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_urls_status ON urls (status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_url_content_matches_url_id ON url_content_matches (url_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_url_reports_report_id ON url_reports (report_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_url_reports_category ON url_reports (category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rule_matches_url_report_id ON rule_matches (url_report_id)')
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("Database initialization completed successfully")


if __name__ == "__main__":
    initialize_database() 