from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="健康检查 / Health check",
    description="检查 FastAPI 服务是否可用。 / Check whether the FastAPI service is available.",
)
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai_job_agent"}
