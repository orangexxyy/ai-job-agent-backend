from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.application_review_service import review_application
from app.services.application_service import get_application
from app.services.hr_reply_draft_llm_service import generate_hr_reply_draft_from_review
from app.services.profile_service import get_candidate_profile


class WorkflowState(TypedDict, total=False):
    application_id: int
    hr_message: Optional[str]
    candidate_profile_loaded: bool
    application_loaded: bool
    company_name: str
    job_title: str
    application_review: Dict[str, Any]
    job_match: Dict[str, Any]
    hr_intent: Optional[Dict[str, Any]]
    review_level: str
    confidence: str
    risk_flags: List[str]
    missing_information: List[str]
    hr_reply_package: Optional[Dict[str, Any]]
    reply_strategy_for_user: Optional[Dict[str, Any]]
    hr_reply_draft: Optional[Dict[str, Any]]
    hr_reply: Optional[Dict[str, Any]]
    workflow_steps: List[Dict[str, str]]
    approval_required: bool
    approved_by_user: bool
    next_action: str
    error_message: Optional[str]
    state_snapshots: List[Dict[str, Any]]
    edge_trace: List[Dict[str, Any]]
    node_debug: Dict[str, Dict[str, Any]]
    debug: Dict[str, Any]


def run_langgraph_workflow_preview(
    application_id: int,
    hr_message: Optional[str] = None,
) -> Dict[str, Any]:
    """运行 LangGraph 版只读 workflow preview。

    主要输入：application_id，以及可选 HR message。
    主要输出：application_review、hr_reply_package、node_debug、edge_trace 和人工审批状态。
    副作用：只读 SQLite；可能在生成 HR reply package 时调用一次 LLM；不写 application，不发送 HR 消息，不自动投递。
    """
    app = _build_graph()
    initial_state: WorkflowState = {
        "application_id": application_id,
        "hr_message": hr_message,
        "candidate_profile_loaded": False,
        "application_loaded": False,
        "company_name": "",
        "job_title": "",
        "application_review": {},
        "job_match": {},
        "hr_intent": None,
        "review_level": "",
        "confidence": "",
        "risk_flags": [],
        "missing_information": [],
        "hr_reply_package": None,
        "reply_strategy_for_user": None,
        "hr_reply_draft": None,
        "hr_reply": None,
        "workflow_steps": [],
        "approval_required": False,
        "approved_by_user": False,
        "next_action": "",
        "error_message": None,
        "state_snapshots": [],
        "edge_trace": [],
        "node_debug": {},
        "debug": _base_debug(),
    }
    final_state = app.invoke(initial_state)
    if final_state.get("error_message"):
        raise ValueError(str(final_state["error_message"]))
    return _build_response_data(final_state)


def _build_graph() -> Any:
    graph = StateGraph(WorkflowState)
    graph.add_node("load_profile_node", load_profile_node)
    graph.add_node("load_application_node", load_application_node)
    graph.add_node("run_application_review_node", run_application_review_node)
    graph.add_node("generate_hr_reply_package_node", generate_hr_reply_package_node)
    graph.add_node("require_user_approval_node", require_user_approval_node)
    graph.add_node("handle_error_node", handle_error_node)

    graph.add_edge(START, "load_profile_node")
    graph.add_conditional_edges(
        "load_profile_node",
        _next_after_error_check,
        {"error": "handle_error_node", "continue": "load_application_node"},
    )
    graph.add_conditional_edges(
        "load_application_node",
        _next_after_error_check,
        {"error": "handle_error_node", "continue": "run_application_review_node"},
    )
    graph.add_conditional_edges(
        "run_application_review_node",
        _next_after_error_check,
        {"error": "handle_error_node", "continue": "generate_hr_reply_package_node"},
    )
    graph.add_conditional_edges(
        "generate_hr_reply_package_node",
        _next_after_error_check,
        {"error": "handle_error_node", "continue": "require_user_approval_node"},
    )
    graph.add_edge("require_user_approval_node", END)
    graph.add_edge("handle_error_node", END)
    return graph.compile()


def load_profile_node(state: WorkflowState) -> WorkflowState:
    profile = get_candidate_profile()
    if profile is None:
        state["error_message"] = "candidate_profile not found"
        _add_edge_trace(state, "load_profile_node", "error", "handle_error_node", "candidate_profile not found")
        _set_node_debug(state, "load_profile_node", llm_used=False, database_read=True, status="error")
        _record_state_snapshot(state, "load_profile_node")
        return state

    state["candidate_profile_loaded"] = True
    _add_step(state, "load_candidate_profile", "completed", "已读取 candidate_profile，作为 LangGraph workflow 的求职者上下文。")
    _add_edge_trace(state, "load_profile_node", "continue", "load_application_node", "error_message is empty")
    _set_node_debug(state, "load_profile_node", llm_used=False, database_read=True, status="success")
    _record_state_snapshot(state, "load_profile_node")
    return state


def load_application_node(state: WorkflowState) -> WorkflowState:
    application = get_application(state["application_id"])
    if application is None:
        state["error_message"] = "application not found"
        _add_edge_trace(state, "load_application_node", "error", "handle_error_node", "application not found")
        _set_node_debug(state, "load_application_node", llm_used=False, database_read=True, status="error")
        _record_state_snapshot(state, "load_application_node")
        return state

    state["application_loaded"] = True
    state["company_name"] = application.company_name
    state["job_title"] = application.job_title
    _add_step(state, "load_application", "completed", "已读取 application，作为 LangGraph workflow 的投递上下文。")
    _add_edge_trace(state, "load_application_node", "continue", "run_application_review_node", "error_message is empty")
    _set_node_debug(state, "load_application_node", llm_used=False, database_read=True, status="success")
    _record_state_snapshot(state, "load_application_node")
    return state


def run_application_review_node(state: WorkflowState) -> WorkflowState:
    try:
        application_review = review_application(
            application_id=state["application_id"],
            hr_message=state.get("hr_message"),
            update_application=False,
        )
    except ValueError as exc:
        state["error_message"] = str(exc)
        _add_edge_trace(state, "run_application_review_node", "error", "handle_error_node", str(exc))
        _set_node_debug(state, "run_application_review_node", llm_used=False, database_read=True, status="error")
        _record_state_snapshot(state, "run_application_review_node")
        return state

    state["application_review"] = application_review
    state["job_match"] = application_review.get("job_match", {})
    state["hr_intent"] = application_review.get("hr_intent")
    state["review_level"] = application_review.get("review_level", "")
    state["confidence"] = application_review.get("confidence", "")
    state["risk_flags"] = application_review.get("risk_flags", [])
    state["missing_information"] = application_review.get("missing_information", [])
    _add_step(state, "run_application_review", "completed", "已运行规则版 application review，生成岗位风险、缺失信息和下一步建议，但未回写 application。")
    _add_edge_trace(state, "run_application_review_node", "continue", "generate_hr_reply_package_node", "application review completed without database write")
    _set_node_debug(state, "run_application_review_node", llm_used=False, database_read=True, status="success")
    _record_state_snapshot(state, "run_application_review_node")
    return state


def generate_hr_reply_package_node(state: WorkflowState) -> WorkflowState:
    hr_message = state.get("hr_message")
    if not hr_message:
        _add_step(state, "generate_hr_reply_package", "skipped", "未传入 HR message，跳过回复策略和 HR 回复草稿生成。")
        _add_edge_trace(state, "generate_hr_reply_package_node", "continue", "require_user_approval_node", "hr_message is empty")
        _set_node_debug(state, "generate_hr_reply_package_node", llm_used=False, database_read=False, status="skipped")
        _record_state_snapshot(state, "generate_hr_reply_package_node")
        return state

    try:
        package = generate_hr_reply_draft_from_review(
            application_id=state["application_id"],
            hr_message=hr_message,
            draft_tone="professional",
            include_raw_prompt=False,
            precomputed_rule_review=state.get("application_review"),
        )
    except ValueError as exc:
        state["error_message"] = str(exc)
        _add_edge_trace(state, "generate_hr_reply_package_node", "error", "handle_error_node", str(exc))
        _set_node_debug(state, "generate_hr_reply_package_node", llm_used=False, database_read=True, status="error")
        _record_state_snapshot(state, "generate_hr_reply_package_node")
        return state

    state["hr_reply_package"] = package
    state["reply_strategy_for_user"] = package.get("reply_strategy_for_user")
    state["hr_reply_draft"] = package.get("hr_reply_draft")
    state["hr_reply"] = package.get("hr_reply_draft")
    state["debug"] = _merge_debug_after_reply_package(state.get("debug", _base_debug()), package)
    _add_step(state, "generate_hr_reply_package", "completed", "已生成回复策略和 HR 回复草稿，等待用户人工确认；未发送消息，未更新 application。")
    _add_edge_trace(state, "generate_hr_reply_package_node", "continue", "require_user_approval_node", "reply package generated without database write")
    _set_node_debug(
        state,
        "generate_hr_reply_package_node",
        llm_used=bool(package.get("llm_used")),
        database_read=True,
        external_api_called=bool(package.get("llm_used")),
        status="success",
        draft_source=package.get("draft_source"),
    )
    _record_state_snapshot(state, "generate_hr_reply_package_node")
    return state


def require_user_approval_node(state: WorkflowState) -> WorkflowState:
    state["approval_required"] = True
    state["approved_by_user"] = False
    state["next_action"] = _select_next_action(state)
    _add_step(state, "require_user_approval", "waiting", "等待用户人工确认；系统不会自动投递、发送 HR 消息或确认面试时间。")
    _add_edge_trace(state, "require_user_approval_node", "stop_for_human", "END", "approval_required is true and approved_by_user is false")
    _set_node_debug(
        state,
        "require_user_approval_node",
        llm_used=False,
        database_read=False,
        status="waiting",
        requires_user_approval=True,
    )
    _record_state_snapshot(state, "require_user_approval_node")
    return state


def handle_error_node(state: WorkflowState) -> WorkflowState:
    _add_step(state, "handle_error", "failed", state.get("error_message") or "workflow failed")
    _add_edge_trace(state, "handle_error_node", "end", "END", state.get("error_message") or "workflow failed")
    _set_node_debug(state, "handle_error_node", llm_used=False, database_read=False, status="failed")
    _record_state_snapshot(state, "handle_error_node")
    return state


def _next_after_error_check(state: WorkflowState) -> str:
    return "error" if state.get("error_message") else "continue"


def _add_step(state: WorkflowState, name: str, status: str, summary: str) -> None:
    steps = list(state.get("workflow_steps", []))
    steps.append({"name": name, "status": status, "summary": summary})
    state["workflow_steps"] = steps


def _record_state_snapshot(state: WorkflowState, after_node: str) -> None:
    snapshots = list(state.get("state_snapshots", []))
    snapshots.append(
        {
            "after_node": after_node,
            "candidate_profile_loaded": bool(state.get("candidate_profile_loaded")),
            "application_loaded": bool(state.get("application_loaded")),
            "company_name": state.get("company_name", ""),
            "job_title": state.get("job_title", ""),
            "has_job_match": bool(state.get("job_match")),
            "has_hr_intent": bool(state.get("hr_intent")),
            "has_application_review": bool(state.get("application_review")),
            "has_hr_reply_package": bool(state.get("hr_reply_package")),
            "has_reply_strategy": bool(state.get("reply_strategy_for_user")),
            "has_hr_reply_draft": bool(state.get("hr_reply_draft")),
            "has_hr_reply": bool(state.get("hr_reply")),
            "approval_required": bool(state.get("approval_required")),
            "approved_by_user": bool(state.get("approved_by_user")),
            "next_action": state.get("next_action", ""),
            "error_message": state.get("error_message"),
        }
    )
    state["state_snapshots"] = snapshots


def _add_edge_trace(state: WorkflowState, from_node: str, decision: str, to_node: str, reason: str) -> None:
    edge_trace = list(state.get("edge_trace", []))
    edge_trace.append({"from": from_node, "decision": decision, "to": to_node, "reason": reason})
    state["edge_trace"] = edge_trace


def _set_node_debug(
    state: WorkflowState,
    node_name: str,
    *,
    llm_used: bool,
    database_read: bool,
    status: str,
    database_write: bool = False,
    external_api_called: bool = False,
    requires_user_approval: bool = False,
    draft_source: Optional[str] = None,
) -> None:
    node_debug = dict(state.get("node_debug", {}))
    payload: Dict[str, Any] = {
        "llm_used": llm_used,
        "database_read": database_read,
        "database_write": database_write,
        "external_api_called": external_api_called,
        "status": status,
    }
    if requires_user_approval:
        payload["requires_user_approval"] = True
    if draft_source:
        payload["draft_source"] = draft_source
    node_debug[node_name] = payload
    state["node_debug"] = node_debug


def _graph_structure() -> Dict[str, Any]:
    return {
        "nodes": [
            "load_profile_node",
            "load_application_node",
            "run_application_review_node",
            "generate_hr_reply_package_node",
            "require_user_approval_node",
            "handle_error_node",
        ],
        "edges": [
            "START -> load_profile_node",
            "load_profile_node -> load_application_node",
            "load_application_node -> run_application_review_node",
            "run_application_review_node -> generate_hr_reply_package_node",
            "generate_hr_reply_package_node -> require_user_approval_node",
            "require_user_approval_node -> END",
            "handle_error_node -> END",
        ],
        "conditional_edges": [
            {"from": "load_profile_node", "condition": "error_message exists ? handle_error_node : load_application_node"},
            {"from": "load_application_node", "condition": "error_message exists ? handle_error_node : run_application_review_node"},
            {"from": "run_application_review_node", "condition": "error_message exists ? handle_error_node : generate_hr_reply_package_node"},
            {"from": "generate_hr_reply_package_node", "condition": "error_message exists ? handle_error_node : require_user_approval_node"},
        ],
    }


def _select_next_action(state: WorkflowState) -> str:
    package = state.get("hr_reply_package")
    if package and (package.get("hr_reply_draft") or {}).get("draft_goal"):
        return "请用户审核 HR 回复草稿，确认后再决定是否发送。"
    application_review = state.get("application_review", {})
    if application_review.get("recommended_action"):
        return str(application_review["recommended_action"])
    return "请用户查看 LangGraph workflow preview 后决定下一步动作。"


def _build_response_data(state: WorkflowState) -> Dict[str, Any]:
    job_match = state.get("job_match", {})
    hr_intent = state.get("hr_intent")
    application_review = state.get("application_review", {})
    return {
        "workflow_mode": "langgraph_preview",
        "workflow_engine": "langgraph_stategraph",
        "application_id": state["application_id"],
        "company_name": state.get("company_name", ""),
        "job_title": state.get("job_title", ""),
        "workflow_steps": state.get("workflow_steps", []),
        "state_summary": {
            "has_candidate_profile": bool(state.get("candidate_profile_loaded")),
            "has_application": bool(state.get("application_loaded")),
            "has_hr_message": bool(state.get("hr_message")),
            "match_level": job_match.get("match_level"),
            "review_level": state.get("review_level") or application_review.get("review_level"),
            "confidence": state.get("confidence") or application_review.get("confidence"),
            "primary_intent": hr_intent.get("primary_intent") if hr_intent else None,
            "reply_draft_generated": bool(state.get("hr_reply_draft")),
        },
        "application_review": application_review,
        "job_match": job_match,
        "hr_intent": hr_intent,
        "hr_reply_package": state.get("hr_reply_package"),
        "reply_strategy_for_user": state.get("reply_strategy_for_user"),
        "hr_reply_draft": state.get("hr_reply_draft"),
        "hr_reply": state.get("hr_reply"),
        "approval_required": bool(state.get("approval_required")),
        "approved_by_user": bool(state.get("approved_by_user")),
        "next_action": state.get("next_action", ""),
        "graph_structure": _graph_structure(),
        "state_snapshots": state.get("state_snapshots", []),
        "edge_trace": state.get("edge_trace", []),
        "node_debug": state.get("node_debug", {}),
        "debug": state.get("debug", _base_debug()),
    }


def _base_debug() -> Dict[str, Any]:
    return {
        "llm_used": False,
        "langgraph_used": True,
        "application_review_used": False,
        "hr_reply_draft_used": False,
        "rag_used": False,
        "playwright_used": False,
        "auto_apply": False,
        "auto_send_message": False,
        "auto_confirm_interview": False,
        "database_write_intended": False,
        "workflow_engine": "langgraph_stategraph",
    }


def _merge_debug_after_reply_package(debug: Dict[str, Any], package: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(debug)
    merged["llm_used"] = bool(package.get("llm_used"))
    merged["application_review_used"] = True
    merged["hr_reply_draft_used"] = True
    merged["langgraph_used"] = True
    merged["rag_used"] = False
    merged["playwright_used"] = False
    merged["auto_apply"] = False
    merged["auto_send_message"] = False
    merged["auto_confirm_interview"] = False
    merged["database_write_intended"] = False
    merged["workflow_engine"] = "langgraph_stategraph"
    return merged
