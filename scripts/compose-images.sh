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
SERVICES=()  # -s 指定的 service 名过滤列表，为空时处理全部

usage() {
  cat <<EOF
用法: $0 [-o | -i] [-f COMPOSE_FILE] [-d OUT_DIR] [-s SERVICES]
  -o    保存 compose 中的镜像到 -d 目录（默认当前目录）
  -i    从 -d 目录加载 *.tar 为镜像，并校验 compose 中列出的镜像是否已存在
  -f    指定 docker-compose 文件（默认 ./docker-compose.yml）
  -d    指定目录（默认 .）
  -s    只处理指定的服务，多个用逗号分隔，例如 -s backend,nginx。不指定则处理全部服务
示例:
  保存全部: $0 -o -f ./docker-compose.yml -d ./images
  加载全部: $0 -i -f ./docker-compose.yml -d ./images
  保存指定服务: $0 -o -f ./docker-compose.yml -d ./images -s backend,nginx
  加载指定服务校验: $0 -i -f ./docker-compose.yml -d ./images -s backend
EOF
}

# 解析参数
while getopts ":oid:f:s:" opt; do
  case "$opt" in
    o) ACTION="save" ;;
    i) ACTION="load" ;;
    d) OUT_DIR="$OPTARG" ;;
    f) COMPOSE_FILE="$OPTARG" ;;
    s) IFS=',' read -r -a SERVICES <<<"$OPTARG" ;;
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

# 提取镜像列表（支持按 -s 过滤指定服务）
get_images() {
  if [[ ${#SERVICES[@]} -eq 0 ]]; then
    # 未指定服务：输出全部
    ${COMPOSE_CMD} -f "$COMPOSE_FILE" config \
      | awk -F: '/^[[:space:]]*image:[[:space:]]*/ { sub(/^[[:space:]]*image:[[:space:]]*/, ""); print }' \
      | sed -e 's/["'\'' ]//g' -e 's/#.*$//' \
      | awk 'NF>0 {print $0}' \
      | sort -u
  else
    # 指定服务：逐个调用 docker compose config <svc> 过滤后抽 image。
    # 若服务名拼错会导致 compose config 报错，错误直接透传给用户。
    for svc in "${SERVICES[@]}"; do
      [[ -z "$svc" ]] && continue
      ${COMPOSE_CMD} -f "$COMPOSE_FILE" config "$svc" \
        | awk -F: '/^[[:space:]]*image:[[:space:]]*/ { sub(/^[[:space:]]*image:[[:space:]]*/, ""); print }' \
        | sed -e 's/["'\'' ]//g' -e 's/#.*$//' \
        | awk 'NF>0 {print $0}'
    done | sort -u
  fi
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
  if [[ ${#SERVICES[@]} -gt 0 ]]; then
    echo "指定服务: ${SERVICES[*]}"
  fi
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
  if [[ ${#SERVICES[@]} -gt 0 ]]; then
    echo "指定服务: ${SERVICES[*]}（仅加载对应服务的 tar，校验也只针对这些服务）"
  fi

  # 构建待加载 tar 文件集：未指定服务时为目录下全部 *.tar；指定后只加载对应镜像的 tar
  local tar_files=()
  if [[ ${#SERVICES[@]} -eq 0 ]]; then
    shopt -s nullglob
    tar_files=("$OUT_DIR"/*.tar)
    shopt -u nullglob
  else
    local target_imgs
    target_imgs=$(get_images)
    while IFS= read -r image; do
      [[ -z "$image" ]] && continue
      local fname
      fname=$(safe_name "$image")
      local tarf="$OUT_DIR/${fname}.tar"
      if [[ -f "$tarf" ]]; then
        tar_files+=("$tarf")
      else
        echo "警告：未找到服务对应的 tar：$tarf（镜像：$image）" >&2
      fi
    done <<<"$target_imgs"
  fi

  if [[ ${#tar_files[@]} -eq 0 ]]; then
    echo "警告：目录中未找到任何可加载的 *.tar 文件" >&2
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
