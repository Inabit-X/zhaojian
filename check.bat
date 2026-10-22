@echo off
setlocal
chcp 936 >nul
title own_partner 连通性自检
cd /d "%~dp0"

echo ============================================
echo    own_partner 连通性自检
echo ============================================
echo.
echo [1/4] 容器状态：
wsl --cd "%CD%" -- bash -lc "docker compose ps"
echo.
echo [2/4] 连续 5 次健康检查（间隔 1 秒）：
for /l %%i in (1,1,5) do (
    curl.exe -sS -m 4 -o NUL -w "  第 %%i 次: HTTP %%{http_code}\n" http://127.0.0.1:18080/api/v1/health/ready
    ping -n 2 127.0.0.1 >nul
)
echo.
echo [3/4] Swagger 文档：
curl.exe -sS -m 4 -o NUL -w "  /docs: HTTP %%{http_code}\n" http://127.0.0.1:18080/docs
echo.
echo [4/4] 前端开发服务器：
curl.exe -sS -m 4 -o NUL -w "  /: HTTP %%{http_code}\n" http://127.0.0.1:5173/
echo.
echo 后端连续 5 次、前端 1 次均为 200 表示连接稳定；出现 000 表示请求没有连上。
echo 前端未启动时，/ 显示 000 属正常，不影响后端。
pause
endlocal
exit /b 0
