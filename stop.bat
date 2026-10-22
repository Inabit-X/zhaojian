@echo off
setlocal
chcp 936 >nul
title own_partner 停止
cd /d "%~dp0"

echo 正在停止前端开发服务器...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
taskkill /FI "WINDOWTITLE eq own_partner frontend*" /T /F >nul 2>&1

echo 正在停止容器并清理 WSL 保活进程...
wsl --cd "%CD%" -- bash -lc "docker compose down"
wsl -- bash -lc "pkill -f 'sleep infinity' >/dev/null 2>&1 || true"
echo.
echo 已停止（前端、backend、db、Redis）。数据卷保留；如需连数据一起删除，请执行：
echo   docker compose down -v
echo.
pause
endlocal
exit /b 0
