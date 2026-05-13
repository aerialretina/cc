"""FastAPI application entrypoint.

Exposes the v1 endpoints described in §5.1 of the build plan.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lip import __version__
from lip.api.routes import (
    admin,
    compensation,
    labor_supply,
    mobility,
    organizations,
    persons,
    postings,
    projects,
)
from lip.logging import configure_logging
from lip.ui.router import router as ui_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield


app = FastAPI(
    title="Labor Intelligence Platform API",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


app.include_router(postings.router, prefix="/v1/postings", tags=["postings"])
app.include_router(compensation.router, prefix="/v1/compensation", tags=["compensation"])
app.include_router(labor_supply.router, prefix="/v1/labor-supply", tags=["labor-supply"])
app.include_router(mobility.router, prefix="/v1/mobility", tags=["mobility"])
app.include_router(organizations.router, prefix="/v1/organizations", tags=["organizations"])
app.include_router(projects.router, prefix="/v1/projects", tags=["projects"])
app.include_router(persons.router, prefix="/v1/persons", tags=["persons"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

# Plaintext front end mounted at /. Routes live under "/" and "/ui/*".
app.include_router(ui_router)
