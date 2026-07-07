import re
from typing import Any, Optional, Tuple

from app.schemas.agent_loop_schema import AgentLoopSimulateRequest
from app.schemas.auto_reply_schema import (
    AutoReplySimulationRequest,
    AutoReplySimulationResult,
)
from app.services.agent_loop_service import simulate_agent_loop
from app.services.profile_service import get_candidate_profile


CONFIRMATION_INTENTS = {
    "salary_or_benefits",
    "outsourcing_or_onsite",
    "overtime_or_work_schedule",
    "privacy_or_documents",
    "schedule_interview",
    "reject_or_close",
}


def simulate_supervised_auto_reply(
    request: AutoReplySimulationRequest,
) -> AutoReplySimulationResult:
    """模拟低风险及明确偏好约束下的 HR 回复候选生成。

    主要输入：application_id、HR message、可选上下文和 slot preview 数量。
    主要输出：Step 20 决策、回复策略、可选 reply_candidate 与安全说明；敏感偏好
    候选仍要求用户确认。
    副作用：只读 SQLite；不调用 LLM，不写 application / action_history，不 book slot，
    不发送 HR 消息，不投递，也不执行招聘平台操作。
    """
    loop = simulate_agent_loop(
        AgentLoopSimulateRequest(
            application_id=request.application_id,
            hr_message=request.hr_message,
            context_note=request.context_note,
            max_available_slots=request.max_available_slots,
        )
    )
    profile = get_candidate_profile()
    strategy, candidate, blocked_reason = _build_reply(loop, profile)
    reply_available = bool(candidate)
    requires_user_confirmation = (
        loop.requires_user_confirmation or loop.detected_intent in CONFIRMATION_INTENTS
    )
    return AutoReplySimulationResult(
        application_id=request.application_id,
        hr_message=request.hr_message,
        detected_intent=loop.detected_intent,
        proposed_action_type=loop.proposed_action_type,
        agent_loop_decision=loop.agent_loop_decision,
        risk_level=loop.policy.risk_level,
        policy_decision=loop.policy.policy_decision,
        reply_strategy=strategy,
        reply_candidate=candidate,
        reply_available=reply_available,
        requires_user_confirmation=requires_user_confirmation,
        requires_user_notification=(
            loop.requires_user_notification or requires_user_confirmation
        ),
        external_action_allowed=False,
        blocked_reason=blocked_reason,
        safety_notes=[
            "reply_candidate 仅供用户审核，不会自动发送。",
            "不会修改 application、写 action_history 或 book slot。",
            "候选回复使用规则模板，不调用 LLM。",
        ],
        debug={
            "step20_agent_loop_reused": True,
            "candidate_profile_loaded": profile is not None,
            "auto_send_message": False,
            "auto_apply": False,
            "auto_confirm_interview": False,
            "attachment_uploaded": False,
            "platform_login_performed": False,
            "captcha_handled": False,
            "database_write_performed": False,
            "application_updated": False,
            "action_history_written": False,
            "slot_booked": False,
            "llm_used": False,
            "external_action_allowed": False,
            "simulation_version": "21-rule-v1",
        },
    )


def _build_reply(loop: Any, profile: Any) -> Tuple[str, Optional[str], Optional[str]]:
    intent = loop.detected_intent
    if loop.agent_loop_decision == "block_action":
        reason = "该请求涉及被禁止的平台自动化、验证码或外部执行动作。"
        return "blocked", None, reason
    preference_candidate = _build_preference_reply(
        intent=intent,
        hr_message=loop.hr_message,
        profile=profile,
    )
    if preference_candidate:
        return (
            "preference_based_sensitive_reply",
            preference_candidate,
            "候选回复基于已确认求职偏好生成，仍需用户审核确认。",
        )
    if intent == "ask_project_experience":
        return "project_experience_summary", _project_reply(profile), None
    if intent == "ask_education_or_basic_info":
        return "education_basic_info", _education_reply(profile), None
    if intent == "ask_resume_or_project_link":
        return "resume_or_project_link", (
            "可以，我可以提供简历和项目介绍供您参考。具体文件或链接会由我确认后手动发送。"
        ), None
    if intent == "schedule_interview":
        if loop.available_slots_preview:
            slots = "；".join(
                f"{item['date']} {item['start_time']}-{item['end_time']}（{item['timezone']}）"
                for item in loop.available_slots_preview
            )
            return "interview_slots_proposal", (
                f"您好，以下时间是目前可参考的面试沟通时间：{slots}。"
                "请您看看哪个时间相对合适，具体安排以双方后续沟通为准。"
            ), None
        return "user_confirmation_required", None, "当前没有可安全提出的 available 面试时间。"
    if intent == "general_followup":
        return "general_followup", "您好，我目前仍在关注合适的机会，方便进一步沟通岗位情况。", None
    if loop.requires_user_confirmation or intent in CONFIRMATION_INTENTS:
        reason = "该场景涉及现实承诺、敏感材料或候选人偏好，需要用户先确认。"
        return "user_confirmation_required", None, reason
    return "unsupported", None, "当前规则模板不支持为该意图生成候选回复。"


def _build_preference_reply(
    *, intent: str, hr_message: str, profile: Any
) -> Optional[str]:
    if profile is None:
        return None
    if intent == "salary_or_benefits":
        return _salary_preference_reply(hr_message, profile)
    if intent == "outsourcing_or_onsite":
        return _outsourcing_or_onsite_reply(hr_message, profile)
    if intent == "overtime_or_work_schedule":
        return _overtime_preference_reply(profile.overtime_policy or "")
    if intent == "privacy_or_documents":
        return _privacy_preference_reply(profile.truth_boundaries or [])
    return None


def _salary_preference_reply(hr_message: str, profile: Any) -> Optional[str]:
    offered_salaries = _extract_salary_values(hr_message)
    minimum_salary = profile.minimum_salary
    expected_min = profile.expected_salary_min
    expected_max = profile.expected_salary_max
    salary_note = (profile.salary_note or "").strip()

    if offered_salaries and minimum_salary and min(offered_salaries) < minimum_salary:
        note = f"{salary_note}。" if salary_note else ""
        return (
            "感谢说明。这个薪资水平与我当前记录的最低考虑范围存在差距，"
            f"希望确认是否有调整空间。{note}也可以结合岗位职责、地点和整体薪酬结构进一步沟通。"
        )
    if offered_salaries and (expected_min is not None or expected_max is not None or minimum_salary):
        offered_salary = min(offered_salaries)
        salary_text = _format_salary_value(offered_salary)
        lower_bound = expected_min if expected_min is not None else minimum_salary
        upper_bound = expected_max
        if (
            (lower_bound is None or offered_salary >= lower_bound)
            and (upper_bound is None or offered_salary <= upper_bound)
        ):
            return (
                f"您好，{salary_text} 在我当前填写的薪资期望范围内，"
                "可以继续结合岗位职责、工作地点、试用期比例、加班强度和整体薪酬结构进一步沟通。"
            )
        if lower_bound is not None and offered_salary < lower_bound:
            note = f"{salary_note}。" if salary_note else ""
            return (
                "感谢说明。这个薪资水平低于我当前填写的薪资参考范围，"
                f"希望确认是否有调整空间。{note}也可以结合岗位职责、地点和整体薪酬结构进一步沟通。"
            )
        return (
            f"您好，{salary_text} 与我当前填写的薪资参考范围需要进一步对齐，"
            "可以结合岗位职责、工作地点、试用期比例、加班强度和整体薪酬结构继续沟通。"
        )
    asks_expectation = any(
        phrase in hr_message for phrase in ("期望薪资", "薪资期望", "期望范围", "薪资范围")
    )
    if asks_expectation and (expected_min is not None or expected_max is not None):
        if expected_min is not None and expected_max is not None:
            range_text = f"{expected_min}-{expected_max} 元/月"
        elif expected_min is not None:
            range_text = f"{expected_min} 元/月起"
        else:
            range_text = f"{expected_max} 元/月以内"
        note = f"{salary_note}。" if salary_note else ""
        return (
            f"您好，我当前记录的期望薪资范围是 {range_text}。{note}"
            "具体可以结合岗位职责、工作地点和整体薪酬结构进一步沟通。"
        )
    return None


def _extract_salary_values(text: str) -> list[int]:
    values = []
    for amount, unit in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*([kKwW千万元]?)", text):
        value = float(amount)
        multiplier = 1
        if unit.lower() == "k" or unit == "千":
            multiplier = 1000
        elif unit.lower() == "w" or unit == "万":
            multiplier = 10000
        normalized = int(value * multiplier)
        if normalized >= 1000:
            values.append(normalized)
    return values


def _format_salary_value(value: int) -> str:
    if value % 1000 == 0:
        return f"{value // 1000}k"
    return f"{value} 元/月"


def _preference_status(policy: str) -> str:
    text = (policy or "").strip()
    matched = re.search(r"偏好状态\s*[：:]\s*([^\n；;]+)", text)
    return matched.group(1).strip() if matched else text


def _outsourcing_or_onsite_reply(hr_message: str, profile: Any) -> Optional[str]:
    outsourcing_terms = ("外包", "乙方", "供应商", "派遣")
    onsite_terms = ("驻场", "客户现场")
    statuses = []
    if any(term in hr_message for term in outsourcing_terms):
        statuses.append(_preference_status(profile.outsourcing_policy or ""))
    if any(term in hr_message for term in onsite_terms):
        statuses.append(_preference_status(profile.onsite_policy or ""))
    statuses = [status for status in statuses if status and "我自己回答" not in status]
    if not statuses:
        return None
    if any("不接受" in status for status in statuses):
        return (
            "感谢说明。根据我当前确认的求职偏好，外包或长期驻场安排暂不符合我的选择；"
            "如岗位性质、合同主体或办公安排有调整，可以再沟通。"
        )
    if any("需要具体确认" in status for status in statuses):
        return (
            "感谢说明。我需要进一步了解合同主体、项目周期、管理方式和实际驻场频率，"
            "再判断是否合适，目前不作接受承诺。"
        )
    if any(
        status.startswith("可接受外包") or status.startswith("可接受短期驻场")
        for status in statuses
    ):
        return (
            "感谢说明。这个方向可以先进一步了解项目内容、合同主体、管理方式和驻场周期，"
            "是否合适仍需结合具体情况进一步判断。"
        )
    return None


def _overtime_preference_reply(policy: str) -> Optional[str]:
    status = _preference_status(policy)
    if not status or "我自己回答" in status:
        return None
    if "不接受单休" in status or "不接受大小周" in status or "不接受单休或大小周" in status:
        return (
            "感谢说明。我的当前工作制偏好是双休，单休或大小周暂不符合我的选择；"
            "如休息制度有调整，可以再沟通。"
        )
    if "需要结合" in status or "需要具体确认" in status:
        return (
            "感谢说明。我需要结合实际休息安排、加班频率、调休机制和薪资结构进一步确认，"
            "目前不作接受承诺。"
        )
    if "双休优先" in status or "偶尔加班" in status:
        return (
            "感谢说明。我的当前偏好是双休，阶段性偶尔加班可以沟通；"
            "具体工作制度和频率可以进一步说明。"
        )
    return None


def _privacy_preference_reply(truth_boundaries: Any) -> Optional[str]:
    prefix = "隐私材料偏好："
    boundary = next(
        (item.strip() for item in truth_boundaries if item.strip().startswith(prefix)),
        "",
    )
    if not boundary or "我自己回答" in boundary:
        return None
    if "面试前不提供" in boundary:
        return (
            "感谢说明。身份证、银行卡、薪资流水等敏感材料在面试前不提供；"
            "如后续确有必要，需要先确认公司真实性、用途和安全渠道，并由我手动处理。"
        )
    return (
        "感谢说明。涉及身份证、银行卡、学历证明或薪资流水等敏感材料，"
        "我需要先确认公司真实性、具体用途和接收渠道，再由我决定是否手动提供。"
    )


def _project_reply(profile: Any) -> str:
    if profile is None:
        return "您好，我做过 Python、FastAPI 相关 AI 应用项目；具体项目能力需要以简历事实为准进一步说明。"
    project_names = "、".join(profile.available_projects[:2])
    context = _compact_excerpt(profile.project_context, ("RAG", "FastAPI", "Agent"), 260)
    details = context or "项目事实以 candidate_profile 中的 project_context 为准"
    prefix = (
        f"我做过的项目主要包括{project_names}。"
        if project_names
        else "我做过 AI 应用开发相关项目。"
    )
    return f"{prefix}{details}。相关能力可以结合具体岗位继续介绍，但不会把未实现规划表述为已有经验。"


def _education_reply(profile: Any) -> str:
    if profile is None:
        return "您好，学历、专业和工作年限需要以我的真实简历为准，我可以按您关注的项目逐项说明。"
    resume_text = profile.resume_text or ""
    education_level = _extract_education_level(resume_text)
    major = _extract_major(resume_text)
    target_role = _extract_target_role(resume_text, profile.target_roles)
    facts = []
    if education_level:
        facts.append(f"我是{education_level}学历")
    if major:
        facts.append(f"专业是{major}")
    if target_role:
        facts.append(f"目前求职方向是{target_role}")
    if facts:
        return f"您好，{'，'.join(facts)}。"
    return "您好，当前 candidate_profile 中没有可直接确认的学历、专业或工作年限信息，需要以真实简历为准。"


def _extract_education_level(resume_text: str) -> Optional[str]:
    levels = ("博士", "研究生", "硕士", "本科", "大专", "专科")
    return next((level for level in levels if level in resume_text), None)


def _extract_major(resume_text: str) -> Optional[str]:
    explicit = re.search(
        r"专业\s*(?:是|为|：|:)\s*([^，,。；;\n]{2,30})",
        resume_text,
    )
    if explicit:
        return explicit.group(1).strip()
    known_majors = (
        "数据科学与大数据技术",
        "大数据技术应用",
        "大数据技术",
    )
    known_major = next(
        (candidate for candidate in known_majors if candidate in resume_text),
        None,
    )
    if known_major:
        return known_major
    suffix = re.search(
        r"(?:^|[，,。；;\n\s])([A-Za-z0-9+#/\-\u4e00-\u9fff]{2,30})专业",
        resume_text,
    )
    return suffix.group(1).strip() if suffix else None


def _extract_target_role(resume_text: str, target_roles: Any) -> Optional[str]:
    matched = re.search(
        r"求职方向\s*(?:为|是|：|:)?\s*([^，,。；;\n]{2,50})",
        resume_text,
    )
    if matched:
        return matched.group(1).strip()
    return target_roles[0].strip() if target_roles else None


def _compact_excerpt(text: str, keywords: Tuple[str, ...], limit: int) -> str:
    parts = [part.strip() for part in re.split(r"[\r\n。；]+", text or "") if part.strip()]
    selected = [part for part in parts if any(keyword.lower() in part.lower() for keyword in keywords)]
    return "；".join(selected)[:limit].rstrip("；，, ")
