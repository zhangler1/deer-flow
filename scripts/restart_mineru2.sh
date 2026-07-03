#!/bin/bash
# 定时重启Docker容器（自定义日志目录 + 容器存在检查）

# ====================== 【可自定义配置】 ======================
# 日志存放目录（你可以随便改，比如 /home/logs /data/logs 等）
LOG_DIR="/home/llm/zhangle/deer-flow/deer-flow-1.0/scripts/logs"
# 日志文件名
LOG_FILE="$LOG_DIR/restart_mineru.log"
# 需要重启的容器列表
CONTAINERS=("mineru-server1" "mineru-sglang1")
# CONTAINERS=("mineru-server1" "mineru-sglang1")
# CONTAINERS=("mineru-server1" "mineru-sglang1" "mineru-server2" "mineru-sglang2" "mineru-server3" "mineru-sglang3" "mineru-server4" "mineru-sglang4")
# 最大重试次数（含首次）
MAX_RETRIES=3
# 重试间隔（秒）
RETRY_INTERVAL=30
# ===============================================================

# 自动创建日志目录（不存在则创建）
mkdir -p $LOG_DIR

# 开始执行
echo "==================== $(date '+%Y-%m-%d %H:%M:%S') 开始执行容器重启任务 ====================" >> $LOG_FILE

# 循环检查并重启容器
for container in "${CONTAINERS[@]}"
do
    if /usr/bin/docker ps -a --format "{{.Names}}" | grep -wq "$container"; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 容器 $container 存在，开始重启..." >> $LOG_FILE
        restart_rc=1
        for attempt in $(seq 1 $MAX_RETRIES); do
            /usr/bin/docker restart "$container" >> $LOG_FILE 2>&1
            restart_rc=$?
            if [ $restart_rc -eq 0 ]; then
                break
            fi
            if [ $attempt -lt $MAX_RETRIES ]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] [第${attempt}/${MAX_RETRIES}次] 重启失败(退出码=$restart_rc)，${RETRY_INTERVAL}s后重试..." >> $LOG_FILE
                sleep $RETRY_INTERVAL
            fi
        done
        if [ $restart_rc -eq 0 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [成功] 容器 $container 重启完成(退出码=0)" >> $LOG_FILE
            # 重启成功后打印资源占用（内存/CPU）
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [资源监控] 容器 $container 资源占用:" >> $LOG_FILE
            /usr/bin/docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" "$container" >> $LOG_FILE 2>&1
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [失败] 容器 $container 重启失败(退出码=$restart_rc)，已达最大重试次数$MAX_RETRIES" >> $LOG_FILE
        fi
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 容器 $container 不存在，跳过" >> $LOG_FILE
    fi
    echo "------------------------------------------------------------------------" >> $LOG_FILE

    # 间隔60秒（仅在不是最后一个容器时等待）
    if [ "$container" != "${CONTAINERS[-1]}" ]; then
        sleep 60
    fi
done

echo "==================== $(date '+%Y-%m-%d %H:%M:%S') 执行完毕 ====================" >> $LOG_FILE
echo -e "\n" >> $LOG_FILE

# #!/bin/bash
# # 每天23:00 自动重启Docker容器
# echo "==================== $(date '+%Y-%m-%d %H:%M:%S') 开始重启容器 ====================" >> /iflytek/jjt/mineru2.1_0114/prod/restart_mineru.log
# # 用绝对路径执行docker命令，定时任务必备
# /usr/bin/docker restart mineru-server1 mineru-sglang1
# /usr/bin/docker restart mineru-server1 mineru-sglang1 mineru-server2 mineru-sglang2 mineru-server3 mineru-sglang3 mineru-server4 mineru-sglang4
# echo "==================== $(date '+%Y-%m-%d %H:%M:%S') 容器重启完成 ====================" >> /iflytek/jjt/mineru2.1_0114/prod/restart_mineru.log 

# 1. 确认脚本有执行权限：
# chmod +x /home/llm/zhangle/deer-flow/deer-flow-1.0/scripts/restart_mineru2.sh
# 2. 编辑当前用户的 crontab：
# crontab -e
# 3. 添加一行（例如每天 23:00 执行）：
# # 分 时 日 月 周  命令
# 0 23 * * * /home/llm/zhangle/deer-flow/deer-flow-1.0/scripts/restart_mineru2.sh >> /dev/null 2>&1
# cron 时间格式说明：
# 字段	值	含义
# 分	0	第 0 分钟
# 时	23	晚上 23 点
# 日	*	每天
# 月	*	每月
# 周	*	每周
# 4. 验证已生效：
# crontab -l
# 注意事项：
# cron 环境变量极简，脚本中已用 /usr/bin/docker 绝对路径是正确的做法
# >> /dev/null 2>&1 是因为脚本内部已经把日志写入 $LOG_FILE，不需要 cron 再转发邮件
# 如果 cron 服务没启动，需执行 sudo systemctl start cron && sudo systemctl enable cron