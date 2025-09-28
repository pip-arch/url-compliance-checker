#!/usr/bin/env python3
"""Patch the database service to use PostgreSQL instead of SQLite."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Replace the SQLite database service with PostgreSQL
import app.services.database
from app.services.database_postgres import DatabaseService

# Monkey-patch the database module
app.services.database.DatabaseService = DatabaseService

print("✅ Database service patched to use PostgreSQL")
print("   Now using Supabase instead of SQLite") 