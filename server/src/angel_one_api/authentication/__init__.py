"""
Angel One Authentication Module
==============================

Centralized authentication and session management for Angel One SmartAPI.

This module consolidates all authentication logic from:
- core/connections.py (SmartAPI client management)
- api_gateway/auth.py (Login logic)
- Scattered authentication across services

Components:
- AuthManager: Central authentication controller
- SessionManager: Session lifecycle management
- TokenManager: Token refresh and validation

Usage:
    from angel_one_api.authentication import AuthManager
    
    auth = AuthManager()
    await auth.login(api_key, client_id, password, totp_secret)
    client = auth.get_authenticated_client()
"""

from angel_one_api.authentication.auth_manager import AuthManager, AuthenticationError
from angel_one_api.authentication.session_manager import SessionManager, SessionError
from angel_one_api.authentication.token_manager import TokenManager, TokenError

__all__ = [
    'AuthManager',
    'SessionManager', 
    'TokenManager',
    'AuthenticationError',
    'SessionError',
    'TokenError'
]
