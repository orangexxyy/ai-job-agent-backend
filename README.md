# AI Job Agent

AI Job Agent 是一个面向 AI应用开发 / 大模型应用开发求职场景的 Human-in-the-loop 后端 Demo。项目当前主要用于求职流程管理、HR 沟通草稿辅助和中文面试展示，帮助候选人把求职档案、投递记录、HR 消息和后续流程管理得更清楚。

本项目不是自动海投工具，不自动发送 HR 消息，不连接真实招聘平台，也不做自动招聘决策。所有涉及投递、沟通、面试时间确认、薪资谈判和外部平台操作的动作，都必须由用户最终确认。

## 当前阶段

当前已完成到 Step 4：

- Step 1：`candidate_profile` 求职档案保存与读取
- Step 2：`/hr/analyze` HR 意图分析
- Step 3：`/hr/reply` HR 回复草稿生成
- Step 4：`/applications` 投递记录管理

现阶段的 `/hr/analyze` 使用本地规则进行意图识别；`/hr/reply` 基于规则和 `candidate_profile` 生成保守的回复草稿。当前接口不真实调用 DeepSeek / LLM，也不消耗真实 API token。

`/hr/reply` 只返回待用户确认的回复草稿，不会自动发送消息。对于项目经验、技术方案、业务方案等高风险问题，当前实现会保持保守边界，避免编造候选人经历。

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
- `POST /hr/reply`：生成 HR 回复草稿
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

读取求职档案：

```bash
curl http://127.0.0.1:8001/profile
```

分析 HR 消息意图：

```bash
curl -X POST http://127.0.0.1:8001/hr/analyze \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What salary package do you expect? Are you available within one week? Can you relocate?\",\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\"}"
```

生成 HR 回复草稿：

```bash
curl -X POST http://127.0.0.1:8001/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What salary package do you expect? Are you available within one week? Can you relocate?\",\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\"}"
```

创建投递记录：

```bash
curl -X POST http://127.0.0.1:8001/applications \
  -H "Content-Type: application/json" \
  -d "{\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\",\"job_source\":\"Manual\",\"job_url\":\"https://example.com/job/123\",\"jd_text\":\"Build AI application workflows with FastAPI and LLM tools.\",\"status\":\"saved\",\"next_action\":\"Review JD fit\",\"notes\":\"Manual tracking record only.\",\"risk_flags\":[]}"
```

查询投递记录：

```bash
curl "http://127.0.0.1:8001/applications?status=saved&limit=50"
```

读取单条投递记录：

```bash
curl http://127.0.0.1:8001/applications/1
```

更新投递记录：

```bash
curl -X PATCH http://127.0.0.1:8001/applications/1 \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"hr_contacted\",\"last_hr_message\":\"HR asked about availability.\",\"next_action\":\"Prepare reply draft\"}"
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

项目也不会编造候选人的工作经历、教育经历、地址、工作年限、薪资、项目历史或其他履历信息。任何涉及真实外部沟通和求职承诺的内容，都应保持 Human-in-the-loop。

## Roadmap

- Step 5：`/hr/reply` 支持 `application_id` 上下文
- Step 6：`job_match` 岗位匹配评分
- Step 7：`resume_text` / `project_context` 增强回复
- Step 8：RAG 化项目经历资料
- Step 9：Playwright dry-run 岗位采集
- Step 10：用户确认后的半自动化流程

