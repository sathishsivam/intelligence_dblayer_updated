from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .security import (
    hash_password,
    verify_password,
    decode_access_token,
)


# ---------------------------------------------------------------------------
# HTTP Bearer authentication
# ---------------------------------------------------------------------------

security = HTTPBearer(
    auto_error=False,
)


# ---------------------------------------------------------------------------
# Temporary development user repository
# ---------------------------------------------------------------------------
#
# This is ONLY for the current local authentication implementation.
#
# Username:
#     admin
#
# Password:
#     admin123
#
# Later this repository can be replaced with the actual dashboard/account
# user repository without changing the orchestration policy layer.
# ---------------------------------------------------------------------------

_USERS = {
    "admin": {
        "username": "admin",
        "display_name": "Administrator",
        "password_hash": hash_password("admin123"),
    }
}


# ---------------------------------------------------------------------------
# User lookup
# ---------------------------------------------------------------------------

def get_user(username: str):
    """
    Return a user by username.

    Returns None when the user does not exist.
    """

    return _USERS.get(username)


# ---------------------------------------------------------------------------
# Password authentication
# ---------------------------------------------------------------------------

def authenticate_user(
    username: str,
    password: str,
):
    """
    Authenticate username/password.

    Returns the user when authentication succeeds.
    Returns None when authentication fails.
    """

    user = get_user(username)

    if user is None:
        return None

    if not verify_password(
        password,
        user["password_hash"],
    ):
        return None

    return user


# ---------------------------------------------------------------------------
# JWT → authenticated user
# ---------------------------------------------------------------------------

def _resolve_user_from_token(
    token: str,
):
    """
    Decode a JWT and resolve the corresponding application user.
    """

    try:
        payload = decode_access_token(token)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    username = payload.get("sub")

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token does not contain a user.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    user = get_user(username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return user


# ---------------------------------------------------------------------------
# Required authentication
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Require a valid Bearer token.

    Used by endpoints where authentication is mandatory.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return _resolve_user_from_token(
        credentials.credentials
    )


# ---------------------------------------------------------------------------
# Optional authentication
# ---------------------------------------------------------------------------

def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Resolve the current user when a Bearer token is supplied.

    No Authorization header:
        returns None.

    Valid Authorization header:
        returns the authenticated user.

    Invalid/expired Authorization header:
        returns HTTP 401.

    This is required for orchestration because an unauthenticated
    request must reach the PolicyEngine so that it can return:

        requires_authentication = true
    """

    if credentials is None:
        return None

    return _resolve_user_from_token(
        credentials.credentials
    )
