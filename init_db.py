#!/usr/bin/env python3
"""
Database initialization script
Run this to create all database tables
"""

from app.db.database import Base, engine
from app.models import Patient, Session, Recording, Analysis

def init_db():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()