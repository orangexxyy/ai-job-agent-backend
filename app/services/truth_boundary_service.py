from typing import Dict, List

from app.schemas.profile_schema import CandidateProfile


FORBIDDEN_CLAIMS = [
    "完整生产级智能招聘系统",
    "生产级智能招聘系统",
    "完整智能招聘系统",
    "复杂 Multi-Agent 平台",
    "完整 Multi-Agent",
    "LoRA 微调",
    "QLoRA 微调",
    "模型训练",
    "全链路本地化部署",
    "自动招聘决策",
    "自动录用",
    "代替 HR 决策",
]


DEFAULT_CANNOT_CLAIM = [
    "不能说做过完整生产级智能招聘系统",
    "不能说做过 LoRA / QLoRA 微调",
    "不能说做过完整复杂 Multi-Agent 平台",
    "不能说 AI 可以代替 HR 做最终招聘决策",
]


def get_cannot_claim(profile: CandidateProfile) -> List[str]:
    return profile.truth_boundaries or DEFAULT_CANNOT_CLAIM


def check_truth_boundary(
    reply_draft: str,
    profile: CandidateProfile,
) -> Dict[str, object]:
    """检查回复草稿是否触碰候选人 truth boundary。

    主要输入：reply_draft 文本和 CandidateProfile 中的 truth_boundaries。
    主要输出：safe_to_send、risk_points、cannot_claim 和 suggested_revision。
    副作用：无数据库读写；仅做内存校验，不调用 LLM，不自动发送 HR 消息。
    """
    risk_points = [
        claim for claim in FORBIDDEN_CLAIMS if claim.lower() in reply_draft.lower()
    ]
    safe_to_send = not risk_points
    suggested_revision = ""
    if risk_points:
        suggested_revision = (
            "建议改为只描述已经提供在 candidate_profile / resume_text / "
            "project_context 中的真实项目经历，并把未完成能力表述为后续可扩展方向。"
        )

    return {
        "safe_to_send": safe_to_send,
        "risk_points": risk_points,
        "cannot_claim": get_cannot_claim(profile),
        "suggested_revision": suggested_revision,
    }
