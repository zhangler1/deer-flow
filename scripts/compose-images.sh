#!/usr/bin/env bash
set -euo pipefail

# compose-images.sh
# 功能：按照指定 docker-compose 文件的 image 列表，支持：
#   -o 保存镜像到 -d 指定目录（默认当前目录）
#   -i 从 -d 指定目录加载 *.tar 为镜像，并校验 compose 中的镜像是否存在
#   -f 指定 docker-compose 文件（默认 ./docker-compose.yml）
#   -d 指定目录（默认 .）
# 用法示例：
#   保存：./compose-images.sh -o -f ./docker-compose.yml -d ./images
#   加载：./compose-images.sh -i -f ./docker-compose.yml -d ./images

OUT_DIR="."
COMPOSE_FILE="./docker-compose.yml"
ACTION=""   # save 或 load

usage() {
  cat <<EOF
用法: $0 [-o | -i] [-f COMPOSE_FILE] [-d OUT_DIR]
  -o    保存 compose 中的镜像到 -d 目录（默认当前目录）
  -i    从 -d 目录加载 *.tar 为镜像，并校验 compose 中列出的镜像是否已存在
  -f    指定 docker-compose 文件（默认 ./docker-compose.yml）
  -d    指定目录（默认 .）
示例:
  保存: $0 -o -f ./docker-compose.yml -d ./images
  加载: $0 -i -f ./docker-compose.yml -d ./images
EOF
}

# 解析参数
while getopts ":oid:f:" opt; do
  case "$opt" in
    o) ACTION="save" ;;
    i) ACTION="load" ;;
    d) OUT_DIR="$OPTARG" ;;
    f) COMPOSE_FILE="$OPTARG" ;;
    :) echo "选项 -$OPTARG 需要参数" >&2; usage; exit 2 ;;
    \?) echo "未知选项: -$OPTARG" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$ACTION" ]]; then
  echo "错误：必须指定 -o（保存）或 -i（加载）中的一个" >&2
  usage
  exit 2
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "错误：找不到 compose 文件: $COMPOSE_FILE" >&2
  exit 1
fi

# 查找 docker compose 命令（优先 v2 的 `docker compose`）
find_compose_cmd() {
  if command -v docker &>/dev/null; then
    if docker compose version &>/dev/null; then
      echo "docker compose"
      return 0
    fi
  fi
  if command -v docker-compose &>/dev/null; then
    echo "docker-compose"
    return 0
  fi
  return 1
}

COMPOSE_CMD=$(find_compose_cmd) || { echo "错误：未找到 docker compose 或 docker-compose 命令" >&2; exit 1; }

# 提取镜像列表
get_images() {
  ${COMPOSE_CMD} -f "$COMPOSE_FILE" config \
    | awk -F: '/^[[:space:]]*image:[[:space:]]*/ { sub(/^[[:space:]]*image:[[:space:]]*/, ""); print }' \
    | sed -e 's/["'\'' ]//g' -e 's/#.*$//' \
    | awk 'NF>0 {print $0}' \
    | sort -u
}

# 为镜像名生成安全文件名
safe_name() {
  echo -n "$1" | sed 's#[/:]#_#g'
}

save_images() {
  mkdir -p "$OUT_DIR"
  local imgs
  imgs=$(get_images)
  if [[ -z "$imgs" ]]; then
    echo "警告：未在 compose 中发现 image 字段。若服务通过 build 生成镜像且未命名 image，请先构建并手动保存对应镜像名。" >&2
  fi
  echo "输出目录: $OUT_DIR"
  echo "准备保存以下镜像："
  echo "$imgs" | sed 's/^/  - /'

  while IFS= read -r image; do
    [[ -z "$image" ]] && continue
    local fname
    fname=$(safe_name "$image")
    local out_file="$OUT_DIR/${fname}.tar"

    echo "==> 处理镜像: $image"
    if ! docker image inspect "$image" >/dev/null 2>&1; then
      echo "   本地未找到镜像，尝试 docker pull $image ..."
      docker pull "$image"
    fi
    echo "   保存为: $out_file"
    docker save -o "$out_file" "$image"
  done <<<"$imgs"
  echo "保存完成，输出目录: $OUT_DIR"
}

load_images() {
  if [[ ! -d "$OUT_DIR" ]]; then
    echo "错误：目录不存在: $OUT_DIR" >&2
    exit 1
  fi
  echo "从目录加载 tar：$OUT_DIR"
  shopt -s nullglob
  local tar_files=("$OUT_DIR"/*.tar)
  shopt -u nullglob
  if [[ ${#tar_files[@]} -eq 0 ]]; then
    echo "警告：目录中未找到任何 *.tar 文件" >&2
  fi

  for tarf in "${tar_files[@]}"; do
    echo "==> docker load -i $tarf"
    docker load -i "$tarf"
  done

  # 加载后校验 compose 中的镜像是否存在
  local imgs
  imgs=$(get_images)
  local missing=()
  while IFS= read -r image; do
    [[ -z "$image" ]] && continue
    if ! docker image inspect "$image" >/dev/null 2>&1; then
      missing+=("$image")
    fi
  done <<<"$imgs"

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "\n以下镜像在加载后仍未找到（可能 tar 中不含该镜像或标签不匹配）："
    for m in "${missing[@]}"; do
      echo "  - $m"
    done
    echo "提示：请确保保存时使用的镜像名与 compose 中一致的 name:tag，或重新保存/加载对应 tar。"
  else
    echo "已成功加载并存在 compose 中声明的所有镜像。"
  fi
}

case "$ACTION" in
  save) save_images ;;
  load) load_images ;;
  *) echo "未知动作: $ACTION" >&2; usage; exit 2 ;;
esac
