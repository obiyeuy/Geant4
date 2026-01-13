#!/bin/bash
# 步进扫描脚本
# 功能：循环不同的ObjShift值，运行模拟并保存结果

# 扫描参数设置
START_Y=-20.0      # 起始位置 (mm)
END_Y=20.0         # 结束位置 (mm)
STEP=0.5          # 步长 (mm)
EVENTS=100000       # 每个位置的事件数（可根据需要修改）


# 可执行文件路径
EXECUTABLE="./CZT"

# 计数器
count=0

# 计算总位置数（使用awk避免依赖bc）
total_positions=$(awk "BEGIN {printf \"%.0f\", ($END_Y - $START_Y) / $STEP + 1}")

# 循环扫描
# 使用awk生成序列，避免依赖seq命令的浮点数支持
# 使用进程替换避免子shell问题，确保计数器正确
while read Y; do
    count=$((count + 1))
    echo ""
    echo "[$count/$total_positions] 正在扫描 Y = $Y mm"
    
    # 格式化Y值（确保一位小数）
    Y_STR=$(printf "%.1f" $Y)
    
    # 检查文件是否已存在（断点续传）
    if [ -f "output/LowEnergy/$Y_STR.txt" ] && \
       [ -f "output/HighEnergy/$Y_STR.txt" ] && \
       [ -f "output/Mydata/$Y_STR.root" ]; then
        echo "  跳过（文件已存在）"
        continue
    fi
  
    # 生成临时宏文件（使用唯一的文件名）
    cat > "scan_temp_$Y_STR.mac" << EOF
## Particle type, position, energy...
## Unit mm
/Xray/det/SetObjShift $Y_STR mm
/run/initialize

#
/run/verbose 1
#
/run/beamOn $EVENTS
EOF
    
    # 运行模拟
    echo "  运行模拟中..."
    $EXECUTABLE scan_temp_${Y_STR}.mac > scan_log_${Y_STR}.log 
    
    # 检查输出文件是否生成
    if [ -f "output/LowEnergy/$Y_STR.txt" ] && \
       [ -f "output/HighEnergy/$Y_STR.txt" ] && \
       [ -f "output/Mydata/$Y_STR.root" ]; then
        echo "  ✓ 完成 Y = $Y mm"
        # 删除日志文件（成功时）
        rm -f scan_log_${Y_STR}.log
    else
        echo "  ✗ 警告: Y = $Y mm 的输出文件可能不完整"
        echo "  请检查日志文件: scan_log_${Y_STR}.log"
    fi
    
    # 清理临时文件
    rm -f scan_temp_${Y_STR}.mac
done < <(awk -v start="$START_Y" -v end="$END_Y" -v step="$STEP" \
    'BEGIN {
        for (i = start; i <= end; i += step) {
            printf "%.1f\n", i
        }
    }')

echo ""
echo "=========================================="
echo "扫描完成！"
echo "总共扫描了 $count 个位置"
echo "=========================================="
