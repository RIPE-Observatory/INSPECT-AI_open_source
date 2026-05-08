from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
from fastapi import Header, HTTPException, status
from jose import jwt
from jose.exceptions import JWTClaimsError, JWTError

from core.config import get_settings

logger = logging.getLogger(__name__)


class ClerkTokenVerifier:
    """Validates Clerk-issued JWTs using the tenant JWKS."""

    def __init__(
        self,
        jwks_url: str,
        issuer: str,
        audiences: Optional[list[str]] = None,
    ):
        self._jwks_url = jwks_url
        self._issuer = issuer
        self._audiences = audiences
        self._jwks: Optional[Dict[str, Any]] = None
        self._last_fetched = 0.0
        self._lock = asyncio.Lock()

    async def _fetch_jwks(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self._jwks_url)
            response.raise_for_status()
            return response.json()

    async def _get_jwks(self) -> Dict[str, Any]:
        async with self._lock:
            now = time.time()
            if self._jwks is None or now - self._last_fetched > 3600:
                self._jwks = await self._fetch_jwks()
                self._last_fetched = now
            return self._jwks

    async def verify(self, token: str) -> Dict[str, Any]:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization token header",
            ) from exc

        jwks = await self._get_jwks()
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == unverified_header.get("kid")), None)
        if key is None:
            # Refresh once in case of rotating keys
            self._jwks = None
            jwks = await self._get_jwks()
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == unverified_header.get("kid")), None)

        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to verify authorization token",
            )

        decode_kwargs: Dict[str, Any] = {
            "token": token,
            "key": key,
            "algorithms": [unverified_header.get("alg", "RS256")],
            "issuer": self._issuer,
        }

        if self._audiences:
            audience_value: str | list[str]
            if len(self._audiences) == 1:
                audience_value = self._audiences[0]
            else:
                audience_value = self._audiences
            decode_kwargs["audience"] = audience_value
        else:
            decode_kwargs["options"] = {"verify_aud": False}

        try:
            decoded = jwt.decode(**decode_kwargs)
        except JWTClaimsError as exc:
            logger.warning("JWT claims validation failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization token validation failed",
            ) from exc
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization token validation failed",
            ) from exc

        return decoded


_token_verifier: Optional[ClerkTokenVerifier] = None


def get_token_verifier() -> ClerkTokenVerifier:
    global _token_verifier
    if _token_verifier is not None:
        return _token_verifier

    settings = get_settings()
    if not settings.CLERK_JWKS_URL or not settings.CLERK_ISSUER:
        raise RuntimeError(
            "Clerk configuration is missing. Set CLERK_JWKS_URL and CLERK_ISSUER."
        )

    _token_verifier = ClerkTokenVerifier(
        jwks_url=settings.CLERK_JWKS_URL,
        issuer=settings.CLERK_ISSUER,
        audiences=settings.CLERK_ALLOWED_AUDIENCES,
    )
    return _token_verifier


@dataclass
class AuthenticatedUser:
    clerk_user_id: str
    session_id: Optional[str]
    claims: Dict[str, Any]


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> AuthenticatedUser:
    settings = get_settings()
    if settings.DISABLE_AUTH:
        return AuthenticatedUser(
            clerk_user_id=settings.DEMO_REVIEWER_ID,
            session_id="demo_session",
            claims={
                "sub": settings.DEMO_REVIEWER_ID,
                "sid": "demo_session",
                "auth_disabled": True,
            },
        )

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing"
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authorization header required",
        )

    verifier = get_token_verifier()
    claims = await verifier.verify(token)
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing subject claim",
        )

    session_id = claims.get("sid")
    return AuthenticatedUser(
        clerk_user_id=clerk_user_id,
        session_id=session_id,
        claims=claims,
    )


async def get_test_user() -> AuthenticatedUser:
    """
    Test user for development/testing environments.
    Only used when ENABLE_TEST_AUTH=true in environment.
    """
    logger.warning("Using test authentication - ONLY for development/testing!")
    return AuthenticatedUser(
        clerk_user_id="test_user_dev",
        session_id="test_session_dev",
        claims={
            "sub": "test_user_dev",
            "sid": "test_session_dev",
            "test_mode": True,
        },
    )
