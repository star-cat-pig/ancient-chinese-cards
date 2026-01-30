#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
古文卡片学习软件命令行版本
"""

import os
import sys
import json
import argparse
from datetime import datetime
from card_manager import CardManager


class AncientChineseCardsCLI:
    """古文卡片学习软件命令行界面类"""
    
    def __init__(self):
        """初始化命令行界面"""
        self.card_manager = CardManager()
        self.load_cards()
    
    def load_cards(self):
        """加载卡片数据"""
        try:
            self.card_manager.load_cards()
            print(f"成功加载 {len(self.card_manager.cards)} 张卡片")
        except Exception as e:
            print(f"加载卡片失败: {str(e)}")
    
    def save_cards(self):
        """保存卡片数据"""
        try:
            self.card_manager.save_cards()
            print("卡片数据已保存")
            return True
        except Exception as e:
            print(f"保存卡片失败: {str(e)}")
            return False
    
    def list_cards(self):
        """列出所有卡片"""
        cards = self.card_manager.sort_cards()
        
        if not cards:
            print("暂无卡片数据")
            return
        
        print(f"\n共有 {len(cards)} 张卡片：\n")
        
        for i, card in enumerate(cards, 1):
            print(f"{i}. {card['keyword']} - {card['definition']}")
            print(f"   出处: {card['source']}")
            print(f"   原文: {card['quote']}")
            if card['notes']:
                print(f"   注释: {card['notes']}")
            print()
    
    def add_card(self):
        """添加新卡片"""
        print("\n添加新卡片")
        print("-" * 50)
        
        # 获取用户输入
        keyword = input("关键词（原文）: ").strip()
        if not keyword:
            print("关键词不能为空")
            return
        
        definition = input("释义（卡片正面）: ").strip()
        if not definition:
            print("释义不能为空")
            return
        
        source = input("出处: ").strip()
        if not source:
            print("出处不能为空")
            return
        
        quote = input("原文引用: ").strip()
        if not quote:
            print("原文引用不能为空")
            return
        
        notes = input("注释（可选）: ").strip()
        
        # 创建卡片数据
        card_data = {
            'keyword': keyword,
            'definition': definition,
            'source': source,
            'quote': quote,
            'notes': notes,
            'tags': []
        }
        
        # 添加卡片
        try:
            card_id = self.card_manager.add_card(card_data)
            print(f"\n卡片已添加，ID: {card_id}")
        except Exception as e:
            print(f"\n添加卡片失败: {str(e)}")
    
    def search_cards(self):
        """搜索卡片"""
        query = input("\n请输入搜索关键词: ").strip()
        if not query:
            print("搜索关键词不能为空")
            return
        
        # 执行搜索
        results = self.card_manager.search_cards(query)
        
        if not results:
            print(f"\n未找到包含 '{query}' 的卡片")
            return
        
        print(f"\n找到 {len(results)} 张包含 '{query}' 的卡片：\n")
        
        for i, card in enumerate(results, 1):
            print(f"{i}. {card['keyword']} - {card['definition']}")
            print(f"   出处: {card['source']}")
            print(f"   原文: {card['quote']}")
            if card['notes']:
                print(f"   注释: {card['notes']}")
            print()
    
    def import_cards(self):
        """导入卡片"""
        print("\n导入卡片")
        print("-" * 50)
        
        # 获取导入方式
        print("请选择导入方式：")
        print("1. 从文件导入")
        print("2. 直接输入文本")
        
        choice = input("请选择 (1/2): ").strip()
        
        if choice == '1':
            # 从文件导入
            file_path = input("请输入文件路径: ").strip()
            
            if not os.path.exists(file_path):
                print(f"文件 '{file_path}' 不存在")
                return
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                
                if not text:
                    print("文件内容为空")
                    return
                
                # 获取是否启用交互式解析
                interactive = input("是否启用交互式解析（遇到无法确定的情况时询问用户）？(y/n): ").strip().lower() == 'y'
                
                # 导入卡片
                stats = self.card_manager.import_cards_from_text(text, interactive=interactive)
                
                # 显示导入统计
                print(f"\n导入完成！")
                print(f"总计处理: {stats['total']} 张")
                print(f"成功添加: {stats['added']} 张")
                print(f"合并重复: {stats['merged']} 张")
                print(f"交互修复: {stats['interactive_fixed']} 张")
                print(f"无法处理: {stats['failed']} 张")
                
            except Exception as e:
                print(f"\n导入失败: {str(e)}")
        
        elif choice == '2':
            # 直接输入文本
            print("\n请输入卡片数据（输入空行结束）：")
            print("格式示例：")
            print("黑色：黝。《闲居赋》:\"浮梁黝以径度\"。")
            print("或者分组格式：")
            print("关键词")
            print("  释义1：出处1:\"原文1\"。")
            print("  释义2：出处2:\"原文2\"。")
            print()
            
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            
            text = '\n'.join(lines)
            
            if not text:
                print("输入内容为空")
                return
            
            try:
                # 获取是否启用交互式解析
                interactive = input("是否启用交互式解析（遇到无法确定的情况时询问用户）？(y/n): ").strip().lower() == 'y'
                
                # 导入卡片
                stats = self.card_manager.import_cards_from_text(text, interactive=interactive)
                
                # 显示导入统计
                print(f"\n导入完成！")
                print(f"总计处理: {stats['total']} 张")
                print(f"成功添加: {stats['added']} 张")
                print(f"合并重复: {stats['merged']} 张")
                print(f"交互修复: {stats['interactive_fixed']} 张")
                print(f"无法处理: {stats['failed']} 张")
                
            except Exception as e:
                print(f"\n导入失败: {str(e)}")
        
        else:
            print("无效的选择")
    
    def export_cards(self):
        """导出卡片"""
        print("\n导出卡片")
        print("-" * 50)
        
        if not self.card_manager.cards:
            print("暂无卡片数据可导出")
            return
        
        # 获取导出方式
        print("请选择导出方式：")
        print("1. 导出到文件")
        print("2. 显示在屏幕上")
        
        choice = input("请选择 (1/2): ").strip()
        
        try:
            # 导出卡片
            text = self.card_manager.export_cards_to_text()
            
            if choice == '1':
                # 导出到文件
                file_path = input("请输入保存路径: ").strip()
                
                if not file_path:
                    print("保存路径不能为空")
                    return
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                print(f"\n成功导出 {len(self.card_manager.cards)} 张卡片到文件 '{file_path}'")
                
            elif choice == '2':
                # 显示在屏幕上
                print(f"\n共 {len(self.card_manager.cards)} 张卡片：\n")
                print(text)
                
            else:
                print("无效的选择")
                
        except Exception as e:
            print(f"\n导出失败: {str(e)}")
    
    def show_menu(self):
        """显示主菜单"""
        print("\n" + "=" * 50)
        print("古文卡片学习软件".center(40))
        print("=" * 50)
        print("1. 查看所有卡片")
        print("2. 添加新卡片")
        print("3. 搜索卡片")
        print("4. 导入卡片")
        print("5. 导出卡片")
        print("6. 保存数据")
        print("0. 退出")
        print("=" * 50)
    
    def run(self):
        """运行命令行界面"""
        while True:
            self.show_menu()
            
            choice = input("请选择操作 (0-6): ").strip()
            
            if choice == '1':
                self.list_cards()
            elif choice == '2':
                self.add_card()
            elif choice == '3':
                self.search_cards()
            elif choice == '4':
                self.import_cards()
            elif choice == '5':
                self.export_cards()
            elif choice == '6':
                self.save_cards()
            elif choice == '0':
                # 询问是否保存
                save = input("是否保存当前数据？(y/n): ").strip().lower()
                if save == 'y':
                    self.save_cards()
                print("\n感谢使用古文卡片学习软件！")
                break
            else:
                print("无效的选择，请重新输入")


def main():
    """主函数"""
    cli = AncientChineseCardsCLI()
    cli.run()


if __name__ == "__main__":
    main()