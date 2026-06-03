import re
import json
from datetime import datetime


def extract_log_tokens(log_file_path, output_json_path, thread_id_prefix):
    """
    从日志文件中提取指定 thread_id 前缀的 CTX_CHECK 日志，并按时间排序输出为 JSON。
    """
    extracted_data = []
    log_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - \[([^\]]+)\] - .*?CTX_CHECK.*?thread_id=([^\s|]+).*?tokens=(\d+)'
    )

    with open(log_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = log_pattern.search(line)
            if match:
                timestamp_str = match.group(1)
                full_thread_id = match.group(3)
                tokens_str = match.group(4)

                if full_thread_id.startswith(thread_id_prefix):
                    extracted_data.append({
                        "thread_id": full_thread_id,
                        "tokens": int(tokens_str),
                        "timestamp": timestamp_str
                    })

    # 按时间戳排序
    extracted_data.sort(key=lambda x: x['timestamp'])

    # 写入 JSON 文件
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(extracted_data, json_file, indent=4, ensure_ascii=False)


def extract_log_nodes(input_file_path, output_file_path, thread_id_prefix):
    pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*-\s*\[([^\]]+)\]\s*-\s*.*?\s*-\s*INFO\s*-\s*✅ NODE_EXIT\s*\|\s*([^\|]+)\s*\|\s*.*?\|\s*(?:总耗时|耗时):\s*(\d+\.?\d*)s'
    )

    results = []

    with open(input_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                log_time_str = match.group(1)
                thread_id = match.group(2)
                node_type = match.group(3)
                duration = match.group(4)

                if thread_id.startswith(thread_id_prefix):
                    entry = {
                        "thread_id": thread_id,
                        "耗时": duration,
                        "时间": log_time_str,
                        "type": node_type
                    }
                    results.append(entry)

    # 按时间排序 (升序)
    results.sort(key=lambda x: datetime.strptime(x["时间"], '%Y-%m-%d %H:%M:%S'))

    # 写入 JSON 文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


# 使用示例

dir = "/iflytek/vllm_models/zhangle/deer-flow/deer-flow-1.0/logs/"
file_log = f"{dir}deer-flow.log.bak"
file_tokens = f"{dir}deer-flow_tokens.json"
file_nodes = f"{dir}deer-flow_nodes.json"

extract_log_tokens(file_log, file_tokens, "stress_20260602_v5_dr_")
extract_log_nodes(file_log, file_nodes, "stress_20260602_v5_dr_")
