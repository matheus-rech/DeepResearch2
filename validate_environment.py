"""
Environment validation module
"""
import os
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def validate_database_connection() -> bool:
    """Check if database connection is available by attempting to connect."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not set")
        return False
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.exc import SQLAlchemyError
        engine = create_engine(database_url)
        with engine.connect():
            # Connection is implicitly checked by entering the 'with' block
            pass
        return True
    except ImportError:
        logger.error("SQLAlchemy is not installed. Cannot validate database connection.")
        return False
    except SQLAlchemyError as e:
        logger.error(f"Database validation failed: {e}")
        return False

def validate_openai_key() -> bool:
    """Check if OpenAI API key is available"""
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("OPENAI_API_KEY not set")
            return False
        return True
    except Exception as e:
        logger.error(f"OpenAI key validation failed: {e}")
        return False

def check_required_ports() -> List[int]:
    """Check if required ports are available (i.e., not already in use)."""
    import socket
    required_ports = [8501, 8000, 5432]
    available_ports = []
    
    for port in required_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                # If a port is in use, bind() will raise an OSError.
                s.bind(("127.0.0.1", port))
                available_ports.append(port)
            except OSError:
                logger.warning(f"Port {port} is already in use and not available.")
    
    return available_ports

def generate_environment_report() -> Tuple[bool, str]:
    """Generate comprehensive environment validation report"""
    checks = []
    
    # Database check
    db_ok = validate_database_connection()
    checks.append(f"Database: {'✓' if db_ok else '✗'}")
    
    # OpenAI key check
    openai_ok = validate_openai_key()
    checks.append(f"OpenAI API: {'✓' if openai_ok else '✗'}")
    
    # Port availability
    ports = check_required_ports()
    checks.append(f"Available ports: {len(ports)}/{len(required_ports)}")

    all_ok = db_ok and openai_ok and len(ports) >= len(required_ports)
    report = "\n".join(checks)
    
    return all_ok, report

if __name__ == "__main__":
    success, report = generate_environment_report()
    print("Environment Validation Report:")
    print(report)
    print(f"Overall status: {'PASS' if success else 'FAIL'}")