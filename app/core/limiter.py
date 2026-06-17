from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.security import decode_access_token

def get_checker_rate_limit_key(request: Request) -> str:
    """Rate limit key generator.
    
    Returns 'checker:{checker_id}' if request is authenticated as checker.
    Otherwise falls back to remote IP address.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = decode_access_token(token)
            if payload and payload.get("type") == "checker":
                checker_id = payload.get("sub")
                if checker_id:
                    return f"checker:{checker_id}"
        except Exception:
            pass
            
    return f"ip:{get_remote_address(request)}"

# Initialize slowapi Limiter
limiter = Limiter(key_func=get_remote_address)
