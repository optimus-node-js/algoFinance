"""
Angel One Database Logging Handler
==================================

Database handler for storing Angel One API logs in the logs_angelone table.
Integrates with existing database service for efficient log storage.

Author: AI Trading System
"""

import asyncio
import json
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from queue import Queue
import threading
import traceback

@dataclass
class LogRecord:
    """Structured log record for database storage."""
    timestamp: datetime
    level: str
    scope: str
    component: str
    message: str
    extra_data: Dict[str, Any]
    session_id: Optional[str] = None
    api_key_id: Optional[str] = None
    error_traceback: Optional[str] = None

class DatabaseLogHandler:
    """
    Async database handler for Angel One logs.
    
    Features:
    - Batch processing for performance
    - Conditional storage based on dbStore flag
    - Integration with existing database service
    - Error recovery and fallback logging
    """
    
    def __init__(self, batch_size: int = 100, batch_timeout: float = 5.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.enabled = True
        
        # Batch processing
        self.log_queue: Queue[LogRecord] = Queue()
        self.batch_buffer: List[LogRecord] = []
        self.last_flush = datetime.now(UTC)
        
        # Threading
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_logs": 0,
            "successful_inserts": 0,
            "failed_inserts": 0,
            "batch_count": 0,
            "last_error": None
        }
        
        # Start background worker
        self._start_worker()
    
    def _start_worker(self):
        """Start the background worker thread for batch processing."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
    
    def _worker_loop(self):
        """Background worker loop for processing log batches."""
        while not self.stop_event.is_set():
            try:
                # Process pending logs
                self._process_pending_logs()
                
                # Check if batch should be flushed
                if self._should_flush_batch():
                    asyncio.run(self._flush_batch())
                
                # Wait before next iteration
                self.stop_event.wait(0.1)
                
            except Exception as e:
                self.stats["last_error"] = str(e)
                # Continue processing despite errors
                continue
    
    def _process_pending_logs(self):
        """Process all pending logs from the queue."""
        processed = 0
        while not self.log_queue.empty() and processed < self.batch_size:
            try:
                log_record = self.log_queue.get_nowait()
                with self.lock:
                    self.batch_buffer.append(log_record)
                processed += 1
            except:
                break
    
    def _should_flush_batch(self) -> bool:
        """Check if the batch should be flushed."""
        with self.lock:
            if len(self.batch_buffer) >= self.batch_size:
                return True
            
            if len(self.batch_buffer) > 0:
                time_since_last_flush = (datetime.now(UTC) - self.last_flush).total_seconds()
                if time_since_last_flush >= self.batch_timeout:
                    return True
        
        return False
    
    async def _flush_batch(self):
        """Flush the current batch to database."""
        if not self.enabled:
            return
        
        with self.lock:
            if not self.batch_buffer:
                return
            
            batch_to_process = self.batch_buffer.copy()
            self.batch_buffer.clear()
            self.last_flush = datetime.now(UTC)
        
        try:
            await self._insert_logs_batch(batch_to_process)
            self.stats["successful_inserts"] += len(batch_to_process)
            self.stats["batch_count"] += 1
            
        except Exception as e:
            self.stats["failed_inserts"] += len(batch_to_process)
            self.stats["last_error"] = str(e)
            
            # Try to write failed logs to file as backup
            await self._backup_failed_logs(batch_to_process, str(e))
    
    async def _insert_logs_batch(self, logs: List[LogRecord]):
        """Insert a batch of logs into the database."""
        try:
            # Import database service - adjust import path as needed
            # This assumes there's a database service available outside angel_one_api
            from database.service import DatabaseService  # Adjust import path
            
            db_service = DatabaseService()
            
            # Prepare batch insert data
            insert_data = []
            for log in logs:
                insert_data.append({
                    "timestamp": log.timestamp,
                    "level": log.level,
                    "scope": log.scope,
                    "component": log.component,
                    "message": log.message,
                    "extra_data": json.dumps(log.extra_data) if log.extra_data else "{}",
                    "session_id": log.session_id,
                    "api_key_id": log.api_key_id,
                    "error_traceback": log.error_traceback
                })
            
            # Execute batch insert
            await db_service.batch_insert("logs_angelone", insert_data)
            
        except ImportError:
            # If database service is not available, log to file
            await self._backup_failed_logs(logs, "Database service not available")
            
        except Exception as e:
            # Log database errors
            raise Exception(f"Database insert failed: {str(e)}")
    
    async def _backup_failed_logs(self, logs: List[LogRecord], error: str):
        """Backup failed logs to file."""
        try:
            from pathlib import Path
            backup_file = Path(__file__).parent / "logs" / "errors" / "database_failures.log"
            
            with open(backup_file, "a", encoding="utf-8") as f:
                f.write(f"\n=== DATABASE FAILURE: {datetime.now(UTC)} ===\n")
                f.write(f"Error: {error}\n")
                f.write(f"Failed to insert {len(logs)} log records\n")
                
                for log in logs:
                    f.write(f"{log.timestamp} | {log.level} | [{log.scope}] {log.component} | {log.message}\n")
                
                f.write("=== END FAILURE BLOCK ===\n\n")
                
        except Exception:
            # If even file backup fails, we can't do much more
            pass
    
    def log(self, record: LogRecord, db_store: bool = True):
        """
        Add a log record to the processing queue.
        
        Args:
            record: The log record to store
            db_store: Whether to store in database (conditional storage)
        """
        if not self.enabled or not db_store:
            return
        
        try:
            self.log_queue.put_nowait(record)
            self.stats["total_logs"] += 1
        except:
            # Queue full - drop oldest logs to make room
            try:
                self.log_queue.get_nowait()  # Remove oldest
                self.log_queue.put_nowait(record)  # Add new
            except:
                pass  # Still couldn't add - skip this log
    
    def log_dict(self, 
                 level: str,
                 scope: str, 
                 component: str,
                 message: str,
                 extra_data: Optional[Dict[str, Any]] = None,
                 session_id: Optional[str] = None,
                 api_key_id: Optional[str] = None,
                 error_traceback: Optional[str] = None,
                 db_store: bool = True):
        """
        Log using dictionary parameters.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            scope: Logging scope (API_METHODS, SERVICES, etc.)
            component: Component name within scope
            message: Log message
            extra_data: Additional structured data
            session_id: Session identifier
            api_key_id: API key identifier
            error_traceback: Error traceback if applicable
            db_store: Whether to store in database
        """
        record = LogRecord(
            timestamp=datetime.now(UTC),
            level=level,
            scope=scope,
            component=component,
            message=message,
            extra_data=extra_data or {},
            session_id=session_id,
            api_key_id=api_key_id,
            error_traceback=error_traceback
        )
        
        self.log(record, db_store)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database handler statistics."""
        with self.lock:
            queue_size = self.log_queue.qsize()
            buffer_size = len(self.batch_buffer)
        
        return {
            **self.stats,
            "queue_size": queue_size,
            "buffer_size": buffer_size,
            "enabled": self.enabled,
            "worker_alive": self.worker_thread.is_alive() if self.worker_thread else False
        }
    
    def flush(self):
        """Force flush of current batch."""
        if self.batch_buffer:
            asyncio.run(self._flush_batch())
    
    def disable(self):
        """Disable database logging."""
        self.enabled = False
    
    def enable(self):
        """Enable database logging."""
        self.enabled = True
        if not self.worker_thread or not self.worker_thread.is_alive():
            self._start_worker()
    
    def shutdown(self):
        """Shutdown the database handler gracefully."""
        # Flush any remaining logs
        self.flush()
        
        # Stop the worker thread
        self.stop_event.set()
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)

# Global database handler instance
db_handler = DatabaseLogHandler()

# Ensure graceful shutdown
import atexit
atexit.register(db_handler.shutdown)
