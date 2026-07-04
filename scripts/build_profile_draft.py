"""从 current_resume.txt 生成可人工审核的 candidate_profile 草稿。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.profile_schema import CandidateProfileInput


DEFAULT_RESUME = Path("docs/input/current_resume.txt")
DEFAULT_SOURCE_REPORT = Path("docs/input/resume_extract_report.md")
DEFAULT_OUTPUT = Path("docs/input/generated/candidate_profile_draft.json")
DEFAULT_REPORT = Path("docs/input/generated/candidate_profile_draft_report.md")

EDUCATION_LEVELS = ("博士", "研究生", "硕士", "本科", "大专", "专科")
MAJOR_ALIASES = (
    "数据科学与大数据技术",
    "大数据技术应用",
    "大数据技术",
)
TARGET_ROLE_RULES = (
    ("AI应用开发工程师", ("AI应用开发工程师", "AI 应用开发工程师")),
    ("大模型应用开发工程师", ("大模型应用开发工程师", "大模型 应用开发工程师")),
    ("Python 后端 + AI", ("Python 后端", "Python后端")),
    ("RAG & Agent 应用开发", ("RAG", "Agent")),
)
TECHNOLOGIES = (
    "FastAPI", "RAG", "FAISS", "BM25", "Reranker", "LangChain",
    "LangGraph", "SQLite", "React", "Java", "SpringBoot", "Python",
    "Embedding", "LLM", "Coze", "飞书",
)
PROJECT_RULES = (
    ("FastAPI + RAG 企业知识库问答系统", ("企业知识库", "RAG")),
    ("AI Job Agent 智能求职助手", ("AI Job Agent",)),
    ("医药文档 RAG 智能问答系统", ("医药", "RAG")),
    ("Coze / 飞书 Workflow 旅游规划助手", ("旅游", "Workflow")),
)
TRUTH_BOUNDARIES = [
    "AI Job Agent 不自动投递岗位。",
    "AI Job Agent 不自动发送真实 HR 消息。",
    "AI Job Agent 不自动确认面试时间。",
    "AI Job Agent 未接入真实招聘平台。",
    "RAG 项目和 AI Job Agent 项目能力边界需要区分。",
    "不把学习中或规划中的能力写成已实现项目经验。",
]


def read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"required input does not exist: {path}")
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError(f"required input is empty: {path}")
    return normalize_text(text)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_name(text: str) -> str | None:
    explicit = re.search(r"(?:姓名|Name)\s*[：:]\s*([\u4e00-\u9fff]{2,6})", text, re.I)
    if explicit:
        return explicit.group(1)
    for line in text.splitlines()[:12]:
        candidate = line.strip()
        if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", candidate):
            return candidate
    return None


def extract_education(text: str) -> str | None:
    return next((level for level in EDUCATION_LEVELS if level in text), None)


def extract_major(text: str) -> str | None:
    explicit = re.search(
        r"专业\s*(?:[：:]|是|为)\s*([^，,。；;\n]{2,30})",
        text,
    )
    if explicit:
        return explicit.group(1).strip()
    known_major = next((major for major in MAJOR_ALIASES if major in text), None)
    if known_major:
        return known_major
    suffix = re.search(
        r"(?:^|[，,。；;\n\s])([A-Za-z0-9+#/\-\u4e00-\u9fff]{2,30})专业",
        text,
    )
    if suffix:
        return suffix.group(1).strip()
    return None


def extract_target_roles(text: str) -> list[str]:
    roles = [
        canonical
        for canonical, aliases in TARGET_ROLE_RULES
        if any(alias.lower() in text.lower() for alias in aliases)
    ]
    if not roles and ("AI" in text or "大模型" in text):
        roles.append("AI应用开发工程师")
    return roles


def extract_technologies(text: str) -> list[str]:
    lowered = text.lower()
    return [technology for technology in TECHNOLOGIES if technology.lower() in lowered]


def extract_projects(text: str) -> list[str]:
    lowered = text.lower()
    projects: list[str] = []
    for project, signals in PROJECT_RULES:
        if all(signal.lower() in lowered for signal in signals):
            projects.append(project)
    return projects


def build_project_context(
    text: str, projects: list[str], technologies: list[str]
) -> str:
    keywords = tuple(
        keyword.lower()
        for keyword in (
            "项目", "RAG", "Agent", "FastAPI", "FAISS", "BM25", "Reranker",
            "LangChain", "LangGraph", "SQLite", "React", "Coze", "飞书",
        )
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    selected: list[str] = []
    for index, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in keywords):
            selected.extend(lines[index : index + 3])
    selected = list(dict.fromkeys(selected))
    headings = [
        "以下内容由 current_resume.txt 规则提取，写入正式 profile 前需要用户审核。",
        f"检测到的项目：{'、'.join(projects) if projects else '待人工确认'}。",
        f"检测到的技术栈：{'、'.join(technologies) if technologies else '待人工确认'}。",
    ]
    if selected:
        headings.extend(["", "简历相关原文片段：", *selected[:40]])
    return "\n".join(headings).strip()


def build_draft(resume_text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    name = extract_name(resume_text)
    education = extract_education(resume_text)
    major = extract_major(resume_text)
    target_roles = extract_target_roles(resume_text)
    technologies = extract_technologies(resume_text)
    projects = extract_projects(resume_text)
    payload: dict[str, Any] = {
        "expected_salary_min": None,
        "expected_salary_max": None,
        "minimum_salary": None,
        "salary_note": "薪资范围和底线需要用户人工确认，不自动生成承诺。",
        "availability_note": "面试时间和到岗时间需要用户人工确认，系统不代替用户敲定。",
        "preferred_cities": [],
        "acceptable_cities": [],
        "relocation_policy": "是否接受异地机会需要用户确认。",
        "outsourcing_policy": "是否接受外包、驻场、合同主体不清晰岗位需要用户确认。",
        "onsite_policy": "现场办公、驻场地点和周期需要用户人工确认。",
        "remote_policy": "远程、混合或现场办公偏好需要用户人工确认。",
        "overtime_policy": "单休、大小周、996 或长期高强度加班需要用户确认。",
        "business_trip_policy": "出差频率、地点和周期需要用户人工确认。",
        "target_roles": target_roles,
        "available_projects": projects,
        "truth_boundaries": TRUTH_BOUNDARIES,
        "resume_text": resume_text,
        "project_context": build_project_context(resume_text, projects, technologies),
    }
    validated = CandidateProfileInput(**payload)
    payload = (
        validated.model_dump()
        if hasattr(validated, "model_dump")
        else validated.dict()
    )
    facts = {
        "name": name,
        "education": education,
        "major": major,
        "target_roles": target_roles,
        "technologies": technologies,
        "projects": projects,
    }
    return payload, facts


def write_report(
    *,
    path: Path,
    resume_path: Path,
    source_report_path: Path,
    payload: dict[str, Any],
    facts: dict[str, Any],
    source_report_exists: bool,
) -> None:
    warnings = []
    for label in ("name", "education", "major"):
        if not facts[label]:
            warnings.append(f"未从 current_resume.txt 明确提取 {label}，需要用户确认。")
    if facts["major"] == "大数据技术":
        warnings.append(
            "detected_major 仅识别到“大数据技术”，专业完整名称可能需要用户确认。"
        )
    if not facts["target_roles"]:
        warnings.append("未检测到明确求职方向，需要用户确认。")
    if not facts["projects"]:
        warnings.append("未检测到已知项目名称，需要用户确认。")
    lines = [
        "# Candidate Profile Draft Report",
        "",
        f"- 生成时间：`{datetime.now(timezone.utc).isoformat()}`",
        f"- 标准简历输入：`{resume_path}`",
        f"- 抽取报告输入：`{source_report_path}`",
        f"- 抽取报告存在：`{source_report_exists}`",
        f"- CandidateProfileInput 校验：`passed`",
        f"- resume_text 字符数：`{len(payload['resume_text'])}`",
        f"- project_context 字符数：`{len(payload['project_context'])}`",
        "",
        "## 规则提取结果",
        "",
        f"- 姓名：`{facts['name'] or '待人工确认'}`",
        f"- 学历：`{facts['education'] or '待人工确认'}`",
        f"- 专业：`{facts['major'] or '待人工确认'}`",
        f"- detected_major：`{facts['major'] or '待人工确认'}`",
        f"- 求职方向：`{'、'.join(facts['target_roles']) or '待人工确认'}`",
        f"- 技术栈：`{'、'.join(facts['technologies']) or '待人工确认'}`",
        f"- 项目：`{'、'.join(facts['projects']) or '待人工确认'}`",
        "",
        "## Warnings",
        "",
        *(f"- {warning}" for warning in warnings),
    ]
    if not warnings:
        lines.append("- 无")
    lines.extend(
        [
            "",
            "## 使用边界",
            "",
            "该 JSON 是用户确认前的 `candidate_profile_draft`，不是正式 `candidate_profile`。",
            "本脚本不调用 `/profile`、不写数据库、不调用 LLM。",
            "Agent Workflow 不直接读取 `current_resume.txt`，仍以正式 `candidate_profile` 为事实源。",
            "",
            "提交前必须人工核对学历、专业、求职方向、项目归属、偏好和 truth boundaries。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a reviewable CandidateProfileInput draft without database writes."
    )
    parser.add_argument("--resume", default=str(DEFAULT_RESUME))
    parser.add_argument("--source-report", default=str(DEFAULT_SOURCE_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    resume_path = Path(args.resume)
    source_report_path = Path(args.source_report)
    output_path = Path(args.output)
    report_path = Path(args.report)
    try:
        resume_text = read_text(resume_path)
        source_report_exists = source_report_path.is_file()
        if source_report_exists:
            source_report_path.read_text(encoding="utf-8-sig")
        payload, facts = build_draft(resume_text)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_report(
        path=report_path,
        resume_path=resume_path,
        source_report_path=source_report_path,
        payload=payload,
        facts=facts,
        source_report_exists=source_report_exists,
    )
    print(f"Generated: {output_path}")
    print(f"Generated: {report_path}")
    print(f"Education detected: {facts['education'] or 'not found'}")
    print(f"Major detected: {facts['major'] or 'not found'}")
    print(f"Target roles detected: {len(facts['target_roles'])}")
    print(f"Projects detected: {len(facts['projects'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
