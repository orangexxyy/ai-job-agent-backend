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
        self._run_step("analyze job match", self._test_job_match)
        self._run_step(
            "verify application updated by job match",
            self._test_application_after_job_match,
        )
        self._run_step(
            "missing application_id job match",
            self._test_missing_application_job_match,
        )
        self._run_step("patch application", self._test_patch_application)
        self._run_step("reject invalid application status", self._test_invalid_status)
        self._run_step("analyze HR message", self._test_hr_analyze)
        self._run_step("old HR reply", self._test_old_hr_reply)
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
        application_id = response.json().get("data", {}).get("id")
        if not isinstance(application_id, int):
            return False
        self.application_id = application_id
        return True

    def _test_read_application(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request("GET", f"/applications/{self.application_id}")
        return self._success(response) and response.json().get("data", {}).get("id") == self.application_id

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

    def _test_patch_application(self) -> bool:
        if self.application_id is None:
            return False
        response = self._request(
            "PATCH",
            f"/applications/{self.application_id}",
            json_body={
                "status": "hr_contacted",
                "last_hr_message": "方便明天下午视频面试吗？",
                "next_action": "确认面试时间",
            },
        )
        return self._success(response) and response.json().get("data", {}).get("status") == "hr_contacted"

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
            "resume_text": "",
            "project_context": "",
        }

    def _test_application(self) -> Dict[str, Any]:
        return {
            "company_name": f"HARNESS Demo Company {self.timestamp}",
            "job_title": "AI Application Developer",
            "job_source": "Manual",
            "job_url": "https://example.com/harness",
            "jd_text": (
                "Build AI application workflows with FastAPI, RAG, Agent, "
                "and human approval."
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
