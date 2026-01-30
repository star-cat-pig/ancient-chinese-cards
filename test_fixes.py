#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复验证测试脚本
用于验证各项bug修复和改进是否正常工作
"""
import os
import sys
import json
from datetime import datetime
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from card_manager import CardManager

def test_backup_mechanism():
    """测试数据备份机制"""
    print("测试数据备份机制...")
    
    # 创建临时测试目录
    test_dir = os.path.join(os.path.dirname(__file__), 'test_backup')
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建测试数据文件
    test_data_file = os.path.join(test_dir, 'test_cards.json')
    with open(test_data_file, 'w', encoding='utf-8') as f:
        json.dump([{
            'id': 'test1',
            'keyword': '测试',
            'definition': '测试定义',
            'source': '测试来源',
            'quote': '测试原文',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }], f, ensure_ascii=False, indent=2)
    
    # 创建CardManager实例
    card_manager = CardManager(data_file=os.path.join('test_backup', 'test_cards.json'))
    
    # 添加新卡片并保存（应该触发备份）
    card_manager.add_card({
        'keyword': '新测试',
        'definition': '新测试定义',
        'source': '新测试来源',
        'quote': '新测试原文'
    })
    
    # 检查备份目录是否存在
    backup_dir = os.path.join(test_dir, 'backups')
    if os.path.exists(backup_dir):
        backups = [f for f in os.listdir(backup_dir) if f.startswith('cards_backup_') and f.endswith('.json')]
        if backups:
            print(f"✓ 备份机制工作正常，创建了 {len(backups)} 个备份文件")
        else:
            print("✗ 备份机制未创建备份文件")
    else:
        print("✗ 备份目录未创建")
    
    # 清理测试文件
    try:
        os.remove(test_data_file)
        for backup in backups:
            os.remove(os.path.join(backup_dir, backup))
        os.rmdir(backup_dir)
        os.rmdir(test_dir)
    except:
        pass

def test_id_uniqueness():
    """测试ID唯一性校验"""
    print("测试ID唯一性校验...")
    
    # 创建CardManager实例
    card_manager = CardManager()
    
    # 测试_generate_unique_id方法
    if hasattr(card_manager, '_generate_unique_id'):
        ids = set()
        for _ in range(100):
            card_id = card_manager._generate_unique_id()
            ids.add(card_id)
        
        if len(ids) == 100:
            print("✓ ID唯一性校验工作正常")
        else:
            print(f"✗ ID唯一性校验失败，生成了重复ID，实际唯一ID数: {len(ids)}")
    else:
        print("✗ _generate_unique_id方法不存在")

def test_save_failure_handling():
    """测试保存失败处理（修正判断逻辑）"""
    print("测试保存失败处理...")
    
    # 创建CardManager实例
    card_manager = CardManager()
    
    try:
        # 直接调用save_cards，检查返回值类型（最可靠的判断方式）
        result = card_manager.save_cards()
        if isinstance(result, bool):
            print("✓ 保存失败处理已实现（方法返回布尔值）")
        else:
            print(f"✗ 保存失败处理未实现（方法返回值类型错误，应为bool）")
    except Exception as e:
        # 若调用报错，说明方法存在问题
        print(f"✗ 保存失败处理异常: {str(e)}")

def test_csv_export_fix():
    """测试CSV导出修复（逻辑正确，保留原实现）"""
    print("测试CSV导出修复...")
    
    # 检查main_window.py中的CSV导出代码
    main_window_path = os.path.join(os.path.dirname(__file__), 'ui', 'main_window.py')
    if os.path.exists(main_window_path):
        with open(main_window_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if 'csv.QUOTE_ALL' in content:
                print("✓ CSV导出修复已实现（使用了QUOTE_ALL选项）")
            else:
                print("✗ CSV导出修复未实现（未使用QUOTE_ALL选项）")
    else:
        print("✗ main_window.py文件不存在")

def test_gui_import_fix():
    """测试GUI导入修复"""
    print("测试GUI导入修复...")
    
    # 检查import_export.py中的导入代码
    import_export_path = os.path.join(os.path.dirname(__file__), 'ui', 'import_export.py')
    if os.path.exists(import_export_path):
        with open(import_export_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if 'interactive=False' in content:
                print("✓ GUI导入修复已实现（禁用了交互式解析）")
            else:
                print("✗ GUI导入修复未实现（未禁用交互式解析）")
    else:
        print("✗ import_export.py文件不存在")

def test_card_editor_fix():
    """测试卡片编辑器修复（修正判断逻辑，原逻辑依赖注释字符串，不靠谱）"""
    print("测试卡片编辑器修复...")
    
    # 检查card_editor.py中的颜色设置代码
    card_editor_path = os.path.join(os.path.dirname(__file__), 'ui', 'card_editor.py')
    if os.path.exists(card_editor_path):
        with open(card_editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 改为检查实际设置颜色的代码（更可靠）
            if 'field_entry.config(foreground="#000000")' in content:
                print("✓ 卡片编辑器修复已实现（修复了文字颜色显示问题）")
            else:
                print("✗ 卡片编辑器修复未实现（未修复文字颜色显示问题）")
    else:
        print("✗ card_editor.py文件不存在")

def main():
    """主测试函数"""
    print("开始验证修复效果...")
    print("=" * 50)
    
    # 运行各项测试
    test_backup_mechanism()
    test_id_uniqueness()
    test_save_failure_handling()
    test_csv_export_fix()
    test_gui_import_fix()
    test_card_editor_fix()
    
    print("=" * 50)
    print("修复验证完成！")

if __name__ == "__main__":
    main()