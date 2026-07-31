#!/bin/bash
set -e

# 显示帮助
usage() {
    echo "Usage: $0 <action> [files...]"
    echo ""
    echo "Actions:"
    echo "  upload [files]  Upload files to share"
    echo "  fetch           Fetch latest from remote"
    echo "  clean           Clean share (preserves history)"
    exit 1
}

# 检查参数
if [ $# -lt 1 ]; then
    usage
fi

ACTION=$1
shift

# 读取配置
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: config.json not found."
    exit 1
fi

SHARE_DIR=$(grep -o '"share_dir":"[^"]*"' "$CONFIG_FILE" | cut -d'"' -f4)
USERNAME=$(grep -o '"username":"[^"]*"' "$CONFIG_FILE" | cut -d'"' -f4)
USERNAME=${USERNAME:-unknown}

# 替换 ~ 为 HOME
SHARE_DIR="${SHARE_DIR/#\~/$HOME}"

# 确保目录存在
mkdir -p "$SHARE_DIR"

cd "$SHARE_DIR"

# 检查 git 仓库
if [ ! -d ".git" ]; then
    echo "Error: $SHARE_DIR is not a git repository."
    exit 1
fi

case "$ACTION" in
    upload)
        # 复制文件到 share
        for src in "$@"; do
            if [ -e "$src" ]; then
                name=$(basename "$src")
                cp -rf "$src" "$SHARE_DIR/$name"
                echo "Copied: $src"
            else
                echo "Warning: not found: $src"
            fi
        done

        # 切到 master 并拉取（冲突时以本地上传的为准）
        git checkout master 2>/dev/null
        git pull -X ours origin master 2>/dev/null || true

        # 检查是否有变更
        if [ -z "$(git status --porcelain)" ]; then
            echo "Nothing to upload."
            exit 0
        fi

        # 提交并推送
        timestamp=$(date "+%Y-%m-%d-%H%M%S")
        git add .
        git commit -m "upload [$USERNAME] $timestamp"
        git push origin master
        echo "Upload complete."
        ;;
    fetch)
        git fetch origin
        git checkout master
        git pull origin master
        echo "Fetch complete."
        ;;
    clean)
        # 清空文件
        git rm -rf . 2>/dev/null || true
        git clean -fd 2>/dev/null || true

        # 创建清空提交
        timestamp=$(date "+%Y-%m-%d %H:%M:%S")
        git commit -m "clear [$USERNAME] $timestamp" --allow-empty

        # 强制推送
        git push origin master -f
        echo "Share cleaned. History preserved."
        ;;
    *)
        usage
        ;;
esac
