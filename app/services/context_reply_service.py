import re
from typing import Dict, List


PROJECT_CONTEXT_INTENTS = {
    "project_experience",
    "technical_question",
    "business_proposal",
}

CONTEXT_KEYWORDS = [
    "RAG",
    "Agent",
    "FastAPI",
    "LLM",
    "Embedding",
    "向量",
    "检索",
    "知识库",
    "SQLite",
    "多轮",
    "HR",
    "智能招聘",
    "求职",
    "Workflow",
    "工作流",
    "医药",
    "企业知识库",
    "问答系统",
    "API",
    "Prompt",
]

FORBIDDEN_CLAIMS = [
    "完整生产级智能招聘系统",
    "自动发送 HR 消息",
    "自动招聘决策",
    "完整 Multi-Agent 平台",
]


def select_relevant_context_snippets(
    message: str,
    resume_text: str,
    project_context: str,
    available_projects: List[str],
    max_snippets: int = 3,
) -> List[Dict[str, str]]:
    candidates = []
    candidates.extend(_split_source("resume_text", resume_text))
    candidates.extend(_split_source("project_context", project_context))
    candidates.extend(
        {
            "source": "available_projects",
            "text": project.strip(),
        }
        for project in available_projects
        if project.strip()
    )

    if not candidates:
        return []

    message_terms = _extract_message_terms(message)
    scored = []
    for candidate in candidates:
        score = _score_text(candidate["text"], message_terms)
        scored.append((score, candidate))

    matched = [
        candidate
        for score, candidate in sorted(scored, key=lambda item: item[0], reverse=True)
        if score > 0
    ]
    selected = matched[:max_snippets]
    if not selected:
        selected = [candidate for _, candidate in scored[:max_snippets] if candidate["text"]]

    return [
        {
            "source": item["source"],
            "text": _truncate(item["text"], 160),
        }
        for item in selected
    ]


def build_context_enhanced_reply(
    intent: str,
    snippets: List[Dict[str, str]],
    truth_boundaries: List[str],
) -> str:
    if not snippets:
        return (
            "这类问题涉及项目经历、技术细节或方案设计。当前 candidate_profile 里还缺少足够的 "
            "resume_text / project_context 片段，建议先补充真实项目上下文后再生成回复草稿。"
            "在没有上下文前，不应该编造完整生产级系统、自动投递或自动发送 HR 消息等经历。"
        )

    context_text = "；".join(snippet["text"] for snippet in snippets)
    boundary_text = _truth_boundary_text(truth_boundaries)

    if intent == "technical_question":
        return (
            "这个技术问题我可以结合当前项目实践来回答。我的相关实践主要包括："
            f"{context_text}。如果涉及生产级高并发、完整权限体系或大规模线上系统，"
            f"我会说明目前仍属于学习和项目 Demo 阶段。{boundary_text}"
        )

    if intent == "business_proposal":
        return (
            "如果从 PoC 方案角度，我会先拆成需求确认、数据来源、规则/检索/LLM 边界、"
            "人工确认和测试验收几个步骤。结合我当前项目经验，可以参考："
            f"{context_text}。完整生产落地还需要结合企业系统权限、数据安全和实际流程。"
            f"{boundary_text}"
        )

    return (
        "关于项目经历，我目前更适合从自己做过的 AI 应用 / RAG / Agent Demo 项目角度来说明。"
        f"相关经历包括：{context_text}。这些项目主要是学习与求职展示级 Demo，"
        f"不会夸大为完整生产级系统。{boundary_text}"
    )


def context_sources(snippets: List[Dict[str, str]]) -> List[str]:
    return list(dict.fromkeys(snippet["source"] for snippet in snippets))


def _split_source(source: str, text: str) -> List[Dict[str, str]]:
    parts = [
        part.strip()
        for part in re.split(r"[\n。；;]+", text or "")
        if part.strip()
    ]
    return [{"source": source, "text": part} for part in parts]


def _extract_message_terms(message: str) -> List[str]:
    terms = [keyword for keyword in CONTEXT_KEYWORDS if keyword.lower() in message.lower()]
    terms.extend(
        term
        for term in re.split(r"[\s，。！？、,.!?]+", message)
        if len(term.strip()) >= 3
    )
    return list(dict.fromkeys(terms))


def _score_text(text: str, message_terms: List[str]) -> int:
    lowered = text.lower()
    score = 0
    for keyword in CONTEXT_KEYWORDS:
        if keyword.lower() in lowered:
            score += 3
    for term in message_terms:
        if term.lower() in lowered:
            score += 2
    return score


def _truth_boundary_text(truth_boundaries: List[str]) -> str:
    cleaned = [
        _sanitize_boundary(boundary.strip())
        for boundary in truth_boundaries
        if boundary.strip()
    ]
    if cleaned:
        return "边界说明：" + "；".join(cleaned[:2]) + "。"
    return "所有内容都需要用户确认后再发送，不能夸大为未实际完成的生产级经验。"


def _sanitize_boundary(text: str) -> str:
    replacements = {
        "完整生产级智能招聘系统": "完整线上系统",
        "自动发送 HR 消息": "外发消息需人工确认",
        "自动招聘决策": "招聘决策类能力",
        "完整 Multi-Agent 平台": "完整多智能体平台",
    }
    sanitized = text
    for source, target in replacements.items():
        sanitized = sanitized.replace(source, target)
    return sanitized


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
