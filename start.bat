@echo off
setlocal
chcp 936 >nul
title own_partner 一键启动
cd /d "%~dp0"

echo ============================================
echo    own_partner  MVP  一键启动
echo ============================================
echo.

if not exist ".env" (
    echo [错误] 缺少 .env 文件。
    echo         请复制 .env.example 为 .env，并把 SECRET_KEY 改成随机值。
    pause
    exit /b 1
)

where wsl >nul 2>nul
if errorlevel 1 (
    echo [错误] 找不到 wsl，请先安装 WSL2。
    pause
    exit /b 1
)

echo [1/5] 检查 WSL 内的 Docker 服务...
wsl -- bash -lc "docker info >/dev/null 2>&1"
if errorlevel 1 (
    echo [错误] Docker 未运行。
    echo         请先在 WSL 终端执行：sudo service docker start
    pause
    exit /b 1
)

echo [2/5] 启动容器（首次构建需要几分钟）...
wsl --cd "%CD%" -- bash -lc "docker compose up -d --wait --wait-timeout 180"
if errorlevel 1 (
    echo [错误] 启动失败，最近日志：
    wsl --cd "%CD%" -- bash -lc "docker compose logs --tail=40"
    pause
    exit /b 1
)

echo [3/5] 启动 WSL 保活进程（防止空闲自动关机导致连接中断）...
wsl -- bash -lc "pkill -f 'sleep infinity' >/dev/null 2>&1 || true"
start "" /min wsl -- sleep infinity

echo [4/5] 后端健康检查...
wsl --cd "%CD%" -- bash -lc "curl -fsS http://127.0.0.1:18080/api/v1/health/ready"
if errorlevel 1 (
    echo [警告] 健康检查未通过，请执行 docker compose logs backend 查看原因。
)
echo.

echo [5/5] 启动前端开发服务器...
where npm >nul 2>nul
if errorlevel 1 (
    echo [警告] 未找到 npm，跳过前端。
    echo         安装 Node.js 20.19+ 后手动执行：cd frontend ^&^& npm run dev
    goto :summary
)

if not exist "frontend\node_modules" (
    echo [提示] 首次运行，安装前端依赖（可能需要几分钟）...
    pushd frontend
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败，跳过前端启动。
        popd
        goto :summary
    )
    popd
)

powershell -NoProfile -Command "try { (New-Object Net.Sockets.TcpClient('127.0.0.1',5173)).Close(); exit 0 } catch { exit 1 }"
if not errorlevel 1 goto :front_ready

echo [5/5] 后台启动 Vite（窗口最小化，关闭该窗口即停止前端）...
start "own_partner frontend" /min cmd /c "cd /d ""%~dp0frontend"" && npm run dev -- --host 127.0.0.1 --port 5173"

echo [5/5] 等待前端就绪（最多 60 秒）...
powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(60); while((Get-Date) -lt $d){ try { (New-Object Net.Sockets.TcpClient('127.0.0.1',5173)).Close(); exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"
if errorlevel 1 (
    echo [警告] 前端 60 秒内未就绪，请查看 "own_partner frontend" 窗口。
    goto :summary
)

:front_ready
if /i "%~1"=="/nobrowser" goto :summary
start "" "http://127.0.0.1:5173/"

:summary
echo.
echo 已启动：
echo   API 文档   http://127.0.0.1:18080/docs
echo   健康检查   http://127.0.0.1:18080/api/v1/health/ready
echo   前端页面   http://127.0.0.1:5173/
echo   连通自检   check.bat
echo.
echo 说明：保活进程会让 WSL 保持运行；如需彻底停止（含前端），双击 stop.bat。
echo.
pause
endlocal
exit /b 0
