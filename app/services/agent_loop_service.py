from typing import Any, Dict, List, Tuple

from app.schemas.agent_loop_schema import AgentLoopSimulateRequest, AgentLoopSimulateResult
from app.schemas.automation_policy_schema import AutomationPolicyRequest
from app.services.action_history_service import list_application_action_history
from app.services.application_service import get_application
from app.services.automation_policy_service import evaluate_automation_policy
from app.services.interview_availability_service import list_interview_availability_slots
from app.services.profile_service import get_candidate_profile


INTENT_RULES: List[Tuple[str, Tuple[str, ...]]] = [
    ("platform_verification", ("验证码", "平台验证", "自动登录", "绕过", "风控", "批量投递")),
    ("privacy_or_documents", ("身份证", "银行卡", "薪资流水", "历史薪资", "学历证书", "学信网", "离职证明", "背调", "合同")),
    ("salary_or_benefits", ("薪资", "工资", "待遇", "期望薪资", "试用期薪资", "五险一金", "年终奖", "8k", "10k", "16k", "能接受吗")),
    ("outsourcing_or_onsite", ("外包", "驻场", "客户现场", "乙方", "派遣", "供应商")),
    ("overtime_or_work_schedule", ("单休", "大小周", "996", "加班", "周末加班", "双休")),
    ("schedule_interview", ("面试", "视频面试", "电话面试", "明天", "下午", "上午", "约时间")),
    ("ask_project_experience", ("项目", "rag", "agent", "fastapi", "langchain", "python", "做过什么", "技术栈")),
    ("ask_education_or_basic_info", ("学历", "专业", "毕业", "学校", "工作年限")),
    ("ask_resume_or_project_link", ("简历", "github", "demo", "作品", "项目链接")),
    ("reject_or_close", ("不合适", "暂不考虑", "岗位关闭", "已招满", "不匹配")),
]

ACTION_BY_INTENT = {
    "ask_project_experience": "send_hr_reply",
    "ask_education_or_basic_info": "send_hr_reply",
    "ask_resume_or_project_link": "send_hr_reply",
    "schedule_interview": "propose_interview_slots",
    "salary_or_benefits": "send_hr_reply",
    "outsourcing_or_onsite": "send_hr_reply",
    "overtime_or_work_schedule": "send_hr_reply",
    "privacy_or_documents": "send_hr_reply",
    "platform_verification": "handle_platform_verification",
    "apply_or_send_external": "apply_job",
    "reject_or_close": "close_application",
    "general_followup": "send_hr_reply",
    "unknown": "generate_hr_reply_draft",
}


def simulate_agent_loop(request: AgentLoopSimulateRequest) -> AgentLoopSimulateResult:
    """模拟一次 observe、intent、policy、plan Agent Loop。

    主要输入：application_id、HR 消息、可选上下文和 slot preview 数量。
    主要输出：观察摘要、意图、拟议动作、策略决策和模拟工具计划。
    副作用：只读数据库；不写状态、不写 history、不调用 LLM、不执行外部动作。
    """
    application = get_application(request.application_id)
    if application is None:
        raise ValueError("application not found")
    profile = get_candidate_profile()
    slots = list_interview_availability_slots(status="available", limit=request.max_available_slots)
    history = list_application_action_history(request.application_id, limit=5)
    intent = _classify_intent(request.hr_message)
    action_type = ACTION_BY_INTENT[intent]
    policy = evaluate_automation_policy(
        AutomationPolicyRequest(
            application_id=request.application_id,
            hr_message=request.hr_message,
            proposed_action_type=action_type,
            context_note=request.context_note,
        )
    )
    loop_decision = _choose_loop_decision(intent, policy)
    slot_preview = _slot_preview(slots) if intent == "schedule_interview" else []
    return AgentLoopSimulateResult(
        application_id=request.application_id,
        hr_message=request.hr_message,
        observation={
            "application_loaded": True,
            "candidate_profile_loaded": profile is not None,
            "available_slots_count": len(slots),
            "recent_action_history_count": len(history),
        },
        detected_intent=intent,
        proposed_action_type=action_type,
        policy=policy,
        agent_loop_decision=loop_decision,
        simulated_next_step=_next_step(loop_decision),
        simulated_tool_plan=_tool_plan(intent, bool(slot_preview)),
        recommended_reply_strategy=_strategy(intent),
        available_slots_preview=slot_preview,
        requires_user_confirmation=policy.requires_user_confirmation,
        requires_user_notification=policy.requires_user_notification,
        external_action_allowed=False,
        debug={
            "auto_send_message": False,
            "auto_apply": False,
            "auto_confirm_interview": False,
            "external_action_allowed": False,
            "database_write_performed": False,
            "policy_version": policy.debug.get("policy_version"),
            "loop_version": "20-rule-v1",
            "llm_used": False,
        },
    )


def _classify_intent(message: str) -> str:
    lowered = message.lower()
    for intent, keywords in INTENT_RULES:
        if any(keyword.lower() in lowered for keyword in keywords):
            return intent
    return "general_followup" if message.strip() else "unknown"


def _choose_loop_decision(intent: str, policy: Any) -> str:
    if policy.policy_decision == "block_external_action":
        return "block_action"
    if policy.requires_user_confirmation:
        return "request_user_confirmation"
    if intent == "schedule_interview" and policy.agent_can_handle:
        return "propose_slots_with_notification"
    if policy.agent_can_handle and policy.risk_level == "low":
        return "auto_handle_internal"
    return "ask_user_for_more_context"


def _slot_preview(slots: List[Any]) -> List[Dict[str, Any]]:
    return [{"id": s.id, "date": s.date, "start_time": s.start_time, "end_time": s.end_time,
             "timezone": s.timezone, "status": s.status, "note_preview": " ".join(s.note.split())[:120]}
            for s in slots]


def _tool_plan(intent: str, has_slots: bool) -> List[Dict[str, Any]]:
    items = [{"tool_name": "automation_policy.evaluate", "purpose": "Evaluate risk and permission",
              "read_only": True, "database_write": False, "external_action": False,
              "result_summary": "Policy evaluated inside simulation."}]
    if intent == "schedule_interview":
        items.append({"tool_name": "interview_availability_slots.list", "purpose": "Read available slots",
                      "read_only": True, "database_write": False, "external_action": False,
                      "result_summary": "Available slots loaded." if has_slots else "No available slot."})
    else:
        items.append({"tool_name": "hr_reply_draft.generate", "purpose": "Recommend a future draft step",
                      "read_only": True, "database_write": False, "external_action": False,
                      "result_summary": "Not executed in simulation."})
    return items


def _next_step(decision: str) -> str:
    return {
        "block_action": "Block the proposed action and notify the user.",
        "request_user_confirmation": "Ask the user to review and confirm before continuing.",
        "propose_slots_with_notification": "Show available slots to the user without booking or sending.",
        "auto_handle_internal": "Prepare an internal response strategy without sending it.",
        "ask_user_for_more_context": "Ask the user for more context before proposing an action.",
    }[decision]


def _strategy(intent: str) -> str:
    return {
        "ask_project_experience": "answer_project_experience_from_profile",
        "ask_education_or_basic_info": "answer_basic_info_from_resume",
        "ask_resume_or_project_link": "answer_link_request_from_profile",
        "schedule_interview": "propose_available_slots",
        "platform_verification": "refuse_platform_automation",
        "privacy_or_documents": "ask_user_to_confirm_sensitive_condition",
    }.get(intent, "wait_for_user_decision")
