#!/usr/bin/env python3
"""
Recreate database tables with UUID support
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import Base, engine
from app.models import Patient, Session, Recording, Analysis

def recreate_tables():
    """Drop and recreate all database tables"""
    print("Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating new tables with UUID support...")
    Base.metadata.create_all(bind=engine)
    
    print("Database tables recreated successfully!")

if __name__ == "__main__":
    recreate_tables()