"""
Database Connection Management
=============================

Async database connection and session management for Angel One API.
"""

import asyncio
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from logger import get_infrastructure_logger

logger = get_infrastructure_logger("database_connection")

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[sessionmaker] = None

def get_database_engine() -> AsyncEngine:
    """Get or create database engine."""
    global _engine
    
    if _engine is None:
        try:
            # Convert regular database URL to async if needed
            database_url = settings.DATABASE_URL
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
            
            _engine = create_async_engine(
                database_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=20,
                pool_pre_ping=True,
                echo=settings.DEBUG
            )
            
            logger.info("Database engine created", {
                "pool_size": settings.DATABASE_POOL_SIZE,
                "debug_mode": settings.DEBUG
            })
            
        except Exception as e:
            logger.error("Failed to create database engine", error=e)
            # Return mock engine for development
            _engine = None
    
    return _engine

def get_session_factory() -> sessionmaker:
    """Get or create async session factory."""
    global _async_session_factory
    
    if _async_session_factory is None:
        engine = get_database_engine()
        
        if engine:
            _async_session_factory = sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Async session factory created")
        else:
            logger.warning("No database engine available, session factory not created")
    
    return _async_session_factory

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    Get async database session with automatic cleanup.
    
    Yields:
        AsyncSession: Database session or None if not available
    """
    session_factory = get_session_factory()
    
    if not session_factory:
        logger.debug("No session factory available, yielding None")
        yield None
        return
    
    session = session_factory()
    try:
        logger.debug("Database session created")
        yield session
        await session.commit()
        logger.debug("Database session committed")
    except Exception as e:
        logger.error("Database session error, rolling back", error=e)
        await session.rollback()
        raise
    finally:
        await session.close()
        logger.debug("Database session closed")

async def get_database_connection():
    """
    Get database connection (legacy compatibility).
    
    Returns:
        Connection object or None
    """
    try:
        engine = get_database_engine()
        if engine:
            async with engine.begin() as conn:
                return conn
        return None
    except Exception as e:
        logger.error("Failed to get database connection", error=e)
        return None

async def test_database_connection() -> bool:
    """
    Test database connectivity.
    
    Returns:
        bool: True if connection successful
    """
    try:
        async with get_async_session() as session:
            if session:
                # Simple test query
                result = await session.execute("SELECT 1")
                row = result.fetchone()
                logger.info("Database connection test successful", {"result": row[0] if row else None})
                return True
            else:
                logger.warning("Database session not available")
                return False
    except Exception as e:
        logger.error("Database connection test failed", error=e)
        return False

async def close_database_connections():
    """Close all database connections."""
    global _engine, _async_session_factory
    
    try:
        if _engine:
            await _engine.dispose()
            logger.info("Database engine disposed")
        
        _engine = None
        _async_session_factory = None
        
    except Exception as e:
        logger.error("Error closing database connections", error=e)
