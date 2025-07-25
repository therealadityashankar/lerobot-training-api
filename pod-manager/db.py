import os
import logging
import aiosqlite
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.getenv("DB_PATH", "pod_manager.db")

# Models
class Pod(BaseModel):
    id: str
    name: str
    gpu_type: str
    gpu_count: int
    status: str
    created_at: str
    updated_at: Optional[str] = None
    terminated_at: Optional[str] = None
    public_ip: Optional[str] = None
    cost_per_hr: Optional[float] = None

class Job(BaseModel):
    id: str
    pod_id: str
    status: str
    progress: Optional[float] = None
    created_at: str
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None

# Database connection context manager
@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

async def init_db():
    """Initialize the database with required tables"""
    logger.info(f"Initializing database at {DB_PATH}")
    
    async with get_db() as db:
        # Create pods table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS pods (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            gpu_type TEXT NOT NULL,
            gpu_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            terminated_at TEXT,
            public_ip TEXT,
            cost_per_hr REAL
        )
        """)
        
        # Create jobs table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            pod_id TEXT NOT NULL,
            status TEXT NOT NULL,
            progress REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            completed_at TEXT,
            error TEXT,
            FOREIGN KEY (pod_id) REFERENCES pods (id)
        )
        """)
        
        await db.commit()
        logger.info("Database initialized successfully")
