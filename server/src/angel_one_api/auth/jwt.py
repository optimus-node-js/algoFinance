"""
JWT Token Management
===================

JWT token encoding, decoding, and validation for FastAPI authentication.
"""

import jwt
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from pydantic import BaseModel

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from logger import get_infrastructure_logger

logger = get_infrastructure_logger("jwt_manager")

class TokenData(BaseModel):
    """JWT token data structure."""
    
    key_id: Optional[str] = None
    client_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: list = []

def encode_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Encode JWT token with expiration.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        str: Encoded JWT token
    """
    try:
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )
        
        logger.debug("JWT token encoded", {
            "expires_at": expire.isoformat(),
            "data_keys": list(data.keys())
        })
        
        return encoded_jwt
        
    except Exception as e:
        logger.error("Failed to encode JWT token", error=e)
        raise

def decode_token(token: str) -> TokenData:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        TokenData: Decoded token data
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        
        token_data = TokenData(
            key_id=payload.get("key_id"),
            client_id=payload.get("client_id"),
            expires_at=datetime.fromtimestamp(payload.get("exp", 0), UTC),
            scopes=payload.get("scopes", [])
        )
        
        logger.debug("JWT token decoded successfully", {
            "key_id": token_data.key_id,
            "expires_at": token_data.expires_at.isoformat() if token_data.expires_at else None
        })
        
        return token_data
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise jwt.InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token", error=e)
        raise
    except Exception as e:
        logger.error("Failed to decode JWT token", error=e)
        raise jwt.InvalidTokenError("Token validation failed")

def create_access_token(data: Dict[str, Any]) -> str:
    """
    Create access token with default settings.
    
    Args:
        data: Data to include in token
        
    Returns:
        str: Access token
    """
    return encode_token(data)

def verify_token(token: str) -> bool:
    """
    Verify if token is valid.
    
    Args:
        token: JWT token to verify
        
    Returns:
        bool: True if token is valid
    """
    try:
        decode_token(token)
        return True
    except:
        return False
