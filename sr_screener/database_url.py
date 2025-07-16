"""
Database URL configuration for production deployment
Handles both SQLite (development) and PostgreSQL (production) connections
"""
import os
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_database_url():
    """
    Get the database URL from environment variables or use SQLite default
    
    Returns:
        str: SQLAlchemy database URL
    """
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        parsed_url = urlparse(database_url)
        if parsed_url.scheme == "postgres":
            database_url = parsed_url._replace(scheme="postgresql").geturl()
        
        logger.info(f"Using production database: {urlparse(database_url).scheme}")
        return database_url
    
    sqlite_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "citations.db")
    logger.info(f"Using development database: SQLite at {sqlite_path}")
    return f"sqlite:///{sqlite_path}"
