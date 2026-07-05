"""使用临时 draft 与 SQLite 验证 Profile Draft Review API。"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _dump(model: object) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai_job_agent_profile_review_") as tmp:
        root = Path(tmp)
        os.environ["DATABASE_PATH"] = str(root / "test.db")
        os.environ["PYTHON_DOTENV_DISABLED"] = "1"

        from fastapi.testclient import TestClient

        from app.database import get_connection
        from app.main import app
        from app.schemas.profile_schema import CandidateProfileInput
        from app.services import profile_draft_service
        from app.services.profile_apply_history_service import (
            list_profile_apply_history,
        )
        from app.services.profile_service import (
            get_candidate_profile,
            save_candidate_profile,
        )

        draft_path = root / "candidate_profile_draft.json"
        backup_dir = root / "profile_backups"
        profile_draft_service.DEFAULT_DRAFT_PATH = draft_path
        profile_draft_service.DEFAULT_BACKUP_DIR = backup_dir

        resume_text = "Synthetic resume fact. " + ("R" * 700)
        project_context = "Synthetic project fact. " + ("P" * 700)
        draft = CandidateProfileInput(
            expected_salary_min=None,
            expected_salary_max=None,
            minimum_salary=None,
            salary_note="薪资需要用户确认。",
            availability_note="面试和到岗时间需要用户确认。",
            outsourcing_policy="外包与驻场需要用户确认。",
            onsite_policy="现场办公安排需要用户确认。",
            overtime_policy="加班安排需要用户确认。",
            business_trip_policy="出差安排需要用户确认。",
            target_roles=["AI应用开发工程师"],
            available_projects=["AI Job Agent"],
            truth_boundaries=["不自动投递", "不发送真实 HR 消息"],
            resume_text=resume_text,
            project_context=project_context,
        )
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            old_profile = CandidateProfileInput(resume_text="old formal profile")
            save_candidate_profile(old_profile)
            before_profile = get_candidate_profile()

            missing = client.get("/profile_draft/review")
            missing_data = missing.json().get("data") or {}
            if (
                missing.status_code != 200
                or missing_data.get("draft_exists") is not False
                or list_profile_apply_history()
                or _dump(get_candidate_profile()) != _dump(before_profile)
            ):
                print("[FAIL] missing draft state is not safe or explainable")
                return 1

            draft_path.write_text(
                json.dumps(_dump(draft), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            path_query = client.get(
                "/profile_draft/review", params={"draft_path": str(draft_path)}
            )
            if path_query.status_code != 422:
                print("[FAIL] review accepted a client-provided draft path")
                return 1

            review_response = client.get("/profile_draft/review")
            if review_response.status_code != 200:
                print(f"[FAIL] GET review status={review_response.status_code}")
                return 1
            review_payload = review_response.json()
            review_data = review_payload.get("data") or {}
            response_text = review_response.text
            if (
                review_payload.get("success") is not True
                or review_data.get("draft_exists") is not True
                or "resume_text" in review_data
                or "project_context" in review_data
                or resume_text in response_text
                or project_context in response_text
                or review_data.get("resume_text_length") != len(resume_text)
                or review_data.get("project_context_length") != len(project_context)
                or len(review_data.get("resume_text_preview") or "") > 503
                or len(review_data.get("project_context_preview") or "") > 503
            ):
                print("[FAIL] GET review leaked full text or returned invalid summary")
                return 1
            if list_profile_apply_history() or _dump(get_candidate_profile()) != _dump(before_profile):
                print("[FAIL] GET review changed database state")
                return 1

            short_draft = CandidateProfileInput(
                resume_text="short resume",
                project_context="short project",
            )
            draft_path.write_text(
                json.dumps(_dump(short_draft), ensure_ascii=False), encoding="utf-8"
            )
            short_review = client.get("/profile_draft/review")
            if (
                short_review.status_code != 200
                or short_draft.resume_text in short_review.text
                or short_draft.project_context in short_review.text
            ):
                print("[FAIL] short review returned complete text")
                return 1
            draft_path.write_text(
                json.dumps(_dump(draft), ensure_ascii=False, indent=2), encoding="utf-8"
            )

            rejected = client.post(
                "/profile_draft/apply", json={"confirmation_text": "NO"}
            )
            if rejected.status_code != 422 or list_profile_apply_history():
                print("[FAIL] invalid confirmation was not safely rejected")
                return 1
            if _dump(get_candidate_profile()) != _dump(before_profile):
                print("[FAIL] invalid confirmation changed profile")
                return 1

            injected = client.post(
                "/profile_draft/apply",
                json={
                    "confirmation_text": "YES",
                    "draft_path": str(draft_path),
                },
            )
            if injected.status_code != 422 or list_profile_apply_history():
                print("[FAIL] apply accepted a client-provided draft path")
                return 1
            if _dump(get_candidate_profile()) != _dump(before_profile):
                print("[FAIL] rejected path injection changed profile")
                return 1

            extra_profile = client.post(
                "/profile_draft/apply",
                json={"confirmation_text": "YES", "resume_text": "must be rejected"},
            )
            if extra_profile.status_code != 422 or list_profile_apply_history():
                print("[FAIL] apply accepted client-provided profile fields")
                return 1

            applied = client.post(
                "/profile_draft/apply", json={"confirmation_text": "YES"}
            )
            if applied.status_code != 200:
                print(f"[FAIL] confirmed apply status={applied.status_code}")
                return 1
            applied_payload = applied.json()
            applied_data = applied_payload.get("data") or {}
            if (
                applied_payload.get("success") is not True
                or applied_data.get("applied") is not True
                or applied_data.get("profile_verified") is not True
                or applied_data.get("backup_created") is not True
                or not applied_data.get("profile_apply_history_id")
                or applied_data.get("external_action_performed") is not False
                or resume_text in applied.text
                or project_context in applied.text
            ):
                print("[FAIL] confirmed apply response is invalid")
                return 1

            saved = get_candidate_profile()
            history = list_profile_apply_history()
            if saved is None or _dump(CandidateProfileInput(**_dump(saved))) != _dump(draft):
                print("[FAIL] confirmed apply did not save the draft")
                return 1
            if len(history) != 1 or history[0].external_action_performed:
                print("[FAIL] confirmed apply did not write exactly one safe history row")
                return 1

            connection = get_connection()
            try:
                raw_detail = connection.execute(
                    "SELECT detail_json FROM profile_apply_history WHERE id = ?",
                    (history[0].id,),
                ).fetchone()["detail_json"]
            finally:
                connection.close()
            if resume_text in raw_detail or project_context in raw_detail:
                print("[FAIL] history contains full resume or project context")
                return 1

        with TestClient(app, client=("203.0.113.10", 50000)) as remote_client:
            remote_review = remote_client.get("/profile_draft/review")
            remote_apply = remote_client.post(
                "/profile_draft/apply", json={"confirmation_text": "YES"}
            )
            if remote_review.status_code != 403 or remote_apply.status_code != 403:
                print("[FAIL] non-local client was not blocked")
                return 1

        print("[PASS] missing draft returned draft_exists=false without writes")
        print("[PASS] client-provided paths and non-local clients were rejected")
        print("[PASS] GET review returned previews without database writes")
        print("[PASS] invalid confirmation was rejected without history")
        print("[PASS] client-provided profile fields were rejected")
        print("[PASS] confirmed apply saved profile and wrote one safe history row")
        print("[PASS] API responses and history contain no complete profile text")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
