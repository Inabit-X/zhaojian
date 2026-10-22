#!/bin/sh
set -e

# 单机 MVP：容器启动时自动迁移。多副本部署时应改为独立 migration job。
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
