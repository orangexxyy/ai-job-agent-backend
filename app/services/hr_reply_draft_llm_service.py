import json
from typing import Any, Dict, List, Optional

from fastapi.encoders import jsonable_encoder

from app.config import settings
from app.services.application_review_service import review_application
from app.services.application_service import get_application
from app.services.llm_service import llm_service
from app.services.profile_service import get_candidate_profile


VALID_DRAFT_TONES = {"professional", "concise", "cautious"}
DRAFT_TYPES = {
    "confirm_details",
    "project_intro",
    "interview_schedule",
    "salary_expectation",
    "polite_decline",
    "general_follow_up",
}


def generate_hr_reply_draft_from_review(
    application_id: int,
    hr_message: Optional[str] = None,
    draft_tone: str = "professional",
    include_raw_prompt: bool = False,
) -> Dict[str, Any]:
    """基于规则 review 一次性生成回复策略和 HR 回复草稿。

    主要输入：application_id、可选 HR message、draft_tone 和调试开关。
    主要输出：reply_strategy_for_user、hr_reply_draft、draft_type、LLM 状态和安全 debug 字段。
    副作用：可能调用一次外部 LLM；不调用 Step 14；不写数据库，不发送 HR 消息，不自动投递，不修改 application。
    """
    normalized_tone = draft_tone if draft_tone in VALID_DRAFT_TONES else "professional"
    rule_review = jsonable_encoder(
        review_application(
            application_id=application_id,
            hr_message=hr_message,
            update_application=False,
        )
    )
    application = get_application(application_id)
    if application is None:
        raise ValueError("application not found")
    profile = get_candidate_profile()

    context = {
        "rule_review": rule_review,
        "application": jsonable_encoder(application),
        "candidate_profile": jsonable_encoder(profile) if profile else None,
        "hr_message": hr_message,
    }
    draft_type = resolve_draft_type(rule_review, application.status)
    fallback = _fallback_result(
        draft_type=draft_type,
        rule_review=rule_review,
        llm_error="api_key_missing" if not settings.deepseek_api_key else None,
    )

    messages = build_prompt_by_draft_type(
        draft_type=draft_type,
        context=context,
        draft_tone=normalized_tone,
    )
    llm_result = llm_service.chat_json(messages)
    parsed = llm_result.get("parsed_json")

    if llm_result.get("success") and isinstance(parsed, dict):
        strategy, draft = _normalize_llm_result(parsed, fallback, draft_type)
        return _build_response(
            application_id=application_id,
            company_name=application.company_name,
            job_title=application.job_title,
            draft_source="llm",
            draft_type=draft_type,
            reply_strategy_for_user=strategy,
            hr_reply_draft=draft,
            rule_review=rule_review,
            llm_used=True,
            llm_error=None,
            include_raw_prompt=include_raw_prompt,
            messages=messages,
        )

    error_message = llm_result.get("message") or "llm_draft_failed"
    fallback = _fallback_result(
        draft_type=draft_type,
        rule_review=rule_review,
        llm_error=error_message,
    )
    return _build_response(
        application_id=application_id,
        company_name=application.company_name,
        job_title=application.job_title,
        draft_source="rule_fallback",
        draft_type=draft_type,
        reply_strategy_for_user=fallback["reply_strategy_for_user"],
        hr_reply_draft=fallback["hr_reply_draft"],
        rule_review=rule_review,
        llm_used=False,
        llm_error=error_message,
        include_raw_prompt=include_raw_prompt,
        messages=messages if include_raw_prompt else None,
    )


def resolve_draft_type(rule_review: Dict[str, Any], application_status: str) -> str:
    hr_intent = rule_review.get("hr_intent") or {}
    intents = set(hr_intent.get("intents") or [])
    primary_intent = hr_intent.get("primary_intent")
    risk_text = " ".join(rule_review.get("risk_flags") or [])
    missing_text = " ".join(rule_review.get("missing_information") or [])

    if intents.intersection({"outsourcing", "onsite"}) or any(
        keyword in risk_text for keyword in ("外包", "驻场", "外派")
    ):
        return "confirm_details"
    if primary_intent in {"project_experience", "technical_question"}:
        return "project_intro"
    if primary_intent == "interview_schedule":
        return "interview_schedule"
    if primary_intent in {"salary_expectation", "salary"}:
        return "salary_expectation"
    if (
        rule_review.get("review_level") == "not_recommended"
        and "是否外包/驻场未明确" not in missing_text
        and application_status in {"rejected", "closed"}
    ):
        return "polite_decline"

    suggested = rule_review.get("suggested_next_message_type")
    if suggested in DRAFT_TYPES and suggested != "none":
        return suggested
    if any(keyword in missing_text for keyword in ("工作方式", "薪资", "外包", "驻场")):
        return "confirm_details"
    return "general_follow_up"


def build_prompt_by_draft_type(
    *,
    draft_type: str,
    context: Dict[str, Any],
    draft_tone: str,
) -> List[Dict[str, str]]:
    specific_goal = _prompt_goal(draft_type)
    system_prompt = (
        "你是 AI Job Agent 的 HR 回复草稿助手。你只生成可人工审核的草稿，不发送消息。"
        "判断优先级必须是：原始 HR message / 原始 JD / application 数据 > evidence > rule_review 结论 > LLM 表达建议。"
        "如果规则结论和原始信息可能冲突，必须写入 reply_strategy_for_user.conflict_warnings，草稿使用“想确认一下”而不是确定性判断。"
        "不得编造候选人经历、薪资、到岗时间、面试时间、地址、学历、项目经历。"
        "不得替用户承诺接受外包、驻场、加班、薪资、offer 或面试时间。"
        "输出必须是 JSON，不要输出 Markdown。"
    )
    user_payload = {
        "task": "一次性生成给用户看的回复策略和给 HR 的回复草稿",
        "draft_type": draft_type,
        "draft_tone": draft_tone,
        "draft_type_goal": specific_goal,
        "expected_json_schema": {
            "reply_strategy_for_user": {
                "summary": "给用户看的回复思路",
                "why_this_draft_type": "为什么选择这个草稿类型",
                "key_risks": ["风险点"],
                "questions_to_confirm": ["需要确认的问题"],
                "conflict_warnings": ["规则和原文可能冲突的地方"],
                "conservative_next_step": "保守下一步建议",
            },
            "hr_reply_draft": {
                "draft_text": "给 HR 的回复草稿",
                "draft_goal": "草稿目标",
                "must_confirm_before_send": ["发送前必须人工确认的事项"],
                "risk_notes": ["风险提示"],
                "safe_to_send": False,
            },
        },
        "context": jsonable_encoder(context),
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def _prompt_goal(draft_type: str) -> str:
    goals = {
        "confirm_details": (
            "向 HR 确认岗位关键信息，不直接答应外包/驻场/薪资/面试时间；重点确认合同主体、"
            "驻场周期、工作地点、工作方式、薪资范围、岗位职责、社保缴纳主体。"
        ),
        "project_intro": (
            "基于真实项目经验介绍 AI 应用开发、RAG、Agent、FastAPI、LangGraph、Workflow 等能力；"
            "不得编造生产数据、团队规模、上线效果、商业收入。"
        ),
        "interview_schedule": (
            "回复面试邀约，只能表达愿意沟通或提供可沟通时间范围；不能替用户自动确认具体面试时间。"
        ),
        "salary_expectation": (
            "保守表达薪资可结合岗位职责、工作方式和面试情况沟通；不承诺最终薪资，不编造当前薪资。"
        ),
        "polite_decline": "礼貌简洁地婉拒，不攻击公司，不暴露过多个人隐私。",
        "general_follow_up": "礼貌跟进，简洁确认下一步，不做承诺。",
    }
    return goals.get(draft_type, goals["general_follow_up"])


def _fallback_result(
    *,
    draft_type: str,
    rule_review: Dict[str, Any],
    llm_error: Optional[str],
) -> Dict[str, Any]:
    risk_flags = rule_review.get("risk_flags") or []
    missing = rule_review.get("missing_information") or []
    strategy = {
        "summary": _strategy_summary(draft_type),
        "why_this_draft_type": _strategy_reason(draft_type, rule_review),
        "key_risks": risk_flags,
        "questions_to_confirm": _questions_to_confirm(draft_type, risk_flags, missing),
        "conflict_warnings": [],
        "conservative_next_step": "先向 HR 确认关键信息，再决定是否继续推进。",
    }
    draft = {
        "draft_text": _fallback_text(draft_type),
        "draft_goal": _draft_goal(draft_type),
        "must_confirm_before_send": _must_confirm_before_send(draft_type, risk_flags, missing),
        "risk_notes": _risk_notes(draft_type, risk_flags, llm_error),
        "safe_to_send": _safe_to_send(draft_type, risk_flags, missing),
    }
    return {"reply_strategy_for_user": strategy, "hr_reply_draft": draft}


def _normalize_llm_result(
    parsed: Dict[str, Any],
    fallback: Dict[str, Any],
    draft_type: str,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    strategy = parsed.get("reply_strategy_for_user")
    draft = parsed.get("hr_reply_draft")
    if not isinstance(strategy, dict):
        strategy = fallback["reply_strategy_for_user"]
    if not isinstance(draft, dict):
        draft = fallback["hr_reply_draft"]
    return (
        {
            "summary": str(strategy.get("summary") or ""),
            "why_this_draft_type": str(strategy.get("why_this_draft_type") or ""),
            "key_risks": _string_list(strategy.get("key_risks")),
            "questions_to_confirm": _string_list(strategy.get("questions_to_confirm")),
            "conflict_warnings": _string_list(strategy.get("conflict_warnings")),
            "conservative_next_step": str(strategy.get("conservative_next_step") or ""),
        },
        {
            "draft_text": str(draft.get("draft_text") or fallback["hr_reply_draft"]["draft_text"]),
            "draft_goal": str(draft.get("draft_goal") or _draft_goal(draft_type)),
            "must_confirm_before_send": _string_list(draft.get("must_confirm_before_send")),
            "risk_notes": _string_list(draft.get("risk_notes")),
            "safe_to_send": bool(draft.get("safe_to_send", False)),
        },
    )


def _build_response(
    *,
    application_id: int,
    company_name: str,
    job_title: str,
    draft_source: str,
    draft_type: str,
    reply_strategy_for_user: Dict[str, Any],
    hr_reply_draft: Dict[str, Any],
    rule_review: Dict[str, Any],
    llm_used: bool,
    llm_error: Optional[str],
    include_raw_prompt: bool,
    messages: Optional[List[Dict[str, str]]],
) -> Dict[str, Any]:
    debug = {
        "draft_engine": "llm_hr_reply_draft",
        "analysis_and_draft_combined": True,
        "step14_llm_enhance_called": False,
        "base_review_engine": "rule_based_application_review",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.deepseek_model,
        "rag_used": False,
        "playwright_used": False,
        "auto_apply": False,
        "auto_send_message": False,
        "auto_update_status": False,
        "database_write_intended": False,
    }
    if include_raw_prompt and messages is not None:
        debug["raw_prompt_messages"] = messages
    return {
        "application_id": application_id,
        "company_name": company_name,
        "job_title": job_title,
        "draft_source": draft_source,
        "draft_type": draft_type,
        "reply_strategy_for_user": reply_strategy_for_user,
        "hr_reply_draft": hr_reply_draft,
        "draft_text": hr_reply_draft["draft_text"],
        "draft_goal": hr_reply_draft["draft_goal"],
        "must_confirm_before_send": hr_reply_draft["must_confirm_before_send"],
        "risk_notes": hr_reply_draft["risk_notes"],
        "safe_to_send": hr_reply_draft["safe_to_send"],
        "human_review_required": True,
        "rule_review": rule_review,
        "llm_enhanced_review": None,
        "llm_used": llm_used,
        "llm_error": llm_error,
        "debug": debug,
    }


def _strategy_summary(draft_type: str) -> str:
    summaries = {
        "confirm_details": "建议先确认岗位关键信息，不要直接答应。",
        "project_intro": "建议基于真实项目经历进行简洁介绍。",
        "interview_schedule": "建议表达愿意沟通，但具体时间确认后再回复。",
        "salary_expectation": "建议保守沟通薪资，先了解岗位职责和薪资范围。",
        "polite_decline": "建议礼貌婉拒当前机会。",
        "general_follow_up": "建议礼貌跟进并确认下一步。",
    }
    return summaries.get(draft_type, summaries["general_follow_up"])


def _strategy_reason(draft_type: str, rule_review: Dict[str, Any]) -> str:
    primary = (rule_review.get("hr_intent") or {}).get("primary_intent")
    return f"根据 HR intent={primary}、风险和缺失信息，草稿类型选择为 {draft_type}。"


def _questions_to_confirm(
    draft_type: str,
    risk_flags: List[str],
    missing: List[str],
) -> List[str]:
    questions = []
    if draft_type == "confirm_details" or risk_flags:
        questions.extend(["合同主体", "驻场周期", "工作地点", "工作方式", "薪资范围", "岗位职责", "社保缴纳主体"])
    if draft_type == "interview_schedule":
        questions.append("可沟通时间是否真实方便")
    if draft_type == "salary_expectation":
        questions.append("期望薪资范围是否符合本人真实意愿")
    questions.extend(missing[:3])
    return list(dict.fromkeys(questions))


def _fallback_text(draft_type: str) -> str:
    texts = {
        "confirm_details": "您好，这个方向我可以进一步了解一下。为了判断是否合适，想先确认一下岗位的用工性质、工作方式、薪资范围和具体职责，谢谢。",
        "project_intro": "您好，我有 AI 应用开发和 RAG / Agent 相关项目经验，可以结合项目情况进一步沟通。具体细节我可以在面试中展开说明，谢谢。",
        "interview_schedule": "您好，我愿意进一步沟通。具体时间我需要确认一下，稍后回复您是否方便，谢谢。",
        "salary_expectation": "您好，薪资方面我希望结合岗位职责、工作方式和面试情况进一步沟通，也想先了解一下贵方的薪资范围，谢谢。",
        "polite_decline": "您好，感谢您的沟通。这个岗位目前和我的方向可能不太匹配，暂时先不继续推进了，祝招聘顺利。",
        "general_follow_up": "您好，我可以进一步了解一下这个岗位，想先确认岗位职责、工作方式和后续流程，谢谢。",
    }
    return texts.get(draft_type, texts["general_follow_up"])


def _draft_goal(draft_type: str) -> str:
    goals = {
        "confirm_details": "确认岗位关键信息后再判断是否继续推进",
        "project_intro": "基于真实项目经历回答项目相关问题",
        "interview_schedule": "表达可继续沟通，但具体面试时间需用户确认",
        "salary_expectation": "保守沟通薪资范围和岗位职责",
        "polite_decline": "礼貌婉拒当前机会",
        "general_follow_up": "保持礼貌跟进并补充确认关键信息",
    }
    return goals.get(draft_type, goals["general_follow_up"])


def _must_confirm_before_send(
    draft_type: str,
    risk_flags: List[str],
    missing: List[str],
) -> List[str]:
    items = ["确认草稿内容符合本人真实意愿"]
    if draft_type in {"confirm_details", "salary_expectation", "interview_schedule"}:
        items.append("确认是否需要补充个人真实信息")
    if risk_flags:
        items.append("确认是否接受或继续了解相关风险点")
    if missing:
        items.append("确认是否需要先向 HR 补充询问缺失信息")
    return list(dict.fromkeys(items))


def _risk_notes(
    draft_type: str,
    risk_flags: List[str],
    llm_error: Optional[str],
) -> List[str]:
    notes = ["草稿不会自动发送，必须人工审核"]
    if draft_type in {"confirm_details", "interview_schedule", "salary_expectation"}:
        notes.append("不要直接承诺薪资、到岗时间、面试时间或工作方式")
    notes.extend(risk_flags[:3])
    if llm_error:
        notes.append(f"LLM 未生成草稿，已使用规则 fallback：{llm_error}")
    return list(dict.fromkeys(notes))


def _safe_to_send(
    draft_type: str,
    risk_flags: List[str],
    missing: List[str],
) -> bool:
    if draft_type in {"confirm_details", "interview_schedule", "salary_expectation"}:
        return False
    return not risk_flags and len(missing) <= 1


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
