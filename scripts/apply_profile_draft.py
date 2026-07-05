"""人工确认后将私有 CandidateProfileInput 草稿应用为正式 profile。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from app.schemas.profile_schema import CandidateProfileInput
from app.services.profile_draft_service import (
    apply_profile_draft,
    load_profile_draft,
)


DEFAULT_DRAFT = Path("docs/input/generated/candidate_profile_draft.json")
DEFAULT_BACKUP_DIR = Path("docs/input/generated/profile_backups")


def preview(text: str, limit: int = 500) -> str:
    compact = " ".join((text or "").split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def console_safe(value: Any) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return str(value).encode(encoding, errors="replace").decode(encoding)


def print_application_summary(
    draft_path: Path, draft: CandidateProfileInput, *, will_write: bool
) -> None:
    print(f"draft_path: {draft_path}")
    print("candidate_profile_input_valid: true")
    print(f"target_roles: {console_safe(draft.target_roles)}")
    print(f"available_projects: {console_safe(draft.available_projects)}")
    print(f"truth_boundaries_count: {len(draft.truth_boundaries)}")
    print(f"truth_boundaries_preview: {console_safe(draft.truth_boundaries[:3])}")
    print(f"resume_text_preview_500: {console_safe(preview(draft.resume_text))}")
    print(f"project_context_preview_500: {console_safe(preview(draft.project_context))}")
    print(f"expected_salary_min: {draft.expected_salary_min}")
    print(f"expected_salary_max: {draft.expected_salary_max}")
    print(f"minimum_salary: {draft.minimum_salary}")
    print(f"salary_note: {console_safe(draft.salary_note)}")
    print(f"outsourcing_policy: {console_safe(draft.outsourcing_policy)}")
    print(f"onsite_policy: {console_safe(draft.onsite_policy)}")
    print(f"overtime_policy: {console_safe(draft.overtime_policy)}")
    print(f"will_write_database: {str(will_write).lower()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or explicitly apply a reviewed candidate profile draft."
    )
    parser.add_argument("--draft", default=str(DEFAULT_DRAFT))
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR))
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.apply and not sys.stdin.isatty():
        print(
            "Error: --apply requires an interactive terminal and manual YES confirmation.",
            file=sys.stderr,
        )
        print("applied: false")
        return 2
    draft_path = Path(args.draft)
    backup_dir = Path(args.backup_dir)
    try:
        draft = load_profile_draft(draft_path)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print_application_summary(draft_path, draft, will_write=args.apply)
    if not args.apply:
        print("mode: dry-run")
        print("applied: false")
        return 0

    confirmation = input("Type YES to back up and apply this draft: ").strip()
    if confirmation != "YES":
        print("Application cancelled; database was not changed.")
        print("applied: false")
        return 1

    try:
        outcome = apply_profile_draft(
            confirmation_text="YES",
            draft_path=draft_path,
            backup_dir=backup_dir,
        )
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if outcome.backup_path is None:
        print("no existing candidate_profile found; backup skipped")
    else:
        print(f"backup_path: {outcome.backup_path}")
    print(f"profile_id: {outcome.profile_id}")
    print(f"backup_created: {str(outcome.backup_created).lower()}")
    print(f"profile_verified: {str(outcome.profile_verified).lower()}")
    print(f"profile_apply_history_id: {outcome.profile_apply_history_id}")
    print(f"applied: {str(outcome.applied).lower()}")
    return 0 if outcome.applied else 1


if __name__ == "__main__":
    raise SystemExit(main())
