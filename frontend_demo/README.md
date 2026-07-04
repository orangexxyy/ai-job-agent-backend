# AI Job Agent Frontend Demo

## VSCode 一键启动

1. 打开 VSCode 左侧 Run and Debug。
2. 选择 `AI Job Agent Full Demo`。
3. 点击绿色播放按钮。
4. 访问 `http://127.0.0.1:5173`。

该 compound 会同时启动 FastAPI `8002` 和静态前端 `5173`，并通过 `serverReadyAction` 尝试打开浏览器。

## 一键启动

```powershell
.\scripts\start_demo.ps1
```

如果 PowerShell 执行策略阻止脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo.ps1
```

脚本默认启动后端 `8002`、前端 `5173` 并打开浏览器。它不会强杀已有端口进程。

## 启动后端

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

## 打开页面

可以直接打开 `frontend_demo/index.html`。后端只为本地 Demo 来源配置了受限 CORS。

如果浏览器限制 `file://` 请求，启动静态服务器：

```powershell
.\.venv\Scripts\python.exe -m http.server 5173 -d frontend_demo
```

然后访问 `http://127.0.0.1:5173`。

页面调用：

- `POST /agent/reply_send_gate/simulate`
- `GET /applications/{application_id}/action_history`

页面不包含真实发送、自动投递、附件上传、平台登录或验证码处理能力。`external_action_performed` 必须保持为 false。
