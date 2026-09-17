"""Authentication boundary for athlete-scoped API requests.

The gateway accepts an HS256 bearer JWT only after the deployment has supplied
``JWT_SECRET_KEY``.  Athlete identity comes from the verified ``sub`` claim;
the client never selects the database user to read.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


logger = logging.getLogger(__name__)
athlete_bearer = HTTPBearer(auto_error=False, scheme_name="athleteBearer")


@dataclass(frozen=True)
class AuthenticatedAthlete:
    """The only athlete identity permitted to reach data retrieval."""

    athlete_id: int


def _authentication_config() -> tuple[str, str | None, str | None]:
    """Read configuration without ever logging a credential value."""

    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        logger.error("JWT authentication is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured",
        )
    return secret, os.getenv("JWT_ISSUER") or None, os.getenv("JWT_AUDIENCE") or None


def _athlete_id_from_claims(claims: dict[str, Any]) -> int:
    subject = claims.get("sub")
    if isinstance(subject, bool):
        raise ValueError("JWT subject must be a positive integer")
    try:
        athlete_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise ValueError("JWT subject must be a positive integer") from exc
    if athlete_id <= 0:
        raise ValueError("JWT subject must be a positive integer")
    return athlete_id


async def require_authenticated_athlete(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(athlete_bearer)],
) -> AuthenticatedAthlete:
    """Verify a short-lived bearer token and return its athlete-scoped subject."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    secret, issuer, audience = _authentication_config()
    decode_kwargs: dict[str, Any] = {
        "algorithms": ["HS256"],
        "options": {"require": ["sub", "exp"]},
    }
    if issuer:
        decode_kwargs["issuer"] = issuer
    if audience:
        decode_kwargs["audience"] = audience

    try:
        claims = jwt.decode(credentials.credentials, secret, **decode_kwargs)
        athlete_id = _athlete_id_from_claims(claims)
    except (jwt.InvalidTokenError, ValueError) as exc:
        logger.warning("Rejected invalid athlete bearer token: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return AuthenticatedAthlete(athlete_id=athlete_id)


def require_matching_athlete_id(requested_athlete_id: int | None, actor: AuthenticatedAthlete) -> int:
    """Allow a legacy body ID only as a checked assertion during client migration."""

    if requested_athlete_id is not None and requested_athlete_id != actor.athlete_id:
        logger.warning("Rejected athlete-ID mismatch for authenticated request")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requested athlete does not match the authenticated athlete",
        )
    return actor.athlete_id
