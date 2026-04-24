#!/usr/bin/env python3
"""Initialize the Proceeds Navigator database."""

import os
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from proceeds_navigator.db.session import init_db

if __name__ == "__main__":
    init_db()
    print("[OK] Database initialized successfully.")
