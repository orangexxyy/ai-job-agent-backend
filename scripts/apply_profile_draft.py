"""人工确认后将私有 CandidateProfileInput 草稿应用为正式 profile。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from app.schemas.profile_schema import CandidateProfileInput
from app.services.profile_service import get_candidate_profile, save_candidate_profile


DEFAULT_DRAFT = Path("docs/input/generated/candidate_profile_draft.json")
DEFAULT_BACKUP_DIR = Path("docs/input/generated/profile_backups")


def model_dump(model: Any) -> dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def profile_input_fields() -> set[str]:
    fields = getattr(CandidateProfileInput, "model_fields", None)
    if fields is None:
        fields = CandidateProfileInput.__fields__
    return set(fields)


def load_draft(path: Path) -> CandidateProfileInput:
    if not path.is_file():
        raise FileNotFoundError(f"draft does not exist: {path}")
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError("draft JSON root must be an object")
    extra_fields = sorted(set(raw) - profile_input_fields())
    if extra_fields:
        raise ValueError(f"draft contains unsupported fields: {', '.join(extra_fields)}")
    return CandidateProfileInput(**raw)


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


def create_backup(profile: Any, backup_dir: Path) -> Path | None:
    if profile is None:
        print("no existing candidate_profile found; backup skipped")
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"candidate_profile_backup_{stamp}.json"
    counter = 1
    while backup_path.exists():
        backup_path = backup_dir / f"candidate_profile_backup_{stamp}_{counter}.json"
        counter += 1
    backup_path.write_text(
        json.dumps(model_dump(profile), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"backup_path: {backup_path}")
    return backup_path


def verify_applied_profile(draft: CandidateProfileInput) -> bool:
    saved = get_candidate_profile()
    if saved is None:
        return False
    saved_input = CandidateProfileInput(**model_dump(saved))
    return model_dump(saved_input) == model_dump(draft)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or explicitly apply a reviewed candidate profile draft."
    )
    parser.add_argument("--draft", default=str(DEFAULT_DRAFT))
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--yes", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.yes and not args.apply:
        print("Error: --yes is only valid together with --apply", file=sys.stderr)
        return 2
    draft_path = Path(args.draft)
    backup_dir = Path(args.backup_dir)
    try:
        draft = load_draft(draft_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print_application_summary(draft_path, draft, will_write=args.apply)
    if not args.apply:
        print("mode: dry-run")
        print("applied: false")
        return 0

    if args.yes:
        print("HIGH CAUTION: --apply --yes bypasses interactive confirmation for testing.")
    else:
        confirmation = input("Type YES to back up and apply this draft: ").strip()
        if confirmation != "YES":
            print("Application cancelled; database was not changed.")
            print("applied: false")
            return 1

    current = get_candidate_profile()
    backup_path = create_backup(current, backup_dir)
    profile_id = save_candidate_profile(draft)
    verified = verify_applied_profile(draft)
    print(f"profile_id: {profile_id}")
    print(f"backup_created: {str(backup_path is not None).lower()}")
    print(f"profile_verified: {str(verified).lower()}")
    print(f"applied: {str(verified).lower()}")
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
