import re
from typing import Any, Dict, List, Optional

from app.schemas.application_schema import ApplicationItem, ApplicationUpdateRequest
from app.schemas.profile_schema import CandidateProfile
from app.services.application_service import get_application, update_application
from app.services.context_reply_service import (
    PROJECT_CONTEXT_INTENTS,
    build_context_enhanced_reply,
    context_sources,
    select_relevant_context_snippets,
)
from app.services.hr_intent_service import analyze_hr_message
from app.services.profile_service import get_candidate_profile
from app.services.truth_boundary_service import check_truth_boundary


HIGH_RISK_INTENTS = {
    "project_experience",
    "technical_question",
    "business_proposal",
}


def generate_hr_reply(
    message: str,
    application_id: Optional[int] = None,
    company_name: Optional[str] = None,
    job_title: Optional[str] = None,
    extra_context: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """生成 Human-in-the-loop 的 HR 回复草稿。

    主要输入：HR message、可选 application_id、公司/岗位上下文和 extra_context。
    主要输出：回复草稿数据；candidate_profile 缺失时返回 None。
    副作用：可能更新 application 的 last_hr_message 和 next_action；不自动发送 HR 消息，不自动投递，不调用 LLM。
    """
    application = None
    application_context = None
    effective_company_name = company_name
    effective_job_title = job_title

    if application_id is not None:
        application = get_application(application_id)
        if application is None:
            raise ValueError("application not found")
        application_context = _build_application_context(application)
        effective_company_name = application.company_name or company_name
        effective_job_title = application.job_title or job_title

    analysis = analyze_hr_message(message, effective_company_name, effective_job_title)
    profile = get_candidate_profile()
    if profile is None:
        return None

    has_context_intent = any(
        intent in PROJECT_CONTEXT_INTENTS for intent in analysis["intents"]
    )
    selected_context_snippets: List[Dict[str, Any]] = []
    context_used: List[str] = []
    context_reply_mode = "template_only"
    if has_context_intent:
        selected_context_snippets = select_relevant_context_snippets(
            message=message,
            resume_text=profile.resume_text,
            project_context=profile.project_context,
            available_projects=profile.available_projects,
        )
        context_used = context_sources(selected_context_snippets)
        context_reply_mode = (
            "profile_context_enhanced"
            if selected_context_snippets
            else "profile_context_missing"
        )

    reply_parts: List[str] = []
    used_sources = [
        "candidate_profile",
        "hr_intent_rules",
        "truth_boundary_rules",
    ]
    if application_context is not None:
        used_sources.append("application_context")

    rendered_high_risk = False
    for intent in analysis["intents"]:
        if intent in HIGH_RISK_INTENTS:
            if rendered_high_risk:
                continue
            rendered_high_risk = True
            part = build_context_enhanced_reply(
                intent=intent,
                snippets=selected_context_snippets,
                truth_boundaries=profile.truth_boundaries,
            )
        else:
            part = _render_intent_reply(intent, profile)
        if part:
            reply_parts.append(part)

    if extra_context:
        reply_parts.append(f"补充说明：{extra_context}")

    reply_draft = _combine_reply_parts(reply_parts)
    reply_draft = _add_application_reply_prefix(reply_draft, application_context)
    truth_result = check_truth_boundary(reply_draft, profile)
    has_high_risk_intent = any(intent in HIGH_RISK_INTENTS for intent in analysis["intents"])
    has_unknown_intent = "unknown" in analysis["intents"]
    missing_required_profile_data = _has_missing_required_profile_data(
        analysis["intents"], profile
    )

    safe_to_send = bool(truth_result["safe_to_send"])
    if has_high_risk_intent or has_unknown_intent or missing_required_profile_data:
        safe_to_send = False

    if analysis["need_resume_context"]:
        used_sources.append("resume_text")
    if analysis["need_project_context"]:
        used_sources.append("project_context")

    application_update_fields: Dict[str, Any] = {}
    application_updated = False
    if application is not None:
        application_update_fields = {
            "last_hr_message": message,
            "next_action": _next_action_for_intent(analysis["primary_intent"]),
        }
        application_updated = _update_application_after_reply(
            application.id,
            application_update_fields,
        )

    suggested_followup = _build_suggested_followup(
        analysis["intents"],
        truth_result["suggested_revision"],
        missing_required_profile_data,
    )
    if has_context_intent and not selected_context_snippets:
        suggested_followup = "请先补充 resume_text / project_context 后再生成项目经历或技术方案类回复。"
    elif has_context_intent:
        suggested_followup = "请用户确认项目上下文和 truth boundary 后再发送。"

    return {
        "original_message": message,
        "application_id": application_id,
        "application_context": application_context,
        "application_updated": application_updated,
        "application_update_fields": application_update_fields,
        "company_name": effective_company_name,
        "job_title": effective_job_title,
        "intents": analysis["intents"],
        "primary_intent": analysis["primary_intent"],
        "reply_draft": reply_draft,
        "safe_to_send": safe_to_send,
        "used_sources": _dedupe(used_sources),
        "context_used": context_used,
        "selected_context_snippets": selected_context_snippets,
        "context_reply_mode": context_reply_mode,
        "truth_boundary": _build_truth_boundary_notes(
            truth_result["risk_points"], missing_required_profile_data
        ),
        "cannot_claim": truth_result["cannot_claim"],
        "risk_level": "high" if has_high_risk_intent else analysis["risk_level"],
        "suggested_followup": suggested_followup,
        "agent_steps": [
            "Received HR message.",
            "Analyzed HR message with rule-based intent analyzer.",
            "Loaded candidate_profile from SQLite.",
            "Selected profile-based reply templates by intents.",
            "Generated reply draft for human approval.",
            "Applied truth boundary rule checks.",
            "Returned reply draft without sending.",
        ],
        "debug": {
            "need_profile": analysis["need_profile"],
            "need_resume_context": analysis["need_resume_context"],
            "need_project_context": analysis["need_project_context"],
            "need_application_history": analysis["need_application_history"],
            "need_llm": analysis["need_llm"],
            "matched_keywords": analysis["matched_keywords"],
            "application_update_error": not application_updated
            if application is not None
            else False,
        },
    }


def _build_application_context(application: ApplicationItem) -> Dict[str, Any]:
    return {
        "id": application.id,
        "company_name": application.company_name,
        "job_title": application.job_title,
        "status": application.status,
        "job_source": application.job_source,
        "job_url": application.job_url,
        "next_action": application.next_action,
        "last_hr_message": application.last_hr_message,
        "jd_text_preview": (application.jd_text or "")[:120],
        "notes": application.notes,
        "risk_flags": application.risk_flags,
    }


def _add_application_reply_prefix(
    reply_draft: str,
    application_context: Optional[Dict[str, Any]],
) -> str:
    if not application_context:
        return reply_draft
    company_name = application_context.get("company_name") or "当前公司"
    job_title = application_context.get("job_title") or "当前岗位"
    return f"针对「{company_name}」的「{job_title}」岗位，{reply_draft}"


def _next_action_for_intent(primary_intent: str) -> str:
    next_actions = {
        "interview_schedule": "确认面试时间",
        "resume_request": "确认并发送简历",
        "github_request": "确认 GitHub 链接后发送",
        "project_experience": "准备项目经历回复",
        "technical_question": "准备技术问题回复",
        "business_proposal": "准备业务方案回复",
        "salary_expectation": "确认薪资回复",
        "availability": "确认到岗时间回复",
        "relocation": "确认异地/外地接受度",
        "outsourcing": "确认外包岗位接受度",
        "unknown": "请用户补充 HR 问题背景",
    }
    return next_actions.get(primary_intent, "请用户补充 HR 问题背景")


def _update_application_after_reply(
    application_id: int,
    update_fields: Dict[str, Any],
) -> bool:
    try:
        updated = update_application(
            application_id,
            ApplicationUpdateRequest(**update_fields),
        )
    except Exception:
        return False
    return updated is not None


def _render_intent_reply(intent: str, profile: CandidateProfile) -> str:
    renderers = {
        "salary_expectation": _salary_reply,
        "availability": _availability_reply,
        "location_preference": _location_reply,
        "relocation": lambda p: p.relocation_policy,
        "outsourcing": lambda p: p.outsourcing_policy,
        "onsite": lambda p: p.onsite_policy,
        "remote": lambda p: p.remote_policy,
        "overtime": lambda p: p.overtime_policy,
        "business_trip": lambda p: p.business_trip_policy,
        "interview_schedule": _interview_schedule_reply,
        "resume_request": _resume_request_reply,
        "github_request": _github_request_reply,
        "project_experience": _high_risk_context_reply,
        "technical_question": _high_risk_context_reply,
        "business_proposal": _high_risk_context_reply,
        "unknown": _unknown_reply,
    }
    renderer = renderers.get(intent)
    if renderer is None:
        return ""
    return renderer(profile).strip()


def _salary_reply(profile: CandidateProfile) -> str:
    if profile.expected_salary_min and profile.expected_salary_max:
        salary = (
            f"我的期望薪资大概在 {profile.expected_salary_min // 1000}K-"
            f"{profile.expected_salary_max // 1000}K 区间"
        )
    elif profile.expected_salary_min:
        salary = f"我的期望薪资从 {profile.expected_salary_min // 1000}K 左右开始沟通"
    else:
        return "薪资部分我需要先补充 candidate_profile 后再给出更准确回复。"

    minimum = (
        f"，最低可接受薪资大概是 {profile.minimum_salary // 1000}K"
        if profile.minimum_salary
        else ""
    )
    note = f" {profile.salary_note}" if profile.salary_note else ""
    return (
        f"{salary}{minimum}，具体也会结合岗位职责、技术方向、薪资结构和后续面试情况综合沟通。"
        f"{note}"
    )


def _availability_reply(profile: CandidateProfile) -> str:
    if profile.availability_note:
        return f"到岗时间这边可以按目前安排沟通：{profile.availability_note}。"
    return "到岗时间我需要先补充 candidate_profile 后再给出更准确回复。"


def _location_reply(profile: CandidateProfile) -> str:
    preferred = "、".join(profile.preferred_cities)
    acceptable = "、".join(profile.acceptable_cities)
    parts = []
    if preferred:
        parts.append(f"我目前优先考虑 {preferred}")
    if profile.remote_policy:
        parts.append(f"远程/混合办公方面：{profile.remote_policy}")
    if acceptable:
        parts.append(f"其他城市也可以结合岗位匹配度进一步沟通：{acceptable}")
    return "。".join(parts) + "。" if parts else "城市偏好需要先补充 candidate_profile 后再回复。"


def _interview_schedule_reply(profile: CandidateProfile) -> str:
    return (
        "面试时间我这边需要确认一下具体安排，可以麻烦您先发一下可选时间段吗？"
        "我确认后尽快回复。"
    )


def _resume_request_reply(profile: CandidateProfile) -> str:
    return (
        "可以的，我稍后可以发您一份简历。也方便问一下这个岗位目前更看重 "
        "AI 应用开发、RAG 项目，还是 Agent / Workflow 相关经验？"
    )


def _github_request_reply(profile: CandidateProfile) -> str:
    urls = _extract_urls(profile.resume_text + "\n" + profile.project_context)
    if urls:
        return "可以的，我这边可以先发这些项目地址：" + "、".join(urls)
    projects = "、".join(profile.available_projects)
    if projects:
        return f"可以的，我稍后整理项目地址发您。主要项目包括 {projects}。"
    return "可以的，我稍后整理 GitHub 项目地址发您。"


def _high_risk_context_reply(profile: CandidateProfile) -> str:
    projects = "、".join(profile.available_projects)
    if not projects:
        projects = "用户已提供的真实项目经历"
    return (
        "这个问题涉及项目经历和技术方案，我需要结合自己的真实项目经历来回答。"
        f"目前可以基于 {projects} 这些内容展开，但完整回答建议后续接入 "
        "resume_text / project_context 或 LLM 后再生成，以避免夸大未实现能力。"
    )


def _unknown_reply(profile: CandidateProfile) -> str:
    return "这条消息的意图还不够明确，建议用户补充上下文后再生成回复。"


def _combine_reply_parts(reply_parts: List[str]) -> str:
    cleaned = [part.rstrip("。") for part in reply_parts if part.strip()]
    if not cleaned:
        return "这条消息暂时无法生成可靠回复草稿，建议用户补充上下文。"
    return "。".join(cleaned) + "。"


def _has_missing_required_profile_data(
    intents: List[str],
    profile: CandidateProfile,
) -> bool:
    checks = {
        "salary_expectation": bool(profile.expected_salary_min),
        "availability": bool(profile.availability_note),
        "location_preference": bool(profile.preferred_cities or profile.acceptable_cities),
    }
    return any(not checks[intent] for intent in intents if intent in checks)


def _build_truth_boundary_notes(
    risk_points: List[str],
    missing_required_profile_data: bool,
) -> List[str]:
    notes = ["Reply draft must be reviewed by the user before sending."]
    if risk_points:
        notes.append("Forbidden or high-risk claims detected: " + "、".join(risk_points))
    if missing_required_profile_data:
        notes.append("Required candidate_profile fields are missing for at least one intent.")
    return notes


def _build_suggested_followup(
    intents: List[str],
    suggested_revision: str,
    missing_required_profile_data: bool,
) -> str:
    if suggested_revision:
        return suggested_revision
    if missing_required_profile_data:
        return "Please complete candidate_profile before sending this reply."
    if "interview_schedule" in intents:
        return "面试时间需要用户最终确认。"
    if "resume_request" in intents:
        return "简历文件需要用户自己确认后发送。"
    if "github_request" in intents:
        return "GitHub 链接需要用户确认真实可公开后发送。"
    if any(intent in HIGH_RISK_INTENTS for intent in intents):
        return "This intent should be handled by future LLM/RAG-enhanced reply generation."
    if "unknown" in intents:
        return "Please clarify the HR message before drafting a reply."
    return "Please review and confirm before sending."


def _extract_urls(text: str) -> List[str]:
    return re.findall(r"https?://[^\s，。；;]+", text)


def _dedupe(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))
