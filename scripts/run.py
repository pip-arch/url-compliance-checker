#!/usr/bin/env python3
"""
Script to run the URL Checker application.
"""
import os
import sys
import subprocess
import uvicorn

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the database initialization script
from scripts.init_db import db_path, initialize_database

if __name__ == "__main__":
    print("Starting URL Checker application...")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database does not exist. Running database initialization...")
        initialize_database()
    
    # Get settings from environment variables, with defaults
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("APP_ENV", "development") == "development"
    
    print(f"URL Checker running at http://{host}:{port}")
    print(f"Environment: {os.getenv('APP_ENV', 'development')}")
    print(f"Hot reload: {reload}")
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    ) 