"""
Angel One Session Manager
========================

Advanced session lifecycle management for Angel One SmartAPI.

Features:
- Session creation and validation
- Automatic session renewal
- Session cleanup and monitoring
- Multi-session support
- Session persistence (optional)
- Health monitoring

Author: AI Trading System
"""

import time
import asyncio
import json
from typing import Dict, Optional, List, Any
from datetime import datetime, UTC, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

# Import new Angel One logger
from ..logger import get_service_logger

logger = get_service_logger("session_manager")

class SessionError(Exception):
    """Raised when session operations fail."""
    pass

@dataclass
class Session:
    """Session data structure."""
    session_id: str
    key_name: str
    client_code: str
    jwt_token: str
    refresh_token: str
    feed_token: str
    created_at: str
    expires_at: str
    last_activity: str
    is_active: bool = True
    login_count: int = 1
    api_calls_made: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create session from dictionary."""
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        try:
            expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.now(UTC) >= expires_at
        except Exception:
            return True
    
    def time_until_expiry(self) -> timedelta:
        """Get time until session expires."""
        try:
            expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return expires_at - datetime.now(UTC)
        except Exception:
            return timedelta(0)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(UTC).isoformat()
        self.api_calls_made += 1

class SessionManager:
    """
    Advanced session lifecycle management.
    
    Handles session creation, validation, renewal, and cleanup
    for multiple Angel One API connections.
    """
    
    def __init__(self, persist_sessions: bool = False, storage_path: Optional[str] = None):
        self._sessions: Dict[str, Session] = {}
        self._session_id_counter: int = 0
        self._persist_sessions = persist_sessions
        self._storage_path = Path(storage_path) if storage_path else Path("sessions.json")
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_interval: int = 300  # 5 minutes
        
        # Load persisted sessions if enabled
        if self._persist_sessions:
            self._load_sessions()
    
    async def create_session(
        self,
        key_name: str,
        session_data: Dict[str, Any]
    ) -> Session:
        """
        Create a new session.
        
        Args:
            key_name: API key identifier
            session_data: Session data from authentication
            
        Returns:
            Session: Created session object
        """
        try:
            self._session_id_counter += 1
            session_id = f"session_{key_name}_{self._session_id_counter}_{int(time.time())}"
            
            # Calculate expiration (24 hours from now)
            created_at = datetime.now(UTC)
            expires_at = created_at + timedelta(hours=24)
            
            session = Session(
                session_id=session_id,
                key_name=key_name,
                client_code=session_data.get('clientcode', ''),
                jwt_token=session_data.get('jwtToken', ''),
                refresh_token=session_data.get('refreshToken', ''),
                feed_token=session_data.get('feedToken', ''),
                created_at=created_at.isoformat(),
                expires_at=expires_at.isoformat(),
                last_activity=created_at.isoformat()
            )
            
            # Store session
            self._sessions[session_id] = session
            
            # Persist if enabled
            if self._persist_sessions:
                self._save_sessions()
            
            # Start monitoring if this is the first session
            if len(self._sessions) == 1 and not self._monitoring_task:
                self._monitoring_task = asyncio.create_task(self._monitor_sessions())
            
            logger.info(f"✅ Session created: {session_id} for {key_name}")
            return session
            
        except Exception as e:
            logger.error(f"❌ Session creation failed for {key_name}: {e}")
            raise SessionError(f"Failed to create session: {e}")
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session or None if not found
        """
        session = self._sessions.get(session_id)
        if session:
            session.update_activity()
        return session
    
    def get_session_by_key(self, key_name: str) -> Optional[Session]:
        """
        Get active session for a specific API key.
        
        Args:
            key_name: API key identifier
            
        Returns:
            Session or None if not found
        """
        for session in self._sessions.values():
            if session.key_name == key_name and session.is_active and not session.is_expired():
                session.update_activity()
                return session
        return None
    
    def get_all_sessions(self) -> List[Session]:
        """Get all sessions."""
        return list(self._sessions.values())
    
    def get_active_sessions(self) -> List[Session]:
        """Get all active, non-expired sessions."""
        return [
            s for s in self._sessions.values() 
            if s.is_active and not s.is_expired()
        ]
    
    async def validate_session(self, session_id: str) -> bool:
        """
        Validate a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if session is valid
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        if not session.is_active:
            return False
        
        if session.is_expired():
            logger.warning(f"⚠️ Session expired: {session_id}")
            await self._mark_session_expired(session_id)
            return False
        
        # Update activity
        session.update_activity()
        
        # Optional: Make a test API call to validate token
        # This would require integration with Angel One API
        
        return True
    
    async def refresh_session(self, session_id: str) -> bool:
        """
        Refresh a session using refresh token.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: Success status
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"⚠️ Session not found for refresh: {session_id}")
            return False
        
        if not session.refresh_token:
            logger.warning(f"⚠️ No refresh token available for {session_id}")
            return False
        
        try:
            # Use token manager to refresh
            from .token_manager import TokenManager
            
            token_manager = TokenManager()
            result = await token_manager.refresh_token(session.refresh_token)
            
            if result['success']:
                # Update session with new tokens
                token_info = result['token_info']
                session.jwt_token = token_info['jwt_token']
                session.refresh_token = token_info['refresh_token']
                session.expires_at = token_info['expires_at']
                session.last_activity = datetime.now(UTC).isoformat()
                session.login_count += 1
                
                # Persist if enabled
                if self._persist_sessions:
                    self._save_sessions()
                
                logger.info(f"✅ Session refreshed: {session_id}")
                return True
            else:
                logger.error(f"❌ Session refresh failed for {session_id}: {result.get('error')}")
                await self._mark_session_expired(session_id)
                return False
                
        except Exception as e:
            logger.error(f"❌ Session refresh error for {session_id}: {e}")
            await self._mark_session_expired(session_id)
            return False
    
    async def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: Success status
        """
        try:
            session = self._sessions.get(session_id)
            if not session:
                return True  # Already gone
            
            # Mark as inactive
            session.is_active = False
            
            # Optional: Call logout API
            try:
                from ..methods.logout import logout
                await logout()
            except Exception as e:
                logger.warning(f"⚠️ Logout API call failed for {session_id}: {e}")
            
            # Remove from memory
            del self._sessions[session_id]
            
            # Persist changes
            if self._persist_sessions:
                self._save_sessions()
            
            logger.info(f"🚪 Session invalidated: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Session invalidation failed for {session_id}: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        expired_sessions = []
        
        for session_id, session in self._sessions.items():
            if session.is_expired() or not session.is_active:
                expired_sessions.append(session_id)
        
        cleaned_count = 0
        for session_id in expired_sessions:
            if await self.invalidate_session(session_id):
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned up {cleaned_count} expired sessions")
        
        return cleaned_count
    
    async def _mark_session_expired(self, session_id: str):
        """Mark a session as expired."""
        session = self._sessions.get(session_id)
        if session:
            session.is_active = False
            logger.warning(f"⚠️ Session marked as expired: {session_id}")
    
    async def _monitor_sessions(self):
        """Background task to monitor sessions."""
        logger.info("🔍 Starting session monitoring")
        
        try:
            while self._sessions:
                await asyncio.sleep(self._cleanup_interval)
                
                # Clean up expired sessions
                cleaned_count = await self.cleanup_expired_sessions()
                
                # Log session statistics
                active_count = len(self.get_active_sessions())
                total_count = len(self._sessions)
                
                if total_count > 0:
                    logger.debug(f"📊 Sessions: {active_count} active, {total_count} total")
                
                # Auto-refresh sessions nearing expiry
                await self._auto_refresh_sessions()
                
        except asyncio.CancelledError:
            logger.info("🔍 Session monitoring stopped")
        except Exception as e:
            logger.error(f"❌ Session monitoring error: {e}")
        finally:
            self._monitoring_task = None
    
    async def _auto_refresh_sessions(self):
        """Automatically refresh sessions nearing expiry."""
        refresh_threshold = timedelta(hours=2)  # Refresh 2 hours before expiry
        
        for session in self.get_active_sessions():
            time_until_expiry = session.time_until_expiry()
            
            if time_until_expiry < refresh_threshold and session.refresh_token:
                logger.info(f"🔄 Auto-refreshing session nearing expiry: {session.session_id}")
                await self.refresh_session(session.session_id)
    
    def _save_sessions(self):
        """Save sessions to persistent storage."""
        if not self._persist_sessions:
            return
        
        try:
            session_data = {
                session_id: session.to_dict() 
                for session_id, session in self._sessions.items()
            }
            
            with open(self._storage_path, 'w') as f:
                json.dump(session_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Failed to save sessions: {e}")
    
    def _load_sessions(self):
        """Load sessions from persistent storage."""
        if not self._persist_sessions or not self._storage_path.exists():
            return
        
        try:
            with open(self._storage_path, 'r') as f:
                session_data = json.load(f)
            
            for session_id, data in session_data.items():
                session = Session.from_dict(data)
                
                # Only load non-expired sessions
                if not session.is_expired():
                    self._sessions[session_id] = session
            
            logger.info(f"📂 Loaded {len(self._sessions)} sessions from storage")
            
        except Exception as e:
            logger.error(f"❌ Failed to load sessions: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        sessions = list(self._sessions.values())
        active_sessions = self.get_active_sessions()
        
        # Calculate uptime statistics
        now = datetime.now(UTC)
        uptimes = []
        for session in active_sessions:
            try:
                created_at = datetime.fromisoformat(session.created_at.replace('Z', '+00:00'))
                uptime = (now - created_at).total_seconds() / 3600  # hours
                uptimes.append(uptime)
            except Exception:
                continue
        
        return {
            'total_sessions': len(sessions),
            'active_sessions': len(active_sessions),
            'expired_sessions': len([s for s in sessions if s.is_expired()]),
            'inactive_sessions': len([s for s in sessions if not s.is_active]),
            'average_uptime_hours': sum(uptimes) / len(uptimes) if uptimes else 0,
            'total_api_calls': sum(s.api_calls_made for s in sessions),
            'monitoring_active': self._monitoring_task is not None,
            'persistence_enabled': self._persist_sessions
        }
    
    async def shutdown(self):
        """Gracefully shutdown session manager."""
        logger.info("🔄 Shutting down session manager")
        
        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Invalidate all sessions
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            await self.invalidate_session(session_id)
        
        # Final save if persistence is enabled
        if self._persist_sessions:
            self._save_sessions()
        
        logger.info("✅ Session manager shutdown complete")

# Global session manager instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get the global SessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
