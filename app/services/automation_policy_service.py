import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.automation_policy_schema import (
    AutomationPolicyDecision,
    AutomationPolicyRequest,
)
from app.services.application_service import get_application
from app.services.profile_service import get_candidate_profile


SUPPORTED_ACTION_TYPES = {
    "generate_hr_reply_draft",
    "send_hr_reply",
    "propose_interview_slots",
    "book_interview_slot",
    "apply_job",
    "close_application",
    "handle_platform_verification",
}

HIGH_RISK_KEYWORDS = {
    "薪资", "工资", "待遇", "期望薪资", "降薪", "试用期", "8k", "10k",
    "外包", "驻场", "客户现场", "出差", "996", "大小周", "加班", "offer",
    "入职", "到岗", "离职", "合同", "背调", "身份证", "银行卡", "学历证书",
    "接受", "确认入职", "签约", "竞业", "保密协议",
}
MEDIUM_RISK_KEYWORDS = {
    "面试", "视频面试", "电话", "电话沟通", "几点", "时间", "明天", "今天",
    "下午", "上午", "晚上", "方便聊", "约时间", "会议",
}
LOW_RISK_KEYWORDS = {
    "项目", "rag", "agent", "fastapi", "langchain", "python", "技术栈",
    "github", "demo", "简历", "介绍一下", "经验", "做过什么",
}
BLOCKED_KEYWORDS = {
    "验证码", "平台验证", "自动登录", "批量投递", "绕过", "风控", "平台限制",
}


def _matched_keywords(text: str, keywords: set[str]) -> List[str]:
    lowered = text.lower()
    return sorted(keyword for keyword in keywords if keyword.lower() in lowered)


def evaluate_automation_policy(
    request: AutomationPolicyRequest,
) -> AutomationPolicyDecision:
    """评估拟议 Agent 动作的风险和人工确认要求。

    主要输入：动作类型、可选 application_id、HR 消息、草稿和上下文备注。
    主要输出：风险等级、Agent 是否可处理、用户确认/通知要求和阻断原因。
    副作用：纯规则只读判断；不写数据库、不调用 LLM、不执行任何外部动作。
    """
    action_type = request.proposed_action_type.strip()
    if action_type not in SUPPORTED_ACTION_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_ACTION_TYPES))
        raise ValueError(f"unsupported proposed_action_type. allowed values: {allowed}")

    application = get_application(request.application_id) if request.application_id else None
    profile = get_candidate_profile()
    application_text = ""
    if application is not None:
        application_text = " ".join(
            [
                application.company_name,
                application.job_title,
                application.jd_text,
                application.jd_summary,
                " ".join(application.jd_keywords),
                " ".join(application.jd_required_skills),
                application.jd_location_requirement,
                application.jd_remote_type,
                " ".join(application.risk_flags),
            ]
        )
    combined_text = " ".join(
        value for value in (
            request.hr_message,
            request.draft_text or "",
            request.context_note or "",
            application_text,
        ) if value
    )
    blocked_matches = _matched_keywords(combined_text, BLOCKED_KEYWORDS)
    high_matches = _matched_keywords(combined_text, HIGH_RISK_KEYWORDS)
    medium_matches = _matched_keywords(combined_text, MEDIUM_RISK_KEYWORDS)
    low_matches = _matched_keywords(combined_text, LOW_RISK_KEYWORDS)
    preference_flags, preference_level, preference_reason, preference_next_step = (
        _evaluate_preference_guardrails(
            text=combined_text,
            salary_text=" ".join((request.hr_message, request.draft_text or "", application_text)),
            context_note=request.context_note or "",
            profile=profile,
            application=application,
        )
    )

    if action_type == "handle_platform_verification" or blocked_matches:
        decision = _blocked_decision(action_type, blocked_matches)
    elif preference_level == "high":
        decision = _high_decision(action_type, [preference_reason])
        decision["policy_decision"] = "recommend_close_or_confirm"
        decision["suggested_next_step"] = preference_next_step
    elif action_type == "apply_job":
        decision = _high_decision(action_type, ["真实投递属于高风险外部动作"])
        decision["policy_decision"] = "block_external_action"
        decision["blocked_by"] = ["external_actions_disabled"]
    elif high_matches:
        decision = _high_decision(
            action_type,
            [f"命中高风险关键词：{', '.join(high_matches)}"],
        )
    elif preference_level == "medium":
        decision = _medium_decision(action_type, confirmation=True)
        decision["reasons"] = [preference_reason]
        decision["suggested_next_step"] = preference_next_step
    elif action_type == "propose_interview_slots":
        decision = _medium_decision(action_type, confirmation=False)
    elif action_type == "book_interview_slot":
        decision = _medium_decision(action_type, confirmation=True)
    elif action_type == "close_application":
        decision = _medium_decision(action_type, confirmation=True, agent_can_handle=False)
    elif medium_matches:
        decision = _medium_decision(action_type, confirmation=True)
        decision["reasons"] = [f"命中中风险关键词：{', '.join(medium_matches)}"]
    else:
        decision = _low_decision(action_type, low_matches)

    decision.update(
        {
            "application_id": request.application_id,
            "proposed_action_type": action_type,
            "external_action_allowed": False,
            "preference_risk_flags": preference_flags,
            "debug": {
                "auto_send_message": False,
                "auto_apply": False,
                "auto_confirm_interview": False,
                "external_action_allowed": False,
                "matched_blocked_keywords": blocked_matches,
                "matched_risk_keywords": high_matches,
                "matched_medium_keywords": medium_matches,
                "matched_low_keywords": low_matches,
                "preference_risk_flags": preference_flags,
                "application_context_loaded": application is not None,
                "candidate_profile_loaded": profile is not None,
                "rule_priority": "blocked > hard preference conflict > high HR commitment > medium preference warning > medium scheduling > low",
                "policy_version": "19A-rule-v2",
            },
        }
    )
    return AutomationPolicyDecision(**decision)


def _evaluate_preference_guardrails(
    *,
    text: str,
    salary_text: str,
    context_note: str,
    profile: Any,
    application: Any,
) -> Tuple[List[str], Optional[str], str, str]:
    flags: List[str] = []
    lowered = text.lower()
    minimum_salary = getattr(profile, "minimum_salary", None) if profile else None
    expected_min = getattr(profile, "expected_salary_min", None) if profile else None
    override = re.search(r"minimum_salary\s*(?:is|=|:)\s*(\d{4,6})", context_note, re.I)
    if override:
        minimum_salary = int(override.group(1))
    salaries = _extract_salaries(salary_text)
    offered_salary = min(salaries) if salaries else None
    if offered_salary is not None and minimum_salary:
        if offered_salary < minimum_salary:
            flags.append("below_minimum_salary")
        elif abs(offered_salary - minimum_salary) <= 500:
            flags.append("salary_at_minimum")
        elif expected_min and offered_salary < expected_min:
            flags.append("salary_below_expected")

    if "单休" in text:
        flags.append("single_day_off")
    if any(word in text for word in ("大小周", "996", "007", "经常加班", "高强度加班", "周末加班")):
        flags.append("overtime_risk")
    elif "偶尔加班" in text:
        flags.append("overtime_risk")

    outsourcing_terms = ("外包", "人力外包", "项目外包", "乙方", "供应商", "派遣")
    onsite_terms = ("驻场", "客户现场", "全职驻场")
    if any(word in text for word in outsourcing_terms) and not _explicitly_accepts(
        getattr(profile, "outsourcing_policy", "") if profile else ""
    ):
        flags.append("outsourcing_risk")
    if any(word in text for word in onsite_terms) and not _explicitly_accepts(
        getattr(profile, "onsite_policy", "") if profile else ""
    ):
        flags.append("onsite_risk")

    if any(word in text for word in ("异地", "搬迁", "长期出差", "全国出差", "驻外")):
        flags.append("relocation_risk")
    if any(word in text for word in ("全职坐班", "必须到岗", "不能远程", "现场办公")):
        remote_policy = getattr(profile, "remote_policy", "") if profile else ""
        remote_required = (
            ("远程" in remote_policy or "混合" in remote_policy)
            and any(word in remote_policy for word in ("优先", "仅", "必须", "只接受"))
        )
        if remote_required:
            flags.append("remote_policy_conflict")

    if application is not None and profile is not None:
        location = application.jd_location_requirement or ""
        allowed_cities = list(profile.preferred_cities) + list(profile.acceptable_cities)
        if location and allowed_cities and not any(city and city in location for city in allowed_cities):
            flags.append("city_not_acceptable")
    if any(word in text for word in ("纯销售", "电话销售", "客服", "纯数据录入", "非开发岗位")):
        flags.append("role_mismatch")

    flags = list(dict.fromkeys(flags))
    hard_flags = {
        "below_minimum_salary", "single_day_off", "outsourcing_risk", "onsite_risk",
        "role_mismatch",
    }
    if hard_flags.intersection(flags):
        return (
            flags,
            "high",
            f"命中候选人硬偏好冲突：{', '.join(flags)}",
            "Ask user whether to continue or reject this opportunity.",
        )
    if flags:
        return (
            flags,
            "medium",
            f"命中候选人偏好提醒：{', '.join(flags)}",
            "Confirm with user before accepting or expressing willingness.",
        )
    return [], None, "", ""


def _extract_salaries(text: str) -> List[int]:
    values: List[int] = []
    for value in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)\s*[kK]\b", text):
        values.append(int(float(value) * 1000))
    for value in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)\s*万", text):
        values.append(int(float(value) * 10000))
    for value in re.findall(r"(?<!\d)(\d{4,6})(?!\d)", text):
        number = int(value)
        if 3000 <= number <= 200000:
            values.append(number)
    return values


def _explicitly_accepts(policy: str) -> bool:
    if not policy or any(word in policy for word in ("不接受", "不优先", "需沟通", "进一步沟通")):
        return False
    return any(word in policy for word in ("可接受", "接受", "均可", "没问题"))


def _low_decision(action_type: str, matches: List[str]) -> Dict[str, Any]:
    return {
        "risk_level": "low",
        "policy_decision": "allow_draft_only",
        "agent_can_handle": True,
        "requires_user_confirmation": False,
        "requires_user_notification": False,
        "reasons": [
            f"内部低风险动作，可生成或处理但不能外发：{action_type}",
            *( [f"命中低风险关键词：{', '.join(matches)}"] if matches else [] ),
        ],
        "blocked_by": ["external_actions_disabled"],
        "suggested_next_step": "允许内部生成或分析；如需外发，仍由用户手动处理。",
    }


def _medium_decision(
    action_type: str,
    *,
    confirmation: bool,
    agent_can_handle: bool = True,
) -> Dict[str, Any]:
    return {
        "risk_level": "medium",
        "policy_decision": (
            "require_user_confirmation" if confirmation else "handle_with_notification"
        ),
        "agent_can_handle": agent_can_handle,
        "requires_user_confirmation": confirmation,
        "requires_user_notification": True,
        "reasons": [f"动作会影响内部跟进或时间状态：{action_type}"],
        "blocked_by": ["external_actions_disabled"],
        "suggested_next_step": (
            "等待用户确认后再修改内部状态。"
            if confirmation
            else "可以生成内部建议，并通知用户；不得自动外发。"
        ),
    }


def _high_decision(action_type: str, reasons: List[str]) -> Dict[str, Any]:
    return {
        "risk_level": "high",
        "policy_decision": "require_user_confirmation",
        "agent_can_handle": False,
        "requires_user_confirmation": True,
        "requires_user_notification": True,
        "reasons": reasons,
        "blocked_by": ["external_actions_disabled"],
        "suggested_next_step": "停止自动处理，交由用户审核和决定。",
    }


def _blocked_decision(action_type: str, matches: List[str]) -> Dict[str, Any]:
    reasons = ["平台验证、登录、批量操作或绕过限制属于禁止自动化范围。"]
    if matches:
        reasons.append(f"命中 blocked 关键词：{', '.join(matches)}")
    return {
        "risk_level": "high",
        "policy_decision": "block_external_action",
        "agent_can_handle": False,
        "requires_user_confirmation": True,
        "requires_user_notification": True,
        "reasons": reasons,
        "blocked_by": ["external_actions_disabled", "platform_automation_blocked"],
        "suggested_next_step": f"阻止动作 {action_type}，不执行平台自动化。",
    }
