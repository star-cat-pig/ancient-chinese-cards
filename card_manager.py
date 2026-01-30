#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
卡片管理类，负责卡片的增删改查、排序和导入导出
"""

import base64
import json
import os
import re
import sys
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

# 尝试导入pypinyin库用于中文排序，如果没有安装则使用备选方案
try:
    from pypinyin import lazy_pinyin
    PINYIN_AVAILABLE = True
except ImportError:
    PINYIN_AVAILABLE = False


class CardManager:
    """卡片管理器类"""
    
    def __init__(self, data_file: str = "cards.json"):
        """
        初始化卡片管理器
        
        Args:
            data_file: 卡片数据存储文件路径（相对于用户数据目录）
        """
        # 获取用户数据目录（跨平台兼容）
        self.user_data_dir = self._get_user_data_dir()
        # 拼接数据文件路径
        self.data_file = os.path.join(self.user_data_dir, data_file)
        self.cards: List[Dict[str, Any]] = []
        self.modified_cards = set()  # 用于跟踪被修改的卡片ID
        # 确保数据目录存在
        self.ensure_data_directory()
        # 加载卡片数据
        self.load_cards()
    
    def _get_user_data_dir(self) -> str:
        """获取跨平台的用户数据目录（可读写）"""
        # 根据系统获取用户目录
        home_dir = os.path.expanduser("~")  # 通用用户目录
        
        # 按系统拼接App专用目录
        if os.name == "nt":  # Windows
            # Windows：C:\\Users\\用户名\\AppData\\Local\\ancient_chinese_cards
            app_data_dir = os.getenv("LOCALAPPDATA", os.path.join(home_dir, "AppData", "Local"))
            user_dir = os.path.join(app_data_dir, "ancient_chinese_cards")
        elif os.name == "posix":  # Mac/Linux
            # Mac：~/Library/Application Support/ancient_chinese_cards
            # Linux：~/.config/ancient_chinese_cards
            if sys.platform == "darwin":
                user_dir = os.path.join(home_dir, "Library", "Application Support", "ancient_chinese_cards")
            else:
                user_dir = os.path.join(home_dir, ".config", "ancient_chinese_cards")
        else:
            # 其他系统：用户目录下的.ancient_chinese_cards
            user_dir = os.path.join(home_dir, ".ancient_chinese_cards")
        
        return user_dir
    
    def ensure_data_directory(self):
        """确保数据目录存在（改进：添加异常处理和提示）"""
        data_dir = os.path.dirname(self.data_file)
        try:
            # exist_ok=True：目录已存在则不报错
            os.makedirs(data_dir, exist_ok=True)
            print(f"数据目录已就绪：{data_dir}")
        except Exception as e:
            # 明确提示目录创建失败
            raise RuntimeError(f"无法创建数据目录：{data_dir}，错误：{str(e)}") from e
    
    def find_duplicate_card(self, keyword: str, definition: str) -> Optional[str]:
        """
        查找重复卡片
        
        Args:
            keyword: 关键词
            definition: 释义
        
        Returns:
            Optional[str]: 如果找到重复卡片，返回卡片ID，否则返回None
        """
        for card in self.cards:
            if (card['keyword'].strip() == keyword.strip() and 
                card['definition'].strip() == definition.strip()):
                return card['id']
        
        return None
    
    def merge_cards(self, card_id1: str, card_data2: Dict[str, Any]) -> bool:
        """
        合并两张卡片
        
        Args:
            card_id1: 第一张卡片ID
            card_data2: 第二张卡片数据
        
        Returns:
            bool: 合并是否成功
        """
        # 获取第一张卡片
        card1 = self.get_card(card_id1)
        if not card1:
            return False
        
        # 合并数据
        merged_notes = card1['notes']
        if card_data2.get('notes', '').strip():
            if merged_notes:
                merged_notes += '\n\n' + card_data2['notes']
            else:
                merged_notes = card_data2['notes']
        
        # 更新卡片
        updated_data = {
            'keyword': card1['keyword'],
            'definition': card1['definition'],
            'source': card1['source'],  # 保留原来源
            'quote': card1['quote'],    # 保留原引用
            'notes': merged_notes,
            'tags': list(set(card1.get('tags', []) + card_data2.get('tags', [])))
        }
        
        return self.update_card(card_id1, updated_data)
    
    def get_all_cards(self) -> List[Dict[str, Any]]:
        """
        获取所有卡片数据
        
        Returns:
            List[Dict[str, Any]]: 卡片数据列表
        """
        return self.cards.copy()
    
    def add_cards(self, cards_data: List[Dict[str, Any]]) -> int:
        """
        批量添加卡片
        
        Args:
            cards_data: 卡片数据列表
        
        Returns:
            int: 成功添加的卡片数量
        """
        added_count = 0
        
        for card_data in cards_data:
            # 确保卡片数据包含必要字段
            if all(key in card_data for key in ['keyword', 'definition']):
                # 生成新的ID，避免ID冲突
                card_data['id'] = self._generate_unique_id()
                # 更新时间戳
                card_data['created_at'] = datetime.now().isoformat()
                card_data['updated_at'] = datetime.now().isoformat()
                
                # 添加到卡片列表
                self.cards.append(card_data)
                self.modified_cards.add(card_data['id'])
                added_count += 1
        
        # 保存卡片
        if added_count > 0:
            self.save_cards()
        
        return added_count
    
    def clear_cards(self) -> bool:
        """
        清空所有卡片
        
        Returns:
            bool: 操作是否成功
        """
        try:
            # 清空卡片列表
            self.cards.clear()
            self.modified_cards.clear()
            
            # 保存空数据
            return self.save_cards()
        except Exception as e:
            print(f"清空卡片失败: {str(e)}")
            return False
    
    def add_card(self, card_data: Dict[str, Any], allow_duplicates: bool = False) -> str:
        """
        添加新卡片
        
        Args:
            card_data: 卡片数据字典
            allow_duplicates: 是否允许重复卡片
        
        Returns:
            str: 新卡片的ID或已存在的卡片ID
        """
        # 检查是否存在重复卡片
        keyword = card_data.get('keyword', '').strip()
        definition = card_data.get('definition', '').strip()
        
        if not allow_duplicates:
            duplicate_id = self.find_duplicate_card(keyword, definition)
            if duplicate_id:
                # 合并卡片
                self.merge_cards(duplicate_id, card_data)
                return duplicate_id
        
        # 生成唯一ID（确保不重复）
        card_id = self._generate_unique_id()
        
        # 创建完整的卡片数据
        card = {
            'id': card_id,
            'keyword': keyword,
            'definition': definition,
            'source': card_data.get('source', ''),
            'quote': card_data.get('quote', ''),
            'notes': card_data.get('notes', ''),
            'tags': card_data.get('tags', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # 添加到卡片列表
        self.cards.append(card)
        
        # 标记为已修改
        self.modified_cards.add(card_id)
        
        # 保存卡片
        if self.save_cards():
            return card_id
        else:
            # 保存失败，从列表中移除新卡片
            self.cards.pop()
            self.modified_cards.remove(card_id)
            return None
    
    def update_card(self, card_id_or_data, card_data=None) -> bool:
        """
        更新卡片
        
        支持两种调用方式：
        1. update_card(card_id, card_data) - 传入卡片ID和更新数据
        2. update_card(card_data) - 传入包含id的完整卡片数据
        
        Args:
            card_id_or_data: 卡片ID或完整的卡片数据
            card_data: 更新的卡片数据（当第一个参数是卡片ID时使用）
        
        Returns:
            bool: 更新是否成功
        """
        # 判断调用方式
        if isinstance(card_id_or_data, dict) and card_data is None:
            # 第二种调用方式：传入完整的卡片数据
            card_data = card_id_or_data
            card_id = card_data.get('id')
            if not card_id:
                return False
        else:
            # 第一种调用方式：传入卡片ID和更新数据
            card_id = card_id_or_data
            if not card_data:
                return False
        
        for i, card in enumerate(self.cards):
            if card['id'] == card_id:
                # 更新卡片数据
                if isinstance(card_id_or_data, dict):
                    # 完整卡片数据更新
                    self.cards[i] = card_data
                else:
                    # 部分字段更新
                    self.cards[i].update({
                        'keyword': card_data.get('keyword', self.cards[i]['keyword']),
                        'definition': card_data.get('definition', self.cards[i]['definition']),
                        'source': card_data.get('source', self.cards[i]['source']),
                        'quote': card_data.get('quote', self.cards[i]['quote']),
                        'notes': card_data.get('notes', self.cards[i]['notes']),
                        'tags': card_data.get('tags', self.cards[i]['tags']),
                        'updated_at': datetime.now().isoformat()
                    })
                
                # 标记为已修改
                self.modified_cards.add(card_id)
                
                # 保存卡片
                if self.save_cards():
                    return True
                else:
                    # 保存失败，保持修改标记
                    return False
        
        return False
    
    def delete_card(self, card_id: str) -> bool:
        """
        删除卡片
        
        Args:
            card_id: 卡片ID
        
        Returns:
            bool: 删除是否成功
        """
        for i, card in enumerate(self.cards):
            if card['id'] == card_id:
                del self.cards[i]
                self.save_cards()
                return True
        
        return False
    
    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """
        获取卡片
        
        Args:
            card_id: 卡片ID
        
        Returns:
            Optional[Dict[str, Any]]: 卡片数据，如果不存在则返回None
        """
        for card in self.cards:
            if card['id'] == card_id:
                return card
        
        return None
    
    def get_all_cards(self) -> List[Dict[str, Any]]:
        """
        获取所有卡片
        
        Returns:
            List[Dict[str, Any]]: 所有卡片列表
        """
        return self.cards
    
    def sort_cards(self) -> List[Dict[str, Any]]:
        """
        按关键词字母顺序排序卡片
        
        Returns:
            List[Dict[str, Any]]: 排序后的卡片列表
        """
        if PINYIN_AVAILABLE:
            # 使用pypinyin进行中文拼音排序
            return sorted(self.cards, key=lambda x: lazy_pinyin(x['keyword'].lower()))
        else:
            # 使用Python内置排序（可能不够准确）
            return sorted(self.cards, key=lambda x: x['keyword'].lower())
    
    def search_cards(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索卡片
        
        Args:
            query: 搜索关键词
        
        Returns:
            List[Dict[str, Any]]: 搜索结果列表
        """
        if not query:
            return self.cards
        
        query = query.lower()
        results = []
        
        for card in self.cards:
            # 在多个字段中搜索
            if (query in card['keyword'].lower() or
                query in card['definition'].lower() or
                query in card['source'].lower() or
                query in card['quote'].lower() or
                query in card['notes'].lower()):
                results.append(card)
        
        return results
    
    def save_cards(self):
        """保存卡片数据到文件（包含自动备份）"""
        try:
            # 创建备份
            backup_path = self._create_backup()
            
            # 保存数据
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.cards, f, ensure_ascii=False, indent=2)
            
            # 保存成功后清空修改标记
            self.modified_cards.clear()
            print(f"成功保存 {len(self.cards)} 张卡片到: {self.data_file}")
            if backup_path:
                print(f"备份文件已创建: {backup_path}")
            return True
        except Exception as e:
            # 友好提示用户，而非仅打印到控制台
            error_msg = f"保存数据失败！请检查目录权限：{os.path.dirname(self.data_file)}，错误：{str(e)}"
            print(error_msg)
            
            # 如果有备份，提示用户
            if os.path.exists(self.data_file):
                latest_backup = self._get_latest_backup()
                if latest_backup:
                    print(f"数据保存失败，但您可以从备份恢复: {latest_backup}")
            
            # 保存失败，保持修改标记
            return False
    
    def _create_backup(self):
        """创建数据备份"""
        if not os.path.exists(self.data_file):
            return None
        
        try:
            # 生成带时间戳的备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(os.path.dirname(self.data_file), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(backup_dir, f"cards_backup_{timestamp}.json")
            
            # 复制当前文件到备份
            import shutil
            shutil.copy2(self.data_file, backup_file)
            
            # 清理旧备份（保留最近5个）
            self._cleanup_old_backups(backup_dir, max_backups=5)
            
            return backup_file
        except Exception as e:
            print(f"创建备份失败: {str(e)}")
            return None
    
    def _cleanup_old_backups(self, backup_dir, max_backups=5):
        """清理旧备份文件"""
        try:
            # 获取所有备份文件并按时间排序
            backups = [f for f in os.listdir(backup_dir) if f.startswith('cards_backup_') and f.endswith('.json')]
            backups.sort(reverse=True)  # 最新的在前
            
            # 删除超出数量限制的备份
            for old_backup in backups[max_backups:]:
                os.remove(os.path.join(backup_dir, old_backup))
        except Exception as e:
            print(f"清理旧备份失败: {str(e)}")
    
    def _get_latest_backup(self):
        """获取最新的备份文件"""
        backup_dir = os.path.join(os.path.dirname(self.data_file), 'backups')
        if not os.path.exists(backup_dir):
            return None
        
        try:
            backups = [f for f in os.listdir(backup_dir) if f.startswith('cards_backup_') and f.endswith('.json')]
            if not backups:
                return None
            
            backups.sort(reverse=True)
            return os.path.join(backup_dir, backups[0])
        except Exception as e:
            print(f"获取最新备份失败: {str(e)}")
            return None
    
    def restore_from_backup(self, backup_file=None):
        """从备份恢复数据"""
        try:
            if not backup_file:
                backup_file = self._get_latest_backup()
            
            if not backup_file or not os.path.exists(backup_file):
                return False
            
            # 加载备份数据
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_cards = json.load(f)
            
            # 验证备份数据
            if not isinstance(backup_cards, list):
                return False
            
            # 替换当前数据
            self.cards = backup_cards
            self.modified_cards.clear()
            
            # 保存恢复的数据
            return self.save_cards()
        except Exception as e:
            print(f"从备份恢复失败: {str(e)}")
            return False
    
    def _generate_unique_id(self):
        """生成唯一的卡片ID（确保不重复）"""
        max_attempts = 10
        for attempt in range(max_attempts):
            card_id = str(uuid.uuid4())
            # 检查ID是否已存在
            if not any(card['id'] == card_id for card in self.cards):
                return card_id
        
        # 如果多次尝试后仍未生成唯一ID，使用时间戳和随机数组合
        import random
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = str(random.randint(1000, 9999))
        return f"{timestamp}_{random_suffix}"
    
    def has_modified_cards(self):
        """检查是否有卡片被修改"""
        return len(self.modified_cards) > 0
    
    def load_cards(self):
        """从文件加载卡片数据（改进：首次运行时创建示例数据）"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.cards = json.load(f)
                print(f"成功加载 {len(self.cards)} 张卡片")
            except json.JSONDecodeError as e:
                print(f"警告：数据文件格式错误，将创建新文件。错误：{str(e)}")
                self.cards = []
                self._create_sample_cards()
        else:
            print(f"未找到数据文件：{self.data_file}")
            self.cards = []
            self._create_sample_cards()
    
    # 新增：加密密钥（保持不变）
    ENCRYPT_KEY = b"ancient_chinese_cards_2024"
    
    def encrypt_card_lines(self, cards):
        """将卡片列表转为行格式字符串并加密"""
        # 1. 按"关键词⚠️释义⚠️出处⚠️原文⚠️注释"格式拼接，每行一条
        lines = []
        for card in cards:
            # 处理空字段（避免拆分出错）
            keyword = card.get('keyword', '').strip()
            definition = card.get('definition', '').strip()
            source = card.get('source', '').strip()
            quote = card.get('quote', '').strip()
            notes = card.get('notes', '').strip()
            # 用特殊分隔符拼接（⚠️几乎不会被用户使用）
            line = f"{keyword}⚠️{definition}⚠️{source}⚠️{quote}⚠️{notes}"
            lines.append(line)
        # 2. 拼接所有行（换行分隔）
        raw_text = "\n".join(lines).encode("utf-8")
        # 3. 异或混淆+Base64加密（保持乱码效果）
        encrypted = bytearray()
        for i in range(len(raw_text)):
            encrypted.append(raw_text[i] ^ self.ENCRYPT_KEY[i % len(self.ENCRYPT_KEY)])
        # 4. 添加ANCC文件头（识别专属格式）
        return b"ANCC_V1" + base64.b64encode(encrypted)
    
    def decrypt_to_cards(self, encrypted_data):
        """解密ANCC文件，转为卡片列表"""
        # 1. 验证文件头
        if not encrypted_data.startswith(b"ANCC_V1"):
            raise ValueError("不是合法的ANCC文件")
        # 2. 解密
        raw_data = base64.b64decode(encrypted_data[7:])  # 去掉文件头
        decrypted = bytearray()
        for i in range(len(raw_data)):
            decrypted.append(raw_data[i] ^ self.ENCRYPT_KEY[i % len(self.ENCRYPT_KEY)])
        # 3. 按行拆分，解析每条卡片
        card_lines = decrypted.decode("utf-8").split("\n")
        cards = []
        for line in card_lines:
            line = line.strip()
            if not line:
                continue
            # 按分隔符拆分字段（兼容空字段）
            fields = line.split("⚠️")
            # 确保字段数量一致（不足补空，多余截断）
            while len(fields) < 5:
                fields.append("")
            keyword, definition, source, quote, notes = fields[:5]
            # 去重判断（按关键词+出处）
            duplicate = False
            for existing in self.cards:
                if existing['keyword'].strip() == keyword and existing['source'].strip() == source:
                    duplicate = True
                    break
            if not duplicate:
                cards.append({
                    'keyword': keyword,
                    'definition': definition,
                    'source': source,
                    'quote': quote,
                    'notes': notes,
                    'tags': []
                })
        return cards
    
    def _create_sample_cards(self):
        """创建示例卡片数据（首次运行时使用）"""
        sample_cards = [
            {
                'id': self._generate_unique_id(),
                'keyword': '学而时习之',
                'definition': '学习了知识然后按时复习它。',
                'source': '《论语·学而》',
                'quote': '子曰："学而时习之，不亦说乎？"',
                'notes': '这是《论语》开篇第一句，强调学习与复习的重要性。',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': self._generate_unique_id(),
                'keyword': '温故知新',
                'definition': '温习旧的知识，能有新的体会和发现。',
                'source': '《论语·为政》',
                'quote': '子曰："温故而知新，可以为师矣。"',
                'notes': '强调复习的重要性，通过复习旧知识可以获得新的理解。',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': self._generate_unique_id(),
                'keyword': '举一反三',
                'definition': '从一件事物的情况、道理类推而知道许多事物的情况、道理。',
                'source': '《论语·述而》',
                'quote': '子曰："不愤不启，不悱不发。举一隅不以三隅反，则不复也。"',
                'notes': '孔子的教学方法，强调启发式教学和类推能力的培养。',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ]
        
        self.cards = sample_cards
        print(f"已创建 {len(sample_cards)} 张示例卡片")
        # 保存示例数据
        self.save_cards()
    
    def import_cards_from_text(self, text: str, allow_duplicates: bool = False, interactive: bool = True) -> Dict[str, int]:
        """
        从文本导入卡片
        
        Args:
            text: 包含卡片数据的文本
            allow_duplicates: 是否允许重复卡片
            interactive: 是否启用交互式解析（遇到无法确定的情况时询问用户）
        
        Returns:
            Dict[str, int]: 导入统计信息
        """
        # 解析文本格式的卡片数据
        # 支持多种格式：
        # 格式1: 释义：关键词。出处:“原文”。
        # 格式2: 释义：关键词。出处：“原文”。
        # 格式3: 关键词
        #       释义1：出处1:“原文1”。
        #       释义2：出处2:“原文2”。
        # 格式4: 释义：出处:“原文”。（适用于已有关键词的情况，支持多种标点符号）
        
        cards = []
        lines = text.strip().split('\n')
        
        # 统计信息
        stats = {
            'total': 0,
            'added': 0,
            'merged': 0,
            'failed': 0,
            'interactive_fixed': 0  # 记录通过交互方式修复的卡片数
        }
        
        i = 0
        current_keyword = None
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # 尝试匹配已知格式
            parsed_data = self._parse_line(line, current_keyword)
            
            if parsed_data:
                # 成功解析，创建卡片数据
                card_data = {
                    'keyword': parsed_data['keyword'].strip(),
                    'definition': parsed_data['definition'].strip(),
                    'source': parsed_data.get('source', '').strip(),
                    'quote': parsed_data.get('quote', '').strip(),
                    'notes': ''
                }
                
                # 检查下一行是否有注释
                if i + 1 < len(lines) and lines[i + 1].strip():
                    next_line = lines[i + 1].strip()
                    if not (re.search(r'：.*[。？]', next_line) or re.search(r'：.*。', next_line)):
                        card_data['notes'] = next_line
                        i += 1
                
                cards.append(card_data)
                current_keyword = None if parsed_data.get('reset_keyword', True) else current_keyword
            
            else:
                # 无法解析的行
                if interactive:
                    # 交互式解析
                    fixed_data = self._interactive_parse(line, current_keyword, cards)
                    if fixed_data:
                        cards.append(fixed_data)
                        stats['interactive_fixed'] += 1
                        current_keyword = None
                    else:
                        # 用户选择跳过或无法修复
                        stats['failed'] += 1
                else:
                    # 非交互式模式下的处理
                    if current_keyword:
                        # 尝试作为注释处理
                        last_card = None
                        for card in reversed(cards):
                            if card['keyword'] == current_keyword:
                                last_card = card
                                break
                        
                        if last_card:
                            if last_card['notes']:
                                last_card['notes'] += '\n' + line
                            else:
                                last_card['notes'] = line
                    else:
                        # 尝试作为新关键词处理
                        if not re.search(r'[：:].*', line) and not any(card['keyword'] == line for card in cards):
                            current_keyword = line
                        else:
                            stats['failed'] += 1
            
            i += 1
        
        # 添加导入的卡片
        stats['total'] = len(cards)
        
        for card_data in cards:
            try:
                card_id = self.add_card(card_data, allow_duplicates)
                
                # 检查是新增还是合并
                if any(card['id'] == card_id for card in self.cards[-len(cards):]):
                    stats['added'] += 1
                else:
                    stats['merged'] += 1
            except Exception as e:
                print(f"导入卡片失败: {str(e)}")
                stats['failed'] += 1
        
        return stats
    
    def _parse_line(self, line: str, current_keyword: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        解析单行文本，尝试匹配已知格式
        
        Args:
            line: 要解析的文本行
            current_keyword: 当前上下文的关键词（如果有）
        
        Returns:
            Optional[Dict[str, Any]]: 解析结果，如果无法解析返回None
        """
        # 检查是否是新的关键词（格式3）
        if current_keyword is None and not re.search(r'：.*[。？]', line):
            # 可能是新的关键词
            return {'keyword': line, 'definition': '', 'reset_keyword': False}
        
        # 尝试匹配卡片格式
        # 格式1: 释义：关键词。出处:“原文”。
        match1 = re.match(r'(.+?)：(.+?)。(.+?):["“](.+?)["”]。?', line)
        if match1:
            definition, keyword, source, quote = match1.groups()
            return {
                'keyword': keyword.strip(),
                'definition': definition.strip(),
                'source': source.strip(),
                'quote': quote.strip()
            }
        
        # 格式2: 释义：关键词。出处：“原文”。
        match2 = re.match(r'(.+?)：(.+?)。(.+?)：["“](.+?)["”]。?', line)
        if match2:
            definition, keyword, source, quote = match2.groups()
            return {
                'keyword': keyword.strip(),
                'definition': definition.strip(),
                'source': source.strip(),
                'quote': quote.strip()
            }
        
        # 格式3: 释义：出处:“原文”。（适用于已有关键词的情况）
        match3 = re.match(r'(.+?)：(.+?):["“](.+?)["”]。?', line)
        if match3 and current_keyword:
            definition, source, quote = match3.groups()
            return {
                'keyword': current_keyword.strip(),
                'definition': definition.strip(),
                'source': source.strip(),
                'quote': quote.strip(),
                'reset_keyword': False
            }
        
        # 格式4: 释义：出处：“原文”。（适用于已有关键词的情况）
        match4 = re.match(r'(.+?)：(.+?)：["“](.+?)["”]。?', line)
        if match4 and current_keyword:
            definition, source, quote = match4.groups()
            return {
                'keyword': current_keyword.strip(),
                'definition': definition.strip(),
                'source': source.strip(),
                'quote': quote.strip(),
                'reset_keyword': False
            }
        
        # 格式5: 释义：关键词。（简化格式，只有释义和关键词）
        match5 = re.match(r'(.+?)：(.+?)。', line)
        if match5:
            if current_keyword:
                # 如果有当前关键词，使用当前关键词
                definition, other = match5.groups()
                return {
                    'keyword': current_keyword.strip(),
                    'definition': definition.strip(),
                    'source': '',
                    'quote': other.strip(),
                    'reset_keyword': False
                }
            else:
                # 否则将第二部分作为关键词
                definition, keyword = match5.groups()
                return {
                    'keyword': keyword.strip(),
                    'definition': definition.strip(),
                    'source': '',
                    'quote': ''
                }
        
        # 特殊格式：不滿：嗛（音切）：高啓《書博鷄者事》：”知使意嗛守。”
        special_match = re.match(r'(.+?)：(.+?)：(.+?):["“](.+?)["”]。?', line)
        if special_match and current_keyword:
            definition, pronunciation, source, quote = special_match.groups()
            return {
                'keyword': current_keyword.strip(),
                'definition': f"{definition.strip()}：{pronunciation.strip()}",
                'source': source.strip(),
                'quote': quote.strip(),
                'reset_keyword': False
            }
        
        return None
    
    def _interactive_parse(self, line: str, current_keyword: Optional[str], existing_cards: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        交互式解析无法自动识别的行
        
        Args:
            line: 无法自动解析的文本行
            current_keyword: 当前上下文的关键词（如果有）
            existing_cards: 已解析的卡片列表
        
        Returns:
            Optional[Dict[str, Any]]: 用户确认的卡片数据，如果用户选择跳过返回None
        """
        print(f"\n无法自动解析以下内容:")
        print(f"  {line}")
        print(f"当前上下文关键词: {current_keyword if current_keyword else '无'}")
        print("\n请选择处理方式:")
        print("1. 这是一个新的关键词")
        print("2. 这是已有关键词的释义行")
        print("3. 这是上一张卡片的注释")
        print("4. 跳过这一行")
        
        while True:
            choice = input("请选择 (1-4): ").strip()
            
            if choice == '1':
                # 作为新关键词
                return {
                    'keyword': line.strip(),
                    'definition': '',
                    'source': '',
                    'quote': '',
                    'notes': ''
                }
            
            elif choice == '2':
                # 作为已有关键词的释义行
                keyword = current_keyword
                if not keyword:
                    keyword = input("请输入关键词: ").strip()
                    if not keyword:
                        print("关键词不能为空")
                        continue
                
                print("请输入这一行的组成部分:")
                definition = input("释义: ").strip()
                source = input("出处 (可选): ").strip()
                quote = input("原文引用 (可选): ").strip()
                
                if not definition:
                    print("释义不能为空")
                    continue
                
                return {
                    'keyword': keyword,
                    'definition': definition,
                    'source': source,
                    'quote': quote,
                    'notes': ''
                }
            
            elif choice == '3':
                # 作为上一张卡片的注释
                if not existing_cards:
                    print("还没有卡片，无法添加注释")
                    continue
                
                last_card = existing_cards[-1].copy()
                if last_card['notes']:
                    last_card['notes'] += '\n' + line
                else:
                    last_card['notes'] = line
                
                # 从列表中移除原卡片，添加更新后的卡片
                existing_cards.pop()
                return last_card
            
            elif choice == '4':
                # 跳过这一行
                return None
            
            else:
                print("无效的选择，请重新输入")
        
        # 添加导入的卡片
        stats['total'] = len(cards)
        
        for card_data in cards:
            try:
                card_id = self.add_card(card_data, allow_duplicates)
                
                # 检查是新增还是合并
                if any(card['id'] == card_id for card in self.cards[-len(cards):]):
                    stats['added'] += 1
                else:
                    stats['merged'] += 1
            except Exception as e:
                print(f"导入卡片失败: {str(e)}")
                stats['failed'] += 1
        
        return stats
    
    def export_cards_to_text(self, group_by_keyword: bool = False) -> str:
        """
        导出卡片为文本格式
        
        Args:
            group_by_keyword: 是否按关键词分组
        
        Returns:
            str: 导出的文本
        """
        if not self.cards:
            return "暂无卡片数据"
        
        text = ""
        
        if group_by_keyword:
            # 按关键词分组
            keyword_groups = {}
            
            for card in self.sort_cards():
                keyword = card['keyword']
                if keyword not in keyword_groups:
                    keyword_groups[keyword] = []
                keyword_groups[keyword].append(card)
            
            # 导出分组数据
            for keyword, cards in keyword_groups.items():
                # 添加关键词
                text += keyword + "\n"
                
                # 添加该关键词下的所有卡片
                for card in cards:
                    # 格式：释义：出处:“原文”。
                    line = f"  {card['definition']}：{card['source']}:“{card['quote']}”。"
                    text += line + "\n"
                    
                    # 如果有注释，添加注释行
                    if card['notes']:
                        # 对注释进行缩进处理
                        notes_lines = card['notes'].split('\n')
                        for note_line in notes_lines:
                            text += "  " + note_line + "\n"
                
                text += "\n"
        else:
            # 不分组，按原格式导出
            for card in self.sort_cards():
                # 格式：释义：关键词。出处:“原文”。
                line = f"{card['definition']}：{card['keyword']}。{card['source']}:“{card['quote']}”。"
                text += line + "\n"
                
                # 如果有注释，添加注释行
                if card['notes']:
                    text += card['notes'] + "\n"
                
                text += "\n"
        
        return text.strip()