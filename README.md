# AI Job Agent

AI Job Agent 是一个面向 AI应用开发 / 大模型应用开发求职场景的 Human-in-the-loop 后端 Demo。项目用于管理求职档案、投递记录、HR 消息、岗位匹配和回复草稿，当前主要服务于学习、求职流程管理和中文面试展示。

本项目不是自动海投工具，不自动发送 HR 消息，不连接真实招聘平台，也不做招聘决策。所有涉及投递、沟通、面试时间确认、薪资承诺和外部平台操作的动作，都必须由用户最终确认。

## 当前阶段

当前已完成到 Step 9：

- Step 1：`candidate_profile` 求职档案保存与读取
- Step 2：`/hr/analyze` 规则版 HR Intent Analyzer
- Step 3：`/hr/reply` 基于 `candidate_profile` 的 HR 回复草稿
- Step 4：`/applications` 投递记录管理
- Step 5：`/hr/reply` 支持可选 `application_id` 上下文
- Step 6：API smoke test harness
- Step 7：`/job_match` 规则版岗位匹配评分
- Step 8：`/hr/reply` 基于 `resume_text` / `project_context` 增强项目类回复草稿
- Step 9：Agent Workflow Design / 面试展示文档收口

当前所有核心能力仍是规则版 baseline，不调用 DeepSeek / LLM，不实现 RAG、Embedding、Playwright 或前端。

## 技术栈

- Python
- FastAPI
- Pydantic
- SQLite
- python-dotenv
- requests
- DeepSeek-compatible config placeholder

项目中保留 DeepSeek-compatible 配置占位，用于后续扩展。当前接口不会真实调用 DeepSeek / LLM。

## 启动方式

安装依赖：

```bash
pip install -r requirements.txt
```

建议使用 `8001` 端口，避免和其他 RAG 项目的 `8000` 端口冲突：

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

访问 Swagger：

```text
http://127.0.0.1:8001/docs
```

## 接口说明

当前可用接口：

- `GET /health`：健康检查
- `POST /profile`：保存或更新 `candidate_profile`
- `GET /profile`：读取 `candidate_profile`
- `POST /hr/analyze`：分析 HR 消息 intent
- `POST /hr/reply`：生成 HR 回复草稿，可选绑定 `application_id`
- `POST /applications`：创建投递记录
- `GET /applications`：查询投递记录列表
- `GET /applications/{application_id}`：读取单条投递记录
- `PATCH /applications/{application_id}`：更新投递记录
- `POST /job_match`：基于规则分析某条 application 的岗位匹配度

## 核心模块

### applications

`applications` 模块用于手动记录和更新求职投递过程中的关键信息，包括公司、岗位、JD、来源、状态、HR 最新消息和下一步动作。

当前只支持手动记录和更新，不做自动投递，不连接真实招聘平台，不抓取岗位，也不会自动联系 HR。

### job_match

`POST /job_match` 是规则版岗位匹配评分接口，用于从求职者侧辅助判断某条 application 是否值得优先跟进。它不是招聘决策系统，不代表招聘方是否录用候选人。

评分维度包括：

- `role_fit`
- `tech_stack_fit`
- `project_relevance`
- `preference_fit`

当 `update_application=true` 时，只会安全回写：

- `applications.match_score`
- `applications.next_action`
- `applications.risk_flags`

它不会修改 `status`，不会修改 `last_hr_message`，不会自动投递，不会自动发送 HR 消息，也不会调用 DeepSeek / LLM。

### `/hr/reply` 与 `application_id`

旧版请求不传 `application_id` 仍然可用。传入 `application_id` 时，系统会读取对应投递记录，优先使用 application 的 `company_name` 和 `job_title` 作为上下文，并返回 `application_context`。

生成回复草稿后，系统只会安全更新：

- `last_hr_message`
- `next_action`

不会自动修改 `status`，不会自动确认面试时间，也不会发送消息。

### `/hr/reply` 与 profile context 增强

当 HR 消息命中 `project_experience`、`technical_question` 或 `business_proposal` 时，`/hr/reply` 会尝试从 `candidate_profile.resume_text`、`candidate_profile.project_context` 和 `candidate_profile.available_projects` 中选择少量相关片段，用来生成更具体但保守的回复草稿。

这不是 RAG，不做 Embedding，不做向量检索，也不调用 DeepSeek / LLM。当前只是本地关键词匹配和短片段选择，最多返回 3 条 `selected_context_snippets`。

返回数据包含：

- `context_used`
- `selected_context_snippets`
- `context_reply_mode`

如果没有可用上下文，接口会返回保守 fallback，提示补充 `resume_text / project_context`，不会编造项目经历。

## API Smoke Test Harness

`scripts/api_smoke_test.py` 是本地接口验收脚本，用于快速检查当前主链路 API 是否可用。它是开发验收工具，不是业务功能。

运行方式：

```bash
python scripts/api_smoke_test.py
```

也可以指定地址：

```bash
python scripts/api_smoke_test.py --base-url http://127.0.0.1:8001
```

脚本会临时写入测试 `candidate_profile`，并在结束时尽量恢复原 profile。脚本会创建一条 `HARNESS Demo Company <timestamp>` application 测试记录，并在收尾阶段尽量标记为 `closed`。

## Step 9 文档入口

- [Agent Workflow Design](docs/agent_workflow_design.md)
- [Interview Talking Points](docs/interview_talking_points.md)
- [Demo Script](docs/demo_script.md)

Step 9 只做文档收口，没有修改业务代码，也没有实现 LangGraph / RAG / Playwright。

## 代码结构与阅读指南

- [Project Structure](docs/project_structure.md)
- [Code Reading Guide](docs/code_reading_guide.md)

这两份文档用于说明 route / schema / service / database 的分层职责、典型调用链，以及未来 workflow / LangGraph 为什么应该优先复用 service 函数，而不是在后端内部再调用自己的 HTTP API。

## 明确边界

当前未实现：

- 自动投递
- 自动发送 HR 消息
- 真实招聘平台接入
- Playwright
- RAG
- Embedding / 向量检索
- 前端
- 真实 LLM 调用
- 生产级权限系统
- 完整多轮聊天
- conversations / messages 持久化
- 招聘决策系统

项目不会编造候选人的工作经历、教育经历、地址、工作年限、薪资、项目历史或其他履历信息。任何涉及真实外部沟通和求职承诺的内容，都必须保持 Human-in-the-loop。

## Roadmap

- Step 10：最小 LangGraph Workflow Demo
- Step 11：岗位来源导入 / 手动 JD 导入
- Step 12：Playwright dry-run 岗位采集
- Step 13：用户确认后的半自动投递流程
- Step 14：RAG 化项目经历资料，optional / later
## Step 10: rule-based workflow_preview

Step 10 新增 `POST /agent/workflow_preview`，用于把已有 service 能力串成一个只读预览流程：

- 读取 `candidate_profile`
- 读取指定 `application`
- 复用 `analyze_job_match(update_application=False)`
- 可选分析 HR message
- 可选复用 `generate_hr_reply(update_application=False)`
- 返回 `workflow_steps`、`state_summary`、`job_match`、`hr_intent`、`hr_reply` 和 Human-in-the-loop 审批状态

这个接口是规则版 workflow preview，不是 LangGraph 实现。它不调用 DeepSeek / LLM，不实现 RAG，不使用 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试时间，也不写入 application。

接口：

- `POST /agent/workflow_preview`

示例请求：

```json
{
  "application_id": 1,
  "hr_message": "方便介绍一下你做过的 RAG 或 Agent 项目吗？"
}
```
## Step 11: minimal LangGraph Workflow Demo

Step 11 新增 `POST /agent/langgraph_workflow_preview`，用于用 LangGraph `StateGraph` 表达 Step 10 的同一条 workflow preview。

它和 `POST /agent/workflow_preview` 并行保留，便于面试展示：

- `POST /agent/workflow_preview`：普通 Python rule-based workflow baseline
- `POST /agent/langgraph_workflow_preview`：LangGraph StateGraph workflow preview

LangGraph 版本会返回：

- `workflow_mode = "langgraph_preview"`
- `workflow_engine = "langgraph_stategraph"`
- `workflow_steps`
- `state_summary`
- `job_match`
- `hr_intent`
- `hr_reply`
- `approval_required = true`
- `approved_by_user = false`

当前只是最小 LangGraph demo，不调用 DeepSeek / LLM，不实现 RAG，不使用 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试时间，也不写入 application。

示例请求：

```json
{
  "application_id": 1,
  "hr_message": "方便介绍一下你做过的 RAG 或 Agent 项目吗？"
}
```
## Step 11.5: LangGraph observability

`POST /agent/langgraph_workflow_preview` 已增强可观测性，返回中额外暴露：

- `graph_structure`：展示 LangGraph nodes、普通 edges、conditional edges
- `state_snapshots`：展示每个关键 node 执行后的轻量 state 变化
- `edge_trace`：展示本次 workflow 实际走过的边和条件判断结果

这些字段用于学习 LangGraph 编排、Swagger 调试和面试展示。当前仍然不调用 DeepSeek / LLM，不实现 RAG，不使用 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试时间，也不写入 application。
