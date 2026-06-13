from typing import Any, Dict, List, Optional, Tuple

from app.schemas.application_schema import ApplicationItem
from app.services.application_service import get_application
from app.services.hr_intent_service import analyze_hr_message
from app.services.job_match_service import analyze_job_match
from app.services.profile_service import get_candidate_profile


AI_KEYWORDS = {
    "RAG",
    "Agent",
    "FastAPI",
    "LangGraph",
    "LangChain",
    "LLM",
    "Embedding",
    "FAISS",
    "BM25",
    "Rerank",
}

STATUS_DELTAS = {
    "hr_contacted": 8,
    "interview_scheduled": 12,
    "interview_done": 6,
    "applied": 4,
    "saved": 0,
    "rejected": -20,
    "closed": -20,
}

HR_INTENT_DELTAS = {
    "interview_schedule": 12,
    "project_experience": 8,
    "technical_question": 8,
    "salary_expectation": 4,
    "availability": 4,
    "resume_request": 4,
}

HIGH_RISK_RULES = {
    "收费": ("存在收费风险", -30, True),
    "押金": ("存在押金风险", -30, True),
    "培训费": ("存在培训费风险", -30, True),
}

RISK_RULES = {
    "外包": ("疑似外包岗位，需要确认合同主体和项目性质", -15),
    "驻场": ("疑似驻场岗位，需要确认是否长期客户现场", -15),
    "外派": ("疑似外派岗位，需要确认工作地点和管理关系", -15),
    "长期现场": ("疑似长期现场工作，需要确认工作方式", -15),
    "项目现场": ("疑似项目现场工作，需要确认工作方式", -15),
    "996": ("疑似高强度工作节奏，需要确认加班边界", -10),
    "单休": ("疑似单休制度，需要确认工作节奏", -10),
    "加班严重": ("疑似长期高强度加班，需要谨慎评估", -10),
    "薪资面议": ("薪资信息不够明确，需要补充确认", -5),
    "薪资不明": ("薪资信息不够明确，需要补充确认", -5),
    "无社保": ("疑似社保风险，需要谨慎评估", -15),
}

REVIEW_LEVELS = {
    "high_priority",
    "normal_priority",
    "cautious_follow_up",
    "low_priority",
    "not_recommended",
}


def review_application(
    application_id: int,
    hr_message: Optional[str] = None,
    update_application: bool = False,
) -> Dict[str, Any]:
    """生成 application 的规则版跟进建议。

    主要输入：application_id、可选 HR message、以及只读 review 开关。
    主要输出：review_score、review_level、recommended_action、风险和缺失信息。
    副作用：只读数据库；不写 application status；不调用 LLM / RAG / Playwright；不自动投递或发送 HR 消息。
    """
    application = get_application(application_id)
    if application is None:
        raise ValueError("application not found")

    job_match, job_match_error = _safe_job_match(application_id)
    hr_text = (hr_message or application.last_hr_message or "").strip()
    hr_intent = (
        analyze_hr_message(hr_text, application.company_name, application.job_title)
        if hr_text
        else None
    )

    score_adjustments: List[Dict[str, Any]] = []
    reasons: List[str] = []
    base_match_score = int(job_match.get("match_score") or 0)
    review_score = int(base_match_score * 0.6)
    score_adjustments.append(
        {
            "factor": "base_job_match",
            "delta": review_score,
            "reason": "基于现有 job_match 分数按 60% 折算",
        }
    )

    keyword_delta, matched_keywords = _score_ai_keywords(application)
    review_score += keyword_delta
    if keyword_delta:
        reasons.append("JD 命中 AI 应用开发相关关键词")
        score_adjustments.append(
            {
                "factor": "ai_application_keywords",
                "delta": keyword_delta,
                "reason": "命中 RAG / Agent / FastAPI / LangGraph 等方向关键词",
            }
        )

    status_delta = STATUS_DELTAS.get(application.status, 0)
    review_score += status_delta
    score_adjustments.append(
        {
            "factor": "application_status",
            "delta": status_delta,
            "reason": f"当前 application status 为 {application.status}",
        }
    )

    if hr_intent:
        primary_intent = hr_intent.get("primary_intent", "unknown")
        hr_delta = HR_INTENT_DELTAS.get(primary_intent, 0)
        review_score += hr_delta
        score_adjustments.append(
            {
                "factor": "hr_intent",
                "delta": hr_delta,
                "reason": f"HR primary_intent 为 {primary_intent}",
            }
        )
        if hr_delta:
            reasons.append("HR 消息显示有明确跟进信号")

    risk_flags, risk_delta, force_not_recommended = _collect_risks(
        application,
        hr_message,
    )
    review_score += risk_delta
    if risk_delta:
        score_adjustments.append(
            {
                "factor": "risk_flags",
                "delta": risk_delta,
                "reason": "命中外包、驻场、薪资或收费类风险词",
            }
        )

    missing_information, missing_delta, serious_missing = _collect_missing_information(
        application,
    )
    review_score += missing_delta
    if missing_delta:
        score_adjustments.append(
            {
                "factor": "missing_information",
                "delta": missing_delta,
                "reason": "JD 或岗位关键信息不完整",
            }
        )

    if application.jd_remote_type == "remote":
        review_score += 5
        score_adjustments.append(
            {"factor": "remote_type", "delta": 5, "reason": "岗位支持 remote"}
        )
    elif application.jd_remote_type == "hybrid":
        review_score += 3
        score_adjustments.append(
            {"factor": "remote_type", "delta": 3, "reason": "岗位支持 hybrid"}
        )

    if job_match_error:
        reasons.append("job_match 暂不可用，已使用保守 review 结果")
        missing_information.append("candidate_profile 缺失，job_match 结果不可用")

    if not reasons:
        reasons.append("基于当前 application 和 JD 信息生成保守跟进建议")

    review_score = max(0, min(100, review_score))
    review_level = _review_level(review_score)
    review_level = _apply_level_overrides(
        review_level=review_level,
        application=application,
        base_match_score=base_match_score,
        risk_flags=risk_flags,
        force_not_recommended=force_not_recommended,
        hr_intent=hr_intent,
        serious_missing=serious_missing,
    )
    recommended_action = _recommended_action(review_level, risk_flags)
    suggested_next_message_type = _suggested_next_message_type(
        review_level,
        missing_information,
        risk_flags,
        hr_intent,
    )

    if update_application:
        reasons.append("本轮 review 保持只读，未写回 next_action / risk_flags / status")

    evidence = _build_evidence(
        application=application,
        job_match=job_match,
        matched_keywords=matched_keywords,
        risk_flags=risk_flags,
        missing_information=missing_information,
        hr_intent=hr_intent,
        hr_message=hr_message,
        job_match_error=job_match_error,
    )
    confidence = _resolve_confidence(
        application=application,
        matched_keywords=matched_keywords,
        risk_flags=risk_flags,
        hr_text=hr_text,
        job_match_error=job_match_error,
    )

    return {
        "application_id": application.id,
        "company_name": application.company_name,
        "job_title": application.job_title,
        "review_mode": "rule_based",
        "review_score": review_score,
        "review_level": review_level,
        "confidence": confidence,
        "recommended_action": recommended_action,
        "evidence": evidence,
        "reasons": _dedupe(reasons),
        "risk_flags": _dedupe(risk_flags),
        "missing_information": _dedupe(missing_information),
        "suggested_next_message_type": suggested_next_message_type,
        "human_review_required": True,
        "job_match": job_match,
        "hr_intent": hr_intent,
        "decision_factors": {
            "base_match_score": base_match_score,
            "score_adjustments": score_adjustments,
            "matched_keywords": matched_keywords,
            "status": application.status,
            "source_type": application.source_type,
            "jd_remote_type": application.jd_remote_type,
            "hr_primary_intent": (
                hr_intent.get("primary_intent") if hr_intent else None
            ),
        },
        "llm_ready_context": _build_llm_ready_context(
            application,
            review_level,
            confidence,
            recommended_action,
            risk_flags,
            missing_information,
            evidence,
            job_match,
        ),
        "llm_used": False,
        "debug": {
            "llm_used": False,
            "rag_used": False,
            "playwright_used": False,
            "auto_apply": False,
            "auto_send_message": False,
            "auto_update_status": False,
            "review_engine": "rule_based_application_review",
            "update_application_requested": update_application,
            "database_write_intended": False,
            "job_match_error": job_match_error,
        },
    }


def _safe_job_match(application_id: int) -> Tuple[Dict[str, Any], Optional[str]]:
    try:
        return analyze_job_match(application_id, update_application=False), None
    except ValueError as exc:
        if str(exc) == "candidate_profile not found":
            return {"match_score": 0, "error": "candidate_profile not found"}, str(exc)
        raise


def _score_ai_keywords(application: ApplicationItem) -> Tuple[int, List[str]]:
    keywords = set(application.jd_keywords or []) | set(application.jd_required_skills or [])
    matched = sorted(keyword for keyword in AI_KEYWORDS if keyword in keywords)
    if len(matched) >= 4:
        return 15, matched
    if len(matched) >= 2:
        return 10, matched
    return 0, matched


def _build_evidence(
    *,
    application: ApplicationItem,
    job_match: Dict[str, Any],
    matched_keywords: List[str],
    risk_flags: List[str],
    missing_information: List[str],
    hr_intent: Optional[Dict[str, Any]],
    hr_message: Optional[str],
    job_match_error: Optional[str],
) -> List[Dict[str, str]]:
    evidence: List[Dict[str, str]] = []
    if job_match_error:
        evidence.append(
            {
                "type": "job_match",
                "text": f"job_match 未完整返回：{job_match_error}",
                "source": "job_match",
                "confidence": "low",
            }
        )
    else:
        evidence.append(
            {
                "type": "job_match",
                "text": f"job_match 返回 match_score={job_match.get('match_score')}",
                "source": "job_match",
                "confidence": "high",
            }
        )
    if matched_keywords:
        evidence.append(
            {
                "type": "jd_keyword",
                "text": f"JD 命中 {', '.join(matched_keywords)}",
                "source": "jd_keywords",
                "confidence": "high" if len(matched_keywords) >= 2 else "medium",
            }
        )
    for risk in risk_flags:
        evidence.append(
            {
                "type": "risk_signal",
                "text": risk,
                "source": _risk_source(risk, application, hr_message),
                "confidence": _risk_confidence(risk),
            }
        )
    for item in missing_information:
        evidence.append(
            {
                "type": "missing_information",
                "text": item,
                "source": "application",
                "confidence": "medium",
            }
        )
    if hr_intent:
        evidence.append(
            {
                "type": "hr_intent",
                "text": f"HR primary_intent={hr_intent.get('primary_intent')}",
                "source": "hr_message" if hr_message else "last_hr_message",
                "confidence": "medium"
                if hr_intent.get("primary_intent") != "unknown"
                else "low",
            }
        )
    evidence.append(
        {
            "type": "status_signal",
            "text": f"application status={application.status}",
            "source": "application_status",
            "confidence": "medium",
        }
    )
    return evidence


def _risk_source(
    risk: str,
    application: ApplicationItem,
    hr_message: Optional[str],
) -> str:
    if hr_message and any(keyword in hr_message for keyword in _risk_keywords_for_text(risk)):
        return "hr_message"
    if application.last_hr_message and any(
        keyword in application.last_hr_message for keyword in _risk_keywords_for_text(risk)
    ):
        return "last_hr_message"
    if application.notes and any(keyword in application.notes for keyword in _risk_keywords_for_text(risk)):
        return "notes"
    return "jd_text"


def _risk_keywords_for_text(risk: str) -> List[str]:
    candidates = [
        "外包",
        "驻场",
        "外派",
        "长期现场",
        "项目现场",
        "996",
        "单休",
        "加班严重",
        "薪资面议",
        "薪资不明",
        "无社保",
        "收费",
        "押金",
        "培训费",
    ]
    return [keyword for keyword in candidates if keyword in risk] or candidates


def _risk_confidence(risk: str) -> str:
    if any(keyword in risk for keyword in ("收费", "押金", "培训费", "外包", "驻场", "外派")):
        return "high"
    if any(keyword in risk for keyword in ("现场", "薪资", "加班", "单休")):
        return "medium"
    return "low"


def _resolve_confidence(
    *,
    application: ApplicationItem,
    matched_keywords: List[str],
    risk_flags: List[str],
    hr_text: str,
    job_match_error: Optional[str],
) -> str:
    jd_complete = (
        bool(application.jd_summary)
        and bool(application.jd_years_requirement)
        and bool(application.jd_location_requirement)
        and application.jd_remote_type != "unknown"
        and len(application.jd_text or "") >= 30
    )
    explicit_risk = any(_risk_confidence(risk) == "high" for risk in risk_flags)
    if not job_match_error and jd_complete and (explicit_risk or len(matched_keywords) >= 4):
        return "high"
    weak_context = (
        len(application.jd_text or "") < 30
        and len(matched_keywords) <= 1
        and not application.jd_location_requirement
        and not application.jd_years_requirement
        and application.jd_remote_type == "unknown"
        and not hr_text
        and not application.notes
    )
    if job_match_error or weak_context:
        return "low"
    return "medium"


def _collect_risks(
    application: ApplicationItem,
    hr_message: Optional[str],
) -> Tuple[List[str], int, bool]:
    text = "\n".join(
        [
            application.jd_text or "",
            application.notes or "",
            application.last_hr_message or "",
            hr_message or "",
            "\n".join(application.risk_flags or []),
        ]
    )
    risk_flags = list(application.risk_flags or [])
    total_delta = 0
    force_not_recommended = False
    for keyword, (risk, delta, forced) in HIGH_RISK_RULES.items():
        if keyword in text:
            risk_flags.append(risk)
            total_delta += delta
            force_not_recommended = force_not_recommended or forced
    for keyword, (risk, delta) in RISK_RULES.items():
        if keyword in text:
            risk_flags.append(risk)
            total_delta += delta
    if application.jd_remote_type == "onsite" and any(
        keyword in text for keyword in ("驻场", "外派", "外包")
    ):
        risk_flags.append("现场办公叠加外包/驻场/外派风险，需要谨慎确认")
        total_delta -= 10
    return _dedupe(risk_flags), total_delta, force_not_recommended


def _collect_missing_information(application: ApplicationItem) -> Tuple[List[str], int, bool]:
    missing: List[str] = []
    delta = 0
    if not application.jd_summary:
        missing.append("岗位 JD 信息不足")
        delta -= 5
    if not application.jd_years_requirement:
        missing.append("工作年限要求未明确")
        delta -= 3
    if not application.jd_location_requirement:
        missing.append("工作地点未明确")
        delta -= 3
    if application.jd_remote_type == "unknown":
        missing.append("工作方式未明确")
        delta -= 3
    if not _has_salary_signal(application):
        missing.append("薪资范围未明确")
    if not _has_outsourcing_signal(application):
        missing.append("是否外包/驻场未明确")
    if len(application.jd_text or "") < 30:
        missing.append("岗位 JD 信息不足")
        delta -= 10
    if get_candidate_profile() is None:
        missing.append("candidate_profile 缺失，无法完整复用 job_match")
    serious_missing = "岗位 JD 信息不足" in missing and len(application.jd_text or "") < 30
    return _dedupe(missing), delta, serious_missing


def _has_salary_signal(application: ApplicationItem) -> bool:
    text = f"{application.jd_text}\n{application.notes}\n{application.last_hr_message}"
    return any(keyword in text for keyword in ("薪资", "薪酬", "月薪", "年薪", "k", "K"))


def _has_outsourcing_signal(application: ApplicationItem) -> bool:
    text = f"{application.jd_text}\n{application.notes}\n{application.last_hr_message}"
    return any(keyword in text for keyword in ("外包", "驻场", "外派", "自研", "正式"))


def _review_level(score: int) -> str:
    if score >= 80:
        return "high_priority"
    if score >= 65:
        return "normal_priority"
    if score >= 45:
        return "cautious_follow_up"
    if score >= 25:
        return "low_priority"
    return "not_recommended"


def _apply_level_overrides(
    *,
    review_level: str,
    application: ApplicationItem,
    base_match_score: int,
    risk_flags: List[str],
    force_not_recommended: bool,
    hr_intent: Optional[Dict[str, Any]],
    serious_missing: bool,
) -> str:
    if force_not_recommended:
        return "not_recommended"
    if application.status in {"rejected", "closed"} and review_level in {
        "high_priority",
        "normal_priority",
        "cautious_follow_up",
    }:
        review_level = "low_priority"
    if base_match_score >= 70 and any(
        ("外包" in risk or "驻场" in risk or "外派" in risk)
        for risk in risk_flags
    ):
        review_level = _min_priority(review_level, "cautious_follow_up")
    if (
        hr_intent
        and hr_intent.get("primary_intent") == "interview_schedule"
        and not force_not_recommended
        and review_level in {"low_priority", "not_recommended"}
    ):
        review_level = "normal_priority"
    if serious_missing:
        review_level = _min_priority(review_level, "cautious_follow_up")
    return review_level


def _min_priority(current: str, cap: str) -> str:
    order = [
        "not_recommended",
        "low_priority",
        "cautious_follow_up",
        "normal_priority",
        "high_priority",
    ]
    return order[min(order.index(current), order.index(cap))]


def _recommended_action(review_level: str, risk_flags: List[str]) -> str:
    actions = {
        "high_priority": "优先跟进，并准备 RAG / Agent / FastAPI 项目说明。",
        "normal_priority": "可以继续跟进，建议补充确认薪资、工作方式和岗位真实职责。",
        "cautious_follow_up": "谨慎跟进，建议先确认外包/驻场/薪资/工作方式等关键信息。",
        "low_priority": "暂不建议投入太多时间，可作为备选岗位观察。",
        "not_recommended": "不建议优先跟进，除非后续信息明显改善或用户主动确认。",
    }
    action = actions.get(review_level, actions["cautious_follow_up"])
    if risk_flags and "确认" not in action and "谨慎" not in action:
        action = f"{action} 建议先确认风险点后再决定是否继续。"
    return action


def _suggested_next_message_type(
    review_level: str,
    missing_information: List[str],
    risk_flags: List[str],
    hr_intent: Optional[Dict[str, Any]],
) -> str:
    if any(
        keyword in " ".join(missing_information + risk_flags)
        for keyword in ("工作方式", "薪资", "外包", "驻场")
    ):
        return "confirm_details"
    if review_level == "not_recommended":
        return "polite_decline"
    primary_intent = hr_intent.get("primary_intent") if hr_intent else None
    if primary_intent in {"project_experience", "technical_question"}:
        return "project_intro"
    if primary_intent == "interview_schedule":
        return "interview_schedule"
    if primary_intent == "salary_expectation":
        return "salary_expectation"
    return "none"


def _build_llm_ready_context(
    application: ApplicationItem,
    review_level: str,
    confidence: str,
    recommended_action: str,
    risk_flags: List[str],
    missing_information: List[str],
    evidence: List[Dict[str, str]],
    job_match: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "application_summary": {
            "company_name": application.company_name,
            "job_title": application.job_title,
            "status": application.status,
            "source_type": application.source_type,
        },
        "job_match_summary": {
            "match_score": job_match.get("match_score"),
            "match_level": job_match.get("match_level"),
        },
        "risks_summary": risk_flags,
        "missing_information": missing_information,
        "suggested_action": recommended_action,
        "review_level": review_level,
        "confidence": confidence,
        "evidence_summary": [item["text"] for item in evidence[:8]],
    }


def _dedupe(items: List[str]) -> List[str]:
    return list(dict.fromkeys(item for item in items if item))
