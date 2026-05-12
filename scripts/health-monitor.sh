#!/usr/bin/env bash
#
# health-monitor.sh — DeerFlow 多容器主动探活 + 自愈重启
#
# 功能：
#   对 TARGETS 数组里每个容器周期性执行探活命令，连续失败达到阈值则重启该容器。
#   与 scripts/daily-restart.sh 组成"主动探活 + 被动定时"的双保险。
#
# 用法：
#   ./scripts/health-monitor.sh [OPTIONS]
#
# Options:
#   --interval SECONDS    探测间隔（默认 15）
#   --timeout SECONDS     单次探测超时（默认 5，供探测命令自行使用）
#   --retries COUNT       连续失败多少次触发重启（默认 3）
#   --cooldown SECONDS    单容器两次重启的最小间隔（默认 90）
#   --no-restart          仅监控、不重启
#   --daemon              后台守护模式
#   --stop                停止后台守护
#   --status              查看守护状态
#   --once                只跑一轮探测（调试用）
#   -h, --help            显示帮助
#
# 典型用法：
#   ./scripts/health-monitor.sh --daemon           # 拉起后台守护
#   ./scripts/health-monitor.sh --status           # 查看状态
#   ./scripts/health-monitor.sh --stop             # 停止守护
#   ./scripts/health-monitor.sh --once --no-restart  # 调试：跑一轮只看结果
#
# 与 daily-restart.sh 配合：
#   在 cron / systemd 触发 daily-restart 前，建议先 --stop 本脚本，
#   daily-restart 结束后再 --daemon 拉起，避免双边抢重启。
# ==============================================================================

set -euo pipefail

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  目标数组 — 每行格式："容器名|探测命令|重启命令"                             ║
# ║  探测命令退出码为 0 视为健康；非 0 视为失败。                                 ║
# ║  - nginx 已映射 80:80，直接从宿主机 curl，最轻量                              ║
# ║  - backend 已映射 8000:8000，走 /health（见 src/server/app.py）              ║
# ║  - frontend 未映射端口，用 docker exec 进入容器探测                          ║
# ║    * dev 镜像（Dockerfile.dev.yml）已装 curl                                 ║
# ║    * 生产 distroless 镜像用 node -e 探测                                     ║
# ║  - easyparse-1/2 未映射端口，用容器内 python socket 探测（与现有 healthcheck ║
# ║    保持一致，见 docker-compose.yml）                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

TARGETS=(
  "deer-flow-nginx|curl -sf -m 3 http://localhost/health|docker restart deer-flow-nginx"
  "deer-flow-backend|curl -sf -m 3 http://localhost:8000/health|docker restart deer-flow-backend"
  "deer-flow-frontend|docker exec deer-flow-frontend curl -sf -m 3 http://localhost:3000/deep-research-deerflow|docker restart deer-flow-frontend"
  "easyparse-1|docker exec easyparse-1 python -c \"import socket;s=socket.socket();s.settimeout(3);s.connect(('127.0.0.1',5000));s.close()\"|docker restart easyparse-1"
  "easyparse-2|docker exec easyparse-2 python -c \"import socket;s=socket.socket();s.settimeout(3);s.connect(('127.0.0.1',5000));s.close()\"|docker restart easyparse-2"
)

# ── 默认参数（可被命令行覆盖） ───────────────────────────────────────────────
INTERVAL=300
TIMEOUT=5
RETRIES=3
COOLDOWN=90
NO_RESTART=false
DAEMON_MODE=false
ONCE=false
ACTION="start"

# ── 路径 ──────────────────────────────────────────────────────────────────
REPO_ROOT="$(builtin cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd -P)"
LOG_DIR="$REPO_ROOT/logs"
LOG_FILE="$LOG_DIR/health-monitor.log"
PID_FILE="$LOG_DIR/health-monitor.pid"

# ── 颜色（仅交互终端使用，写入日志文件时禁用） ────────────────────────────
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
else
    GREEN=''; RED=''; YELLOW=''; BLUE=''; NC=''
fi

# ── 参数解析 ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --interval)   INTERVAL="$2"; shift 2 ;;
        --timeout)    TIMEOUT="$2"; shift 2 ;;
        --retries)    RETRIES="$2"; shift 2 ;;
        --cooldown)   COOLDOWN="$2"; shift 2 ;;
        --no-restart) NO_RESTART=true; shift ;;
        --daemon)     DAEMON_MODE=true; shift ;;
        --stop)       ACTION="stop"; shift ;;
        --status)     ACTION="status"; shift ;;
        --once)       ONCE=true; shift ;;
        -h|--help)    sed -n '2,/^# =\+$/p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) echo "Unknown option: $1"; echo "Use --help for usage."; exit 1 ;;
    esac
done

# ── 日志工具 ──────────────────────────────────────────────────────────────
log() {
    local level="$1"; shift
    local ts; ts="$(date '+%Y-%m-%d %H:%M:%S')"
    local msg="[$ts] [$level] $*"
    mkdir -p "$LOG_DIR"
    echo "$msg" >> "$LOG_FILE"
    if [[ -t 1 ]]; then
        case "$level" in
            INFO)  echo -e "${GREEN}${msg}${NC}" ;;
            WARN)  echo -e "${YELLOW}${msg}${NC}" ;;
            ERROR) echo -e "${RED}${msg}${NC}" ;;
            *)     echo "$msg" ;;
        esac
    else
        echo "$msg"
    fi
}

# ── 探活：执行 probe_cmd，返回 0=健康，非 0=失败 ───────────────────────────
probe_target() {
    local probe_cmd="$1"
    # 用 bash -c 执行，超时由 timeout(1) 兜底，防止 docker exec 本身 hang
    if timeout "$((TIMEOUT + 2))" bash -c "$probe_cmd" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# ── 状态文件：记录每个容器的 failure_count 和 last_restart_ts ─────────────
state_file_for() {
    echo "$LOG_DIR/.hm-state-$1"
}

get_state() {
    local f; f="$(state_file_for "$1")"
    if [[ -f "$f" ]]; then cat "$f"; else echo "0 0"; fi
}

set_state() {
    local f; f="$(state_file_for "$1")"
    echo "$2 $3" > "$f"
}

# ── 对单个目标执行一次探活 ────────────────────────────────────────────────
check_one_target() {
    local line="$1"
    local name probe restart
    IFS='|' read -r name probe restart <<< "$line"

    local state; state="$(get_state "$name")"
    local fails last_restart
    fails="$(echo "$state" | awk '{print $1}')"
    last_restart="$(echo "$state" | awk '{print $2}')"

    if probe_target "$probe"; then
        if [[ "$fails" -gt 0 ]]; then
            log INFO "[$name] 恢复健康（此前连续失败 $fails 次）"
        fi
        set_state "$name" 0 "$last_restart"
        return 0
    fi

    fails=$((fails + 1))
    log WARN "[$name] 探测失败 ($fails/$RETRIES) — $probe"

    if [[ $fails -lt $RETRIES ]]; then
        set_state "$name" "$fails" "$last_restart"
        return 1
    fi

    # 达到重启阈值
    if $NO_RESTART; then
        log WARN "[$name] 已连续失败 $fails 次，但 --no-restart 开启，不执行重启"
        set_state "$name" "$fails" "$last_restart"
        return 1
    fi

    local now; now=$(date +%s)
    local elapsed=$((now - last_restart))
    if [[ $elapsed -lt $COOLDOWN ]]; then
        log WARN "[$name] 冷却期未过（${elapsed}s < ${COOLDOWN}s），暂不重启"
        set_state "$name" "$fails" "$last_restart"
        return 1
    fi

    log ERROR "[$name] 连续失败 $fails 次，触发重启：$restart"
    if bash -c "$restart" >/dev/null 2>&1; then
        log INFO "[$name] 重启命令已执行成功"
        set_state "$name" 0 "$now"
    else
        log ERROR "[$name] 重启失败，保留失败计数待下轮再试"
        set_state "$name" "$fails" "$last_restart"
    fi
}

# ── 主循环 ─────────────────────────────────────────────────────────────────
run_monitor() {
    mkdir -p "$LOG_DIR"
    log INFO "========== Health Monitor Started =========="
    log INFO "interval=${INTERVAL}s timeout=${TIMEOUT}s retries=${RETRIES} cooldown=${COOLDOWN}s"
    log INFO "targets=${#TARGETS[@]} auto-restart=$(if $NO_RESTART; then echo OFF; else echo ON; fi)"

    # 清理：确保 PID 文件在退出时删除
    trap 'log INFO "Health monitor shutting down..."; rm -f "$PID_FILE"; exit 0' INT TERM
    trap 'rm -f "$PID_FILE"' EXIT

    local round=0
    while true; do
        round=$((round + 1))
        for target in "${TARGETS[@]}"; do
            check_one_target "$target" || true
        done

        if $ONCE; then
            log INFO "--once 模式：单轮结束，退出"
            break
        fi
        sleep "$INTERVAL"
    done
}

# ── daemon 控制 ────────────────────────────────────────────────────────────
stop_daemon() {
    if [[ -f "$PID_FILE" ]]; then
        local pid; pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
            rm -f "$PID_FILE"
            log INFO "Health monitor daemon (PID $pid) stopped."
            echo -e "${GREEN}Stopped (PID $pid)${NC}"
        else
            rm -f "$PID_FILE"
            echo "Stale PID file removed."
        fi
    else
        echo "Not running."
    fi
}

check_status() {
    if [[ -f "$PID_FILE" ]]; then
        local pid; pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}Running (PID $pid)${NC}"
            echo "  Log: $LOG_FILE"
            echo "  Targets: ${#TARGETS[@]}"
            for t in "${TARGETS[@]}"; do echo "    - ${t%%|*}"; done
            return 0
        else
            echo -e "${YELLOW}Not running (stale PID file)${NC}"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo -e "${YELLOW}Not running${NC}"
        return 1
    fi
}

# ── action 路由 ────────────────────────────────────────────────────────────
case "$ACTION" in
    stop)   stop_daemon ;;
    status) check_status ;;
    start)
        if $DAEMON_MODE; then
            if [[ -f "$PID_FILE" ]]; then
                pid=$(cat "$PID_FILE")
                if kill -0 "$pid" 2>/dev/null; then
                    echo -e "${YELLOW}Already running (PID $pid). Use --stop first.${NC}"
                    exit 1
                fi
                rm -f "$PID_FILE"
            fi
            mkdir -p "$LOG_DIR"
            echo -e "${BLUE}Starting health-monitor as daemon...${NC}"
            nohup bash "$0" \
                --interval "$INTERVAL" \
                --timeout "$TIMEOUT" \
                --retries "$RETRIES" \
                --cooldown "$COOLDOWN" \
                $($NO_RESTART && echo '--no-restart') \
                >> "$LOG_FILE" 2>&1 &
            pid=$!
            echo "$pid" > "$PID_FILE"
            echo -e "${GREEN}Started (PID $pid)${NC}"
            echo "  Log: $LOG_FILE"
        else
            run_monitor
        fi
        ;;
esac
