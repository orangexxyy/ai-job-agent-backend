import re
from typing import Any, Optional, Tuple

from app.schemas.agent_loop_schema import AgentLoopSimulateRequest
from app.schemas.auto_reply_schema import (
    AutoReplySimulationRequest,
    AutoReplySimulationResult,
)
from app.services.agent_loop_service import simulate_agent_loop
from app.services.profile_service import get_candidate_profile


CONFIRMATION_INTENTS = {
    "salary_or_benefits",
    "outsourcing_or_onsite",
    "overtime_or_work_schedule",
    "privacy_or_documents",
    "reject_or_close",
}


def simulate_supervised_auto_reply(
    request: AutoReplySimulationRequest,
) -> AutoReplySimulationResult:
    """模拟低风险 HR 回复候选生成。

    主要输入：application_id、HR message、可选上下文和 slot preview 数量。
    主要输出：Step 20 决策、回复策略、可选 reply_candidate 与安全说明。
    副作用：只读 SQLite；不调用 LLM，不写 application / action_history，不 book slot，
    不发送 HR 消息，不投递，也不执行招聘平台操作。
    """
    loop = simulate_agent_loop(
        AgentLoopSimulateRequest(
            application_id=request.application_id,
            hr_message=request.hr_message,
            context_note=request.context_note,
            max_available_slots=request.max_available_slots,
        )
    )
    profile = get_candidate_profile()
    strategy, candidate, blocked_reason = _build_reply(loop, profile)
    reply_available = bool(candidate)
    requires_user_confirmation = (
        loop.requires_user_confirmation or loop.detected_intent in CONFIRMATION_INTENTS
    )
    return AutoReplySimulationResult(
        application_id=request.application_id,
        hr_message=request.hr_message,
        detected_intent=loop.detected_intent,
        proposed_action_type=loop.proposed_action_type,
        agent_loop_decision=loop.agent_loop_decision,
        risk_level=loop.policy.risk_level,
        policy_decision=loop.policy.policy_decision,
        reply_strategy=strategy,
        reply_candidate=candidate,
        reply_available=reply_available,
        requires_user_confirmation=requires_user_confirmation,
        requires_user_notification=(
            loop.requires_user_notification or requires_user_confirmation
        ),
        external_action_allowed=False,
        blocked_reason=blocked_reason,
        safety_notes=[
            "reply_candidate 仅供用户审核，不会自动发送。",
            "不会修改 application、写 action_history 或 book slot。",
            "候选回复使用规则模板，不调用 LLM。",
        ],
        debug={
            "step20_agent_loop_reused": True,
            "candidate_profile_loaded": profile is not None,
            "auto_send_message": False,
            "auto_apply": False,
            "auto_confirm_interview": False,
            "attachment_uploaded": False,
            "platform_login_performed": False,
            "captcha_handled": False,
            "database_write_performed": False,
            "application_updated": False,
            "action_history_written": False,
            "slot_booked": False,
            "llm_used": False,
            "external_action_allowed": False,
            "simulation_version": "21-rule-v1",
        },
    )


def _build_reply(loop: Any, profile: Any) -> Tuple[str, Optional[str], Optional[str]]:
    intent = loop.detected_intent
    if loop.agent_loop_decision == "block_action":
        reason = "该请求涉及被禁止的平台自动化、验证码或外部执行动作。"
        return "blocked", None, reason
    if loop.requires_user_confirmation or intent in CONFIRMATION_INTENTS:
        reason = "该场景涉及现实承诺、敏感材料或候选人偏好，需要用户先确认。"
        return "user_confirmation_required", None, reason
    if intent == "ask_project_experience":
        return "project_experience_summary", _project_reply(profile), None
    if intent == "ask_education_or_basic_info":
        return "education_basic_info", _education_reply(profile), None
    if intent == "ask_resume_or_project_link":
        return "resume_or_project_link", (
            "可以，我可以提供简历和项目介绍供您参考。具体文件或链接会由我确认后手动发送。"
        ), None
    if intent == "schedule_interview":
        if loop.agent_loop_decision == "propose_slots_with_notification" and loop.available_slots_preview:
            slots = "；".join(
                f"{item['date']} {item['start_time']}-{item['end_time']}（{item['timezone']}）"
                for item in loop.available_slots_preview
            )
            return "interview_slots_proposal", (
                f"您好，以下时间我目前比较方便：{slots}。请您看看哪个时间合适，最终时间以双方确认后为准。"
            ), None
        return "user_confirmation_required", None, "当前没有可安全提出的 available 面试时间。"
    if intent == "general_followup":
        return "general_followup", "您好，我目前仍在关注合适的机会，方便进一步沟通岗位情况。", None
    return "unsupported", None, "当前规则模板不支持为该意图生成候选回复。"


def _project_reply(profile: Any) -> str:
    if profile is None:
        return "您好，我做过 Python、FastAPI 相关 AI 应用项目；具体项目能力需要以简历事实为准进一步说明。"
    project_names = "、".join(profile.available_projects[:2])
    context = _compact_excerpt(profile.project_context, ("RAG", "FastAPI", "Agent"), 260)
    details = context or "项目事实以 candidate_profile 中的 project_context 为准"
    prefix = (
        f"我做过的项目主要包括{project_names}。"
        if project_names
        else "我做过 AI 应用开发相关项目。"
    )
    return f"{prefix}{details}。相关能力可以结合具体岗位继续介绍，但不会把未实现规划表述为已有经验。"


def _education_reply(profile: Any) -> str:
    if profile is None:
        return "您好，学历、专业和工作年限需要以我的真实简历为准，我可以按您关注的项目逐项说明。"
    resume_text = profile.resume_text or ""
    education_level = _extract_education_level(resume_text)
    major = _extract_major(resume_text)
    target_role = _extract_target_role(resume_text, profile.target_roles)
    facts = []
    if education_level:
        facts.append(f"我是{education_level}学历")
    if major:
        facts.append(f"专业是{major}")
    if target_role:
        facts.append(f"目前求职方向是{target_role}")
    if facts:
        return f"您好，{'，'.join(facts)}。"
    return "您好，当前 candidate_profile 中没有可直接确认的学历、专业或工作年限信息，需要以真实简历为准。"


def _extract_education_level(resume_text: str) -> Optional[str]:
    levels = ("博士", "研究生", "硕士", "本科", "大专", "专科")
    return next((level for level in levels if level in resume_text), None)


def _extract_major(resume_text: str) -> Optional[str]:
    explicit = re.search(
        r"专业\s*(?:是|为|：|:)\s*([^，,。；;\n]{2,30})",
        resume_text,
    )
    if explicit:
        return explicit.group(1).strip()
    suffix = re.search(
        r"([A-Za-z0-9+#/\-\u4e00-\u9fff]{2,30})专业",
        resume_text,
    )
    return suffix.group(1).strip() if suffix else None


def _extract_target_role(resume_text: str, target_roles: Any) -> Optional[str]:
    matched = re.search(
        r"求职方向\s*(?:为|是|：|:)?\s*([^，,。；;\n]{2,50})",
        resume_text,
    )
    if matched:
        return matched.group(1).strip()
    return target_roles[0].strip() if target_roles else None


def _compact_excerpt(text: str, keywords: Tuple[str, ...], limit: int) -> str:
    parts = [part.strip() for part in re.split(r"[\r\n。；]+", text or "") if part.strip()]
    selected = [part for part in parts if any(keyword.lower() in part.lower() for keyword in keywords)]
    return "；".join(selected)[:limit].rstrip("；，, ")
