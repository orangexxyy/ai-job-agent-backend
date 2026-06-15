import argparse
import sys
import time
from typing import Any, Callable, Dict, List, Optional

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:8001"
TIMEOUT_SECONDS = 8

PROFILE_FIELDS = [
    "expected_salary_min",
    "expected_salary_max",
    "minimum_salary",
    "salary_note",
    "availability_note",
    "preferred_cities",
    "acceptable_cities",
    "relocation_policy",
    "outsourcing_policy",
    "onsite_policy",
    "remote_policy",
    "overtime_policy",
    "business_trip_policy",
    "target_roles",
    "available_projects",
    "truth_boundaries",
    "resume_text",
    "project_context",
]


class SmokeTestHarness:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.results: List[bool] = []
        self.original_profile: Optional[Dict[str, Any]] = None
        self.original_profile_exists = False
        self.application_id: Optional[int] = None
        self.interview_slot_id: Optional[int] = None
        self.timestamp = int(time.time())

    def run(self) -> int:
        if not self._backup_profile():
            self._print_summary()
            return 1

        self._run_step("health check", self._test_health)
        self._run_step("save test profile", self._test_save_profile)
        self._run_step("read test profile", self._test_read_profile)
        self._run_step("create application", self._test_create_application)
        self._run_step("read application", self._test_read_application)
        self._run_step("workflow preview", self._test_workflow_preview)
        self._run_step(
            "verify workflow preview is read-only",
            self._test_application_after_workflow_preview,
        )
        self._run_step(
            "langgraph workflow preview",
            self._test_langgraph_workflow_preview,
        )
        self._run_step(
            "verify langgraph workflow preview is read-only",
            self._test_application_after_langgraph_workflow_preview,
        )
        self._run_step("analyze job match", self._test_job_match)
        self._run_step(
            "verify application updated by job match",
            self._test_application_after_job_match,
        )
        self._run_step(
            "missing application_id job match",
            self._test_missing_application_job_match,
        )
        self._run_step("application review", self._test_application_review)
        self._run_step(
            "high risk application review",
            self._test_high_risk_application_review,
        )
        self._run_step(
            "LLM enhanced application review",
            self._test_llm_enhanced_application_review,
        )
        self._run_step(
            "LLM HR reply draft",
            self._test_llm_hr_reply_draft,
        )
        self._run_step(
            "project intro fact boundary",
            self._test_project_intro_fact_boundary,
        )
        self._run_step(
            "interview schedule without availability slot",
            self._test_interview_schedule_without_slot,
        )
        self._run_step(
            "create interview availability slot",
            self._test_create_interview_availability_slot,
        )
        self._run_step(
            "interview schedule with availability slot",
            self._test_interview_schedule_with_slot,
        )
        self._run_step(
            "langgraph interview schedule safety",
            self._test_langgraph_interview_schedule_safety,
        )
        self._run_step(
            "expire interview availability slot",
            self._test_expire_interview_availability_slot,
        )
        self._run_step(
            "verify application review is read-only",
            self._test_application_after_application_review,
        )
        self._run_step("patch application", self._test_patch_application)
        self._run_step("reject invalid application status", self._test_invalid_status)
        self._run_step("analyze HR message", self._test_hr_analyze)
        self._run_step("old HR reply", self._test_old_hr_reply)
        self._run_step(
            "context-enhanced HR reply",
            self._test_context_enhanced_hr_reply,
        )
        self._run_step(
            "application-context HR reply",
            self._test_application_context_hr_reply,
        )
        self._run_step(
            "verify application updated by HR reply",
            self._test_application_after_hr_reply,
        )
        self._run_step(
            "missing application_id HR reply",
            self._test_missing_application_hr_reply,
        )
        self._run_step("close harness application", self._test_close_application)
        self._run_step("restore profile", self._restore_profile)

        self._print_summary()
        return 0 if all(self.results) else 1

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Optional[requests.Response]:
        try:
            return requests.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json_body,
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            print(f"[FAIL] request {method} {path}: {exc}")
            return None

    def _backup_profile(self) -> bool:
        response = self._request("GET", "/profile")
        if response is None:
            print("API server is not reachable. Please start FastAPI first.")
            return False
        if response.status_code != 200:
            print(f"[FAIL] backup profile: HTTP {response.status_code}")
            return False

        payload = response.json()
        self.original_profile_exists = bool(payload.get("success"))
        if self.original_profile_exists and payload.get("data"):
            self.original_profile = self._profile_input_from_response(payload["data"])
        return True

    def _run_step(self, name: str, func: Callable[[], bool]) -> None:
        try:
            passed = func()
        except Exception as exc:
            print(f"[FAIL] {name}: {exc}")
            passed = False

        self.results.append(passed)
        if passed:
            suffix = f" id={self.application_id}" if name == "create application" else ""
            print(f"[PASS] {name}{suffix}")
        else:
            print(f"[FAIL] {name}")

    def _test_health(self) -> bool:
        response = self._request("GET", "/health")
        if response is None or response.status_code != 200:
            return False
        payload = response.json()
        return payload.get("success") is True or payload.get("status") in {"ok", "healthy"}

    def _test_save_profile(self) -> bool:
        response = self._request("POST", "/profile", json_body=self._test_profile())
        return self._success(response)

    def _test_read_profile(self) -> bool:
        response = self._request("GET", "/profile")
        if not self._success(response):
            return False
        payload = response.json()
        return payload.get("data", {}).get("expected_salary_min") == 15000

    def _test_create_application(self) -> bool:
        response = self._request(
            "POST",
            "/applications",
            json_body=self._test_application(),
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        application_id = data.get("id")
        if not isinstance(application_id, int):
            return False
        self.application_id = application_id
        keywords = set(data.get("jd_keywords", []))
        keyword_hits = len({"Python", "FastAPI", "RAG"}.intersection(keywords))
        return (
            data.get("source_type") == "boss"
            and bool(data.get("jd_summary"))
            and keyword_hits >= 2
            and isinstance(data.get("jd_required_skills"), list)
            and bool(data.get("jd_years_requirement"))
            and "杭州" in data.get("jd_location_requirement", "")
            and data.get("jd_remote_type") in {"remote", "hybrid", "onsite", "unknown"}
        )

    def _test_read_application(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request("GET", f"/applications/{self.application_id}")
        return self._success(response) and response.json().get("data", {}).get("id") == self.application_id

    def _test_workflow_preview(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/agent/workflow_preview",
            json_body={
                "application_id": self.application_id,
                "hr_message": "Which RAG or Agent related projects have you built?",
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        step_names = {step.get("name") for step in data.get("workflow_steps", [])}
        debug = data.get("debug", {})
        hr_reply = data.get("hr_reply") or {}
        return (
            data.get("workflow_mode") == "rule_based_preview"
            and data.get("application_id") == self.application_id
            and {
                "load_candidate_profile",
                "load_application",
                "run_job_match",
                "analyze_hr_intent",
                "generate_reply_draft",
                "require_user_approval",
            }.issubset(step_names)
            and data.get("approval_required") is True
            and data.get("approved_by_user") is False
            and debug.get("llm_used") is False
            and debug.get("langgraph_used") is False
            and debug.get("rag_used") is False
            and debug.get("auto_apply") is False
            and debug.get("auto_send_message") is False
            and debug.get("database_write_intended") is False
            and bool(hr_reply.get("reply_draft"))
            and hr_reply.get("application_updated") is False
            and hr_reply.get("debug", {}).get("application_update_skipped") is True
        )

    def _test_application_after_workflow_preview(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request("GET", f"/applications/{self.application_id}")
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        return (
            data.get("status") == "saved"
            and data.get("next_action") == "Harness initial action"
            and not data.get("last_hr_message")
            and data.get("match_score") is None
        )

    def _test_langgraph_workflow_preview(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/agent/langgraph_workflow_preview",
            json_body={
                "application_id": self.application_id,
                "hr_message": "这个岗位是外包项目，需要长期驻场客户现场，你能接受吗？",
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        step_names = {step.get("name") for step in data.get("workflow_steps", [])}
        graph_structure = data.get("graph_structure") or {}
        graph_nodes = set(graph_structure.get("nodes", []))
        state_snapshots = data.get("state_snapshots") or []
        snapshot_nodes = {snapshot.get("after_node") for snapshot in state_snapshots}
        edge_trace = data.get("edge_trace") or []
        debug = data.get("debug", {})
        node_debug = data.get("node_debug") or {}
        application_review = data.get("application_review") or {}
        hr_reply_package = data.get("hr_reply_package") or {}
        reply_strategy = data.get("reply_strategy_for_user") or {}
        hr_reply_draft = data.get("hr_reply_draft") or {}
        return (
            data.get("workflow_mode") == "langgraph_preview"
            and data.get("workflow_engine") == "langgraph_stategraph"
            and data.get("application_id") == self.application_id
            and {
                "load_candidate_profile",
                "load_application",
                "run_application_review",
                "generate_hr_reply_package",
                "require_user_approval",
            }.issubset(step_names)
            and data.get("approval_required") is True
            and data.get("approved_by_user") is False
            and debug.get("langgraph_used") is True
            and debug.get("application_review_used") is True
            and debug.get("hr_reply_draft_used") is True
            and debug.get("rag_used") is False
            and debug.get("auto_apply") is False
            and debug.get("auto_send_message") is False
            and debug.get("auto_confirm_interview") is False
            and debug.get("database_write_intended") is False
            and {
                "load_profile_node",
                "load_application_node",
                "run_application_review_node",
                "generate_hr_reply_package_node",
                "require_user_approval_node",
            }.issubset(graph_nodes)
            and bool(graph_structure.get("conditional_edges"))
            and bool(state_snapshots)
            and "load_profile_node" in snapshot_nodes
            and "run_application_review_node" in snapshot_nodes
            and "generate_hr_reply_package_node" in snapshot_nodes
            and "require_user_approval_node" in snapshot_nodes
            and bool(edge_trace)
            and any(edge.get("from") == "load_profile_node" for edge in edge_trace)
            and any(
                edge.get("to") in {"require_user_approval_node", "END"}
                for edge in edge_trace
            )
            and bool(application_review)
            and bool(reply_strategy)
            and bool(hr_reply_draft)
            and bool(hr_reply_package)
            and hr_reply_package.get("draft_source") in {"llm", "rule_fallback"}
            and node_debug.get("run_application_review_node", {}).get("llm_used") is False
            and node_debug.get("generate_hr_reply_package_node", {}).get("database_write") is False
            and data.get("hr_reply") == hr_reply_draft
        )

    def _test_application_after_langgraph_workflow_preview(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request("GET", f"/applications/{self.application_id}")
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        return (
            data.get("status") == "saved"
            and data.get("next_action") == "Harness initial action"
            and not data.get("last_hr_message")
            and data.get("match_score") is None
        )

    def _test_job_match(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/job_match",
            json_body={
                "application_id": self.application_id,
                "update_application": True,
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        match_score = data.get("match_score")
        return (
            data.get("application_id") == self.application_id
            and isinstance(match_score, int)
            and 0 <= match_score <= 100
            and data.get("match_level")
            in {"strong_match", "possible_match", "weak_match", "not_recommended"}
            and bool(data.get("dimensions"))
            and data.get("debug", {}).get("llm_used") is False
        )

    def _test_application_after_job_match(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request("GET", f"/applications/{self.application_id}")
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        return (
            isinstance(data.get("match_score"), int)
            and bool(data.get("next_action"))
            and data.get("status") == "saved"
        )

    def _test_missing_application_job_match(self) -> bool:
        response = self._request(
            "POST",
            "/job_match",
            json_body={
                "application_id": 999999999,
                "update_application": True,
            },
        )
        if response is None or response.status_code != 200:
            return False
        payload = response.json()
        return (
            payload.get("success") is False
            and payload.get("message") == "application not found"
            and payload.get("data") is None
        )

    def _test_application_review(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/application_review",
            json_body={
                "application_id": self.application_id,
                "update_application": False,
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        debug = data.get("debug", {})
        llm_ready_context = data.get("llm_ready_context", {})
        return (
            data.get("application_id") == self.application_id
            and data.get("review_mode") == "rule_based"
            and data.get("llm_used") is False
            and isinstance(data.get("review_score"), int)
            and data.get("review_level")
            in {
                "high_priority",
                "normal_priority",
                "cautious_follow_up",
                "low_priority",
                "not_recommended",
            }
            and data.get("confidence") in {"high", "medium", "low"}
            and isinstance(data.get("evidence"), list)
            and bool(data.get("evidence"))
            and bool(data.get("recommended_action"))
            and isinstance(data.get("reasons"), list)
            and data.get("human_review_required") is True
            and llm_ready_context.get("confidence") in {"high", "medium", "low"}
            and isinstance(llm_ready_context.get("evidence_summary"), list)
            and debug.get("auto_send_message") is False
            and debug.get("auto_apply") is False
            and debug.get("auto_update_status") is False
            and debug.get("llm_used") is False
            and debug.get("rag_used") is False
            and debug.get("playwright_used") is False
        )

    def _test_high_risk_application_review(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/application_review",
            json_body={
                "application_id": self.application_id,
                "hr_message": "这个岗位是外包，需要长期驻场，可以接受吗？",
                "update_application": False,
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        risk_text = " ".join(data.get("risk_flags", []))
        evidence = data.get("evidence", [])
        action = data.get("recommended_action", "")
        return (
            data.get("review_level")
            in {"cautious_follow_up", "not_recommended", "low_priority"}
            and ("外包" in risk_text or "驻场" in risk_text)
            and any(item.get("type") == "risk_signal" for item in evidence)
            and any(item.get("source") == "hr_message" for item in evidence)
            and ("确认" in action or "谨慎" in action)
            and data.get("suggested_next_message_type") == "confirm_details"
        )

    def _test_llm_enhanced_application_review(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/application_review/llm_enhance",
            json_body={
                "application_id": self.application_id,
                "hr_message": "这个岗位是外包，需要长期驻场，可以接受吗？",
                "include_raw_prompt": False,
            },
        )
        if response is None or response.status_code != 200:
            return False
        payload = response.json()
        data = payload.get("data") or {}
        debug = data.get("debug", {})
        llm_error = data.get("llm_error") or payload.get("message")
        llm_not_used_with_error = data.get("llm_used") is False and bool(llm_error)
        llm_used_with_result = (
            data.get("llm_used") is True
            and isinstance(data.get("llm_enhanced_review"), dict)
        )
        return (
            payload.get("success") is True
            and data.get("application_id") == self.application_id
            and bool(data.get("rule_review"))
            and data.get("human_review_required") is True
            and (llm_not_used_with_error or llm_used_with_result)
            and debug.get("auto_send_message") is False
            and debug.get("auto_apply") is False
            and debug.get("auto_update_status") is False
            and debug.get("database_write_intended") is False
            and "raw_prompt_messages" not in debug
        )

    def _test_llm_hr_reply_draft(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/application_review/hr_reply_draft",
            json_body={
                "application_id": self.application_id,
                "hr_message": "这个岗位是外包项目，需要长期驻场客户现场，你能接受吗？",
                "draft_tone": "professional",
                "include_raw_prompt": False,
            },
        )
        if response is None or response.status_code != 200:
            return False
        payload = response.json()
        data = payload.get("data") or {}
        debug = data.get("debug", {})
        strategy = data.get("reply_strategy_for_user") or {}
        draft = data.get("hr_reply_draft") or {}
        return (
            payload.get("success") is True
            and data.get("application_id") == self.application_id
            and isinstance(strategy, dict)
            and bool(strategy.get("summary"))
            and isinstance(draft, dict)
            and isinstance(draft.get("draft_text"), str)
            and data.get("draft_type") == "confirm_details"
            and data.get("draft_source") in {"llm", "rule_fallback"}
            and isinstance(data.get("draft_text"), str)
            and isinstance(data.get("safe_to_send"), bool)
            and data.get("human_review_required") is True
            and isinstance(data.get("llm_used"), bool)
            and bool(data.get("rule_review"))
            and debug.get("analysis_and_draft_combined") is True
            and debug.get("step14_llm_enhance_called") is False
            and debug.get("auto_send_message") is False
            and debug.get("auto_apply") is False
            and debug.get("auto_update_status") is False
            and debug.get("database_write_intended") is False
            and "raw_prompt_messages" not in debug
        )

    def _test_project_intro_fact_boundary(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/application_review/hr_reply_draft",
            json_body={
                "application_id": self.application_id,
                "hr_message": "你做过 RAG 或 Agent 相关项目吗？可以简单介绍一下吗？",
                "draft_tone": "professional",
                "include_raw_prompt": False,
            },
        )
        if response is None or response.status_code != 200:
            return False
        payload = response.json()
        data = payload.get("data") or {}
        draft_text = data.get("draft_text") or ""
        forbidden = [
            "AI Job Agent 使用 RAG 检索",
            "AI Job Agent 利用 RAG 技术",
            "AI Job Agent 使用 RAG",
            "RAG 项目使用 LangGraph",
            "RAG 项目接入 LangGraph",
            "自动发送 HR 消息",
            "自动投递",
            "企业级生产系统",
        ]
        return (
            payload.get("success") is True
            and data.get("draft_type") == "project_intro"
            and bool(draft_text)
            and all(item not in draft_text for item in forbidden)
            and "RAG 企业知识库" in draft_text
            and "AI Job Agent" in draft_text
            and data.get("human_review_required") is True
        )

    def _test_interview_schedule_without_slot(self) -> bool:
        if self.application_id is None:
            return False
        available = self._request("GET", "/interview_availability_slots")
        if available is not None and self._success(available):
            existing_slots = available.json().get("data") or []
            if existing_slots:
                return True
        response = self._request(
            "POST",
            "/application_review/hr_reply_draft",
            json_body={
                "application_id": self.application_id,
                "hr_message": "明天下午三点方便视频面试吗？",
                "draft_tone": "professional",
                "include_raw_prompt": False,
            },
        )
        if response is None or response.status_code != 200:
            return False
        payload = response.json()
        data = payload.get("data") or {}
        draft_text = data.get("draft_text") or ""
        forbidden = ["后天上午", "明天下午或后天上午", "可以明天下午", "明天下午可以"]
        return (
            payload.get("success") is True
            and data.get("draft_type") == "interview_schedule"
            and data.get("availability_missing") is True
            and data.get("available_slots_used") == []
            and data.get("safe_to_send") is False
            and data.get("human_review_required") is True
            and all(item not in draft_text for item in forbidden)
            and ("确认一下日程" in draft_text or "稍后回复" in draft_text)
        )

    def _test_create_interview_availability_slot(self) -> bool:
        response = self._request(
            "POST",
            "/interview_availability_slots",
            json_body={
                "date": "2026-06-20",
                "start_time": "14:00",
                "end_time": "16:00",
                "timezone": "Asia/Shanghai",
                "status": "available",
                "note": f"HARNESS slot {self.timestamp}",
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data") or {}
        self.interview_slot_id = data.get("id")
        return (
            data.get("date") == "2026-06-20"
            and data.get("start_time") == "14:00"
            and data.get("end_time") == "16:00"
            and data.get("status") == "available"
        )

    def _test_interview_schedule_with_slot(self) -> bool:
        if self.application_id is None or self.interview_slot_id is None:
            return False
        response = self._request(
            "POST",
            "/application_review/hr_reply_draft",
            json_body={
                "application_id": self.application_id,
                "hr_message": "最近什么时候方便面试？",
                "draft_tone": "professional",
                "include_raw_prompt": False,
            },
        )
        if response is None or response.status_code != 200:
            return False
        payload = response.json()
        data = payload.get("data") or {}
        draft_text = data.get("draft_text") or ""
        slots = data.get("available_slots_used") or []
        return (
            payload.get("success") is True
            and data.get("draft_type") == "interview_schedule"
            and data.get("availability_missing") is False
            and any(slot.get("id") == self.interview_slot_id for slot in slots)
            and "2026-06-20" in draft_text
            and "14:00-16:00" in draft_text
            and data.get("safe_to_send") is False
            and data.get("human_review_required") is True
        )

    def _test_langgraph_interview_schedule_safety(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/agent/langgraph_workflow_preview",
            json_body={
                "application_id": self.application_id,
                "hr_message": "最近什么时候方便面试？",
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data") or {}
        debug = data.get("debug") or {}
        steps = {step.get("name") for step in data.get("workflow_steps", [])}
        return (
            data.get("approval_required") is True
            and data.get("approved_by_user") is False
            and "require_user_approval" in steps
            and debug.get("auto_confirm_interview") is False
            and debug.get("auto_send_message") is False
        )

    def _test_expire_interview_availability_slot(self) -> bool:
        if self.interview_slot_id is None:
            return False
        response = self._request(
            "PATCH",
            f"/interview_availability_slots/{self.interview_slot_id}",
            json_body={"status": "expired", "note": f"HARNESS expired {self.timestamp}"},
        )
        if not self._success(response):
            return False
        data = response.json().get("data") or {}
        return data.get("status") == "expired"

    def _test_application_after_application_review(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request("GET", f"/applications/{self.application_id}")
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        return data.get("status") == "saved"

    def _test_patch_application(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "PATCH",
            f"/applications/{self.application_id}",
            json_body={
                "status": "hr_contacted",
                "jd_text": (
                    "岗位职责：支持 remote 远程协作，负责 Docker、React "
                    "和 FastAPI 相关 AI 应用开发。"
                ),
                "last_hr_message": "方便明天下午视频面试吗？",
                "next_action": "确认面试时间",
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        keywords = set(data.get("jd_keywords", []))
        return (
            data.get("status") == "hr_contacted"
            and data.get("jd_remote_type") == "remote"
            and {"Docker", "React"}.issubset(keywords)
        )

    def _test_invalid_status(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "PATCH",
            f"/applications/{self.application_id}",
            json_body={"status": "auto_applied"},
        )
        if response is None or response.status_code != 200:
            return False
        payload = response.json()
        return payload.get("success") is False and "invalid status" in payload.get("message", "")

    def _test_hr_analyze(self) -> bool:
        response = self._request(
            "POST",
            "/hr/analyze",
            json_body={
                "message": "你期望薪资多少？一周能到岗吗？接受外地吗？",
                "company_name": "HARNESS Demo Company",
                "job_title": "AI Application Developer",
            },
        )
        if not self._success(response):
            return False
        intents = set(response.json().get("data", {}).get("intents", []))
        return {"salary_expectation", "availability", "relocation"}.issubset(intents)

    def _test_old_hr_reply(self) -> bool:
        response = self._request(
            "POST",
            "/hr/reply",
            json_body={
                "message": "你期望薪资多少？一周能到岗吗？接受外地吗？",
                "company_name": "HARNESS Demo Company",
                "job_title": "AI Application Developer",
                "extra_context": "",
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        return bool(data.get("reply_draft")) and data.get("safe_to_send") is True

    def _test_context_enhanced_hr_reply(self) -> bool:
        response = self._request(
            "POST",
            "/hr/reply",
            json_body={
                "message": "Which RAG or Agent related projects have you built?",
                "company_name": "HARNESS Demo Company",
                "job_title": "AI Application Developer",
                "extra_context": "",
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        reply_draft = data.get("reply_draft", "")
        context_used = set(data.get("context_used", []))
        forbidden_phrases = [
            "完整生产级智能招聘系统",
            "自动发送 HR 消息",
            "自动招聘决策",
        ]
        return (
            bool(reply_draft)
            and bool(data.get("selected_context_snippets"))
            and data.get("context_reply_mode") == "profile_context_enhanced"
            and bool(context_used.intersection({"resume_text", "project_context"}))
            and all(phrase not in reply_draft for phrase in forbidden_phrases)
        )

    def _test_application_context_hr_reply(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "POST",
            "/hr/reply",
            json_body={
                "application_id": self.application_id,
                "message": "方便明天下午视频面试吗？",
                "company_name": "",
                "job_title": "",
                "extra_context": "",
            },
        )
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        context = data.get("application_context") or {}
        update_fields = data.get("application_update_fields") or {}
        return (
            data.get("application_id") == self.application_id
            and bool(context.get("company_name"))
            and bool(context.get("job_title"))
            and "jd_text_preview" in context
            and "jd_text" not in context
            and data.get("application_updated") is True
            and update_fields.get("last_hr_message") == "方便明天下午视频面试吗？"
            and update_fields.get("next_action") == "确认面试时间"
        )

    def _test_application_after_hr_reply(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request("GET", f"/applications/{self.application_id}")
        if not self._success(response):
            return False
        data = response.json().get("data", {})
        return (
            data.get("last_hr_message") == "方便明天下午视频面试吗？"
            and data.get("next_action") == "确认面试时间"
            and data.get("status") == "hr_contacted"
        )

    def _test_missing_application_hr_reply(self) -> bool:
        response = self._request(
            "POST",
            "/hr/reply",
            json_body={
                "application_id": 999999999,
                "message": "方便面试吗？",
                "company_name": "",
                "job_title": "",
                "extra_context": "",
            },
        )
        if response is None or response.status_code != 200:
            return False
        payload = response.json()
        return (
            payload.get("success") is False
            and payload.get("message") == "application not found"
            and payload.get("data") is None
        )

    def _test_close_application(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "PATCH",
            f"/applications/{self.application_id}",
            json_body={
                "status": "closed",
                "next_action": "Harness test completed",
            },
        )
        return self._success(response)

    def _restore_profile(self) -> bool:
        if not self.original_profile_exists:
            print("[WARN] no original profile found; test profile was left in place.")
            return True
        if self.original_profile is None:
            print("[WARN] original profile existed but could not be restored.")
            return False
        response = self._request("POST", "/profile", json_body=self.original_profile)
        if not self._success(response):
            print("[WARN] failed to restore original profile.")
            return False
        return True

    def _success(self, response: Optional[requests.Response]) -> bool:
        if response is None or response.status_code != 200:
            return False
        return response.json().get("success") is True

    def _print_summary(self) -> None:
        total = len(self.results)
        passed = sum(1 for result in self.results if result)
        failed = total - passed
        print()
        print("Smoke Test Summary")
        print(f"Total: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")

    def _profile_input_from_response(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        return {field: profile.get(field) for field in PROFILE_FIELDS}

    def _test_profile(self) -> Dict[str, Any]:
        return {
            "expected_salary_min": 15000,
            "expected_salary_max": 20000,
            "minimum_salary": 13000,
            "salary_note": "优先考虑 AI 应用开发方向，具体薪资结合岗位职责沟通。",
            "availability_note": "一周左右可协调",
            "preferred_cities": ["杭州", "上海", "远程"],
            "acceptable_cities": ["AI方向匹配的其他城市可沟通"],
            "relocation_policy": "长期外地驻场不优先，AI方向强匹配可沟通",
            "outsourcing_policy": "优先正式岗位，AI项目质量高可进一步了解",
            "onsite_policy": "正常办公室工作可接受，长期客户现场需进一步沟通",
            "remote_policy": "远程或混合办公可接受",
            "overtime_policy": "项目阶段性加班可沟通，长期高强度加班不优先",
            "business_trip_policy": "短期出差可沟通，长期频繁出差不优先",
            "target_roles": ["AI应用开发工程师", "大模型应用开发工程师"],
            "available_projects": [
                "FastAPI + RAG 企业知识库问答系统",
                "AI Job Agent 智能求职助手",
            ],
            "truth_boundaries": [
                "没有做过完整生产级智能招聘系统",
                "不会自动发送 HR 消息",
            ],
            "resume_text": (
                "Candidate built a FastAPI + RAG enterprise knowledge base demo "
                "with document ingestion, hybrid retrieval, reranker, SQLite "
                "conversation records, and human review. Candidate also built "
                "AI Job Agent for HR intent analysis, reply drafts, and "
                "application tracking."
            ),
            "project_context": (
                "RAG project uses FastAPI, txt/PDF/Excel ingestion, FAISS + BM25 "
                "+ RRF hybrid retrieval, reranker, low_confidence handling, and "
                "SQLite records. AI Job Agent supports candidate_profile, "
                "applications, HR reply, job_match, and API smoke test harness."
            ),
        }

    def _test_application(self) -> Dict[str, Any]:
        return {
            "company_name": f"HARNESS Demo Company {self.timestamp}",
            "job_title": "AI Application Developer",
            "source": "BOSS直聘",
            "job_url": "https://example.com/harness",
            "jd_text": (
                "岗位职责：负责基于 Python、FastAPI、RAG、LangGraph 的企业 AI 应用开发。"
                "任职要求：熟悉 LLM API、向量检索、Prompt Engineering，有 1-3 年后端开发经验，"
                "可接受杭州现场办公。"
            ),
            "status": "saved",
            "next_action": "Harness initial action",
            "notes": "created by scripts/api_smoke_test.py",
            "risk_flags": ["harness_test"],
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local API smoke tests.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"FastAPI base URL. Default: {DEFAULT_BASE_URL}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    harness = SmokeTestHarness(args.base_url)
    return harness.run()


if __name__ == "__main__":
    sys.exit(main())
