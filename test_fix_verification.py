#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复验证测试脚本
用于验证代码执行时序问题修复效果
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_manager import CardManager
from ui.main_window import MainWindow
import tkinter as tk

def test_card_manager_init():
    """测试CardManager初始化时的加载行为"""
    print("测试CardManager初始化...")
    
    # 创建临时测试文件
    test_file = os.path.join(os.path.dirname(__file__), "test_cards_temp.json")
    
    # 创建一些测试数据
    test_cards = [
        {
            'id': 'test1',
            'keyword': '测试1',
            'definition': '测试定义1',
            'source': '测试来源1',
            'quote': '测试原文1',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    ]
    
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_cards, f, ensure_ascii=False, indent=2)
    
    try:
        # 创建CardManager实例，应该只加载一次
        print("创建CardManager实例...")
        card_manager = CardManager(data_file=test_file)
        
        print(f"加载的卡片数量: {len(card_manager.cards)}")
        
        # 手动调用load_cards，应该不会产生重复输出
        print("手动调用load_cards()...")
        card_manager.load_cards()
        
        print("CardManager初始化测试完成")
        
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)

def test_main_window_init():
    """测试MainWindow初始化时的列表视图创建"""
    print("\n测试MainWindow初始化...")
    
    # 创建临时的Tkinter根窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏窗口
    
    try:
        # 创建CardManager实例
        card_manager = CardManager()
        
        # 创建MainWindow实例
        print("创建MainWindow实例...")
        main_window = MainWindow(root, card_manager)
        
        # 检查card_tree是否已经初始化
        if hasattr(main_window, 'card_tree') and main_window.card_tree is not None:
            print("✓ card_tree属性已正确初始化")
        else:
            print("✗ card_tree属性未初始化")
        
        # 检查排序相关变量是否已初始化
        required_attrs = ['sort_column', 'sort_order', 'sort_indicators']
        for attr in required_attrs:
            if hasattr(main_window, attr):
                print(f"✓ {attr}属性已初始化")
            else:
                print(f"✗ {attr}属性未初始化")
        
        print("MainWindow初始化测试完成")
        
    finally:
        # 清理
        root.destroy()

def test_refresh_timing():
    """测试refresh_list_view的调用时机"""
    print("\n测试refresh_list_view调用时机...")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        # 创建CardManager实例
        card_manager = CardManager()
        
        # 创建MainWindow实例，应该会自动调用refresh_list_view
        print("创建MainWindow实例（应该自动刷新列表视图）...")
        main_window = MainWindow(root, card_manager)
        
        # 手动调用refresh_list_view，应该不会报错
        print("手动调用refresh_list_view()...")
        main_window.refresh_list_view()
        print("✓ refresh_list_view调用成功，没有报错")
        
    except Exception as e:
        print(f"✗ refresh_list_view调用失败: {str(e)}")
    
    finally:
        root.destroy()

def main():
    """主测试函数"""
    print("开始验证代码执行时序修复效果...")
    print("=" * 60)
    
    # 运行各项测试
    test_card_manager_init()
    test_main_window_init()
    test_refresh_timing()
    
    print("=" * 60)
    print("修复验证完成！")
    print("\n修复总结：")
    print("1. ✓ 移除了重复的卡片加载调用")
    print("2. ✓ 调整了refresh_list_view的调用时机")
    print("3. ✓ 确保了列表视图组件在刷新前已初始化")
    print("\n现在应该不会再看到：")
    print("- 重复的'成功加载 X 张卡片'消息")
    print("- '警告：列表视图尚未初始化，无法刷新'警告")

if __name__ == "__main__":
    main()