#!/usr/bin/env bash
# 重新编译 Geant4 并启用多线程支持
# 使用: chmod +x rebuild_geant4_multithread.sh && ./rebuild_geant4_multithread.sh
# 注意：此脚本会复用已有的源码和 ROOT 安装，只重新编译 Geant4

set -euo pipefail
IFS=$'\n\t'

# ----------------------
# 全局配置（与安装脚本保持一致）
# ----------------------
BASE="$HOME/software"
SRC="$BASE/src"
BUILD="$BASE/build"
INSTALL="$BASE/install"
GEANT4_VER="11.1.2"
NUMJOBS="$(nproc)"

echo "============================================================"
echo "重新编译 Geant4 并启用多线程支持"
echo "配置："
echo "  BASE=$BASE"
echo "  SRC=$SRC"
echo "  BUILD=$BUILD"
echo "  INSTALL=$INSTALL"
echo "  GEANT4_VER=$GEANT4_VER"
echo "  NUMJOBS=$NUMJOBS"
echo "============================================================"

# ----------------------
# 1) 检查并下载 Geant4 源码（如果不存在）
# ----------------------
GEANT4_TAR="v${GEANT4_VER}.tar.gz"
GEANT4_DIR="$SRC/geant4-${GEANT4_VER}"

cd "$SRC"
if [ ! -d "$GEANT4_DIR" ]; then
  echo "[INFO] Geant4 源码目录不存在，需要下载"
  if [ ! -f "$GEANT4_TAR" ]; then
    echo "[INFO] 下载 Geant4 源码 tarball"
    wget -O "$GEANT4_TAR" "https://github.com/Geant4/geant4/archive/refs/tags/v${GEANT4_VER}.tar.gz"
  fi
  echo "[INFO] 解压 Geant4 源码"
  tar -xzf "$GEANT4_TAR"
else
  echo "[INFO] Geant4 源码目录已存在: $GEANT4_DIR，跳过下载"
fi

# ----------------------
# 2) 备份旧的构建目录（可选，保留作为备份）
# ----------------------
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OLD_BUILD_BACKUP="$BUILD/geant4-build-backup-${TIMESTAMP}"

if [ -d "$BUILD/geant4-build" ]; then
  echo "[INFO] 备份旧的构建目录到: $OLD_BUILD_BACKUP"
  mv "$BUILD/geant4-build" "$OLD_BUILD_BACKUP" || true
  echo "[INFO] 备份完成，如需恢复可手动移动回来"
fi

# ----------------------
# 3) 创建新的构建目录并配置（启用多线程）
# ----------------------
mkdir -p "$BUILD/geant4-build"
cd "$BUILD/geant4-build"

echo "[INFO] 配置 Geant4（启用多线程支持）"
echo "[INFO] 关键变更: GEANT4_BUILD_MULTITHREADED=ON"

# 检查 Python 环境（如果使用虚拟环境）
PYTHON_EXEC="$(which python3)"
if [ -f "$HOME/pyg4/bin/activate" ]; then
  echo "[INFO] 检测到虚拟环境，使用虚拟环境中的 Python"
  # shellcheck source=/dev/null
  source "$HOME/pyg4/bin/activate"
  PYTHON_EXEC="$(which python)"
fi

# 配置 CMake，启用多线程
cmake "$GEANT4_DIR" \
    -DCMAKE_INSTALL_PREFIX="$INSTALL/geant4" \
    -DGEANT4_INSTALL_DATA=ON \
    -DGEANT4_BUILD_MULTITHREADED=ON \
    -DGEANT4_USE_QT=ON \
    -DGEANT4_USE_OPENGL_X11=ON \
    -DGEANT4_USE_SYSTEM_EXPAT=OFF \
    -DGEANT4_BUILD_TLS_MODEL=global-dynamic \
    -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_BUILD_TYPE=Release \
    -DPython3_EXECUTABLE="$PYTHON_EXEC" \
    -DGEANT4_USE_PYTHON=ON

# ----------------------
# 4) 编译和安装
# ----------------------
echo "[INFO] 开始编译 Geant4（使用 $NUMJOBS 个并行任务）"
echo "[INFO] 这可能需要较长时间，请耐心等待..."
make -j"${NUMJOBS}"

echo "[INFO] 安装 Geant4"
make install

# ----------------------
# 5) 验证多线程支持
# ----------------------
echo "[INFO] 验证多线程支持是否启用"
if [ -f "$INSTALL/geant4/bin/geant4-config" ]; then
  echo "[INFO] 检查 geant4-config 输出:"
  "$INSTALL/geant4/bin/geant4-config" --cflags | grep -i multithread && \
    echo "  ✓ 多线程标志已启用" || \
    echo "  ⚠ 未在编译标志中找到多线程标识（可能正常，取决于 Geant4 版本）"
fi

# 检查 CMakeCache.txt
if [ -f "$BUILD/geant4-build/CMakeCache.txt" ]; then
  MULTITHREAD_STATUS=$(grep "GEANT4_BUILD_MULTITHREADED:BOOL" "$BUILD/geant4-build/CMakeCache.txt" | cut -d'=' -f2)
  if [ "$MULTITHREAD_STATUS" = "ON" ]; then
    echo "  ✓ CMakeCache.txt 确认: GEANT4_BUILD_MULTITHREADED=ON"
  else
    echo "  ✗ 警告: CMakeCache.txt 显示 GEANT4_BUILD_MULTITHREADED=$MULTITHREAD_STATUS"
  fi
fi

# ----------------------
# 6) 更新环境变量（如果使用虚拟环境）
# ----------------------
if [ -f "$HOME/pyg4/bin/activate" ]; then
  echo "[INFO] 检测到虚拟环境，确保环境变量已更新"
  echo "[INFO] 请重新激活虚拟环境以使用新的 Geant4:"
  echo "      source $HOME/pyg4/bin/activate"
fi

# ----------------------
# 7) 完成提示
# ----------------------
echo "============================================================"
echo "Geant4 重新编译完成！"
echo ""
echo "重要提示："
echo "1. 如果使用虚拟环境，请重新激活: source \$HOME/pyg4/bin/activate"
echo "2. 需要重新编译您的应用程序（CZT）以链接新的 Geant4 库"
echo "3. 旧的构建目录已备份到: $OLD_BUILD_BACKUP"
echo ""
echo "下一步："
echo "  cd /home/yyb/workspace/XRay-all/XRay-detectionCode/code/build"
echo "  cmake .."
echo "  make"
echo "============================================================"

