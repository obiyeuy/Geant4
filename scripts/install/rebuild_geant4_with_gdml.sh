#!/usr/bin/env bash
# 保存为: rebuild_restore_data_default.sh
# 作用：备份数据 -> 重装 Geant4 (开启 GDML, 不下载) -> 将数据恢复回默认安装目录

set -euo pipefail

# --- 基础配置 ---
BASE="$HOME/software"
GEANT4_VER="11.1.2"
SRC="$BASE/src/geant4-${GEANT4_VER}"
BUILD_DIR="$BASE/build/geant4-build"
INSTALL_DIR="$BASE/install/geant4"

# 这是数据备份的临时避难所
SAFE_BACKUP_DIR="$BASE/geant4_data_backup" 
NUMJOBS="$(nproc)"

echo "========================================================"
echo " 正在执行：Geant4 重装 (GDML=ON, 数据原位恢复模式)"
echo "========================================================"

# ----------------------------------------------------
# 1. 【核心步骤】备份数据
# ----------------------------------------------------
echo "[STEP 1] 正在备份现有的物理数据..."

mkdir -p "$SAFE_BACKUP_DIR"

# 尝试在旧安装路径找数据
# 注意：路径通常是 install/geant4/share/Geant4-11.1.2/data
OLD_DATA_PATH="$INSTALL_DIR/share/Geant4-${GEANT4_VER}/data"

# 如果找不到带版本号的，尝试找通用的 (防御性编程)
if [ ! -d "$OLD_DATA_PATH" ]; then
    OLD_DATA_PATH="$INSTALL_DIR/share/Geant4/data"
fi

# 检查备份目录里是否已经有数据（防止重复备份导致覆盖）
if [ "$(ls -A $SAFE_BACKUP_DIR)" ]; then
    echo "  ✓ 备份目录 ($SAFE_BACKUP_DIR) 已有数据，将使用现有备份。"
else
    # 开始从旧安装目录备份
    if [ -d "$OLD_DATA_PATH" ] && [ "$(ls -A $OLD_DATA_PATH)" ]; then
        echo "  [BACKUP] 发现旧安装数据，正在移动到备份目录..."
        # 这里用 mv (移动) 而不是 cp，因为旧目录马上要被重写了
        mv "$OLD_DATA_PATH"/* "$SAFE_BACKUP_DIR/"
        echo "  ✓ 数据已安全移至: $SAFE_BACKUP_DIR"
    else
        echo "  [WARN] 未在旧安装目录找到数据！"
        echo "  如果这是第一次运行此脚本，且备份目录也是空的，"
        echo "  那么稍后我们可能无法恢复数据（除非你选择重新下载）。"
        # 暂停让用户确认
        echo "  按 Ctrl+C 终止，或等待 3 秒继续..."
        sleep 3
    fi
fi

# ----------------------------------------------------
# 2. 清理环境
# ----------------------------------------------------
echo "[STEP 2] 清理构建环境..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# ----------------------------------------------------
# 3. 配置 CMake
# ----------------------------------------------------
echo "[STEP 3] 运行 CMake (开启 GDML, 禁止下载)..."
cd "$BUILD_DIR"

CMAKE_ARGS=(
    "$SRC"
    -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR"
    -DGEANT4_BUILD_MULTITHREADED=ON
    -DGEANT4_USE_QT=ON
    -DGEANT4_USE_OPENGL_X11=ON
    -DGEANT4_USE_SYSTEM_EXPAT=OFF
    -DGEANT4_BUILD_TLS_MODEL=global-dynamic
    -DCMAKE_CXX_STANDARD=17
    -DCMAKE_BUILD_TYPE=Release
    -DPython3_EXECUTABLE="$(which python)"
    -DGEANT4_USE_PYTHON=ON
    
    # === 开启 GDML ===
    -DGEANT4_USE_GDML=ON
)

# === 数据策略：不下载，也不指定外部路径 ===
# 我们让 CMake 以为数据会安装在默认位置，但我们要手动关掉下载
if [ -n "$SAFE_BACKUP_DIR" ] && [ "$(ls -A $SAFE_BACKUP_DIR)" ]; then
    echo "  [CONFIG] 检测到本地备份数据。配置 CMake 不下载数据。"
    CMAKE_ARGS+=( -DGEANT4_INSTALL_DATA=OFF )
else
    echo "  [CONFIG] 无备份数据！被迫开启下载 (DATA=ON)。"
    CMAKE_ARGS+=( -DGEANT4_INSTALL_DATA=ON )
fi

# 自动找 XercesC
if pkg-config --exists xerces-c; then
    CMAKE_ARGS+=( -DXercesC_ROOT="$(pkg-config --variable=prefix xerces-c)" )
fi

cmake "${CMAKE_ARGS[@]}"

# ----------------------------------------------------
# 4. 编译与安装
# ----------------------------------------------------
echo "[STEP 4] 开始编译 (-j${NUMJOBS})..."
make -j12

echo "[STEP 5] 安装..."
make install

# ----------------------------------------------------
# 5. 【核心步骤】恢复数据到默认位置
# ----------------------------------------------------
echo "[STEP 6] 将数据恢复回默认安装目录..."

# 计算默认安装位置: install/geant4/share/Geant4/data
TARGET_DATA_DIR="$INSTALL_DIR/share/Geant4/data"

# 如果目标目录不存在（因为我们关了下载，CMake 可能创建了空目录也可能没创建），手动创建
if [ ! -d "$TARGET_DATA_DIR" ]; then
    mkdir -p "$TARGET_DATA_DIR"
fi

if [ "$(ls -A $SAFE_BACKUP_DIR)" ]; then
    echo "  [RESTORE] 正在将数据从备份目录复制回: $TARGET_DATA_DIR"
    cp -r "$SAFE_BACKUP_DIR"/* "$TARGET_DATA_DIR/"
    echo "  ✓ 数据已归位。"
else
    echo "  [WARN] 备份目录为空，没有什么可以恢复的。"
fi

# ----------------------------------------------------
# 6. 修正 Python 环境
# ----------------------------------------------------
echo "[STEP 7] 更新环境配置..."
VENV="$HOME/pyg4"
if [ -d "$VENV" ]; then
    if ! grep -q "G4INSTALL" "$VENV/bin/activate"; then
        cat >> "$VENV/bin/activate" <<EOF
export G4INSTALL="$INSTALL_DIR"
export G4PREFIX="$INSTALL_DIR"
[ -f "\$G4INSTALL/bin/geant4.sh" ] && . "\$G4INSTALL/bin/geant4.sh"
EOF
    fi
fi

echo "========================================================"
echo "重装完成！"
echo "数据已位于标准路径: $TARGET_DATA_DIR"
echo "GDML 状态检查: $($INSTALL_DIR/bin/geant4-config --features | grep gdml)"
echo "========================================================"


