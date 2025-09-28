#!/usr/bin/env python3
"""Test Supabase database connection"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import logging

# Load environment
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL
db_url = os.getenv("DATABASE_URL")
if not db_url:
    logger.error("DATABASE_URL not found in environment!")
    sys.exit(1)

# Mask password for display
if "postgresql://" in db_url:
    parts = db_url.split(":")
    if len(parts) > 2:
        masked_url = f"{parts[0]}:{parts[1]}:****@{parts[2].split('@')[1]}"
        logger.info(f"Using database URL: {masked_url}")
else:
    logger.error("DATABASE_URL is not a PostgreSQL URL!")
    sys.exit(1)

try:
    # Create engine
    engine = create_engine(db_url)
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), current_user"))
        db_name, user = result.fetchone()
        logger.info(f"✅ Connected to database: {db_name} as user: {user}")
        
        # Check tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result]
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # Check url_processing_queue structure
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'url_processing_queue' 
            ORDER BY ordinal_position
        """))
        
        columns = [(row[0], row[1]) for row in result]
        logger.info("url_processing_queue columns:")
        for col_name, col_type in columns:
            logger.info(f"  - {col_name}: {col_type}")
        
        # Check total URLs
        result = conn.execute(text("SELECT COUNT(*) FROM url_processing_queue"))
        total_count = result.scalar()
        logger.info(f"Total URLs in queue: {total_count}")
        
    logger.info("✅ Database connection successful!")
    
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")
    sys.exit(1) 