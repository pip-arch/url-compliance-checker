#!/usr/bin/env python3
"""Run improved URL processing with PostgreSQL/Supabase database."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Apply PostgreSQL patch BEFORE importing anything else
from scripts.patch_database_service import *

# Now import and run the improved process
from scripts.run_improved_process import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main()) 