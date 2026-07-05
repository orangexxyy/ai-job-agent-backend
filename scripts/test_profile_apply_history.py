"""使用临时 SQLite 验证 profile apply history 的最小安全边界。"""

from __future__ import annotations

import builtins
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _run_main(
    main: Callable[[], int],
    argv: list[str],
    confirmation: str | None = None,
) -> int:
    original_argv = sys.argv
    original_input = builtins.input
    original_stdin = sys.stdin

    class InteractiveStdin:
        @staticmethod
        def isatty() -> bool:
            return True

    try:
        sys.argv = argv
        if confirmation is not None:
            builtins.input = lambda _prompt="": confirmation
            sys.stdin = InteractiveStdin()  # type: ignore[assignment]
        return main()
    finally:
        sys.argv = original_argv
        builtins.input = original_input
        sys.stdin = original_stdin


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai_job_agent_profile_history_") as tmp:
        root = Path(tmp)
        os.environ["DATABASE_PATH"] = str(root / "test.db")
        os.environ["PYTHON_DOTENV_DISABLED"] = "1"

        from app.database import get_connection, init_database
        from app.schemas.profile_schema import CandidateProfileInput
        from app.services.profile_apply_history_service import (
            create_profile_apply_history,
            list_profile_apply_history,
        )
        from app.services.profile_service import save_candidate_profile
        from scripts.apply_profile_draft import main as apply_main

        init_database()
        save_candidate_profile(CandidateProfileInput(resume_text="old profile"))

        draft = CandidateProfileInput(
            target_roles=["AI应用开发工程师"],
            available_projects=["AI Job Agent"],
            truth_boundaries=["不自动投递", "不自动发送 HR 消息"],
            resume_text="synthetic resume body",
            project_context="synthetic project context",
        )
        draft_path = root / "candidate_profile_draft.json"
        backup_dir = root / "backups"
        payload = draft.model_dump() if hasattr(draft, "model_dump") else draft.dict()
        draft_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        base_args = [
            "apply_profile_draft.py",
            "--draft",
            str(draft_path),
            "--backup-dir",
            str(backup_dir),
        ]

        if _run_main(apply_main, base_args) != 0 or list_profile_apply_history():
            print("[FAIL] dry-run wrote history")
            return 1
        if _run_main(apply_main, base_args + ["--apply"], "NO") != 1:
            print("[FAIL] cancelled apply returned unexpected status")
            return 1
        if list_profile_apply_history():
            print("[FAIL] cancelled apply wrote history")
            return 1
        if _run_main(apply_main, base_args + ["--apply"], "YES") != 0:
            print("[FAIL] confirmed apply failed")
            return 1

        history = list_profile_apply_history()
        if len(history) != 1:
            print(f"[FAIL] expected one history row, got {len(history)}")
            return 1
        item = history[0]
        expected_detail = {
            "target_roles_count": 1,
            "available_projects_count": 1,
            "truth_boundaries_count": 2,
            "resume_text_length": len(draft.resume_text),
            "project_context_length": len(draft.project_context),
        }
        if (
            not item.user_confirmed
            or not item.profile_verified
            or item.external_action_performed
            or item.detail_json != expected_detail
            or not item.backup_path
        ):
            print("[FAIL] confirmed history fields are invalid")
            return 1

        connection = get_connection()
        try:
            raw_detail = connection.execute(
                "SELECT detail_json FROM profile_apply_history WHERE id = ?", (item.id,)
            ).fetchone()["detail_json"]
        finally:
            connection.close()
        if draft.resume_text in raw_detail or draft.project_context in raw_detail:
            print("[FAIL] history contains full resume or project context")
            return 1

        try:
            create_profile_apply_history(
                draft_path="draft.json",
                backup_path=None,
                profile_verified=True,
                user_confirmed=True,
                external_action_performed=True,
                detail_json=expected_detail,
            )
        except ValueError:
            pass
        else:
            print("[FAIL] external action history was accepted")
            return 1
        try:
            create_profile_apply_history(
                draft_path="draft.json",
                backup_path=None,
                profile_verified=True,
                user_confirmed=True,
                external_action_performed=False,
                detail_json={**expected_detail, "resume_text": "forbidden body"},
            )
        except ValueError:
            pass
        else:
            print("[FAIL] non-whitelisted detail was accepted")
            return 1
        if len(list_profile_apply_history()) != 1:
            print("[FAIL] rejected history changed the database")
            return 1

        print("[PASS] dry-run and cancellation wrote no history")
        print("[PASS] confirmed apply wrote one lightweight history row")
        print("[PASS] external_action_performed=true was rejected")
        print("[PASS] full-text detail fields were rejected")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
