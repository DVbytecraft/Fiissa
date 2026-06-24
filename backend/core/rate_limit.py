"""
Rate limiting Redis-backed via slowapi.
Limites configurées pour les endpoints sensibles :
- OTP : 5 req / min / IP
- Login staff : 10 req / min / IP
- Submit-proof : 10 req / min / IP
- Endpoints publics reçus : 30 req / min / IP
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
)
