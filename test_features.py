#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复后的测试脚本
"""

import os
import json

def test_settings_file():
    """测试设置文件结构"""
    print("=== 测试设置文件 ===")
    
    # 获取用户数据目录
    user_data_dir = os.path.expanduser("~/.chinese_flashcards")
    preferences_file = os.path.join(user_data_dir, 'user_preferences.json')
    
    if os.path.exists(preferences_file):
        print(f"设置文件存在: {preferences_file}")
        with open(preferences_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        print(f"设置文件内容: {json.dumps(settings, indent=2, ensure_ascii=False)}")
        
        # 检查是否包含editor设置
        if 'editor' in settings:
            print(f"✓ editor设置存在: {settings['editor']}")
        else:
            print("✗ editor设置不存在")
            # 创建默认的editor设置
            settings['editor'] = {'auto_fill_source': True}
            with open(preferences_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            print("已添加默认editor设置")
    else:
        print(f"设置文件不存在: {preferences_file}")
        # 创建默认设置文件
        os.makedirs(user_data_dir, exist_ok=True)
        default_settings = {
            'editor': {'auto_fill_source': True},
            'data': {},
            'sort': {'column': None, 'order': 'asc', 'is_time_sort': True},
            'ui': {'theme': 'default', 'window_position': None, 'window_size': None}
        }
        with open(preferences_file, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, indent=2, ensure_ascii=False)
        print("已创建默认设置文件")

def main():
    """主函数"""
    test_settings_file()
    print("\n测试完成！")

if __name__ == "__main__":
    main()
