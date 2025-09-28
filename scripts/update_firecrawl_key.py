#!/usr/bin/env python3
import os
import re

# New Firecrawl API key
NEW_API_KEY = "fc-a2f91968c3374fcbbb847383ba6cb03e"

# Update .env file
env_file = ".env"
env_backup = ".env.backup"

# Read current .env
with open(env_file, 'r') as f:
    content = f.read()

# Backup current .env
with open(env_backup, 'w') as f:
    f.write(content)

# Update Firecrawl API key
updated_content = re.sub(
    r'FIRECRAWL_API_KEY=.*',
    f'FIRECRAWL_API_KEY={NEW_API_KEY}',
    content
)

# Write updated .env
with open(env_file, 'w') as f:
    f.write(updated_content)

print(f"✅ Updated Firecrawl API key to: {NEW_API_KEY[:10]}...{NEW_API_KEY[-10:]}")
print(f"✅ Backup saved to: {env_backup}")

# Also set it in the current environment
os.environ['FIRECRAWL_API_KEY'] = NEW_API_KEY
print("✅ Updated environment variable") 