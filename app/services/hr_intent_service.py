from typing import Any, Dict, List, Optional


INTENT_KEYWORDS: Dict[str, List[str]] = {
    "salary_expectation": [
        "期望薪资",
        "薪资",
        "工资",
        "待遇",
        "多少钱",
        "薪资要求",
        "最低多少",
        "package",
        "salary",
    ],
    "availability": [
        "到岗",
        "入职",
        "多久能到",
        "一周",
        "最快什么时候",
        "入职时间",
        "available",
    ],
    "location_preference": [
        "城市",
        "地点",
        "杭州",
        "上海",
        "重庆",
        "深圳",
        "北京",
        "远程",
        "base",
        "工作地",
    ],
    "relocation": [
        "外地",
        "异地",
        "搬家",
        "relocate",
        "relocation",
        "去外地",
    ],
    "outsourcing": [
        "外包",
        "外派",
        "乙方",
        "客户现场",
        "派驻",
        "outsourcing",
    ],
    "onsite": [
        "驻场",
        "现场办公",
        "到公司办公",
        "坐班",
        "on-site",
        "onsite",
    ],
    "remote": [
        "远程",
        "居家",
        "remote",
        "混合办公",
        "hybrid",
    ],
    "overtime": [
        "加班",
        "强度",
        "996",
        "大小周",
        "工作强度",
    ],
    "business_trip": [
        "出差",
        "差旅",
        "长期出差",
        "短期出差",
    ],
    "project_experience": [
        "项目",
        "经历",
        "做过",
        "rag",
        "agent",
        "智能招聘",
        "知识库",
        "workflow",
        "工作流",
        "简历筛选",
    ],
    "technical_question": [
        "怎么实现",
        "技术方案",
        "架构",
        "embedding",
        "向量",
        "检索",
        "reranker",
        "fastapi",
        "langchain",
        "sqlite",
        "faiss",
        "bm25",
    ],
    "business_proposal": [
        "方案",
        "怎么做",
        "落地",
        "业务",
        "智能招聘",
        "质量审核",
        "知识库",
        "客服",
        "自动化",
        "ai改造",
    ],
    "interview_schedule": [
        "面试",
        "电话",
        "视频",
        "沟通",
        "几点",
        "时间",
        "约",
        "方便吗",
    ],
    "resume_request": [
        "简历",
        "附件",
        "pdf",
        "作品集",
        "项目介绍",
        "发一份",
    ],
    "github_request": [
        "github",
        "代码",
        "仓库",
        "项目地址",
        "repo",
    ],
}


INTENT_PRIORITY = [
    "interview_schedule",
    "salary_expectation",
    "availability",
    "relocation",
    "outsourcing",
    "onsite",
    "remote",
    "location_preference",
    "project_experience",
    "technical_question",
    "business_proposal",
    "resume_request",
    "github_request",
    "overtime",
    "business_trip",
    "unknown",
]


INTENT_SOURCE_RULES: Dict[str, Dict[str, bool]] = {
    "salary_expectation": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "availability": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "location_preference": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "relocation": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "outsourcing": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "onsite": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "remote": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "overtime": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "business_trip": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "project_experience": {
        "need_profile": True,
        "need_resume_context": True,
        "need_project_context": True,
        "need_application_history": False,
        "need_llm": True,
    },
    "technical_question": {
        "need_profile": True,
        "need_resume_context": True,
        "need_project_context": True,
        "need_application_history": False,
        "need_llm": True,
    },
    "business_proposal": {
        "need_profile": True,
        "need_resume_context": True,
        "need_project_context": True,
        "need_application_history": False,
        "need_llm": True,
    },
    "interview_schedule": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": True,
        "need_llm": False,
    },
    "resume_request": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "github_request": {
        "need_profile": True,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
    "unknown": {
        "need_profile": False,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    },
}


RISK_LEVEL_RULES = {
    "salary_expectation": "medium",
    "availability": "low",
    "location_preference": "low",
    "remote": "low",
    "relocation": "medium",
    "outsourcing": "medium",
    "onsite": "medium",
    "overtime": "medium",
    "business_trip": "medium",
    "project_experience": "high",
    "technical_question": "high",
    "business_proposal": "high",
    "interview_schedule": "medium",
    "resume_request": "medium",
    "github_request": "medium",
    "unknown": "medium",
}


RISK_ORDER = {"low": 1, "medium": 2, "high": 3}


def analyze_hr_message(
    message: str,
    company_name: Optional[str] = None,
    job_title: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_message = message.lower()
    matched_keywords: Dict[str, List[str]] = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        hits = [
            keyword
            for keyword in keywords
            if keyword.lower() in normalized_message
        ]
        if hits:
            matched_keywords[intent] = hits

    _remove_contextual_false_positives(normalized_message, matched_keywords)
    intents = _sort_intents(list(matched_keywords.keys()))
    if not intents:
        intents = ["unknown"]
        matched_keywords = {"unknown": []}

    primary_intent = intents[0]
    source_flags = _merge_source_rules(intents)
    risk_level = _resolve_risk_level(intents)

    return {
        "original_message": message,
        "company_name": company_name,
        "job_title": job_title,
        "intents": intents,
        "primary_intent": primary_intent,
        **source_flags,
        "risk_level": risk_level,
        "matched_keywords": matched_keywords,
        "suggested_next_action": _suggest_next_action(intents),
    }


def _sort_intents(intents: List[str]) -> List[str]:
    return sorted(intents, key=lambda intent: INTENT_PRIORITY.index(intent))


def _remove_contextual_false_positives(
    normalized_message: str,
    matched_keywords: Dict[str, List[str]]
) -> None:
    project_hits = matched_keywords.get("project_experience")
    if (
        project_hits
        and "github_request" in matched_keywords
        and set(project_hits) == {"项目"}
    ):
        matched_keywords.pop("project_experience")

    resume_hits = matched_keywords.get("resume_request")
    if (
        resume_hits
        and "简历筛选" in normalized_message
        and set(resume_hits) == {"简历"}
    ):
        matched_keywords.pop("resume_request")


def _merge_source_rules(intents: List[str]) -> Dict[str, bool]:
    merged = {
        "need_profile": False,
        "need_resume_context": False,
        "need_project_context": False,
        "need_application_history": False,
        "need_llm": False,
    }
    for intent in intents:
        rules = INTENT_SOURCE_RULES[intent]
        for key, value in rules.items():
            merged[key] = merged[key] or value
    return merged


def _resolve_risk_level(intents: List[str]) -> str:
    levels = [RISK_LEVEL_RULES[intent] for intent in intents]
    return max(levels, key=lambda level: RISK_ORDER[level])


def _suggest_next_action(intents: List[str]) -> str:
    if "interview_schedule" in intents:
        return "Prepare a schedule reply draft, but the interview time must be confirmed by the user."
    if any(
        intent in intents
        for intent in ["project_experience", "technical_question", "business_proposal"]
    ):
        return "Read candidate_profile, resume_text, and project_context before generating a truth-bounded draft."
    if any(intent in intents for intent in ["resume_request", "github_request"]):
        return "Use candidate_profile and user-confirmed materials before sharing any external link or file."
    if "unknown" in intents:
        return "Ask the user for clarification before generating a reply draft."
    return "Use candidate_profile to generate a safe reply draft."
