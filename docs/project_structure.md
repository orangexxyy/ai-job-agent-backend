# Project Structure

## 整体目录结构

当前项目采用常见 FastAPI 分层结构：

```text
ai_job_agent/
├─ app/
│  ├─ main.py
│  ├─ database.py
│  ├─ models.py
│  ├─ routes/
│  ├─ schemas/
│  └─ services/
├─ scripts/
├─ docs/
├─ README.md
├─ AGENTS.md
└─ requirements.txt
```

## 每一层的职责

- `app/main.py`  
  FastAPI 应用入口，负责创建 `FastAPI` 实例、注册 routes，并在启动时初始化 SQLite 数据库。

- `app/routes/`  
  HTTP 接口层。routes 只负责接收请求、调用 service、包装 response，不应该写大量业务逻辑。

- `app/schemas/`  
  Pydantic 数据结构层，定义请求体和响应体字段。schemas 只描述数据结构，不放业务判断。

- `app/services/`  
  业务逻辑层。profile、application、HR intent、HR reply、job_match、truth boundary 等核心逻辑都在这里。

- `app/database.py` / `app/models.py`  
  SQLite 连接和建表 SQL。数据库结构变化属于高风险操作，必须谨慎并同步文档。

- `scripts/`  
  开发测试脚本，例如 `api_smoke_test.py`，用于从外部通过 HTTP 验证主链路接口。

- `docs/`  
  设计文档、面试话术、演示脚本、结构说明和阅读指南。

## route / service 的区别

`GET /profile` 是 HTTP 接口，面向 Swagger、前端、测试脚本或外部调用方。

`get_candidate_profile()` 是内部 service 函数，面向后端代码、workflow、未来 LangGraph node 调用。

两者职责不同：

- route 是对外入口，关注 HTTP request / response。
- service 是可复用业务能力，关注具体业务规则和数据读写。

## 为什么后端内部 workflow 不建议再 HTTP 调自己

未来 workflow / LangGraph node 应该优先调用 `services/` 下的函数，而不是在后端内部再请求自己的 HTTP API。

原因：

- 避免额外 HTTP 开销。
- 避免依赖端口和服务启动状态。
- 避免循环调用。
- 更容易做单元测试和集成测试。
- 更容易复用业务逻辑。
- 更清楚地区分内部编排和外部 API。

FastAPI routes 是对外入口，LangGraph nodes 是内部编排步骤，二者都应该复用 service 层。

## 典型调用链

### POST /profile

```text
POST /profile
-> profile_routes.py
-> profile_service.py
-> database.py
-> SQLite
```

### POST /hr/reply

```text
POST /hr/reply
-> hr_routes.py
-> hr_reply_service.py
-> hr_intent_service.py
-> profile_service.py
-> context_reply_service.py
-> truth_boundary_service.py
-> application_service.py
```

### POST /job_match

```text
POST /job_match
-> job_match_routes.py
-> job_match_service.py
-> application_service.py
-> profile_service.py
```

### scripts/api_smoke_test.py

```text
scripts/api_smoke_test.py
-> HTTP 调用本地 FastAPI
-> 验证主链路接口
```

## 主要 service 函数速查

关键 public service function 应使用中文 docstring，技术名词保留英文，并简要说明用途、输入、输出和副作用，尤其是 SQLite 写入、Human-in-the-loop、LLM、RAG、LangGraph、Playwright 等边界。

| 函数 | 文件 | 作用 |
| --- | --- | --- |
| `save_candidate_profile` | `app/services/profile_service.py` | 保存单用户 `candidate_profile` |
| `get_candidate_profile` | `app/services/profile_service.py` | 读取单用户 `candidate_profile` |
| `create_application` | `app/services/application_service.py` | 创建投递记录 |
| `list_applications` | `app/services/application_service.py` | 查询投递记录列表 |
| `get_application` | `app/services/application_service.py` | 读取单条投递记录 |
| `update_application` | `app/services/application_service.py` | 局部更新投递记录 |
| `analyze_hr_message` | `app/services/hr_intent_service.py` | 规则版 HR intent 分析 |
| `generate_hr_reply` | `app/services/hr_reply_service.py` | 生成 HR 回复草稿 |
| `select_relevant_context_snippets` | `app/services/context_reply_service.py` | 从 profile context 中选择相关片段 |
| `build_context_enhanced_reply` | `app/services/context_reply_service.py` | 生成项目/技术/方案类增强草稿 |
| `analyze_job_match` | `app/services/job_match_service.py` | 规则版岗位匹配评分 |
| `check_truth_boundary` | `app/services/truth_boundary_service.py` | 检查回复草稿是否触碰事实边界 |

## 为未来 workflow / LangGraph 做准备

未来 workflow node 应该优先复用 `services/` 下的函数，而不是重复写 HTTP 请求。

推荐方向：

- `load_profile` node 调用 `get_candidate_profile()`。
- `load_application` node 调用 `get_application()`。
- `run_job_match` node 调用 `analyze_job_match()`。
- `generate_reply_draft` node 调用 `generate_hr_reply()`。
- `update_application` node 调用 `update_application()`。

这样可以保持业务逻辑集中在 service 层，让 FastAPI routes 和 LangGraph workflow 都复用同一套能力。
