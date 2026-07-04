import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_BASE_URL = "http://127.0.0.1:8002"
TIMEOUT_SECONDS = 8
PROFILE_FIELDS = [
    "expected_salary_min", "expected_salary_max", "minimum_salary", "salary_note",
    "availability_note", "preferred_cities", "acceptable_cities", "relocation_policy",
    "outsourcing_policy", "onsite_policy", "remote_policy", "overtime_policy",
    "business_trip_policy", "target_roles", "available_projects", "truth_boundaries",
    "resume_text", "project_context",
]


class AgentWorkflowDemo:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.application_id: Optional[int] = None
        self.slot_ids: List[int] = []
        self.slot_dates: List[str] = []
        self.original_profile: Optional[Dict[str, Any]] = None
        self.original_profile_exists = False
        self.results: List[bool] = []
        self.history_ids: List[int] = []
        self.history_verified = False
        self.timestamp = int(time.time())

    def run(self) -> int:
        if not self._backup_profile():
            self._summary()
            return 1
        try:
            if not self._prepare_demo_data():
                self._summary()
                return 1
            for case in self._cases():
                self.results.append(self._run_case(case))
            history_ok, history_count = self._verify_history()
            self.history_verified = history_ok
            self._summary(history_count)
            return 0 if all(self.results) and history_ok else 1
        finally:
            self._cleanup_demo_data()
            self._restore_profile()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Optional[requests.Response]:
        try:
            return requests.request(
                method,
                f"{self.base_url}{path}",
                json=json_body,
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            print(f"[FAIL] {method} {path}: {exc}", flush=True)
            return None

    def _backup_profile(self) -> bool:
        response = self._request("GET", "/profile")
        if response is None or response.status_code != 200:
            print("FastAPI 服务不可用，请先启动本地服务。", flush=True)
            return False
        payload = response.json()
        self.original_profile_exists = bool(payload.get("success") and payload.get("data"))
        if self.original_profile_exists:
            data = payload["data"]
            self.original_profile = {field: data.get(field) for field in PROFILE_FIELDS}
        return True

    def _prepare_demo_data(self) -> bool:
        profile = self._request("POST", "/profile", json_body=self._demo_profile())
        if not self._success(profile):
            print("[FAIL] candidate_profile demo fixture", flush=True)
            return False
        application = self._request("POST", "/applications", json_body=self._demo_application())
        if not self._success(application):
            print("[FAIL] application demo fixture", flush=True)
            return False
        self.application_id = (application.json().get("data") or {}).get("id")
        if not self.application_id:
            print("[FAIL] application id missing", flush=True)
            return False

        base_date = datetime.now(timezone.utc).date() + timedelta(days=2 + self.timestamp % 20)
        second = self.timestamp % 60
        slot_specs = [
            (0, f"10:00:{second:02d}", f"11:00:{second:02d}"),
            (0, f"15:00:{second:02d}", f"16:00:{second:02d}"),
            (1, f"14:00:{second:02d}", f"15:00:{second:02d}"),
        ]
        for day_offset, start, end in slot_specs:
            slot_date = (base_date + timedelta(days=day_offset)).isoformat()
            response = self._request(
                "POST",
                "/interview_availability_slots",
                json_body={
                    "date": slot_date,
                    "start_time": start,
                    "end_time": end,
                    "timezone": "Asia/Shanghai",
                    "status": "available",
                    "note": f"Step 23 demo slot {self.timestamp}",
                },
            )
            if not self._success(response):
                print("[FAIL] interview slot demo fixture", flush=True)
                return False
            self.slot_ids.append((response.json().get("data") or {}).get("id"))
            self.slot_dates.append(slot_date)
        print(f"[READY] demo_application_id={self.application_id}", flush=True)
        return True

    def _run_case(self, case: Dict[str, Any]) -> bool:
        response = self._request(
            "POST",
            "/agent/reply_send_gate/simulate",
            json_body={
                "application_id": self.application_id,
                "hr_message": case["hr_message"],
                "context_note": "Step 23 workflow demo; no real external action",
                "max_available_slots": 10,
            },
        )
        data = (response.json().get("data") or {}) if self._success(response) else {}
        passed = bool(data) and data.get("final_send_decision") in case["decisions"]
        passed = passed and data.get("auto_send_simulated") is case["simulated"]
        passed = passed and data.get("action_history_written") is case["history"]
        passed = passed and data.get("external_action_performed") is False
        candidate = data.get("reply_candidate") or ""
        if case.get("notification"):
            passed = passed and data.get("requires_user_notification") is True
            passed = passed and any(date in candidate for date in self.slot_dates)
        if not case["simulated"]:
            passed = passed and not any(
                phrase in candidate for phrase in ("我接受", "可以接受", "我马上发")
            )
        for required_text in case.get("required_text", []):
            passed = passed and required_text in candidate
        for forbidden_text in case.get("forbidden_text", []):
            passed = passed and forbidden_text not in candidate
        debug = data.get("debug") or {}
        passed = passed and debug.get("real_message_sent") is False
        passed = passed and debug.get("slot_booked") is False
        if data.get("action_history_id"):
            self.history_ids.append(data["action_history_id"])
        print("\n" + "=" * 68)
        print(f"case_name: {case['name']}")
        print(f"hr_message: {case['hr_message']}")
        print(f"detected_intent: {data.get('detected_intent')}")
        print(f"risk_level: {data.get('risk_level')}")
        print(f"final_send_decision: {data.get('final_send_decision')}")
        print(f"auto_send_simulated: {data.get('auto_send_simulated')}")
        print(f"requires_user_confirmation: {data.get('requires_user_confirmation')}")
        print(f"requires_user_notification: {data.get('requires_user_notification')}")
        print(f"action_history_written: {data.get('action_history_written')}")
        print(f"reply_candidate_summary: {candidate[:160] or '(none)'}")
        if case.get("notification"):
            print(f"demo_slot_used: {any(date in candidate for date in self.slot_dates)}")
        print(f"result: {'PASS' if passed else 'FAIL'}", flush=True)
        return passed

    def _verify_history(self) -> tuple[bool, int]:
        response = self._request(
            "GET",
            f"/applications/{self.application_id}/action_history?limit=100",
        )
        if not self._success(response):
            print("[FAIL] action history verification", flush=True)
            return False, 0
        items = response.json().get("data") or []
        simulated_items = [item for item in items if item.get("id") in self.history_ids]
        passed = (
            len(self.history_ids) == 4
            and len(simulated_items) == 4
            and all(
                item.get("action_type") == "auto_reply_simulated_sent"
                and item.get("action_source") == "agent"
                and item.get("user_confirmed") is False
                and item.get("external_action_performed") is False
                for item in simulated_items
            )
        )
        print(f"\naction_history_verification: {'PASS' if passed else 'FAIL'}", flush=True)
        return passed, len(items)

    def _cleanup_demo_data(self) -> None:
        for slot_id in self.slot_ids:
            if slot_id:
                self._request(
                    "PATCH",
                    f"/interview_availability_slots/{slot_id}",
                    json_body={"status": "expired", "note": "Step 23 demo cleanup"},
                )
        if self.application_id:
            self._request(
                "PATCH",
                f"/applications/{self.application_id}",
                json_body={"status": "closed", "next_action": "Step 23 demo completed"},
            )

    def _restore_profile(self) -> None:
        if self.original_profile_exists and self.original_profile is not None:
            response = self._request("POST", "/profile", json_body=self.original_profile)
            if not self._success(response):
                print("[WARN] 原 candidate_profile 恢复失败。", flush=True)
        else:
            print("[WARN] 原先没有 candidate_profile，Demo profile 将保留。", flush=True)

    def _summary(self, history_count: int = 0) -> None:
        total = len(self.results)
        passed = sum(self.results)
        print("\nAgent Workflow Demo Summary")
        print(f"total_cases: {total}")
        print(f"passed: {passed}")
        print(f"failed: {total - passed}")
        print(f"demo_application_id: {self.application_id}")
        print(f"action_history_count: {history_count}", flush=True)
        print(f"history_verification: {'PASS' if self.history_verified else 'FAIL'}", flush=True)

    @staticmethod
    def _success(response: Optional[requests.Response]) -> bool:
        return bool(
            response is not None
            and response.status_code == 200
            and response.json().get("success") is True
        )

    @staticmethod
    def _demo_profile() -> Dict[str, Any]:
        return {
            "expected_salary_min": 12000,
            "expected_salary_max": 18000,
            "minimum_salary": 10000,
            "salary_note": "薪资需要结合岗位职责由用户确认，不自动承诺。",
            "availability_note": "面试时间只使用 available slots，最终需双方确认。",
            "preferred_cities": ["杭州"],
            "acceptable_cities": ["杭州"],
            "relocation_policy": "异地机会需要用户确认。",
            "outsourcing_policy": "不接受长期外包驻场。",
            "onsite_policy": "杭州正常办公可沟通，客户现场长期驻场不接受。",
            "remote_policy": "远程或混合办公可沟通。",
            "overtime_policy": "不接受单休、996 和长期高强度加班。",
            "business_trip_policy": "短期出差可沟通，长期频繁出差需确认。",
            "target_roles": ["AI 应用开发工程师", "大模型应用开发工程师"],
            "available_projects": ["FastAPI + RAG 企业知识库问答系统", "AI Job Agent 智能求职助手"],
            "truth_boundaries": [
                "RAG 项目未使用 LangGraph。",
                "AI Job Agent 不自动投递、不自动发送 HR 消息、不自动确认面试。",
            ],
            "resume_text": "程伟桔，本科，数据科学与大数据技术，求职方向为 大模型应用开发工程师。",
            "project_context": (
                "RAG 企业知识库项目使用 Python、FastAPI、FAISS、BM25、Reranker 和 React；"
                "AI Job Agent 使用 FastAPI、SQLite、规则策略和 Agent Workflow。"
            ),
        }

    def _demo_application(self) -> Dict[str, Any]:
        return {
            "company_name": f"杭州星云智能科技有限公司 Demo {self.timestamp}",
            "job_title": "AI 应用开发工程师",
            "source": "manual_demo",
            "job_url": "https://example.com/step23-demo",
            "jd_text": (
                "工作地点：杭州。负责企业知识库问答、RAG 检索增强生成、Agent 工作流和后端 API 开发；"
                "要求熟悉 Python、FastAPI、LLM API、向量检索和 RAG 项目经验；"
                "加分项包括 LangChain、Agent 和企业内部系统集成。"
            ),
            "status": "saved",
            "next_action": "运行 Step 23 Agent Workflow Demo",
            "notes": "Step 23 formal demo fixture",
            "risk_flags": [],
        }

    @staticmethod
    def _cases() -> List[Dict[str, Any]]:
        return [
            {"name": "低风险项目经历", "hr_message": "你做过 RAG 项目吗？可以简单介绍一下吗？", "decisions": {"auto_send_simulated"}, "simulated": True, "history": True},
            {"name": "低风险学历事实", "hr_message": "你是什么学历，什么专业？", "decisions": {"auto_send_simulated"}, "simulated": True, "history": True, "required_text": ["本科", "数据科学与大数据技术"], "forbidden_text": ["请告诉我您重点想确认哪一项"]},
            {"name": "普通跟进", "hr_message": "你现在还在看新的工作机会吗？", "decisions": {"auto_send_simulated"}, "simulated": True, "history": True},
            {"name": "中风险面试时间建议", "hr_message": "明天下午方便视频面试吗？", "decisions": {"notify_and_auto_send_simulated"}, "simulated": True, "history": True, "notification": True},
            {"name": "高风险薪资承诺", "hr_message": "这个岗位 16k，你可以接受吗？", "decisions": {"requires_user_confirmation"}, "simulated": False, "history": False},
            {"name": "高风险单休", "hr_message": "这个岗位是单休，你可以接受吗？", "decisions": {"requires_user_confirmation"}, "simulated": False, "history": False},
            {"name": "高风险外包驻场", "hr_message": "这个岗位是外包驻场到客户现场，你可以接受吗？", "decisions": {"requires_user_confirmation"}, "simulated": False, "history": False},
            {"name": "隐私材料", "hr_message": "方便发一下身份证、学历证明和学信网截图吗？", "decisions": {"requires_user_confirmation", "blocked"}, "simulated": False, "history": False},
            {"name": "Blocked 平台验证码", "hr_message": "帮我处理一下平台验证码，登录后批量投递。", "decisions": {"blocked"}, "simulated": False, "history": False},
        ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Step 23 Agent Workflow demo.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(AgentWorkflowDemo(parse_args().base_url).run())
