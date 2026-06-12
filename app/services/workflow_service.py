from typing import Any, Dict, List, Optional

from app.services.application_service import get_application
from app.services.hr_intent_service import analyze_hr_message
from app.services.hr_reply_service import generate_hr_reply
from app.services.job_match_service import analyze_job_match
from app.services.profile_service import get_candidate_profile


def run_workflow_preview(
    application_id: int,
    hr_message: Optional[str] = None,
) -> Dict[str, Any]:
    """运行规则版 workflow_preview，串联现有 service 形成只读预览。

    主要输入：application_id，以及可选 HR message。
    主要输出：workflow_steps、state_summary、job_match、可选 hr_intent / hr_reply 和 Human-in-the-loop 审批状态。
    副作用：只读 SQLite，不写 application，不调用 LLM / RAG / LangGraph / Playwright，不自动投递，不自动发送 HR 消息。
    """
    workflow_steps: List[Dict[str, str]] = []

    profile = get_candidate_profile()
    if profile is None:
        raise ValueError("candidate_profile not found")
    _add_step(
        workflow_steps,
        "load_candidate_profile",
        "completed",
        "已读取 candidate_profile，作为岗位匹配和回复草稿的求职者上下文。",
    )

    application = get_application(application_id)
    if application is None:
        raise ValueError("application not found")
    _add_step(
        workflow_steps,
        "load_application",
        "completed",
        "已读取 application，作为本次 workflow_preview 的投递上下文。",
    )

    job_match = analyze_job_match(
        application_id=application_id,
        update_application=False,
    )
    _add_step(
        workflow_steps,
        "run_job_match",
        "completed",
        "已复用 /job_match 规则评分能力，但未回写 application。",
    )

    hr_intent = None
    hr_reply = None
    if hr_message:
        hr_intent = analyze_hr_message(
            message=hr_message,
            company_name=application.company_name,
            job_title=application.job_title,
        )
        _add_step(
            workflow_steps,
            "analyze_hr_intent",
            "completed",
            "已复用规则版 HR Intent Analyzer 分析 HR message。",
        )

        hr_reply = generate_hr_reply(
            message=hr_message,
            application_id=application_id,
            company_name="",
            job_title="",
            extra_context="",
            update_application=False,
        )
        if hr_reply is None:
            raise ValueError("candidate_profile not found")
        _add_step(
            workflow_steps,
            "generate_reply_draft",
            "completed",
            "已生成 Human-in-the-loop 回复草稿，但未更新 application，也未发送消息。",
        )
    else:
        _add_step(
            workflow_steps,
            "analyze_hr_intent",
            "skipped",
            "未传入 HR message，跳过 HR intent 分析。",
        )
        _add_step(
            workflow_steps,
            "generate_reply_draft",
            "skipped",
            "未传入 HR message，跳过 HR 回复草稿生成。",
        )

    _add_step(
        workflow_steps,
        "require_user_approval",
        "waiting",
        "等待用户人工确认；系统不会自动投递、发送 HR 消息或确认面试时间。",
    )

    primary_intent = hr_intent.get("primary_intent") if hr_intent else None
    reply_draft_generated = bool(hr_reply and hr_reply.get("reply_draft"))
    next_action = _select_next_action(job_match, hr_reply)

    return {
        "workflow_mode": "rule_based_preview",
        "application_id": application.id,
        "company_name": application.company_name,
        "job_title": application.job_title,
        "workflow_steps": workflow_steps,
        "state_summary": {
            "has_candidate_profile": True,
            "has_application": True,
            "has_hr_message": bool(hr_message),
            "match_level": job_match.get("match_level"),
            "primary_intent": primary_intent,
            "reply_draft_generated": reply_draft_generated,
        },
        "job_match": job_match,
        "hr_intent": hr_intent,
        "hr_reply": hr_reply,
        "approval_required": True,
        "approved_by_user": False,
        "next_action": next_action,
        "debug": {
            "llm_used": False,
            "langgraph_used": False,
            "rag_used": False,
            "playwright_used": False,
            "auto_apply": False,
            "auto_send_message": False,
            "auto_confirm_interview": False,
            "database_write_intended": False,
            "workflow_engine": "plain_python_rules",
        },
    }


def _add_step(
    workflow_steps: List[Dict[str, str]],
    name: str,
    status: str,
    summary: str,
) -> None:
    workflow_steps.append(
        {
            "name": name,
            "status": status,
            "summary": summary,
        }
    )


def _select_next_action(
    job_match: Dict[str, Any],
    hr_reply: Optional[Dict[str, Any]],
) -> str:
    if hr_reply and hr_reply.get("suggested_followup"):
        return str(hr_reply["suggested_followup"])
    if job_match.get("suggested_next_action"):
        return str(job_match["suggested_next_action"])
    return "请用户查看 workflow_preview 后决定下一步动作。"
