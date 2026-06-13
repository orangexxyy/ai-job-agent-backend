import json
from typing import Any, Dict, Optional

from fastapi.encoders import jsonable_encoder

from app.config import settings
from app.services.application_review_service import review_application
from app.services.llm_service import llm_service


def enhance_application_review_with_llm(
    application_id: int,
    hr_message: Optional[str] = None,
    include_raw_prompt: bool = False,
) -> Dict[str, Any]:
    """基于规则版 application review 生成只读 LLM 增强分析。

    主要输入：application_id、可选 HR message、是否返回 raw prompt。
    主要输出：规则 review、LLM 增强结果、LLM 调用状态和安全 debug 字段。
    副作用：可能调用外部 DeepSeek-compatible LLM；不写数据库，不改 application，不发送 HR 消息，不自动投递。
    """
    rule_review = jsonable_encoder(review_application(
        application_id=application_id,
        hr_message=hr_message,
        update_application=False,
    ))
    messages = _build_messages(rule_review)
    llm_result = llm_service.chat_json(messages)
    llm_enhanced_review = llm_result.get("parsed_json")
    llm_error = None if llm_result.get("success") else llm_result.get("message")
    data = {
        "application_id": rule_review["application_id"],
        "company_name": rule_review["company_name"],
        "job_title": rule_review["job_title"],
        "rule_review": rule_review,
        "llm_enhanced_review": llm_enhanced_review,
        "llm_used": llm_result.get("llm_used", False),
        "llm_error": llm_error,
        "human_review_required": True,
        "debug": {
            "review_engine": "llm_enhanced_application_review",
            "base_review_engine": "rule_based_application_review",
            "llm_provider": llm_result.get("provider", settings.llm_provider),
            "llm_model": llm_result.get("model", settings.deepseek_model),
            "rag_used": False,
            "playwright_used": False,
            "auto_apply": False,
            "auto_send_message": False,
            "auto_update_status": False,
            "database_write_intended": False,
            "llm_call_success": llm_result.get("success", False),
            "llm_raw_text": llm_result.get("raw_text"),
        },
    }
    if include_raw_prompt:
        data["debug"]["raw_prompt_messages"] = messages
    return data


def _build_messages(rule_review: Dict[str, Any]) -> list[Dict[str, str]]:
    system_prompt = (
        "你是 AI Job Agent 的只读分析助手。你只能基于用户提供的规则版 review 结果做解释增强，"
        "不能从零判断岗位，不能接管求职流程。必须严格区分：原始事实、规则推断、LLM 建议。"
        "不得编造 JD、HR 消息、候选人经历、薪资、面试时间、公司信息。"
        "不能建议自动发送消息，不能代替用户确认面试时间，不能承诺薪资、到岗时间、地点或工作方式。"
        "当 confidence=low 时，必须保守表达信息不足、需要确认。"
        "当规则判断和原始信息冲突时，必须指出冲突并建议用户确认。"
        "输出必须是 JSON，不要输出 Markdown。"
    )
    user_payload = {
        "task": "基于规则版 application_review 结果生成只读增强分析",
        "rule_result_is_baseline_not_final_fact": True,
        "human_review_required": True,
        "must_not_auto_send_message": True,
        "must_not_auto_apply": True,
        "must_not_auto_update_status": True,
        "expected_json_schema": {
            "enhanced_summary": "中文总结该岗位当前是否值得跟进",
            "rule_result_check": "说明规则结果是否合理，以及是否需要保守处理",
            "possible_conflicts": ["可能的规则误判或信息冲突"],
            "missing_questions_to_confirm": ["建议向 HR 或自己确认的问题"],
            "conservative_next_step": "保守下一步建议",
            "risk_explanation": "自然语言解释风险",
            "confidence_explanation": "解释 confidence 的含义和当前级别原因",
            "user_decision_required": True,
        },
        "rule_review": rule_review,
    }
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False),
        },
    ]
