#!/bin/bash
# 安装依赖到指定目录

TARGET_DIR="/opt/maxkb/python-packages"

# 创建目录
mkdir -p $TARGET_DIR

# 安装依赖到指定目录
pip install pulumi pulumi-aws boto3 --target=$TARGET_DIR --upgrade

echo "依赖已安装到: $TARGET_DIR"
echo ""
echo "使用时需要在 Python 代码中添加以下路径:"
echo "import sys"
echo "sys.path.insert(0, '/opt/maxkb/python-packages')"
