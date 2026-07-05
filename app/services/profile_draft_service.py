import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.database import init_database
from app.schemas.profile_draft_schema import ProfileDraftReviewData
from app.schemas.profile_schema import CandidateProfileInput
from app.services.profile_apply_history_service import create_profile_apply_history
from app.services.profile_service import get_candidate_profile, save_candidate_profile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DRAFT_PATH = PROJECT_ROOT / "docs/input/generated/candidate_profile_draft.json"
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "docs/input/generated/profile_backups"
PREVIEW_LENGTH = 500


@dataclass(frozen=True)
class ProfileDraftApplyOutcome:
    applied: bool
    profile_id: Optional[int]
    backup_path: Optional[Path]
    profile_verified: bool
    profile_apply_history_id: Optional[int]
    external_action_performed: bool = False

    @property
    def backup_created(self) -> bool:
        return self.backup_path is not None


def _model_dump(model: Any) -> dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _profile_input_fields() -> set[str]:
    fields = getattr(CandidateProfileInput, "model_fields", None)
    if fields is None:
        fields = CandidateProfileInput.__fields__
    return set(fields)


def _preview(text: str) -> str:
    compact = " ".join((text or "").split())
    if not compact:
        return ""
    preview_length = min(PREVIEW_LENGTH, max(1, len(compact) // 2))
    if preview_length >= len(compact):
        return "[content omitted]"
    return compact[:preview_length] + "..."


def load_profile_draft(draft_path: Optional[Path] = None) -> CandidateProfileInput:
    """读取并校验本地 candidate_profile draft。

    主要输入为可选本地路径，输出 CandidateProfileInput；只读文件，不写数据库、
    不调用 LLM，也不执行任何外部动作。
    """
    path = draft_path or DEFAULT_DRAFT_PATH
    if not path.is_file():
        raise FileNotFoundError(f"profile draft does not exist: {path}")
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError("profile draft JSON root must be an object")
    extra_fields = sorted(set(raw) - _profile_input_fields())
    if extra_fields:
        raise ValueError(
            "profile draft contains unsupported fields: " + ", ".join(extra_fields)
        )
    return CandidateProfileInput(**raw)


def get_profile_draft_review(
    draft_path: Optional[Path] = None,
) -> ProfileDraftReviewData:
    """生成不含完整简历正文的 profile draft 审核视图。

    主要输入为可选 draft 路径，输出结构化字段、文本预览和长度。
    只读本地文件，不写 SQLite/history，不调用 LLM，也不执行外部动作。
    """
    resolved_draft_path = draft_path or DEFAULT_DRAFT_PATH
    if not resolved_draft_path.is_file():
        return ProfileDraftReviewData(draft_exists=False)
    draft = load_profile_draft(resolved_draft_path)
    return ProfileDraftReviewData(
        draft_exists=True,
        target_roles=draft.target_roles,
        available_projects=draft.available_projects,
        truth_boundaries=draft.truth_boundaries,
        expected_salary_min=draft.expected_salary_min,
        expected_salary_max=draft.expected_salary_max,
        minimum_salary=draft.minimum_salary,
        salary_note=draft.salary_note,
        availability_note=draft.availability_note,
        preferred_cities=draft.preferred_cities,
        acceptable_cities=draft.acceptable_cities,
        relocation_policy=draft.relocation_policy,
        outsourcing_policy=draft.outsourcing_policy,
        onsite_policy=draft.onsite_policy,
        remote_policy=draft.remote_policy,
        overtime_policy=draft.overtime_policy,
        business_trip_policy=draft.business_trip_policy,
        resume_text_preview=_preview(draft.resume_text),
        project_context_preview=_preview(draft.project_context),
        resume_text_length=len(draft.resume_text),
        project_context_length=len(draft.project_context),
    )


def _create_backup(profile: Any, backup_dir: Path) -> Optional[Path]:
    if profile is None:
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"candidate_profile_backup_{stamp}.json"
    counter = 1
    while backup_path.exists():
        backup_path = backup_dir / f"candidate_profile_backup_{stamp}_{counter}.json"
        counter += 1
    backup_path.write_text(
        json.dumps(_model_dump(profile), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return backup_path


def _verify_profile(draft: CandidateProfileInput) -> bool:
    saved = get_candidate_profile()
    if saved is None:
        return False
    saved_input = CandidateProfileInput(**_model_dump(saved))
    return _model_dump(saved_input) == _model_dump(draft)


def apply_profile_draft(
    *,
    confirmation_text: str,
    draft_path: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
) -> ProfileDraftApplyOutcome:
    """在精确确认后备份、应用并验证本地 profile draft。

    主要输入为 confirmation_text 及可选本地路径，输出 apply、backup、verify 和
    history 结果。会写 SQLite 和私有 backup；仅在验证成功后写轻量 history，
    不保存完整正文、不调用 LLM、不发送消息、不投递，也不确认面试。
    """
    if confirmation_text != "YES":
        raise ValueError("confirmation_text must equal YES")
    resolved_draft_path = draft_path or DEFAULT_DRAFT_PATH
    resolved_backup_dir = backup_dir or DEFAULT_BACKUP_DIR
    draft = load_profile_draft(resolved_draft_path)

    init_database()
    current = get_candidate_profile()
    backup_path = _create_backup(current, resolved_backup_dir)
    profile_id = save_candidate_profile(draft)
    verified = _verify_profile(draft)
    history_id = None
    if verified:
        history = create_profile_apply_history(
            draft_path=str(resolved_draft_path),
            backup_path=str(backup_path) if backup_path is not None else None,
            profile_verified=True,
            user_confirmed=True,
            external_action_performed=False,
            detail_json={
                "target_roles_count": len(draft.target_roles),
                "available_projects_count": len(draft.available_projects),
                "truth_boundaries_count": len(draft.truth_boundaries),
                "resume_text_length": len(draft.resume_text),
                "project_context_length": len(draft.project_context),
            },
        )
        history_id = history.id

    return ProfileDraftApplyOutcome(
        applied=verified,
        profile_id=profile_id,
        backup_path=backup_path,
        profile_verified=verified,
        profile_apply_history_id=history_id,
        external_action_performed=False,
    )
