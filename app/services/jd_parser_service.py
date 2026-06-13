import re
from typing import Any, Dict, List, Optional


SOURCE_RULES = [
    ("boss", ["boss", "BOSS", "boss直聘"]),
    ("liepin", ["猎聘"]),
    ("lagou", ["拉勾"]),
    ("zhilian", ["智联"]),
    ("51job", ["前程", "51job"]),
    ("official_website", ["官网", "official"]),
    ("linkedin", ["linkedin", "领英"]),
    ("referral", ["内推", "referral"]),
]

TECH_KEYWORDS = [
    "Python",
    "FastAPI",
    "Flask",
    "Django",
    "Java",
    "Spring Boot",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "SQLite",
    "Redis",
    "Docker",
    "Linux",
    "Git",
    "LLM",
    "RAG",
    "Agent",
    "LangChain",
    "LangGraph",
    "Embedding",
    "Vector Database",
    "FAISS",
    "Milvus",
    "Elasticsearch",
    "BM25",
    "Rerank",
    "Prompt Engineering",
    "OpenAI",
    "DeepSeek",
    "Qwen",
    "DashScope",
    "PyTorch",
    "LoRA",
    "vLLM",
    "Ollama",
    "React",
]

REQUIRED_SKILL_HINTS = [
    "要求",
    "任职要求",
    "技能要求",
    "熟悉",
    "掌握",
    "经验",
    "优先",
]

LOCATION_KEYWORDS = [
    "远程",
    "杭州",
    "上海",
    "北京",
    "深圳",
    "广州",
    "成都",
    "西安",
    "南京",
    "苏州",
]


def normalize_source(source: Optional[str]) -> str:
    """标准化岗位来源。

    主要输入：原始来源文本，例如 BOSS直聘、官网、内推。
    主要输出：固定枚举 source_type。
    副作用：不写数据库，不调用 LLM / RAG / Embedding。
    """
    if not source or not source.strip():
        return "manual"
    source_text = source.strip()
    lowered = source_text.lower()
    for source_type, keywords in SOURCE_RULES:
        for keyword in keywords:
            if keyword.lower() in lowered or keyword in source_text:
                return source_type
    return "other"


def extract_jd_keywords(jd_text: str) -> List[str]:
    """从 JD 文本中抽取规则关键词。

    主要输入：JD 原文。
    主要输出：命中的技术关键词列表，保留预设技术名词大小写并去重。
    副作用：不写数据库；只是规则匹配，不调用 LLM，也不声称语义理解。
    """
    if not jd_text:
        return []
    lowered = jd_text.lower()
    matched = [
        keyword
        for keyword in TECH_KEYWORDS
        if keyword.lower() in lowered
    ]
    return _dedupe(matched)


def extract_required_skills(jd_text: str) -> List[str]:
    """抽取任职要求附近的技能关键词。

    主要输入：JD 原文。
    主要输出：偏向“要求/熟悉/掌握/经验”等语句附近的技术关键词。
    副作用：不写数据库；本地规则 baseline，不调用 LLM / RAG / Embedding。
    """
    keywords = extract_jd_keywords(jd_text)
    if not jd_text or not keywords:
        return []
    segments = re.split(r"[。；;\n]", jd_text)
    requirement_text = "\n".join(
        segment
        for segment in segments
        if any(hint in segment for hint in REQUIRED_SKILL_HINTS)
    )
    if not requirement_text:
        return keywords[:]
    lowered_requirement = requirement_text.lower()
    required = [
        keyword
        for keyword in keywords
        if keyword.lower() in lowered_requirement
    ]
    return required or keywords[:]


def extract_years_requirement(jd_text: str) -> str:
    """提取 JD 中的工作年限要求。

    主要输入：JD 原文。
    主要输出：如 1年以上、1-3年、3年以上、经验不限、应届；未命中返回空字符串。
    副作用：不写数据库，不调用 LLM。
    """
    if not jd_text:
        return ""
    patterns = [
        r"\d+\s*-\s*\d+\s*年",
        r"\d+\s*年以上",
        r"经验不限",
        r"应届",
    ]
    for pattern in patterns:
        match = re.search(pattern, jd_text)
        if match:
            return re.sub(r"\s+", "", match.group(0))
    return ""


def extract_location_requirement(jd_text: str) -> str:
    """提取 JD 中出现的地点要求。

    主要输入：JD 原文。
    主要输出：命中的地点关键词，用中文逗号连接；未命中返回空字符串。
    副作用：不写数据库，不调用 LLM。
    """
    if not jd_text:
        return ""
    locations = [location for location in LOCATION_KEYWORDS if location in jd_text]
    return "、".join(_dedupe(locations))


def extract_remote_type(jd_text: str) -> str:
    """提取工作方式类型。

    主要输入：JD 原文。
    主要输出：remote、hybrid、onsite 或 unknown。
    副作用：不写数据库，不调用 LLM。
    """
    if not jd_text:
        return "unknown"
    lowered = jd_text.lower()
    if "远程" in jd_text or "remote" in lowered:
        return "remote"
    if "混合" in jd_text or "hybrid" in lowered:
        return "hybrid"
    onsite_keywords = ["现场", "驻场", "到岗", "坐班", "现场办公", "onsite"]
    if any(keyword in jd_text or keyword in lowered for keyword in onsite_keywords):
        return "onsite"
    return "unknown"


def summarize_jd_rule_based(jd_text: str) -> str:
    """生成本地规则版 JD 摘要。

    主要输入：JD 原文。
    主要输出：1-3 句中文摘要，只基于规则抽取字段拼接；JD 为空时返回空字符串。
    副作用：不写数据库，不调用 LLM，不编造 JD 未提到的信息。
    """
    if not jd_text:
        return ""
    keywords = extract_jd_keywords(jd_text)
    years = extract_years_requirement(jd_text)
    location = extract_location_requirement(jd_text)
    remote_type = extract_remote_type(jd_text)
    parts = []
    if keywords:
        parts.append(f"该岗位主要涉及 {'、'.join(keywords[:8])} 等方向")
    if years:
        parts.append(f"经验要求为 {years}")
    if location:
        parts.append(f"地点要求包含 {location}")
    if remote_type != "unknown":
        parts.append(f"工作方式倾向 {remote_type}")
    if not parts:
        return "该 JD 暂未命中明确的规则关键词。该摘要由本地规则生成，仅用于求职者侧快速筛选。"
    return "。".join(parts) + "。该摘要由本地规则生成，仅用于求职者侧快速筛选。"


def parse_jd(jd_text: str, source: Optional[str] = None) -> Dict[str, Any]:
    """统一解析 JD 和岗位来源。

    主要输入：JD 原文和可选岗位来源文本。
    主要输出：source_type、jd_summary、jd_keywords、jd_required_skills、年限、地点和工作方式。
    副作用：不写数据库；不调用 LLM / RAG / Embedding，不抓取岗位。
    """
    return {
        "source_type": normalize_source(source),
        "jd_summary": summarize_jd_rule_based(jd_text),
        "jd_keywords": extract_jd_keywords(jd_text),
        "jd_required_skills": extract_required_skills(jd_text),
        "jd_years_requirement": extract_years_requirement(jd_text),
        "jd_location_requirement": extract_location_requirement(jd_text),
        "jd_remote_type": extract_remote_type(jd_text),
    }


def _dedupe(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))
