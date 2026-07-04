param(
    [int]$BackendPort = 8002,
    [int]$FrontendPort = 5173,
    [switch]$NoBrowser,
    [switch]$Headless,
    [int]$TestDurationSeconds = 0
)

$ErrorActionPreference = "Stop"
$expectedRoot = [System.IO.Path]::GetFullPath("D:\software\Code\ai_job_agent")
$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))

if (-not [string]::Equals($projectRoot, $expectedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Error "Current project root must be D:\software\Code\ai_job_agent. Actual: $projectRoot"
    exit 1
}

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    Write-Error ".venv Python was not found: $python"
    exit 1
}

function Test-PortInUse {
    param([int]$Port)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Port)
        if (-not $task.Wait(500)) { return $false }
        return $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

$occupied = @()
foreach ($port in @($BackendPort, $FrontendPort)) {
    if (Test-PortInUse -Port $port) { $occupied += $port }
}
if ($occupied.Count -gt 0) {
    Write-Warning "Ports may already be in use. Close old services or inspect these ports: $($occupied -join ', ')"
    Write-Warning "No process was killed and no new service was started."
    exit 1
}

$backendUrl = "http://127.0.0.1:$BackendPort"
$frontendUrl = "http://127.0.0.1:$FrontendPort"
$windowStyle = "Normal"
if ($Headless) { $windowStyle = "Hidden" }

$backendCommand = "Set-Location -LiteralPath '$projectRoot'; & '$python' -m uvicorn app.main:app --reload --host 127.0.0.1 --port $BackendPort"
$frontendCommand = "Set-Location -LiteralPath '$projectRoot'; & '$python' -m http.server $FrontendPort -d frontend_demo"
$backendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($backendCommand))
$frontendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($frontendCommand))

if ($Headless) {
    $backendArgs = @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", $BackendPort.ToString())
    $frontendArgs = @("-m", "http.server", $FrontendPort.ToString(), "-d", "frontend_demo")
    $backendOut = Join-Path $env:TEMP "ai_job_agent_demo_backend.out.log"
    $backendErr = Join-Path $env:TEMP "ai_job_agent_demo_backend.err.log"
    $frontendOut = Join-Path $env:TEMP "ai_job_agent_demo_frontend.out.log"
    $frontendErr = Join-Path $env:TEMP "ai_job_agent_demo_frontend.err.log"
    $backendProcess = Start-Process -FilePath $python -ArgumentList $backendArgs -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
    $frontendProcess = Start-Process -FilePath $python -ArgumentList $frontendArgs -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru
}
else {
    $backendArgs = @("-NoLogo", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $backendEncoded)
    $frontendArgs = @("-NoLogo", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $frontendEncoded)
    $backendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $backendArgs -WorkingDirectory $projectRoot -WindowStyle Normal -PassThru
    $frontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $frontendArgs -WorkingDirectory $projectRoot -WindowStyle Normal -PassThru
}

Start-Sleep -Seconds 3

if ($backendProcess.HasExited -or $frontendProcess.HasExited) {
    Write-Error "A demo service exited during startup. Check BackendPort and FrontendPort."
    exit 1
}

Write-Host ""
Write-Host "AI Job Agent Demo is starting" -ForegroundColor Green
Write-Host "Backend URL: $backendUrl"
Write-Host "Swagger URL: $backendUrl/docs"
Write-Host "Frontend URL: $frontendUrl"
Write-Host "Backend PID: $($backendProcess.Id)"
Write-Host "Frontend PID: $($frontendProcess.Id)"
Write-Host ""
Write-Host "Close either service window, or press Ctrl+C in a Backend / Frontend window, to stop the demo."

if (-not $NoBrowser) {
    Start-Process $frontendUrl | Out-Null
}

if ($TestDurationSeconds -gt 0) {
    Start-Sleep -Seconds $TestDurationSeconds
}
else {
    while (-not $backendProcess.HasExited -and -not $frontendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
}

foreach ($process in @($backendProcess, $frontendProcess)) {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "Demo services started by this script have been stopped."
