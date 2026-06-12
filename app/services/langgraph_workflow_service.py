from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.application_service import get_application
from app.services.hr_intent_service import analyze_hr_message
from app.services.hr_reply_service import generate_hr_reply
from app.services.job_match_service import analyze_job_match
from app.services.profile_service import get_candidate_profile


class WorkflowState(TypedDict, total=False):
    application_id: int
    hr_message: Optional[str]
    candidate_profile_loaded: bool
    application_loaded: bool
    company_name: str
    job_title: str
    job_match: Dict[str, Any]
    hr_intent: Optional[Dict[str, Any]]
    hr_reply: Optional[Dict[str, Any]]
    workflow_steps: List[Dict[str, str]]
    approval_required: bool
    approved_by_user: bool
    next_action: str
    error_message: Optional[str]
    state_snapshots: List[Dict[str, Any]]
    edge_trace: List[Dict[str, Any]]
    debug: Dict[str, Any]


def run_langgraph_workflow_preview(
    application_id: int,
    hr_message: Optional[str] = None,
) -> Dict[str, Any]:
    """运行最小 LangGraph StateGraph 版 workflow preview。

    主要输入：application_id，以及可选 HR message。
    主要输出：workflow_steps、graph_structure、state_snapshots、edge_trace、job_match、hr_intent、hr_reply 和人工审批状态。
    副作用：只读 SQLite，不写 application；使用 LangGraph StateGraph 编排；不调用 LLM，不自动发送 HR 消息，不自动投递。
    """
    app = _build_graph()
    initial_state: WorkflowState = {
        "application_id": application_id,
        "hr_message": hr_message,
        "candidate_profile_loaded": False,
        "application_loaded": False,
        "company_name": "",
        "job_title": "",
        "job_match": {},
        "hr_intent": None,
        "hr_reply": None,
        "workflow_steps": [],
        "approval_required": False,
        "approved_by_user": False,
        "next_action": "",
        "error_message": None,
        "state_snapshots": [],
        "edge_trace": [],
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
    graph.add_node("run_job_match_node", run_job_match_node)
    graph.add_node("analyze_hr_intent_node", analyze_hr_intent_node)
    graph.add_node("generate_reply_draft_node", generate_reply_draft_node)
    graph.add_node("require_user_approval_node", require_user_approval_node)
    graph.add_node("handle_error_node", handle_error_node)

    graph.add_edge(START, "load_profile_node")
    graph.add_conditional_edges(
        "load_profile_node",
        _next_after_error_check,
        {
            "error": "handle_error_node",
            "continue": "load_application_node",
        },
    )
    graph.add_conditional_edges(
        "load_application_node",
        _next_after_error_check,
        {
            "error": "handle_error_node",
            "continue": "run_job_match_node",
        },
    )
    graph.add_edge("run_job_match_node", "analyze_hr_intent_node")
    graph.add_edge("analyze_hr_intent_node", "generate_reply_draft_node")
    graph.add_edge("generate_reply_draft_node", "require_user_approval_node")
    graph.add_edge("require_user_approval_node", END)
    graph.add_edge("handle_error_node", END)
    return graph.compile()


def load_profile_node(state: WorkflowState) -> WorkflowState:
    profile = get_candidate_profile()
    if profile is None:
        state["error_message"] = "candidate_profile not found"
        _add_edge_trace(
            state,
            "load_profile_node",
            "error",
            "handle_error_node",
            "candidate_profile not found",
        )
        _record_state_snapshot(state, "load_profile_node")
        return state

    state["candidate_profile_loaded"] = True
    _add_step(
        state,
        "load_candidate_profile",
        "completed",
        "已读取 candidate_profile，作为 LangGraph workflow 的求职者上下文。",
    )
    _add_edge_trace(
        state,
        "load_profile_node",
        "continue",
        "load_application_node",
        "error_message is empty",
    )
    _record_state_snapshot(state, "load_profile_node")
    return state


def load_application_node(state: WorkflowState) -> WorkflowState:
    application = get_application(state["application_id"])
    if application is None:
        state["error_message"] = "application not found"
        _add_edge_trace(
            state,
            "load_application_node",
            "error",
            "handle_error_node",
            "application not found",
        )
        _record_state_snapshot(state, "load_application_node")
        return state

    state["application_loaded"] = True
    state["company_name"] = application.company_name
    state["job_title"] = application.job_title
    _add_step(
        state,
        "load_application",
        "completed",
        "已读取 application，作为 LangGraph workflow 的投递上下文。",
    )
    _add_edge_trace(
        state,
        "load_application_node",
        "continue",
        "run_job_match_node",
        "error_message is empty",
    )
    _record_state_snapshot(state, "load_application_node")
    return state


def run_job_match_node(state: WorkflowState) -> WorkflowState:
    state["job_match"] = analyze_job_match(
        application_id=state["application_id"],
        update_application=False,
    )
    _add_step(
        state,
        "run_job_match",
        "completed",
        "已复用 /job_match 规则评分能力，但未回写 application。",
    )
    _add_edge_trace(
        state,
        "run_job_match_node",
        "continue",
        "analyze_hr_intent_node",
        "job_match completed without database write",
    )
    _record_state_snapshot(state, "run_job_match_node")
    return state


def analyze_hr_intent_node(state: WorkflowState) -> WorkflowState:
    hr_message = state.get("hr_message")
    if not hr_message:
        _add_step(
            state,
            "analyze_hr_intent",
            "skipped",
            "未传入 HR message，跳过 HR intent 分析。",
        )
        _add_edge_trace(
            state,
            "analyze_hr_intent_node",
            "continue",
            "generate_reply_draft_node",
            "hr_message is empty",
        )
        _record_state_snapshot(state, "analyze_hr_intent_node")
        return state

    state["hr_intent"] = analyze_hr_message(
        message=hr_message,
        company_name=state.get("company_name", ""),
        job_title=state.get("job_title", ""),
    )
    _add_step(
        state,
        "analyze_hr_intent",
        "completed",
        "已复用规则版 HR Intent Analyzer 分析 HR message。",
    )
    _add_edge_trace(
        state,
        "analyze_hr_intent_node",
        "continue",
        "generate_reply_draft_node",
        "hr intent analyzed",
    )
    _record_state_snapshot(state, "analyze_hr_intent_node")
    return state


def generate_reply_draft_node(state: WorkflowState) -> WorkflowState:
    hr_message = state.get("hr_message")
    if not hr_message:
        _add_step(
            state,
            "generate_reply_draft",
            "skipped",
            "未传入 HR message，跳过 HR 回复草稿生成。",
        )
        _add_edge_trace(
            state,
            "generate_reply_draft_node",
            "continue",
            "require_user_approval_node",
            "hr_message is empty",
        )
        _record_state_snapshot(state, "generate_reply_draft_node")
        return state

    hr_reply = generate_hr_reply(
        message=hr_message,
        application_id=state["application_id"],
        company_name="",
        job_title="",
        extra_context="",
        update_application=False,
    )
    if hr_reply is None:
        state["error_message"] = "candidate_profile not found"
        _record_state_snapshot(state, "generate_reply_draft_node")
        return state

    state["hr_reply"] = hr_reply
    _add_step(
        state,
        "generate_reply_draft",
        "completed",
        "已生成 Human-in-the-loop 回复草稿，但未更新 application，也未发送消息。",
    )
    _add_edge_trace(
        state,
        "generate_reply_draft_node",
        "continue",
        "require_user_approval_node",
        "reply draft generated without database write",
    )
    _record_state_snapshot(state, "generate_reply_draft_node")
    return state


def require_user_approval_node(state: WorkflowState) -> WorkflowState:
    state["approval_required"] = True
    state["approved_by_user"] = False
    state["next_action"] = _select_next_action(state)
    _add_step(
        state,
        "require_user_approval",
        "waiting",
        "等待用户人工确认；系统不会自动投递、发送 HR 消息或确认面试时间。",
    )
    _add_edge_trace(
        state,
        "require_user_approval_node",
        "stop_for_human",
        "END",
        "approval_required is true and approved_by_user is false",
    )
    _record_state_snapshot(state, "require_user_approval_node")
    return state


def handle_error_node(state: WorkflowState) -> WorkflowState:
    _add_step(
        state,
        "handle_error",
        "failed",
        state.get("error_message") or "workflow failed",
    )
    _add_edge_trace(
        state,
        "handle_error_node",
        "end",
        "END",
        state.get("error_message") or "workflow failed",
    )
    _record_state_snapshot(state, "handle_error_node")
    return state


def _next_after_error_check(state: WorkflowState) -> str:
    return "error" if state.get("error_message") else "continue"


def _add_step(
    state: WorkflowState,
    name: str,
    status: str,
    summary: str,
) -> None:
    steps = list(state.get("workflow_steps", []))
    steps.append(
        {
            "name": name,
            "status": status,
            "summary": summary,
        }
    )
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
            "has_hr_reply": bool(state.get("hr_reply")),
            "approval_required": bool(state.get("approval_required")),
            "approved_by_user": bool(state.get("approved_by_user")),
            "next_action": state.get("next_action", ""),
            "error_message": state.get("error_message"),
        }
    )
    state["state_snapshots"] = snapshots


def _add_edge_trace(
    state: WorkflowState,
    from_node: str,
    decision: str,
    to_node: str,
    reason: str,
) -> None:
    edge_trace = list(state.get("edge_trace", []))
    edge_trace.append(
        {
            "from": from_node,
            "decision": decision,
            "to": to_node,
            "reason": reason,
        }
    )
    state["edge_trace"] = edge_trace


def _graph_structure() -> Dict[str, Any]:
    return {
        "nodes": [
            "load_profile_node",
            "load_application_node",
            "run_job_match_node",
            "analyze_hr_intent_node",
            "generate_reply_draft_node",
            "require_user_approval_node",
            "handle_error_node",
        ],
        "edges": [
            "START -> load_profile_node",
            "run_job_match_node -> analyze_hr_intent_node",
            "analyze_hr_intent_node -> generate_reply_draft_node",
            "generate_reply_draft_node -> require_user_approval_node",
            "require_user_approval_node -> END",
            "handle_error_node -> END",
        ],
        "conditional_edges": [
            {
                "from": "load_profile_node",
                "condition": "error_message exists ? handle_error_node : load_application_node",
            },
            {
                "from": "load_application_node",
                "condition": "error_message exists ? handle_error_node : run_job_match_node",
            },
        ],
    }


def _select_next_action(state: WorkflowState) -> str:
    hr_reply = state.get("hr_reply")
    if hr_reply and hr_reply.get("suggested_followup"):
        return str(hr_reply["suggested_followup"])
    job_match = state.get("job_match", {})
    if job_match.get("suggested_next_action"):
        return str(job_match["suggested_next_action"])
    return "请用户查看 LangGraph workflow preview 后决定下一步动作。"


def _build_response_data(state: WorkflowState) -> Dict[str, Any]:
    job_match = state.get("job_match", {})
    hr_intent = state.get("hr_intent")
    hr_reply = state.get("hr_reply")
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
            "primary_intent": hr_intent.get("primary_intent") if hr_intent else None,
            "reply_draft_generated": bool(hr_reply and hr_reply.get("reply_draft")),
        },
        "job_match": job_match,
        "hr_intent": hr_intent,
        "hr_reply": hr_reply,
        "approval_required": bool(state.get("approval_required")),
        "approved_by_user": bool(state.get("approved_by_user")),
        "next_action": state.get("next_action", ""),
        "graph_structure": _graph_structure(),
        "state_snapshots": state.get("state_snapshots", []),
        "edge_trace": state.get("edge_trace", []),
        "debug": state.get("debug", _base_debug()),
    }


def _base_debug() -> Dict[str, Any]:
    return {
        "llm_used": False,
        "langgraph_used": True,
        "rag_used": False,
        "playwright_used": False,
        "auto_apply": False,
        "auto_send_message": False,
        "auto_confirm_interview": False,
        "database_write_intended": False,
        "workflow_engine": "langgraph_stategraph",
    }
