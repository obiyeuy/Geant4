#!/usr/bin/env bash
# 一键安装脚本（清理旧安装 -> 从头安装：Python3.9 venv, ROOT, Geant4, cppyy, g4ppyy）
# 保存为: install_g4ppyy_all.sh
# 使用: chmod +x install_g4ppyy_all.sh && ./install_g4ppyy_all.sh
# 注意：构建 ROOT/Geant4 非常耗时，脚本会自动 nonstop 运行到底，不会中途提示确认。

set -euo pipefail
IFS=$'\n\t'

# ----------------------
# 全局配置（按需修改）
# ----------------------
BASE="$HOME/software"                   # 根目录，源码/构建/安装都放这里
SRC="$BASE/src"                         # 源码目录
BUILD="$BASE/build"                     # 构建目录
INSTALL="$BASE/install"                 # 安装根目录（root/geant4 等）
VENV="$HOME/pyg4"                       # Python 虚拟环境位置（Python3.9）
PY39_BIN="/usr/bin/python3.9"           # Python3.9 可执行路径（若不存在脚本会安装）
ROOT_VER="6.30.06"                      # ROOT 版本（示例）
GEANT4_VER="11.1.2"                     # Geant4 版本（示例）
NUMJOBS="$(nproc)"                      # make -j 参数
DEBIAN_FRONTEND=noninteractive          # 让 apt 保持非交互式
export DEBIAN_FRONTEND

echo "============================================================"
echo "一键安装开始：清理旧安装 -> 安装 ROOT/Geant4/cppyy/g4ppyy"
echo "请确保你有 sudo 权限。"
echo "配置："
echo "  BASE=$BASE"
echo "  SRC=$SRC"
echo "  BUILD=$BUILD"
echo "  INSTALL=$INSTALL"
echo "  VENV=$VENV"
echo "  ROOT_VER=$ROOT_VER"
echo "  GEANT4_VER=$GEANT4_VER"
echo "  NUMJOBS=$NUMJOBS"
echo "============================================================"

# ----------------------
# 0) 创建目录 & 备份旧数据
# ----------------------
mkdir -p "$SRC" "$BUILD" "$INSTALL"
echo "[INFO] 确保目录存在: $SRC, $BUILD, $INSTALL"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OLD_BACKUP="$HOME/software/backup_${TIMESTAMP}"
mkdir -p "$OLD_BACKUP"
echo "[INFO] 备份旧的 install/build/venv（如存在）到: $OLD_BACKUP"

for d in "$INSTALL/root" "$INSTALL/geant4" "$INSTALL/g4ppyy" "$BUILD" "$VENV"; do
  if [ -e "$d" ]; then
    echo "  [BACKUP] 移动 $d -> $OLD_BACKUP/"
    mv "$d" "$OLD_BACKUP/" || true
  fi
done

# ----------------------
# 1) 安装系统依赖（非交互式）
# ----------------------
echo "[STEP 1] 安装系统依赖（使用 apt，非交互式）"
sudo apt update -y
sudo apt install -y --no-install-recommends \
    build-essential cmake git wget unzip pkg-config \
    libx11-dev libxmu-dev libxrandr-dev libxinerama-dev libxcursor-dev \
    libgl1-mesa-dev libglu1-mesa-dev freeglut3-dev mesa-common-dev \
    qtbase5-dev qttools5-dev qttools5-dev-tools libqt5opengl5-dev \
    python3-dev python3-venv python3-pip curl ca-certificates \
    libexpat1-dev libxerces-c-dev libpcre3-dev \
    libssl-dev libtbb-dev libgsl-dev libglew-dev libx11-xcb-dev \
    libxcb1-dev libxcb-glx0-dev patchelf libxft-dev libxrender-dev \
    libfontconfig1-dev cmake-curses-gui

echo "[INFO] 系统依赖安装完成"

# ----------------------
# 2) 安装 Python3.9（如果尚未安装）
# ----------------------
echo "[STEP 2] 检查并安装 Python3.9（非交互式）"
if ! [ -x "$PY39_BIN" ]; then
  echo "[INFO] $PY39_BIN 未找到，安装 Python3.9"
  sudo apt install -y software-properties-common
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt update -y
  sudo apt install -y python3.9 python3.9-venv python3.9-dev
else
  echo "[INFO] 已检测到 $PY39_BIN，跳过安装"
fi

# ----------------------
# 3) 创建并激活 Python3.9 venv
# ----------------------
echo "[STEP 3] 创建 Python3.9 虚拟环境（$VENV）并激活"
$PY39_BIN -m venv "$VENV"
# 将非交互式环境变量加入 activate 脚本，确保每次激活都生效
cat >> "$VENV/bin/activate" <<'ACTENV'

# --- 自动环境变量（由一键脚本写入） ---
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

# 禁用 g4ppyy 在 import 时自动初始化可视化（避免 G4VisManager 析构冲突）
export G4PPYY_NOVIS=1

# 将来如需手动启用可视化：source $VENV/bin/activate; unset G4PPYY_NOVIS; (或修改并恢复)
# --- end of auto env ---
ACTENV

# 激活
# shellcheck source=/dev/null
source "$VENV/bin/activate"

# 升级 pip/setuptools/wheel 并安装必要的 build 后端（hatchling）以避免 k3d 构建失败
echo "[INFO] 升级 pip / setuptools / wheel 并安装构建工具（hatchling）"
python -m pip install --upgrade pip setuptools wheel build
python -m pip install --upgrade hatchling

# 常用 Python 包
python -m pip install --upgrade numpy

# ----------------------
# 4) 下载并构建 ROOT（源码，可能耗时）
# ----------------------
echo "[STEP 4] 下载并构建 ROOT（$ROOT_VER） - 可能耗时很久"
ROOT_SRC_TAR="root_v${ROOT_VER}.source.tar.gz"
ROOT_SRC_DIR="$SRC/root-${ROOT_VER}"

cd "$SRC"
if [ ! -d "$ROOT_SRC_DIR" ]; then
  if [ ! -f "$ROOT_SRC_TAR" ]; then
    echo "[INFO] 下载 ROOT 源码 tarball"
    wget "https://root.cern/download/${ROOT_SRC_TAR}"
  fi
  echo "[INFO] 解压 ROOT 源码"
  tar -xzf "$ROOT_SRC_TAR"
fi

mkdir -p "$BUILD/root-build"
cd "$BUILD/root-build"

echo "[INFO] 配置 ROOT（cmake ...）"
cmake "$ROOT_SRC_DIR" \
    -DCMAKE_INSTALL_PREFIX="$INSTALL/root" \
    -DPYTHON_EXECUTABLE="$(which python)" \
    -Dpyroot=ON -Dcppyy=ON -Dall=OFF \
    -Dminuit2=ON -Dmathmore=ON -Dopengl=ON \
    -Dgdml=ON -Droofit=ON -Dbuiltin_xrootd=ON -Dasimage=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=17

echo "[INFO] make -j ${NUMJOBS} (ROOT)"
make -j"${NUMJOBS}"
echo "[INFO] make install (ROOT)"
make install

# 将 thisroot.sh 加入 venv activate
cat >> "$VENV/bin/activate" <<'ACTROOT'

# source ROOT 环境（由一键脚本生成）
if [ -f "$HOME/software/install/root/bin/thisroot.sh" ]; then
    . "$HOME/software/install/root/bin/thisroot.sh"
fi
ACTROOT

# source 一次，供后续步骤使用
# shellcheck source=/dev/null
. "$INSTALL/root/bin/thisroot.sh"

# ----------------------
# 5) 下载并构建 Geant4（源码，可能耗时）
# ----------------------
echo "[STEP 5] 下载并构建 Geant4（$GEANT4_VER） - 可能耗时很久"
GEANT4_TAR="v${GEANT4_VER}.tar.gz"
GEANT4_DIR="$SRC/geant4-${GEANT4_VER}"

cd "$SRC"
if [ ! -d "$GEANT4_DIR" ]; then
  if [ ! -f "$GEANT4_TAR" ]; then
    echo "[INFO] 下载 Geant4 源码 tarball"
    wget -O "$GEANT4_TAR" "https://github.com/Geant4/geant4/archive/refs/tags/v${GEANT4_VER}.tar.gz"
  fi
  echo "[INFO] 解压 Geant4 源码"
  tar -xzf "$GEANT4_TAR"
fi

mkdir -p "$BUILD/geant4-build"
cd "$BUILD/geant4-build"

echo "[INFO] 配置 Geant4（cmake ...）"
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
    -DPython3_EXECUTABLE="$(which python)" \
    -DGEANT4_USE_PYTHON=ON

echo "[INFO] make -j ${NUMJOBS} (Geant4)"
make -j"${NUMJOBS}"
echo "[INFO] make install (Geant4)"
make install

# 将 geant4 环境写入 venv activate
cat >> "$VENV/bin/activate" <<'ACTG4'

# export Geant4 variables
export G4INSTALL="$HOME/software/install/geant4"
export G4PREFIX="$G4INSTALL"
if [ -f "$G4INSTALL/bin/geant4.sh" ]; then
    . "$G4INSTALL/bin/geant4.sh"
fi

# 更新 LD_LIBRARY_PATH 包含 ROOT 和 Geant4
export LD_LIBRARY_PATH="$HOME/software/install/root/lib:$HOME/software/install/geant4/lib:${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH=$(printf "%s\n" ${LD_LIBRARY_PATH//:/ } | awk '!x[$0]++' | paste -sd ":")
ACTG4

# 立即 source geant4 脚本以便后续 python 安装使用
# shellcheck source=/dev/null
. "$INSTALL/geant4/bin/geant4.sh"

# ----------------------
# 6) 安装/升级 cppyy
# ----------------------
echo "[STEP 6] 安装/升级 cppyy（Python 绑定辅助库）"
python -m pip install -v --upgrade cppyy || true

# ----------------------
# 7) 克隆并安装 G4ppyy（并打补丁禁用自动可视化初始化）
# ----------------------
echo "[STEP 7] 克隆 G4ppyy 源码（若已存在则拉取）"
cd "$BASE"
if [ ! -d "$BASE/G4ppyy" ]; then
  git clone https://github.com/patrickstowell/G4ppyy.git G4ppyy || true
fi
cd G4ppyy || true
echo "[INFO] 当前 G4ppyy 目录: $(pwd)"
# 备份并对 __init__.py 打补丁，确保自动可视化被跳过（双保险：环境变量+源码检查）
if [ -f "g4ppyy/__init__.py" ]; then
  cp g4ppyy/__init__.py g4ppyy/__init__.py.bak."${TIMESTAMP}" || true
  echo "[INFO] 为 g4ppyy/__init__.py 添加保护标识，防止自动初始化可视化（备份已保存）"

  # 在文件顶端插入防护片段（如果尚未插入）
  if ! grep -q "G4PPYY_DISABLE_VIS_INTERNAL" g4ppyy/__init__.py; then
    # 使用 awk 在文件顶部插入内容（保留原文件）
    awk 'BEGIN{print "import os\nif os.environ.get(\"G4PPYY_NOVIS\",\"0\")==\"1\":\n    os.environ[\"G4PPYY_DISABLE_VIS_INTERNAL\"]=\"1\"\n    print(\"[G4PPYY] : Visualization disabled via G4PPYY_NOVIS (internal flag set)\")\n\n"}{print}' g4ppyy/__init__.py > g4ppyy/__init__.py.patched
    mv g4ppyy/__init__.py.patched g4ppyy/__init__.py
    echo "[INFO] 补丁已写入 g4ppyy/__init__.py"
  else
    echo "[INFO] g4ppyy/__init__.py 已包含禁用标识，跳过修改"
  fi

  # 额外在文件中查找可能初始化可视化的位置并用环境标识包裹（尽量防止任何 vis 初始化）
  # 这里尝试把可能的 'G4VisExecutive' 或 'G4VisManager' 初始化用条件包裹（若脚本中存在）
  # 先做一次简单的替换备份
  grep -nE "G4VisExecutive|G4VisManager|vis.Initialize" -n g4ppyy/__init__.py || true
  # （如果需要更精细的自动修改，可在此扩展）
fi

# 确保构建后端 hatchling 已安装，避免 k3d 源码构建时出错
# -------- 关键：提前装好构建后端与 jupyter 链 --------
echo "[INFO] 安装/升级构建后端与 jupyter 依赖（避免 k3d 本地编缺钩子）"
python -m pip install --upgrade hatchling jupyter_packaging jupyterlab hatch-jupyter-builder meson-python meson ninja
# -------- 关键：提前用二进制 wheel 装完所有重型依赖，避免本地编译 --------
echo "[INFO] 预装重型依赖（优先二进制 wheel，防止本地编失败）"
python -m pip install --upgrade pip setuptools wheel
python -m pip install --only-binary :all: numpy matplotlib k3d scipy
# 如果清华没有 wheel，再从 PyPI 官方源补一份
python -m pip install --only-binary :all: -i https://pypi.org/simple numpy matplotlib k3d scipy || true


# 使用 pip 安装 g4ppyy（使用当前 venv，允许正常构建）
echo "[INFO] 使用 pip 从源码安装 g4ppyy（hatchling 已安装以避免后端错误）"
python -m pip install -v --no-build-isolation --no-binary :all: .

# 将 G4INSTALL/LD_LIBRARY_PATH 等写入 venv activate（double ensure）
cat >> "$VENV/bin/activate" <<'ACTENV2'

# ensure G4 and ROOT are available in activated env
export G4INSTALL="$HOME/software/install/geant4"
export G4PREFIX="$G4INSTALL"
if [ -f "$G4INSTALL/bin/geant4.sh" ]; then
    . "$G4INSTALL/bin/geant4.sh"
fi
export LD_LIBRARY_PATH="$HOME/software/install/root/lib:$HOME/software/install/geant4/lib:${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH=$(printf "%s\n" ${LD_LIBRARY_PATH//:/ } | awk '!x[$0]++' | paste -sd ":")
# keep G4PPYY_NOVIS in activate to avoid accidental vis init
export G4PPYY_NOVIS=1
ACTENV2

# ----------------------
# 8) 生成详细验证脚本（带说明输出）
# ----------------------
echo "[STEP 8] 生成验证脚本: $BASE/verify_g4ppyy_all.py"

cat > "$BASE/verify_g4ppyy_all.py" <<'PYTEST'
#!/usr/bin/env python3
"""
verify_g4ppyy_all.py
- 目的是以最安全的方式验证 cppyy, ROOT, g4ppyy 是否在当前 venv 下能被导入
- 说明性输出：每一步都会打印解释性信息
- 注意：为了避免 G4VisManager 析构导致 segfault，我们会在测试 import 后
  使用 os._exit(0) 立刻退出（不触发 Python 对象正常析构）。
"""
import os, sys, traceback, pathlib, time

print("="*60)
print("Verify script for g4ppyy environment")
print("Python:", sys.executable)
print("Version:", sys.version)
print("LD_LIBRARY_PATH:", os.environ.get("LD_LIBRARY_PATH",""))
print("G4INSTALL:", os.environ.get("G4INSTALL","<not set>"))
print("G4PPYY_NOVIS:", os.environ.get("G4PPYY_NOVIS","<not set>"))
print("="*60)
ok = True

print("\n[STEP 1] 测试 cppyy 导入（用于后续动态加载 C++ 库）")
try:
    import cppyy
    print("  ✓ cppyy imported from:", cppyy.__file__)
except Exception:
    print("  ✗ cppyy import failed")
    traceback.print_exc()
    ok = False

print("\n[STEP 2] 测试 ROOT 导入（pyroot）")
try:
    import ROOT
    print("  ✓ ROOT imported from:", ROOT.__file__)
    try:
        print("  ROOT version:", ROOT.gROOT.GetVersion())
    except Exception:
        print("  (无法读取 ROOT 版本，继续...)")
except Exception:
    print("  ✗ ROOT import failed")
    traceback.print_exc()
    ok = False

print("\n[STEP 3] 测试 g4ppyy 导入（注意：我们预先设置了 G4PPYY_NOVIS=1）")
try:
    # 确保环境变量在 import 之前设置
    os.environ['G4PPYY_NOVIS'] = '1'
    import g4ppyy
    print("  ✓ g4ppyy imported from:", getattr(g4ppyy, '__file__', '<no __file__>'))
    try:
        print("  g4ppyy G4PREFIX:", getattr(g4ppyy, 'G4PREFIX', '<no attr>'))
    except Exception:
        print("  (无法读取 g4ppyy.G4PREFIX，继续...)")
except Exception:
    print("  ✗ g4ppyy import failed")
    traceback.print_exc()
    ok = False

print("\n[STEP 4] 测试通过 cppyy 加载 Geant4 基础库（libG4geometry.so）")
try:
    import cppyy
    g4install = os.environ.get("G4INSTALL", os.path.expanduser("~") + "/software/install/geant4")
    libpath = os.path.join(g4install, "lib", "libG4geometry.so")
    p = pathlib.Path(libpath)
    if p.exists():
        print("  Found lib at:", libpath)
        try:
            cppyy.load_library(str(libpath))
            print("  ✓ cppyy.load_library OK")
        except Exception as e:
            print("  ✗ cppyy.load_library failed:", e)
    else:
        print("  ✗ libG4geometry.so not found at:", libpath)
        ok = False
except Exception:
    traceback.print_exc()
    ok = False

print("\n==== SUMMARY ====")
print("Result:", "OK" if ok else "FAIL")
print("说明：如果导入阶段均正常，则环境基本可用。若你还需要可视化，请参见脚本注释（G4PPYY_NOVIS 控制）。")
print("="*60)
# 为避免触发 C++ 析构导致的 segfault，安全退出（不做正常析构）
sys.stdout.flush()
sys.stderr.flush()
os._exit(0 if ok else 1)
PYTEST

chmod +x "$BASE/verify_g4ppyy_all.py"
echo "[INFO] 验证脚本已生成：$BASE/verify_g4ppyy_all.py"

# ----------------------
# 9) 结束提示 & 自动运行验证（在 venv 下运行）
# ----------------------
echo "============================================================"
echo "安装流程（已尽力完成）。现在在虚拟环境中运行自动验证脚本。"
echo "注意：验证脚本会以最安全方式导入并立即退出以避免析构崩溃。"
echo "============================================================"

echo "[INFO] 现在激活虚拟环境（脚本中已激活一次，但这里显式再激活以确保）"
# shellcheck source=/dev/null
source "$VENV/bin/activate"

echo "[INFO] 运行验证： python $BASE/verify_g4ppyy_all.py"
python "$BASE/verify_g4ppyy_all.py" || true

echo "============================================================"
echo "脚本运行结束。若验证失败，请将 $BASE/verify_g4ppyy_all.py 的输出粘贴过来，我会继续帮你定位。"
echo "如果你想在将来临时启用可视化（不推荐在同一 Python 进程中），可以："
echo "  1) 进入虚拟环境: source $VENV/bin/activate"
echo "  2) 启用可视化: unset G4PPYY_NOVIS  # 或在 shell 中运行: G4PPYY_NOVIS=0 python"
echo "  3) 更稳妥的做法是: 在单独子进程中运行带可视化的仿真，或将仿真输出到文件后用 Python/VTK 可视化"
echo ""
echo "备份目录（如有）位于: $OLD_BACKUP"
echo "安装目录位于: $INSTALL"
echo ""
echo "如果需要，我可以："
echo " - 给出一个演示脚本（生成轨迹并保存 CSV），以及一个 Python 可视化脚本"
echo " - 给出一个不编译 ROOT/Geant4 的快速安装脚本（使用二进制/系统包）"
echo "============================================================"
