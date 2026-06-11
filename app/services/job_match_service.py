from typing import Any, Dict, List, Set, Tuple

from app.schemas.application_schema import ApplicationUpdateRequest
from app.schemas.job_match_schema import JobMatchDimension
from app.services.application_service import get_application, update_application
from app.services.profile_service import get_candidate_profile


SCORING_VERSION = "rule_based_v1"

ROLE_KEYWORDS = [
    "AI应用",
    "AI 应用",
    "大模型",
    "LLM",
    "RAG",
    "Agent",
    "智能体",
    "工作流",
    "Workflow",
    "知识库",
    "Python后端",
    "Python 后端",
    "AI application",
    "AI Application",
]

TECH_KEYWORDS = [
    "Python",
    "FastAPI",
    "API",
    "SQLite",
    "RAG",
    "Agent",
    "LLM",
    "Embedding",
    "向量",
    "检索",
    "知识库",
    "Prompt",
    "Workflow",
    "工作流",
]

PROJECT_KEYWORDS = [
    "企业知识库",
    "医药文档",
    "RAG",
    "AI Job Agent",
    "智能求职",
    "智能招聘",
    "HR",
    "Workflow",
    "工作流",
    "文档问答",
    "问答系统",
]

PREFERENCE_POSITIVE_KEYWORDS = [
    "远程",
    "混合办公",
    "杭州",
    "上海",
    "重庆",
    "Remote",
    "remote",
    "hybrid",
]

RISK_KEYWORDS = {
    "外包": "JD 可能涉及外包，需要确认岗位性质",
    "外派": "JD 可能涉及外派，需要确认工作地点和合同关系",
    "驻场": "JD 可能涉及驻场，需要确认是否长期客户现场",
    "客户现场": "JD 可能涉及客户现场，需要确认工作方式",
    "长期出差": "JD 可能涉及长期出差，需要谨慎评估",
    "频繁出差": "JD 可能涉及频繁出差，需要谨慎评估",
    "996": "JD 可能涉及高强度工作，需要确认工作节奏",
    "大小周": "JD 可能涉及大小周，需要确认工作制度",
    "高强度加班": "JD 可能涉及高强度加班，需要确认边界",
    "销售性质": "JD 可能偏销售性质，需要确认岗位职责",
    "纯销售": "JD 可能偏纯销售，需要确认岗位职责",
}

TRUTH_BOUNDARY_KEYWORDS = {
    "完整智能招聘系统": "JD 可能涉及完整智能招聘系统，需要注意 truth boundary",
    "自动招聘": "JD 可能涉及自动招聘，需要注意 human-in-the-loop 边界",
    "自动投递": "JD 可能涉及自动投递，需要注意项目边界",
}


def analyze_job_match(
    application_id: int,
    update_application: bool = True,
) -> Dict[str, Any]:
    application = get_application(application_id)
    if application is None:
        raise ValueError("application not found")

    profile = get_candidate_profile()
    if profile is None:
        raise ValueError("candidate_profile not found")

    job_text = "\n".join(
        [
            application.job_title or "",
            application.jd_text or "",
            application.notes or "",
        ]
    )
    profile_projects_text = "\n".join(profile.available_projects)

    role_dimension = _score_keywords("role_fit", 25, job_text, ROLE_KEYWORDS)
    tech_dimension = _score_keywords("tech_stack_fit", 35, job_text, TECH_KEYWORDS)
    project_dimension = _score_project_relevance(
        job_text,
        profile_projects_text,
    )
    preference_dimension, preference_risks = _score_preference(job_text)

    dimensions = [
        role_dimension,
        tech_dimension,
        project_dimension,
        preference_dimension,
    ]
    match_score = sum(dimension.score for dimension in dimensions)
    match_score = max(0, min(100, match_score))
    match_level = _match_level(match_score)
    recommendation = _recommendation(match_level)
    matched_signals = _dedupe(
        signal
        for dimension in dimensions
        for signal in dimension.matched_signals
    )
    missing_signals = _dedupe(
        signal
        for dimension in dimensions
        for signal in dimension.missing_signals
    )
    risk_flags = _dedupe(preference_risks + _truth_boundary_risks(job_text))
    suggested_next_action = _suggest_next_action(match_level, matched_signals, risk_flags)

    application_update_fields: Dict[str, Any] = {}
    application_updated = False
    if update_application:
        application_update_fields = {
            "match_score": match_score,
            "next_action": suggested_next_action,
            "risk_flags": risk_flags,
        }
        updated = update_application_record(application_id, application_update_fields)
        application_updated = updated

    return {
        "application_id": application.id,
        "company_name": application.company_name,
        "job_title": application.job_title,
        "match_score": match_score,
        "match_level": match_level,
        "recommendation": recommendation,
        "dimensions": dimensions,
        "matched_signals": matched_signals,
        "missing_signals": missing_signals,
        "risk_flags": risk_flags,
        "suggested_next_action": suggested_next_action,
        "application_updated": application_updated,
        "application_update_fields": application_update_fields,
        "debug": {
            "scoring_version": SCORING_VERSION,
            "used_sources": ["candidate_profile", "application"],
            "llm_used": False,
            "update_application_requested": update_application,
        },
    }


def update_application_record(
    application_id: int,
    update_fields: Dict[str, Any],
) -> bool:
    updated = update_application(
        application_id,
        ApplicationUpdateRequest(**update_fields),
    )
    return updated is not None


def _score_keywords(
    name: str,
    max_score: int,
    text: str,
    keywords: List[str],
) -> JobMatchDimension:
    matched = _matched_keywords(text, keywords)
    missing = _missing_keywords(keywords, matched, limit=4)
    score = _proportional_score(len(matched), len(keywords), max_score)
    return JobMatchDimension(
        name=name,
        score=score,
        max_score=max_score,
        matched_signals=matched,
        missing_signals=missing,
    )


def _score_project_relevance(
    job_text: str,
    profile_projects_text: str,
) -> JobMatchDimension:
    combined_text = f"{job_text}\n{profile_projects_text}"
    matched = _matched_keywords(combined_text, PROJECT_KEYWORDS)
    missing = _missing_keywords(PROJECT_KEYWORDS, matched, limit=4)
    score = _proportional_score(len(matched), len(PROJECT_KEYWORDS), 20)
    return JobMatchDimension(
        name="project_relevance",
        score=score,
        max_score=20,
        matched_signals=matched,
        missing_signals=missing,
    )


def _score_preference(text: str) -> Tuple[JobMatchDimension, List[str]]:
    positive = _matched_keywords(text, PREFERENCE_POSITIVE_KEYWORDS)
    risk_matches = [
        keyword for keyword in RISK_KEYWORDS if keyword.lower() in text.lower()
    ]
    base_score = 12
    positive_score = min(8, len(positive) * 2)
    risk_penalty = min(12, len(risk_matches) * 4)
    score = max(0, min(20, base_score + positive_score - risk_penalty))
    risk_flags = [RISK_KEYWORDS[keyword] for keyword in risk_matches]
    missing = ["远程/混合办公/目标城市信号"] if not positive else []
    return (
        JobMatchDimension(
            name="preference_fit",
            score=score,
            max_score=20,
            matched_signals=positive,
            missing_signals=missing,
        ),
        risk_flags,
    )


def _matched_keywords(text: str, keywords: List[str]) -> List[str]:
    lowered_text = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered_text]


def _missing_keywords(
    keywords: List[str],
    matched: List[str],
    limit: int,
) -> List[str]:
    matched_set: Set[str] = set(matched)
    return [keyword for keyword in keywords if keyword not in matched_set][:limit]


def _proportional_score(hit_count: int, total_count: int, max_score: int) -> int:
    if hit_count <= 0 or total_count <= 0:
        return 0
    coverage = min(1.0, hit_count / max(1, total_count / 2))
    return round(max_score * coverage)


def _truth_boundary_risks(text: str) -> List[str]:
    lowered_text = text.lower()
    return [
        risk
        for keyword, risk in TRUTH_BOUNDARY_KEYWORDS.items()
        if keyword.lower() in lowered_text
    ]


def _match_level(score: int) -> str:
    if score >= 80:
        return "strong_match"
    if score >= 60:
        return "possible_match"
    if score >= 40:
        return "weak_match"
    return "not_recommended"


def _recommendation(match_level: str) -> str:
    recommendations = {
        "strong_match": "建议优先跟进",
        "possible_match": "可以进一步了解",
        "weak_match": "建议谨慎评估",
        "not_recommended": "不建议优先投入",
    }
    return recommendations[match_level]


def _suggest_next_action(
    match_level: str,
    matched_signals: List[str],
    risk_flags: List[str],
) -> str:
    if match_level == "strong_match":
        base = "优先跟进，并准备 AI 应用 / RAG / Agent 项目讲法"
    elif match_level == "possible_match":
        base = "进一步了解岗位职责、团队方向和技术栈"
    elif match_level == "weak_match":
        base = "谨慎评估岗位匹配度，补充确认关键职责"
    else:
        base = "不建议优先投入，除非后续信息显示岗位更匹配"

    if risk_flags:
        return f"{base}；同时确认风险点：{risk_flags[0]}"
    if matched_signals:
        return f"{base}；可重点突出 {matched_signals[0]} 相关经验"
    return base


def _dedupe(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))
