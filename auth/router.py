
from fastapi import APIRouter, HTTPException

from .models import (
    LoginRequest,
    LoginResponse,
)
from .service import authenticate_user
from .security import create_access_token


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    request: LoginRequest,
):

    user = authenticate_user(
        username=request.username,
        password=request.password,
    )

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_access_token(
        username=user["username"],
        display_name=user["display_name"],
    )

    return LoginResponse(
        access_token=token,
        username=user["username"],
        display_name=user["display_name"],
    )
