
import os
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash

SECRET_KEY = os.getenv(
    "AIZILLON_AUTH_SECRET",
    "CHANGE_THIS_SECRET_IN_PRODUCTION",
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(
        password,
        hashed_password,
    )


def create_access_token(
    *,
    username: str,
    display_name: str,
) -> str:

    now = datetime.now(timezone.utc)

    payload = {
        "sub": username,
        "name": display_name,
        "iat": now,
        "exp": (
            now
            + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        ),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:

    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )
