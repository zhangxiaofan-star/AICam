#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版刀具数据更新脚本
"""

import pandas as pd
import os
import shutil
from datetime import datetime

def update_tools_csv():
    """更新tools.csv文件，添加T014数据"""
    tools_file = "dataset/tools.csv"
    
    print("🔄 开始更新tools.csv文件...")
    
    # 备份原文件
    backup_file = f"dataset/tools_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    shutil.copy2(tools_file, backup_file)
    print(f"📁 原文件已备份到: {backup_file}")
    
    try:
        # 读取现有数据
        df = pd.read_csv(tools_file, encoding='utf-8')
        print(f"📊 当前数据行数: {len(df)}")
        
        # 检查T014是否已存在
        if 'T014' in df['刀具id'].values:
            print("⚠️  T014已存在，将更新数据")
            df.loc[df['刀具id'] == 'T014', ['刀具名称', '直径', 'R角', '刃数', '伸出长']] = [
                'B0.5R0.25', 0.5, 0.25, 1, 10
            ]
        else:
            # 添加T014数据
            new_row = {
                '刀具id': 'T014',
                '刀具名称': 'B0.5R0.25',
                '直径': 0.5,
                'R角': 0.25,
                '刃数': 1,
                '伸出长': 10
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            print("✅ T014数据添加成功")
        
        # 保存更新后的数据
        df.to_csv(tools_file, index=False, encoding='utf-8')
        print(f"💾 文件保存成功，共 {len(df)} 条记录")
        
        # 显示更新后的数据
        print("\n📋 更新后的刀具数据:")
        print(df.to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        # 恢复备份
        shutil.copy2(backup_file, tools_file)
        print("🔄 已恢复原文件")
        return False

def replace_with_new_csv(new_csv_path, target_type="tools"):
    """使用新的CSV文件替换现有文件"""
    if not os.path.exists(new_csv_path):
        print(f"❌ 新CSV文件不存在: {new_csv_path}")
        return False
    
    if target_type == "tools":
        target_file = "dataset/tools.csv"
    elif target_type == "processes":
        target_file = "dataset/processes.csv"
    else:
        print(f"❌ 不支持的文件类型: {target_type}")
        return False
    
    print(f"🔄 开始替换 {target_file}...")
    
    # 备份原文件
    backup_file = f"{target_file.replace('.csv', '')}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if os.path.exists(target_file):
        shutil.copy2(target_file, backup_file)
        print(f"📁 原文件已备份到: {backup_file}")
    
    try:
        # 验证新文件格式
        new_df = pd.read_csv(new_csv_path, encoding='utf-8')
        
        if target_type == "tools":
            required_columns = ['刀具id', '刀具名称', '直径', 'R角', '刃数', '伸出长']
        else:  # processes
            required_columns = ['特征id', '特征名称', '特征类型', '工艺类型', '刀具id', '主轴转速', '进给速度', '切削深度']
        
        # 检查列名
        missing_cols = [col for col in required_columns if col not in new_df.columns]
        if missing_cols:
            print(f"❌ 新CSV文件缺少必要列: {missing_cols}")
            return False
        
        # 复制文件
        shutil.copy2(new_csv_path, target_file)
        print(f"✅ 文件替换成功: {target_file}")
        print(f"📊 新数据包含 {len(new_df)} 条记录")
        
        # 显示新数据
        print(f"\n📋 新的{target_type}数据:")
        print(new_df.to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"❌ 替换失败: {e}")
        return False

def main():
    """主函数"""
    print("🛠️  CSV数据更新工具")
    print("=" * 50)
    
    import sys
    
    if len(sys.argv) > 1:
        # 使用新CSV文件替换
        new_csv_path = sys.argv[1]
        csv_type = sys.argv[2] if len(sys.argv) > 2 else "tools"
        
        print(f"📁 使用新CSV文件: {new_csv_path}")
        print(f"📋 文件类型: {csv_type}")
        
        success = replace_with_new_csv(new_csv_path, csv_type)
    else:
        # 默认添加T014数据
        print("📝 添加T014刀具数据")
        success = update_tools_csv()
    
    if success:
        print("\n✅ 数据更新成功！")
        print("💡 提示: 如需更新知识图谱，请运行 csv_to_neo4j.py")
    else:
        print("\n❌ 数据更新失败！")

if __name__ == "__main__":
    main()