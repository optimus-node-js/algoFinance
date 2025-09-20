"""
Authentication Service Package
=============================

Handles all authentication operations for Angel One API.
"""

from .auth_manager import AuthManager, AuthenticationError

__all__ = [
    "AuthManager",
    "AuthenticationError"
]
