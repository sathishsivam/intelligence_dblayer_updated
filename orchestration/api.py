from fastapi import APIRouter, Depends

from .models.request import (
    ConfirmationRequest,
    OrchestrationRequest,
)
from .models.response import OrchestrationResponse
from .service import OrchestrationService

from ..auth.service import get_optional_current_user


router = APIRouter(
    prefix="/orchestration",
    tags=["Orchestration"],
)

orchestration_service = OrchestrationService()


def build_user_context(current_user) -> dict:
    """
    Build trusted user context from the authenticated user.

    Security-sensitive authentication information must come
    from the server-side authenticated identity, not from the
    Flutter request body.
    """

    if current_user is None:
        return {}

    return {
        "authenticated": True,
        "username": current_user["username"],
        "display_name": current_user["display_name"],
    }


@router.post(
    "/execute",
    response_model=OrchestrationResponse,
)
async def execute_orchestration(
    request: OrchestrationRequest,
    current_user=Depends(get_optional_current_user),
) -> OrchestrationResponse:
    """
    Execute an orchestration request.

    Authentication is optional at the API boundary.

    This is intentional because the orchestration policy engine
    must be able to determine whether the requested operation
    requires authentication and return:

        requires_authentication=True

    to the Workspace when the user is not authenticated.

    If a valid JWT is supplied, the authenticated dashboard
    user's identity is injected into user_context.
    """

    request.user_context = build_user_context(current_user)

    return await orchestration_service.process(request)


@router.post(
    "/confirm",
    response_model=OrchestrationResponse,
)
async def confirm_orchestration(
    request: ConfirmationRequest,
    current_user=Depends(get_optional_current_user),
) -> OrchestrationResponse:
    """
    Confirm a previously prepared orchestration action.

    The authenticated identity is always derived from the
    server-side JWT rather than trusting user_context supplied
    by Flutter.
    """

    user_context = build_user_context(current_user)

    return await orchestration_service.confirm(
        confirmation_id=request.confirmation_id,
        session_id=request.session_id,
        user_context=user_context,
    )