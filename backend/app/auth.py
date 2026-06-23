import os

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from sqlalchemy import select

from .db import AsyncSessionLocal
from .models import User

security = HTTPBearer()

CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL", "")

_jwks: dict | None = None


async def _get_jwks() -> dict:
    global _jwks
    if _jwks is None:
        if not CLERK_JWKS_URL:
            raise HTTPException(status_code=500, detail="CLERK_JWKS_URL not configured")
        async with httpx.AsyncClient() as client:
            r = await client.get(CLERK_JWKS_URL, timeout=10.0)
            r.raise_for_status()
            _jwks = r.json()
    return _jwks


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False, "leeway": 10},
        )
        clerk_id: str = payload["sub"]
        email: str = payload.get("email", "")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(clerk_id=clerk_id, email=email, role="student")
            session.add(user)
            await session.commit()
            await session.refresh(user)

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
