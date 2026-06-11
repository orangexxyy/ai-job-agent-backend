# AI Job Agent

AI Job Agent 是一个面向 AI应用开发 / 大模型应用开发求职场景的 Human-in-the-loop 后端 Demo。项目当前主要用于求职流程管理、HR 沟通草稿辅助和中文面试展示，帮助候选人把求职档案、投递记录、HR 消息和后续动作管理得更清楚。

本项目不是自动海投工具，不自动发送 HR 消息，不连接真实招聘平台，也不做自动招聘决策。所有涉及投递、沟通、面试时间确认、薪资谈判和外部平台操作的动作，都必须由用户最终确认。

## 当前阶段

当前已完成到 Step 6：

- Step 1：`candidate_profile` 求职档案保存与读取
- Step 2：`/hr/analyze` HR 意图分析
- Step 3：`/hr/reply` HR 回复草稿生成
- Step 4：`/applications` 投递记录管理
- Step 5：`/hr/reply` 支持可选 `application_id` 上下文
- Step 6：API smoke test harness

现阶段的 `/hr/analyze` 使用本地规则进行意图识别；`/hr/reply` 基于规则、`candidate_profile` 和可选的 `applications` 投递记录生成保守回复草稿。当前接口不真实调用 DeepSeek / LLM，也不消耗真实 API token。

当 `/hr/reply` 请求传入 `application_id` 时，系统会读取对应投递记录，优先使用 application 中的 `company_name` 和 `job_title` 作为公司和岗位上下文，并在返回结果中包含 `application_context`。生成草稿后，系统只会安全更新该投递记录的 `last_hr_message` 和 `next_action`，不会自动发送消息、不会自动确认面试、不会自动修改投递状态。

当前不是完整多轮聊天系统，没有 conversations 表或 messages 表。

## 技术栈

- Python
- FastAPI
- Pydantic
- SQLite
- python-dotenv
- requests
- DeepSeek-compatible config placeholder

项目中保留了 DeepSeek-compatible 配置占位，用于后续接入真实 LLM 服务时扩展。当前阶段不会真实调用 DeepSeek / LLM。

## 启动方式

安装依赖：

```bash
pip install -r requirements.txt
```

如需本地配置，可参考 `.env.example` 创建 `.env`。真实 API key 只能放在 `.env`，不要提交到 Git。

建议使用 `8001` 端口，避免和 RAG 项目的 `8000` 端口冲突：

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

启动后访问：

```text
http://127.0.0.1:8001/docs
```

## 接口说明

当前可用接口：

- `GET /health`：健康检查
- `POST /profile`：保存或更新 `candidate_profile`
- `GET /profile`：读取 `candidate_profile`
- `POST /hr/analyze`：分析 HR 消息意图
- `POST /hr/reply`：生成 HR 回复草稿，可选绑定 `application_id`
- `POST /applications`：创建投递记录
- `GET /applications`：查询投递记录列表
- `GET /applications/{application_id}`：读取单条投递记录
- `PATCH /applications/{application_id}`：更新投递记录

## applications 模块说明

`applications` 模块用于手动记录和更新求职投递过程中的关键信息，包括：

- 公司
- 岗位
- JD
- 来源
- 状态
- HR 最新消息
- 下一步动作

该模块当前只支持手动记录和更新，不做自动投递，不连接真实招聘平台，不抓取岗位，也不会自动联系 HR。它的目标是为后续的岗位匹配、HR 沟通历史、面试状态追踪和求职复盘提供结构化数据基础。

## `/hr/reply` 与 `application_id`

旧版请求不传 `application_id` 时仍然可用，逻辑保持为基于 `candidate_profile` 和 HR intent 规则生成草稿。

新版请求可以传入 `application_id`：

```json
{
  "application_id": 1,
  "message": "方便明天下午视频面试吗？",
  "company_name": "",
  "job_title": "",
  "extra_context": ""
}
```

当记录存在时，返回数据会包含：

- `application_id`
- `application_context`
- `application_updated`
- `application_update_fields`

当记录不存在时，返回：

```json
{
  "success": false,
  "message": "application not found",
  "data": null
}
```

## API 示例

健康检查：

```bash
curl http://127.0.0.1:8001/health
```

保存求职档案：

```bash
curl -X POST http://127.0.0.1:8001/profile \
  -H "Content-Type: application/json" \
  -d "{\"expected_salary_min\":15000,\"expected_salary_max\":20000,\"minimum_salary\":13000,\"preferred_cities\":[\"Hangzhou\",\"Shanghai\"],\"target_roles\":[\"AI Application Developer\"],\"available_projects\":[\"FastAPI + RAG knowledge base\"],\"truth_boundaries\":[\"No production-grade multi-agent platform experience\"]}"
```

生成绑定投递记录的 HR 回复草稿：

```bash
curl -X POST http://127.0.0.1:8001/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":1,\"message\":\"方便明天下午视频面试吗？\",\"company_name\":\"\",\"job_title\":\"\",\"extra_context\":\"\"}"
```

创建投递记录：

```bash
curl -X POST http://127.0.0.1:8001/applications \
  -H "Content-Type: application/json" \
  -d "{\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\",\"job_source\":\"Manual\",\"job_url\":\"https://example.com/job/123\",\"jd_text\":\"Build AI application workflows with FastAPI and LLM tools.\",\"status\":\"saved\",\"next_action\":\"Review JD fit\",\"notes\":\"Manual tracking record only.\",\"risk_flags\":[]}"
```

读取单条投递记录：

```bash
curl http://127.0.0.1:8001/applications/1
```

## 明确边界

当前未实现：

- 自动投递
- 自动发送 HR 消息
- 真实招聘平台接入
- Playwright
- RAG
- 前端
- JD 匹配评分
- 真实 LLM 调用
- 自动面试时间确认
- 生产级权限系统
- 完整多轮聊天
- conversations / messages 持久化

项目也不会编造候选人的工作经历、教育经历、地址、工作年限、薪资、项目历史或其他履历信息。任何涉及真实外部沟通和求职承诺的内容，都应保持 Human-in-the-loop。

## API Smoke Test Harness

`scripts/api_smoke_test.py` 是本地接口验收脚本，用于快速检查当前主链路 API 是否可用。它是开发验收工具，不是业务功能，不新增任何业务接口。

使用前需要先启动 FastAPI 服务：

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

默认测试地址为：

```text
http://127.0.0.1:8001
```

运行方式：

```bash
python scripts/api_smoke_test.py
```

也可以指定地址：

```bash
python scripts/api_smoke_test.py --base-url http://127.0.0.1:8001
```

脚本会临时写入测试 `candidate_profile`，并在结束时尽量恢复原 profile。由于当前没有删除 profile 的接口，如果测试前没有 profile，脚本会保留测试 profile 并输出 warning。

脚本会创建一条 `HARNESS Demo Company <timestamp>` application 测试记录，并在收尾阶段尽量把它标记为 `closed`。脚本不调用 LLM，不调用 DeepSeek，不自动投递，不自动发送 HR 消息，不连接真实招聘平台。

## Roadmap

- Step 6：API smoke test harness
- Step 7：`job_match` 岗位匹配评分
- Step 8：`resume_text` / `project_context` 增强回复
- Step 9：RAG 化项目经历资料
- Step 10：Playwright dry-run 岗位采集
- Step 11：用户确认后的半自动化流程
