"""
Mock 搜索服务统一启动器
========================
一键启动所有 Mock 服务，用于外网开发时替代内网接口。

服务清单：
  8010  mock_search_api       bocomsearch（内网知识库） + online_search（互联网搜索）
  8011  mock_industry_report  行业研报查询
  8012  mock_news             新闻列表查询
  8013  mock_news_detail      新闻详情查询

用法：
  # 启动全部服务（推荐，后台多进程）
  cd middlewares/search && python main.py

  # 只启动搜索接口（bocomsearch + online_search）
  cd middlewares/search && python main.py --only search

  # 使用 uv 环境
  cd middlewares/search && uv run python main.py
"""

import argparse
import subprocess
import sys
import os
import time
import signal
from pathlib import Path

# 切换到脚本所在目录，确保 uvicorn 能找到模块
os.chdir(Path(__file__).parent)

SERVICES = {
    "search": {
        "module": "mock_search_api:app",
        "port": 8010,
        "desc": "bocomsearch（内网知识库） + online_search（互联网搜索）",
    },
    "industry": {
        "module": "mock_industry_report_api:app",
        "port": 8011,
        "desc": "行业研报查询",
    },
    "news": {
        "module": "mock_news_api:app",
        "port": 8012,
        "desc": "新闻列表查询",
    },
    "news_detail": {
        "module": "mock_news_detail_api:app",
        "port": 8013,
        "desc": "新闻详情查询",
    },
}


def start_service(name: str, cfg: dict) -> subprocess.Popen:
    cmd = [
        sys.executable, "-m", "uvicorn",
        cfg["module"],
        "--host", "0.0.0.0",
        "--port", str(cfg["port"]),
        "--reload",
    ]
    print(f"  ▶  [{name}] 端口 {cfg['port']}  {cfg['desc']}")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    return proc


def main():
    parser = argparse.ArgumentParser(description="Mock 服务统一启动器")
    parser.add_argument(
        "--only",
        choices=list(SERVICES.keys()),
        default=None,
        help="只启动指定服务（默认启动全部）",
    )
    args = parser.parse_args()

    to_start = {args.only: SERVICES[args.only]} if args.only else SERVICES

    print("\n=== Mock 服务启动 ===")
    processes = {}
    for name, cfg in to_start.items():
        processes[name] = start_service(name, cfg)
        time.sleep(0.3)  # 错开启动时间，避免端口竞争

    print(f"\n✅ 已启动 {len(processes)} 个服务，Ctrl+C 停止所有服务\n")

    def shutdown(sig, frame):
        print("\n[停止] 正在关闭所有 Mock 服务...")
        for name, proc in processes.items():
            proc.terminate()
            print(f"  ✕  [{name}] 已停止")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 主循环：转发所有子进程的输出
    import select
    fds = {proc.stdout.fileno(): name for name, proc in processes.items()}
    while True:
        try:
            readable, _, _ = select.select(list(fds.keys()), [], [], 1.0)
            for fd in readable:
                name = fds[fd]
                line = processes[name].stdout.readline()
                if line:
                    print(f"[{name}] {line}", end="")
        except Exception:
            pass

        # 检查是否有子进程意外退出
        for name, proc in list(processes.items()):
            if proc.poll() is not None:
                print(f"\n⚠️  [{name}] 意外退出（代码 {proc.returncode}），请检查日志")
                processes.pop(name)

        if not processes:
            print("所有服务均已退出，启动器退出。")
            break


if __name__ == "__main__":
    main()
