"""
Database Models
==============

SQLAlchemy models for Angel One API data storage.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from datetime import datetime

# Base class for all models
Base = declarative_base()

class LogEntry(Base):
    """Log entries table for database storage."""
    
    __tablename__ = "logs_angelone"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(20), index=True)
    logger_name = Column(String(100), index=True)
    message = Column(Text)
    extra_data = Column(JSON)
    session_id = Column(String(100), index=True)
    api_key_id = Column(String(100), index=True)
    method_name = Column(String(100), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class APICall(Base):
    """API call tracking table."""
    
    __tablename__ = "api_calls"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    endpoint = Column(String(200), index=True)
    method = Column(String(10), index=True)
    status_code = Column(Integer, index=True)
    response_time_ms = Column(Integer)
    request_id = Column(String(100), index=True)
    user_agent = Column(String(500))
    client_ip = Column(String(50))
    success = Column(Boolean, index=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class HealthCheck(Base):
    """Health check results table."""
    
    __tablename__ = "health_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    overall_status = Column(String(20), index=True)
    component_results = Column(JSON)
    response_time_ms = Column(Integer)
    healthy_components = Column(Integer)
    total_components = Column(Integer)
    system_metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)



