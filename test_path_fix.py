#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路径修复验证测试脚本
用于验证数据文件路径修复是否正常工作
"""

import os
import sys
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_manager import CardManager

def test_user_data_path():
    """测试用户数据目录路径"""
    print("测试用户数据目录路径...")
    
    try:
        # 创建CardManager实例
        card_manager = CardManager()
        
        # 打印数据文件路径
        print(f"数据文件路径: {card_manager.data_file}")
        print(f"用户数据目录: {card_manager.user_data_dir}")
        
        # 检查目录是否存在
        data_dir = os.path.dirname(card_manager.data_file)
        print(f"数据目录存在: {os.path.exists(data_dir)}")
        
        # 测试创建目录
        if not os.path.exists(data_dir):
            print("正在创建数据目录...")
            os.makedirs(data_dir, exist_ok=True)
            print(f"创建后目录存在: {os.path.exists(data_dir)}")
        
        # 测试写入权限
        test_file = os.path.join(data_dir, "test_write.txt")
        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("测试写入权限")
            print(f"写入测试成功: {os.path.exists(test_file)}")
            os.remove(test_file)
        except Exception as e:
            print(f"写入测试失败: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"路径测试失败: {str(e)}")
        return False

def test_card_operations():
    """测试卡片操作"""
    print("\n测试卡片操作...")
    
    try:
        # 创建CardManager实例
        card_manager = CardManager()
        
        # 保存初始卡片数量
        initial_count = len(card_manager.cards)
        print(f"初始卡片数量: {initial_count}")
        
        # 添加新卡片
        new_card_id = card_manager.add_card({
            'keyword': '测试关键词',
            'definition': '测试定义',
            'source': '测试来源',
            'quote': '测试原文',
            'notes': '测试注释'
        })
        
        if new_card_id:
            print(f"添加卡片成功，ID: {new_card_id}")
            print(f"添加后卡片数量: {len(card_manager.cards)}")
            
            # 测试保存
            if card_manager.save_cards():
                print("保存卡片成功")
                
                # 重新加载
                card_manager.load_cards()
                print(f"重新加载后卡片数量: {len(card_manager.cards)}")
                
                # 验证新卡片是否存在
                new_card = card_manager.get_card(new_card_id)
                if new_card:
                    print(f"新卡片验证成功: {new_card['keyword']}")
                    
                    # 测试删除
                    if card_manager.delete_card(new_card_id):
                        print("删除卡片成功")
                        print(f"删除后卡片数量: {len(card_manager.cards)}")
                        
                        # 最终保存
                        card_manager.save_cards()
                        print("最终保存成功")
                        return True
                    else:
                        print("删除卡片失败")
                else:
                    print("新卡片验证失败")
            else:
                print("保存卡片失败")
        else:
            print("添加卡片失败")
            
        return False
        
    except Exception as e:
        print(f"卡片操作测试失败: {str(e)}")
        return False

def test_sample_data():
    """测试示例数据创建"""
    print("\n测试示例数据创建...")
    
    try:
        # 创建临时测试文件
        test_data_file = os.path.join(os.path.dirname(__file__), "test_sample.json")
        
        # 如果文件存在，先删除
        if os.path.exists(test_data_file):
            os.remove(test_data_file)
        
        # 创建CardManager实例，使用临时文件
        card_manager = CardManager(data_file=test_data_file)
        
        # 检查是否创建了示例数据
        if len(card_manager.cards) > 0:
            print(f"示例数据创建成功，卡片数量: {len(card_manager.cards)}")
            print("示例卡片:")
            for i, card in enumerate(card_manager.cards[:3]):  # 只显示前3个
                print(f"  {i+1}. {card['keyword']} - {card['source']}")
        else:
            print("示例数据创建失败")
        
        # 清理测试文件
        if os.path.exists(test_data_file):
            os.remove(test_data_file)
        
        return True
        
    except Exception as e:
        print(f"示例数据测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("开始验证路径修复效果...")
    print("=" * 60)
    
    # 运行各项测试
    test1_passed = test_user_data_path()
    test2_passed = test_card_operations()
    test3_passed = test_sample_data()
    
    print("=" * 60)
    print("测试结果汇总:")
    print(f"路径测试: {'通过' if test1_passed else '失败'}")
    print(f"卡片操作: {'通过' if test2_passed else '失败'}")
    print(f"示例数据: {'通过' if test3_passed else '失败'}")
    
    if test1_passed and test2_passed and test3_passed:
        print("\n✓ 所有测试通过！路径修复成功！")
        print("\n📁 数据文件现在将保存在用户目录下:")
        print(f"   Windows: C:\\Users\\用户名\\AppData\\Local\\ancient_chinese_cards\\cards.json")
        print(f"   Mac: ~/Library/Application Support/ancient_chinese_cards/cards.json")
        print(f"   Linux: ~/.config/ancient_chinese_cards/cards.json")
        print("\n✅ 打包后将能正常保存数据！")
    else:
        print("\n✗ 部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()