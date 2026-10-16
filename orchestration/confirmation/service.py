from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import uuid4

from .models import PendingConfirmation


class ConfirmationService:
    """
    Development-time transaction-bound confirmation store.

    This intentionally uses in-memory storage.

    Production:
        Replace this with Redis/database-backed storage.
    """

    DEFAULT_EXPIRY_SECONDS = 300

    def __init__(
        self,
        expiry_seconds: int = DEFAULT_EXPIRY_SECONDS,
    ):
        self.expiry_seconds = expiry_seconds

        self._store: dict[
            str,
            PendingConfirmation,
        ] = {}

        self._lock = Lock()

    def create(
        self,
        *,
        session_id: str | None,
        intent: str,
        capability_name: str,
        arguments: dict,
    ) -> PendingConfirmation:

        now = datetime.now(timezone.utc)

        confirmation = PendingConfirmation(
            confirmation_id=str(uuid4()),
            session_id=session_id,
            intent=intent,
            capability_name=capability_name,
            arguments=dict(arguments),
            created_at=now,
            expires_at=(
                now
                + timedelta(
                    seconds=self.expiry_seconds
                )
            ),
            status="PENDING",
        )

        with self._lock:
            self._store[
                confirmation.confirmation_id
            ] = confirmation

        return confirmation

    def get(
        self,
        confirmation_id: str,
    ) -> PendingConfirmation | None:

        with self._lock:
            confirmation = self._store.get(
                confirmation_id
            )

        if confirmation is None:
            return None

        if self._is_expired(confirmation):
            self._mark_expired(
                confirmation_id
            )
            return None

        return confirmation

    def consume(
        self,
        *,
        confirmation_id: str,
        session_id: str | None,
    ) -> PendingConfirmation | None:

        with self._lock:

            confirmation = self._store.get(
                confirmation_id
            )

            if confirmation is None:
                return None

            if confirmation.status != "PENDING":
                return None

            if self._is_expired(confirmation):
                confirmation.status = "EXPIRED"
                return None

            if confirmation.session_id != session_id:
                return None

            confirmation.status = "CONSUMED"

            return confirmation

    def _is_expired(
        self,
        confirmation: PendingConfirmation,
    ) -> bool:

        return (
            datetime.now(timezone.utc)
            >= confirmation.expires_at
        )

    def _mark_expired(
        self,
        confirmation_id: str,
    ) -> None:

        with self._lock:

            confirmation = self._store.get(
                confirmation_id
            )

            if confirmation is not None:
                confirmation.status = "EXPIRED"