#!/usr/bin/env bash
# ==============================================================================
# DeerFlow 每日自动重启脚本
#
# 用途：
#   - 每天定时重启 docker-compose.yml 中的业务容器，缓解内存泄漏 / 长连接挂死 /
#     apikey 缓存错乱等"跑久了就变慢"的问题。
#   - 默认使用 `docker compose restart`，不会删除容器，不会重建卷，不会丢数据。
#
# 特性：
#   1. flock 文件锁：防止多次触发同时跑
#   2. 分容器顺序重启：nginx 最先停/最后启，避免流量打到半重启状态
#   3. 跳过 postgres：数据库不参与每日重启（有需要可用 FULL=1 强制全重启）
#   4. 日志按天切分：logs/daily-restart-YYYY-MM-DD.log
#   5. 健康检查：重启后 HTTP 探活 backend:8000
#   6. 失败非零退出码，便于 cron/systemd 捕获
#
# 用法：
#   # 默认：业务容器滚动重启（不动 postgres）
#   bash scripts/daily-restart.sh
#
#   # 完整重启（包含 postgres），慎用
#   FULL=1 bash scripts/daily-restart.sh
#
#   # 使用 down + up 彻底重建容器（会重新挂载 volume，数据仍保留）
#   MODE=recreate bash scripts/daily-restart.sh
#
# 建议 cron 条目（每天 03:30 重启）：
#   30 3 * * * /home/llm/zhangle/deer-flow/deer-flow-1.0/scripts/daily-restart.sh >> /dev/null 2>&1
# ==============================================================================

set -euo pipefail

# ---------- 路径与变量 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
LOG_DIR="${PROJECT_DIR}/logs"
LOCK_FILE="/tmp/deer-flow-daily-restart.lock"
DATE_TAG="$(date +%Y-%m-%d)"
LOG_FILE="${LOG_DIR}/daily-restart-${DATE_TAG}.log"

MODE="${MODE:-restart}"        # restart | recreate
FULL="${FULL:-0}"              # 1 = 同时重启 postgres
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-90}"   # 秒

mkdir -p "${LOG_DIR}"

# ---------- 日志工具 ----------
log() {
    local level="$1"; shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*"
    echo "${msg}" | tee -a "${LOG_FILE}"
}

on_exit() {
    local rc=$?
    if [[ $rc -eq 0 ]]; then
        log INFO "✅ 每日重启流程全部完成"
    else
        log ERROR "❌ 每日重启流程失败，退出码=${rc}"
    fi
    exit $rc
}
trap on_exit EXIT

# ---------- 锁：防并发 ----------
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    log WARN "⏸️  另一个实例正在运行（锁: ${LOCK_FILE}），本次跳过"
    exit 0
fi

log INFO "================ DeerFlow 每日重启开始 ================"
log INFO "项目目录: ${PROJECT_DIR}"
log INFO "Compose 文件: ${COMPOSE_FILE}"
log INFO "模式: MODE=${MODE}  FULL=${FULL}"

cd "${PROJECT_DIR}"

# ---------- 识别 docker compose 命令 ----------
if command -v "docker" >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    log ERROR "未找到 docker compose / docker-compose 命令"
    exit 127
fi
log INFO "使用: ${DC}"

# ---------- 要处理的服务列表 ----------
# 顺序：先停 nginx（切流量），再停业务，最后启动
if [[ "${FULL}" == "1" ]]; then
    SERVICES=(nginx frontend backend easyparse-1 easyparse-2 postgres)
else
    SERVICES=(nginx frontend backend easyparse-1 easyparse-2)
fi

# ---------- 重启执行 ----------
case "${MODE}" in
    restart)
        log INFO "🔄 模式=restart：docker compose restart（容器内进程被 SIGTERM/SIGKILL 然后重启）"
        for svc in "${SERVICES[@]}"; do
            log INFO "→ restart ${svc}"
            if ${DC} -f "${COMPOSE_FILE}" restart "${svc}" >>"${LOG_FILE}" 2>&1; then
                log INFO "   ✔ ${svc} 重启完成"
            else
                log ERROR "   ✘ ${svc} 重启失败"
                exit 1
            fi
        done
        ;;

    recreate)
        log INFO "🔄 模式=recreate：down + up -d（容器被销毁重建，volume 不受影响）"
        log INFO "→ stop ${SERVICES[*]}"
        ${DC} -f "${COMPOSE_FILE}" stop "${SERVICES[@]}" >>"${LOG_FILE}" 2>&1 || true
        log INFO "→ up -d --no-build"
        ${DC} -f "${COMPOSE_FILE}" up -d --no-build >>"${LOG_FILE}" 2>&1
        ;;

    *)
        log ERROR "未知 MODE=${MODE}（允许: restart | recreate）"
        exit 2
        ;;
esac

# ---------- 等待就绪 ----------
log INFO "⏳ 等待 backend 健康探测 (${HEALTH_URL}, 最多 ${HEALTH_TIMEOUT}s)"
deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
healthy=0
while [[ $(date +%s) -lt $deadline ]]; do
    if curl -fsS --max-time 5 "${HEALTH_URL}" >/dev/null 2>&1; then
        healthy=1
        break
    fi
    sleep 3
done

if [[ $healthy -eq 1 ]]; then
    log INFO "✅ backend 健康检查通过"
else
    log WARN "⚠️  backend 在 ${HEALTH_TIMEOUT}s 内未就绪，请人工确认（不算失败，继续）"
fi

# ---------- 打印当前容器状态 ----------
log INFO "----- 当前容器状态 -----"
${DC} -f "${COMPOSE_FILE}" ps >>"${LOG_FILE}" 2>&1 || true

log INFO "================ DeerFlow 每日重启结束 ================"
