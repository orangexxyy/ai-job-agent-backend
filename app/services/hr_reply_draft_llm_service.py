import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi.encoders import jsonable_encoder

from app.config import settings
from app.services.application_review_service import review_application
from app.services.application_service import get_application
from app.services.interview_availability_service import list_interview_availability_slots
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

PROJECT_BOUNDARY_VIOLATION_PATTERNS = (
    "AI Job Agent 使用 RAG",
    "AI Job Agent 利用 RAG",
    "AI Job Agent 接入 RAG",
    "AI Job Agent 通过 RAG",
    "AI Job Agent 使用向量",
    "AI Job Agent 使用 Embedding",
    "AI Job Agent 使用 FAISS",
    "AI Job Agent 使用 BM25",
    "AI Job Agent 使用 Reranker",
    "RAG 项目使用 LangGraph",
    "RAG 项目接入 LangGraph",
    "RAG 项目利用 LangGraph",
    "RAG 项目通过 LangGraph",
)

FORBIDDEN_PROJECT_EXAGGERATIONS = (
    "自动发送 HR 消息",
    "自动投递",
    "企业级生产系统",
)

SAFE_PROJECT_INTRO_FALLBACK_TEXT = (
    "您好，我做过两个相关 Demo：一个是 FastAPI + RAG 企业知识库问答系统，"
    "重点是文档入库、txt / PDF / Excel 解析、FAISS + BM25 + RRF 混合检索、"
    "Reranker、low_confidence 判断和 SQLite 多轮会话；另一个是 AI Job Agent 求职助手，"
    "重点是 candidate profile、application tracking、JD parsing、job_match、"
    "application_review、HR 回复草稿和 LangGraph workflow preview。两个项目侧重点不同，"
    "我可以在面试中分别展开。"
)


def generate_hr_reply_draft_from_review(
    application_id: int,
    hr_message: Optional[str] = None,
    draft_tone: str = "professional",
    include_raw_prompt: bool = False,
    precomputed_rule_review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """基于 application review 生成回复策略和 HR 回复草稿。

    主要输入：application_id、可选 HR message、draft_tone、调试开关，以及可选的已计算 rule_review。
    主要输出：reply_strategy_for_user、hr_reply_draft、draft_type、可用时间字段、LLM 状态和安全 debug。
    副作用：可能调用一次外部 LLM；只读 SQLite；不写 application，不自动发送 HR 消息，不自动投递，不自动确认面试。
    """
    normalized_tone = draft_tone if draft_tone in VALID_DRAFT_TONES else "professional"
    if precomputed_rule_review is not None:
        rule_review = jsonable_encoder(precomputed_rule_review)
    else:
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
    draft_type = resolve_draft_type(rule_review, application.status)
    available_slots = (
        _serialize_available_slots(list_interview_availability_slots(status="available"))
        if draft_type == "interview_schedule"
        else []
    )

    context = {
        "rule_review": rule_review,
        "application": jsonable_encoder(application),
        "candidate_profile": jsonable_encoder(profile) if profile else None,
        "hr_message": hr_message,
        "available_slots": available_slots,
    }
    fallback = _fallback_result(
        draft_type=draft_type,
        rule_review=rule_review,
        llm_error="api_key_missing" if not settings.deepseek_api_key else None,
        available_slots=available_slots,
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
        strategy, draft, project_boundary_fallback = _apply_project_fact_boundary(
            draft_type,
            strategy,
            draft,
            fallback,
        )
        strategy, draft, availability_boundary_fallback = _apply_interview_availability_boundary(
            draft_type,
            strategy,
            draft,
            fallback,
            available_slots,
        )
        return _build_response(
            application_id=application_id,
            company_name=application.company_name,
            job_title=application.job_title,
            draft_source="llm" if not project_boundary_fallback and not availability_boundary_fallback else "rule_fallback",
            draft_type=draft_type,
            reply_strategy_for_user=strategy,
            hr_reply_draft=draft,
            rule_review=rule_review,
            llm_used=not project_boundary_fallback and not availability_boundary_fallback,
            llm_error=None if not project_boundary_fallback and not availability_boundary_fallback else "safety_boundary_fallback",
            include_raw_prompt=include_raw_prompt,
            messages=messages,
            available_slots=available_slots,
            project_fact_boundary_fallback=project_boundary_fallback,
            availability_boundary_fallback=availability_boundary_fallback,
        )

    error_message = llm_result.get("message") or "llm_draft_failed"
    fallback = _fallback_result(
        draft_type=draft_type,
        rule_review=rule_review,
        llm_error=error_message,
        available_slots=available_slots,
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
        available_slots=available_slots,
        project_fact_boundary_fallback=False,
        availability_boundary_fallback=False,
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
        "如果规则结论和原始信息可能冲突，必须写入 reply_strategy_for_user.conflict_warnings，"
        "草稿使用“想确认一下”而不是确定性判断。"
        "不得编造候选人经历、薪资、到岗时间、面试时间、地址、学历、项目经历。"
        "不得替用户承诺接受外包、驻场、加班、薪资、offer 或面试时间。"
        "输出必须是 JSON，不要输出 Markdown。"
    )
    user_payload: Dict[str, Any] = {
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
    if draft_type == "project_intro":
        user_payload["project_fact_boundary"] = {
            "RAG_enterprise_knowledge_base_can_say": [
                "FastAPI",
                "文档入库",
                "txt / PDF / Excel",
                "Document / chunk / metadata",
                "FAISS + BM25 + RRF",
                "Reranker",
                "low_confidence",
                "SQLite 多轮会话",
                "React Demo",
            ],
            "RAG_enterprise_knowledge_base_must_not_say": [
                "LangGraph",
                "自动投递",
                "自动发送 HR 消息",
                "招聘 Agent",
            ],
            "AI_Job_Agent_can_say": [
                "FastAPI",
                "candidate profile",
                "application tracking",
                "JD parsing",
                "job_match",
                "application_review",
                "LLM enhanced review",
                "HR reply draft",
                "LangGraph workflow preview",
                "require_user_approval_node",
                "node_debug / edge_trace / state_snapshots",
            ],
            "AI_Job_Agent_must_not_say": [
                "RAG 检索",
                "Embedding",
                "向量数据库",
                "FAISS / BM25 / Reranker",
                "自动投递",
                "自动发送 HR 消息",
                "自动确认面试",
                "企业级生产系统",
            ],
            "rules": [
                "不要把不同项目的技术栈混合到同一个项目里。",
                "如果 HR 同时问 RAG 和 Agent，可以分两个项目介绍。",
                "不得说 RAG 项目使用 LangGraph。",
                "不得说 AI Job Agent 使用 RAG / 向量检索。",
                "如果不确定某项技术属于哪个项目，保守说明可以进一步展开，不要编造归属。",
            ],
        }
    if draft_type == "interview_schedule":
        user_payload["interview_availability_rules"] = {
            "available_slots": context.get("available_slots") or [],
            "rules": [
                "如果 available_slots 为空，不得虚构明天下午、后天上午或任何具体可用时间段。",
                "如果 available_slots 为空，只能回复需要先确认日程，稍后回复是否方便。",
                "如果 available_slots 非空，只能从 available_slots 中选择或提供时间段。",
                "不得自动确认 HR 提出的具体面试时间，除非用户后续明确确认。",
            ],
        }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def _prompt_goal(draft_type: str) -> str:
    goals = {
        "confirm_details": (
            "向 HR 确认岗位关键事实，不直接答应外包、驻场、薪资或面试安排；"
            "重点确认合同主体、驻场周期、工作地点、工作方式、薪资范围、岗位职责和社保缴纳主体。"
        ),
        "project_intro": (
            "基于真实项目经验介绍 RAG 企业知识库 Demo 和 AI Job Agent Demo。必须区分两个项目的技术栈："
            "RAG 项目可以说 FastAPI、文档入库、txt / PDF / Excel、FAISS + BM25 + RRF、Reranker、"
            "low_confidence 和 SQLite 多轮会话，但不得说使用 LangGraph；AI Job Agent 可以说 "
            "candidate profile、application tracking、JD parsing、job_match、application_review、"
            "HR reply draft、LangGraph workflow preview、require_user_approval_node、node_debug / edge_trace / "
            "state_snapshots，但不得说使用 RAG / Embedding / 向量检索。不得编造生产数据、团队规模、上线效果或商业收入。"
        ),
        "interview_schedule": (
            "回复面试邀约时必须基于 available_slots。没有 available_slots 时，只能说明需要先确认日程后再回复；"
            "有 available_slots 时，只能提供这些时间段供 HR 参考。不得自动确认 HR 提出的具体面试时间。"
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
    available_slots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    risk_flags = rule_review.get("risk_flags") or []
    missing = rule_review.get("missing_information") or []
    strategy = {
        "summary": _strategy_summary(draft_type),
        "why_this_draft_type": _strategy_reason(draft_type, rule_review),
        "key_risks": risk_flags,
        "questions_to_confirm": _questions_to_confirm(draft_type, risk_flags, missing),
        "conflict_warnings": [],
        "conservative_next_step": "先由用户审核草稿，再决定是否发送给 HR。",
    }
    draft = {
        "draft_text": _fallback_text(draft_type, available_slots),
        "draft_goal": _draft_goal(draft_type),
        "must_confirm_before_send": _must_confirm_before_send(draft_type, risk_flags, missing),
        "risk_notes": _risk_notes(draft_type, risk_flags, llm_error),
        "safe_to_send": _safe_to_send(draft_type, risk_flags, missing),
    }
    if draft_type == "interview_schedule":
        draft["safe_to_send"] = False
        if not available_slots:
            strategy["questions_to_confirm"].append("用户需要先确认自己的可用面试时间")
        else:
            strategy["questions_to_confirm"].append("用户发送前需要再次确认这些时间段仍然可用")
    return {"reply_strategy_for_user": strategy, "hr_reply_draft": draft}


def _normalize_llm_result(
    parsed: Dict[str, Any],
    fallback: Dict[str, Any],
    draft_type: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
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


def _apply_project_fact_boundary(
    draft_type: str,
    strategy: Dict[str, Any],
    draft: Dict[str, Any],
    fallback: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
    if draft_type != "project_intro":
        return strategy, draft, False
    text = draft.get("draft_text", "")
    if not _contains_project_boundary_violation(text):
        return strategy, draft, False
    safe_strategy = dict(fallback["reply_strategy_for_user"])
    safe_draft = dict(fallback["hr_reply_draft"])
    safe_draft["draft_text"] = SAFE_PROJECT_INTRO_FALLBACK_TEXT
    safe_draft["safe_to_send"] = False
    safe_draft["risk_notes"] = list(
        dict.fromkeys(
            _string_list(safe_draft.get("risk_notes"))
            + ["已触发项目事实边界 fallback：避免混淆 RAG 项目和 AI Job Agent 技术栈。"]
        )
    )
    safe_strategy["conflict_warnings"] = list(
        dict.fromkeys(
            _string_list(safe_strategy.get("conflict_warnings"))
            + ["草稿疑似混淆不同项目技术栈，已替换为安全项目介绍。"]
        )
    )
    return safe_strategy, safe_draft, True


def _apply_interview_availability_boundary(
    draft_type: str,
    strategy: Dict[str, Any],
    draft: Dict[str, Any],
    fallback: Dict[str, Any],
    available_slots: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
    if draft_type != "interview_schedule":
        return strategy, draft, False
    safe_strategy = dict(strategy)
    safe_draft = dict(draft)
    fallback_draft = fallback["hr_reply_draft"]
    fallback_strategy = fallback["reply_strategy_for_user"]
    safe_draft["draft_text"] = fallback_draft["draft_text"]
    safe_draft["safe_to_send"] = False
    safe_draft["risk_notes"] = list(
        dict.fromkeys(
            _string_list(safe_draft.get("risk_notes"))
            + _string_list(fallback_draft.get("risk_notes"))
            + ["面试时间草稿必须基于用户维护的 available slots，发送前仍需人工确认。"]
        )
    )
    safe_draft["must_confirm_before_send"] = list(
        dict.fromkeys(
            _string_list(safe_draft.get("must_confirm_before_send"))
            + _string_list(fallback_draft.get("must_confirm_before_send"))
            + ["确认日程后再发送，不自动确认面试时间"]
        )
    )
    safe_strategy["questions_to_confirm"] = list(
        dict.fromkeys(
            _string_list(safe_strategy.get("questions_to_confirm"))
            + _string_list(fallback_strategy.get("questions_to_confirm"))
        )
    )
    return safe_strategy, safe_draft, True


def _contains_project_boundary_violation(text: str) -> bool:
    normalized = text.replace(" ", "")
    for pattern in PROJECT_BOUNDARY_VIOLATION_PATTERNS:
        if pattern.replace(" ", "") in normalized:
            return True
    return any(pattern in text for pattern in FORBIDDEN_PROJECT_EXAGGERATIONS)


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
    available_slots: List[Dict[str, Any]],
    project_fact_boundary_fallback: bool,
    availability_boundary_fallback: bool,
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
        "auto_confirm_interview": False,
        "database_write_intended": False,
        "project_fact_boundary_fallback": project_fact_boundary_fallback,
        "availability_boundary_fallback": availability_boundary_fallback,
    }
    if include_raw_prompt and messages is not None:
        debug["raw_prompt_messages"] = messages
    availability_missing = draft_type == "interview_schedule" and not available_slots
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
        "available_slots_used": available_slots if draft_type == "interview_schedule" else [],
        "availability_source": "interview_availability_slots" if draft_type == "interview_schedule" else None,
        "availability_missing": availability_missing,
        "rule_review": rule_review,
        "llm_enhanced_review": None,
        "llm_used": llm_used,
        "llm_error": llm_error,
        "debug": debug,
    }


def _strategy_summary(draft_type: str) -> str:
    summaries = {
        "confirm_details": "建议先确认岗位关键信息，不要直接答应。",
        "project_intro": "建议分开介绍 RAG 企业知识库 Demo 和 AI Job Agent Demo，避免混淆技术栈。",
        "interview_schedule": "建议基于用户维护的可用时间段沟通；没有时间段时先确认日程。",
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
    questions: List[str] = []
    if draft_type == "confirm_details" or risk_flags:
        questions.extend(["合同主体", "驻场周期", "工作地点", "工作方式", "薪资范围", "岗位职责", "社保缴纳主体"])
    if draft_type == "interview_schedule":
        questions.append("用户维护的可用面试时间是否仍然准确")
    if draft_type == "salary_expectation":
        questions.append("期望薪资范围是否符合本人真实意愿")
    questions.extend(missing[:3])
    return list(dict.fromkeys(questions))


def _fallback_text(draft_type: str, available_slots: List[Dict[str, Any]]) -> str:
    texts = {
        "confirm_details": (
            "您好，这个方向我可以进一步了解一下。为了判断是否合适，想先确认一下岗位的用工性质、"
            "工作方式、薪资范围和具体职责，谢谢。"
        ),
        "project_intro": SAFE_PROJECT_INTRO_FALLBACK_TEXT,
        "interview_schedule": _interview_schedule_fallback_text(available_slots),
        "salary_expectation": (
            "您好，薪资方面我希望结合岗位职责、工作方式和面试情况进一步沟通，"
            "也想先了解一下贵方的薪资范围，谢谢。"
        ),
        "polite_decline": "您好，感谢您的沟通。这个岗位目前和我的方向可能不太匹配，暂时先不继续推进了，祝招聘顺利。",
        "general_follow_up": "您好，我可以进一步了解一下这个岗位，想先确认岗位职责、工作方式和后续流程，谢谢。",
    }
    return texts.get(draft_type, texts["general_follow_up"])


def _interview_schedule_fallback_text(available_slots: List[Dict[str, Any]]) -> str:
    if not available_slots:
        return (
            "您好，感谢您的邀请。这个时间我需要先确认一下日程，稍后回复您是否方便。"
            "也想请问一下面试预计时长和会议形式，谢谢。"
        )
    slot_text = "；".join(
        f"{slot['date']} {slot['start_time']}-{slot['end_time']} {slot['timezone']}"
        for slot in available_slots[:5]
    )
    return (
        f"您好，感谢您的邀请。我这边可以提供以下可沟通时间段供您参考：{slot_text}。"
        "您看哪个时间方便？发送前我会再确认一次日程，谢谢。"
    )


def _draft_goal(draft_type: str) -> str:
    goals = {
        "confirm_details": "确认岗位关键信息后再判断是否继续推进",
        "project_intro": "基于真实项目经历回答项目相关问题，并区分不同项目技术栈",
        "interview_schedule": "基于用户维护的可用时间段沟通，具体面试时间仍需用户确认",
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
    if draft_type == "project_intro":
        items.append("确认没有混淆 RAG 项目和 AI Job Agent 项目的技术栈")
    if draft_type == "interview_schedule":
        items.append("确认日程后再发送，不自动确认面试时间")
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
    if draft_type == "project_intro":
        notes.append("不得把 RAG 企业知识库项目说成使用 LangGraph，也不得把 AI Job Agent 说成使用 RAG / 向量检索")
    notes.extend(risk_flags[:3])
    if llm_error:
        notes.append(f"LLM 未生成草稿，已使用规则 fallback：{llm_error}")
    return list(dict.fromkeys(notes))


def _safe_to_send(
    draft_type: str,
    risk_flags: List[str],
    missing: List[str],
) -> bool:
    if draft_type in {"confirm_details", "interview_schedule", "salary_expectation", "project_intro"}:
        return False
    return not risk_flags and len(missing) <= 1


def _serialize_available_slots(slots: Any) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    seen = set()
    for slot in slots:
        key = (slot.date, slot.start_time, slot.end_time, slot.timezone)
        if key in seen:
            continue
        seen.add(key)
        serialized.append(
            {
                "id": slot.id,
                "date": slot.date,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "timezone": slot.timezone,
                "status": slot.status,
                "note": slot.note,
            }
        )
    return serialized


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
