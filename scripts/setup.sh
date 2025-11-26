#!/bin/bash

# SQLite 数据目录初始化脚本
# 用法: ./scripts/setup.sh

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 数据库目录配置
DATA_DIR="./data"
DB_FILE="${DATA_DIR}/flow_test.db"

echo -e "${YELLOW}===== SQLite 数据目录初始化开始 =====${NC}"
echo -e "数据目录: ${DATA_DIR}"
echo -e "数据库文件: ${DB_FILE}"
echo -e "${YELLOW}=====================================${NC}"

# 创建数据目录
echo -e "${GREEN}1. 创建数据目录...${NC}"
if [ ! -d "${DATA_DIR}" ]; then
    mkdir -p "${DATA_DIR}"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 数据目录创建成功${NC}"
    else
        echo -e "${RED}✗ 数据目录创建失败${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ 数据目录已存在${NC}"
fi

# 检查数据库文件
echo -e "${GREEN}2. 检查数据库文件...${NC}"
if [ -f "${DB_FILE}" ]; then
    echo -e "${GREEN}✓ 数据库文件已存在${NC}"
    ls -lh "${DB_FILE}"
else
    echo -e "${GREEN}✓ 数据库文件将在首次运行时自动创建${NC}"
fi

# 设置权限
echo -e "${GREEN}3. 设置目录权限...${NC}"
chmod 755 "${DATA_DIR}"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 权限设置成功${NC}"
else
    echo -e "${RED}✗ 权限设置失败${NC}"
    exit 1
fi

echo -e "${YELLOW}===== SQLite 初始化完成 =====${NC}"
echo -e "${GREEN}✓ 数据目录已准备就绪！${NC}"
echo -e ""
echo -e "${YELLOW}说明:${NC}"
echo -e "  - SQLite 数据库无需手动初始化"
echo -e "  - 数据库文件将在首次运行时自动创建"
echo -e "  - 表结构将由 GORM 自动迁移创建"
echo -e ""
echo -e "${GREEN}您可以运行: go run cmd/api/main.go${NC}"
