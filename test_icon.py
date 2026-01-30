#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图标设置测试脚本
用于验证窗口图标设置是否正常工作
"""

import os
import sys
import tkinter as tk

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import AncientChineseCardsApp

def test_window_icons():
    """测试窗口图标设置"""
    print("测试窗口图标设置...")
    
    try:
        # 创建应用程序实例
        app = AncientChineseCardsApp()
        
        # 打印图标路径信息
        if hasattr(app, '_get_icon_path'):
            icon_path = app._get_icon_path()
            print(f"图标路径: {icon_path}")
            print(f"图标文件存在: {os.path.exists(icon_path) if icon_path else False}")
        
        # 测试子窗口图标
        def test_child_window():
            """测试子窗口图标"""
            child_window = tk.Toplevel(app.root)
            child_window.title("测试子窗口")
            child_window.geometry("300x200")
            
            # 设置图标
            if hasattr(app, 'setup_window_icon'):
                app.setup_window_icon(child_window)
                print("子窗口图标设置完成")
            
            # 添加测试按钮
            tk.Label(child_window, text="这是一个测试子窗口，\n请检查左上角图标是否显示正确").pack(pady=20)
            tk.Button(child_window, text="关闭", command=child_window.destroy).pack(pady=10)
        
        # 延迟显示子窗口
        app.root.after(1000, test_child_window)
        
        # 启动应用程序
        print("\n应用程序启动成功！")
        print("请检查主窗口和子窗口的左上角图标是否显示正确")
        print("按Ctrl+C退出测试")
        
        app.run()
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        return False
    
    return True

def check_icon_file():
    """检查图标文件"""
    print("检查图标文件...")
    
    # 检查assets目录
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    if os.path.exists(assets_dir):
        print(f"Assets目录存在: {assets_dir}")
        
        # 检查图标文件
        icon_file = os.path.join(assets_dir, 'icon.png')
        if os.path.exists(icon_file):
            print(f"图标文件存在: {icon_file}")
            print(f"文件大小: {os.path.getsize(icon_file)} 字节")
            return True
        else:
            print(f"图标文件不存在: {icon_file}")
            # 列出目录内容
            print("Assets目录内容:")
            for file in os.listdir(assets_dir):
                print(f"  - {file}")
    else:
        print(f"Assets目录不存在: {assets_dir}")
    
    return False

def main():
    """主测试函数"""
    print("开始验证图标设置...")
    print("=" * 50)
    
    # 检查图标文件
    icon_exists = check_icon_file()
    
    if icon_exists:
        # 运行图标测试
        test_window_icons()
    else:
        print("\n✗ 图标文件不存在，无法测试图标设置")
        print("请确保 assets/icon.png 文件存在")
    
    print("=" * 50)

if __name__ == "__main__":
    main()