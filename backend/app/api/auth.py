from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
import os

RATE_LIMIT = 10 
API_KEY_NAME = "X-API-Key"
API_KEY_SECRET = os.getenv("API_KEY_SECRET", "api-key-secret")

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY_SECRET:
        return api_key
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API Key inválida o faltante",
    )