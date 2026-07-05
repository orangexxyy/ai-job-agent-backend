from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_database
from app.routes import (
    agent_routes,
    agent_loop_routes,
    auto_reply_routes,
    application_review_routes,
    application_routes,
    automation_policy_routes,
    health_routes,
    hr_routes,
    interview_availability_routes,
    job_match_routes,
    profile_routes,
    profile_draft_routes,
    reply_send_gate_routes,
)


OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "健康检查 / Service health check",
    },
    {
        "name": "profile",
        "description": "候选人档案 / Candidate Profile",
    },
    {
        "name": "profile_draft",
        "description": "本地候选人画像草稿审核 / Local Profile Draft Review",
    },
    {
        "name": "applications",
        "description": "投递记录与用户确认后的状态更新 / Applications and user-confirmed state updates",
    },
    {
        "name": "application_review",
        "description": "岗位复盘与当前主流程 HR 回复草稿 / Application Review & HR Reply",
    },
    {
        "name": "interview_availability_slots",
        "description": "面试可用时间管理 / Interview Availability",
    },
    {
        "name": "agent",
        "description": "Agent 工作流预览 / Agent Workflow Preview",
    },
    {
        "name": "hr",
        "description": "旧版 HR 接口，保留兼容 / Legacy HR Interfaces",
    },
    {
        "name": "job_match",
        "description": "规则版岗位匹配 / Job Match",
    },
]


app = FastAPI(
    title="AI Job Agent",
    description="Human-in-the-loop AI job search assistant MVP.",
    version="0.1.0",
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["null", "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_database()


app.include_router(health_routes.router)
app.include_router(profile_routes.router)
app.include_router(profile_draft_routes.router)
app.include_router(hr_routes.router)
app.include_router(application_routes.router)
app.include_router(automation_policy_routes.router)
app.include_router(application_review_routes.router)
app.include_router(job_match_routes.router)
app.include_router(agent_routes.router)
app.include_router(agent_loop_routes.router)
app.include_router(auto_reply_routes.router)
app.include_router(reply_send_gate_routes.router)
app.include_router(interview_availability_routes.router)
