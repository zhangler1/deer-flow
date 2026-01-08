#!/bin/bash
# 离线构建准备脚本
# 在有网环境执行此脚本，准备离线构建所需的所有文件

set -e

echo "🚀 开始准备离线构建包..."

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否在正确的目录
if [ ! -f "package.json" ]; then
    echo "❌ 错误：请在项目 web 目录下执行此脚本"
    exit 1
fi

# 1. 清理旧文件
echo -e "${BLUE}📦 清理旧的构建文件...${NC}"
rm -rf node_modules .next
rm -f deer-flow-offline-*.tar.gz

# 2. 安装依赖
echo -e "${BLUE}📥 安装所有依赖（包括 devDependencies）...${NC}"
pnpm install --frozen-lockfile

# 3. 验证依赖
echo -e "${BLUE}✅ 验证依赖完整性...${NC}"
if [ ! -d "node_modules" ]; then
    echo "❌ 错误：node_modules 安装失败"
    exit 1
fi

# 4. 创建离线包
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="deer-flow-offline-${TIMESTAMP}.tar.gz"

echo -e "${BLUE}📦 打包离线构建所需文件...${NC}"

# 创建临时目录
mkdir -p offline-build-temp
cd offline-build-temp

# 复制必要文件
echo "  - 复制 package.json 和 lockfile"
cp ../package.json ../pnpm-lock.yaml ./

echo "  - 复制 node_modules (~500MB, 可能需要几分钟)"
cp -r ../node_modules ./

echo "  - 复制 Dockerfile"
cp ../Dockerfile.offline ./Dockerfile

# 打包
cd ..
echo -e "${BLUE}🗜️  压缩打包（这可能需要几分钟）...${NC}"
tar -czf "${PACKAGE_NAME}" -C offline-build-temp .

# 清理临时目录
rm -rf offline-build-temp

# 5. 显示结果
FILE_SIZE=$(du -h "${PACKAGE_NAME}" | cut -f1)
echo ""
echo -e "${GREEN}✨ 离线构建包准备完成！${NC}"
echo ""
echo "📦 包名称: ${PACKAGE_NAME}"
echo "📊 文件大小: ${FILE_SIZE}"
echo ""
echo "📝 接下来的步骤："
echo "  1. 将 ${PACKAGE_NAME} 传输到内网服务器"
echo "     scp ${PACKAGE_NAME} user@internal-server:/tmp/"
echo ""
echo "  2. 在内网服务器上解压并构建"
echo "     mkdir -p deer-flow-web && cd deer-flow-web"
echo "     tar -xzf /tmp/${PACKAGE_NAME}"
echo "     # 复制项目源代码（排除 node_modules）"
echo "     rsync -av --exclude='node_modules' /path/to/source/ ./"
echo "     docker build -t deer-flow-web:offline --build-arg NEXT_PUBLIC_API_URL=http://your-api:8000 ."
echo ""
echo -e "${GREEN}🎉 完成！${NC}"
