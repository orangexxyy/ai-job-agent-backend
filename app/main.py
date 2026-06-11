from fastapi import FastAPI

from app.database import init_database
from app.routes import (
    application_routes,
    health_routes,
    hr_routes,
    job_match_routes,
    profile_routes,
)


app = FastAPI(
    title="AI Job Agent",
    description="Human-in-the-loop AI job search assistant MVP.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_database()


app.include_router(health_routes.router)
app.include_router(profile_routes.router)
app.include_router(hr_routes.router)
app.include_router(application_routes.router)
app.include_router(job_match_routes.router)
