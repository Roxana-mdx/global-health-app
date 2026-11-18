"""Presentation: the two action buttons. POST, because they change something."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.controllers.templating import templates
from app.dependencies import get_etl_service
from app.services.etl_service import EtlService
from etl.step_result import StepResult

router = APIRouter(prefix="/actions")


def _render_step_results(
    request: Request, *, action: str, description: str, results: list[StepResult]
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "action_result.html",
        {
            "action": action,
            "description": description,
            "results": results,
            "failed": sum(1 for result in results if result.is_failed),
        },
    )


@router.post("/extract", response_class=HTMLResponse)
def extract(
    request: Request, service: Annotated[EtlService, Depends(get_etl_service)]
) -> HTMLResponse:
    return _render_step_results(
        request,
        action="Extract",
        description="Downloaded the World Bank data into data/raw/ and checked the IHME file.",
        results=service.extract_all(),
    )


@router.post("/load", response_class=HTMLResponse)
def transform_and_load(
    request: Request, service: Annotated[EtlService, Depends(get_etl_service)]
) -> HTMLResponse:
    return _render_step_results(
        request,
        action="Transform & Load",
        description="Transformed the saved raw files, cleaned them and loaded them into the database.",
        results=service.transform_and_load_all(),
    )