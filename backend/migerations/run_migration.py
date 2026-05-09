# migrations/run_migration.py

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env")

# Path to migration SQL file
SQL_FILE = Path("migerations/001_schema.sql")

if not SQL_FILE.exists():
    raise FileNotFoundError(f"{SQL_FILE} not found")

# Read SQL
sql_content = SQL_FILE.read_text(encoding="utf-8")

# Create DB engine
engine = create_engine(DATABASE_URL)

print("Running migration...")

# Execute SQL
with engine.begin() as connection:
    connection.execute(text(sql_content))

print("Migration completed successfully.")