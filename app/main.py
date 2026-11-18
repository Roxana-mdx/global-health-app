"""Create the application and include the routers. Nothing else."""
from fastapi import FastAPI

from app.controllers import etl_controller, observation_controller


def create_app() -> FastAPI:
    # No JSON API in this lab, so no OpenAPI schema or /docs pages either.
    app = FastAPI(
        title="Global Health Data Platform",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    app.include_router(observation_controller.router)
    app.include_router(etl_controller.router)
    return app


app = create_app()