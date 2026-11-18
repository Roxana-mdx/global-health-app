"""The one place that knows how to build each service (dependency injection)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.observation_repository import ObservationRepository
from app.services.etl_service import EtlService
from app.services.observation_service import ObservationService


def get_observation_service(
    session: Annotated[Session, Depends(get_db)],
) -> ObservationService:
    """get_db opens a session, the repository receives it, the service receives the repository."""
    return ObservationService(ObservationRepository(session))


def get_etl_service() -> EtlService:
    return EtlService()