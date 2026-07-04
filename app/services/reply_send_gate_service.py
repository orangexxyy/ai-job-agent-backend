import re
from typing import List, Optional, Tuple

from app.schemas.auto_reply_schema import AutoReplySimulationRequest
from app.schemas.reply_send_gate_schema import (
    ReplySendGateSimulationRequest,
    ReplySendGateSimulationResult,
)
from app.services.action_history_service import create_application_action_history
from app.services.application_service import get_application
from app.services.auto_reply_service import simulate_supervised_auto_reply


SAFETY_PATTERNS = {
    "salary_commitment": (
        r"我接受",
        r"可以接受",
        r"薪资可以",
        r"这个薪资没问题",
        r"同意这个薪资",
        r"接受\s*\d+(?:\.\d+)?\s*[kK千]",
    ),
    "work_condition_commitment": (
        r"可以单休",
        r"接受单休",
        r"可以大小周",
        r"可以\s*996",
        r"可以长期加班",
        r"可以外包",
        r"可以驻场",
        r"可以客户现场",
    ),
    "privacy_material_commitment": (
        r"我马上发身份证",
        r"我马上发银行卡",
        r"我马上发学历证明",
        r"我马上发学信网截图",
        r"我马上发薪资流水",
        r"我马上发离职证明",
        r"我可以提供背调授权",
    ),
    "offer_or_contract_commitment": (
        r"我接受\s*offer",
        r"我可以入职",
        r"我确认入职",
        r"我同意合同",
        r"我同意竞业",
    ),
    "platform_operation_commitment": (
        r"我来处理验证码",
        r"我帮你登录",
        r"我可以批量投递",
        r"我绕过验证",
    ),
}


def check_final_reply_safety(reply_candidate: Optional[str]) -> Tuple[bool, List[str]]:
    """检查最终候选回复中的承诺和平台操作风险。

    主要输入：待通过发送门禁的 reply_candidate。
    主要输出：是否通过以及命中的风险 flag 列表。
    副作用：纯内存规则检查；不读写数据库、不调用 LLM、不执行外部动作。
    """
    if not reply_candidate:
        return True, []
    flags = [
        flag
        for flag, patterns in SAFETY_PATTERNS.items()
        if any(re.search(pattern, reply_candidate, re.IGNORECASE) for pattern in patterns)
    ]
    return not flags, flags


def simulate_reply_send_gate(
    request: ReplySendGateSimulationRequest,
) -> ReplySendGateSimulationResult:
    """模拟最终回复发送门禁，并仅记录通过门禁的模拟发送历史。

    主要输入：application_id、HR message、可选上下文和 slot preview 数量。
    主要输出：最终安全检查、发送门禁决策及可选 action_history id。
    副作用：仅在 auto_send_simulated=true 时写入 SQLite action_history；不修改
    application，不 book slot，不调用 LLM，不发送消息、不投递或执行平台操作。
    """
    auto_reply = simulate_supervised_auto_reply(
        AutoReplySimulationRequest(
            application_id=request.application_id,
            hr_message=request.hr_message,
            context_note=request.context_note,
            max_available_slots=request.max_available_slots,
        )
    )
    safety_passed, safety_flags = check_final_reply_safety(
        auto_reply.reply_candidate
    )
    decision, simulated, blocked_reason = _decide_send_gate(
        auto_reply=auto_reply,
        safety_passed=safety_passed,
        safety_flags=safety_flags,
    )
    history_id = None
    if simulated:
        application = get_application(request.application_id)
        if application is None:
            raise ValueError("application not found")
        history = create_application_action_history(
            application_id=request.application_id,
            action_type="auto_reply_simulated_sent",
            action_source="agent",
            before_status=application.status,
            after_status=application.status,
            before_next_action=application.next_action,
            after_next_action=application.next_action,
            user_confirmed=False,
            external_action_performed=False,
            risk_level=auto_reply.risk_level,
            summary="Agent simulated auto reply for low/medium-risk HR message",
            detail_json={
                "hr_message": request.hr_message,
                "detected_intent": auto_reply.detected_intent,
                "proposed_action_type": auto_reply.proposed_action_type,
                "final_send_decision": decision,
                "reply_candidate": auto_reply.reply_candidate,
                "final_safety_flags": safety_flags,
                "external_action_allowed": False,
                "external_action_performed": False,
            },
        )
        history_id = history.id
    confirmation_required = (
        auto_reply.requires_user_confirmation
        or decision == "requires_user_confirmation"
    )
    notification_required = (
        auto_reply.requires_user_notification
        or decision == "notify_and_auto_send_simulated"
    )
    return ReplySendGateSimulationResult(
        application_id=request.application_id,
        hr_message=request.hr_message,
        detected_intent=auto_reply.detected_intent,
        proposed_action_type=auto_reply.proposed_action_type,
        risk_level=auto_reply.risk_level,
        policy_decision=auto_reply.policy_decision,
        reply_available=auto_reply.reply_available,
        reply_candidate=auto_reply.reply_candidate,
        final_safety_check_passed=safety_passed,
        final_safety_flags=safety_flags,
        final_send_decision=decision,
        auto_send_simulated=simulated,
        requires_user_confirmation=confirmation_required,
        requires_user_notification=notification_required,
        blocked_reason=blocked_reason,
        action_history_written=history_id is not None,
        action_history_id=history_id,
        external_action_allowed=False,
        external_action_performed=False,
        debug={
            "step21_auto_reply_reused": True,
            "real_message_sent": False,
            "application_updated": False,
            "slot_booked": False,
            "llm_used": False,
            "attachment_uploaded": False,
            "platform_login_performed": False,
            "captcha_handled": False,
            "external_action_allowed": False,
            "external_action_performed": False,
            "database_write_scope": (
                "action_history_only" if history_id is not None else "none"
            ),
            "simulation_version": "22-rule-v1",
        },
    )


def _decide_send_gate(
    *, auto_reply: object, safety_passed: bool, safety_flags: List[str]
) -> Tuple[str, bool, Optional[str]]:
    if auto_reply.reply_strategy == "blocked":
        return "blocked", False, auto_reply.blocked_reason
    if not safety_passed:
        platform_flag = "platform_operation_commitment" in safety_flags
        return (
            "blocked" if platform_flag else "requires_user_confirmation",
            False,
            "最终文本安全检查未通过。",
        )
    if auto_reply.requires_user_confirmation:
        return "requires_user_confirmation", False, auto_reply.blocked_reason
    if not auto_reply.reply_candidate:
        return "no_reply_available", False, auto_reply.blocked_reason
    if auto_reply.risk_level == "low":
        return "auto_send_simulated", True, None
    if auto_reply.risk_level == "medium":
        return "notify_and_auto_send_simulated", True, None
    return "requires_user_confirmation", False, "当前风险等级不允许模拟自动发送。"
