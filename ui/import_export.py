#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
古文卡片学习软件 - 完整导入导出版
支持：多分隔符兼容（，、。、；）、有无《》出处识别、语义自动匹配
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
from typing import Optional

# -------------------------- 核心：卡片管理器（支持多格式解析）--------------------------
class CardManager:
    """卡片管理器：负责卡片存储、导入（多格式兼容）、导出"""
    def __init__(self):
        self.cards = []  # 存储所有卡片
        
        # 预设常见典籍和作者（可按需扩展）
        self.common_books = [
            "论语", "孟子", "大学", "中庸", "道德经", "庄子", "史记", "汉书",
            "后汉书", "三国志", "资治通鉴", "闲居赋", "登楼赋", "醉书斋记",
            "世说新语", "郁离子", "池北书库记", "沈氏姑生壙銘", "与徐司空蝶園書二",
            "读郁离子", "书博鷄者事", "庄子集解", "陈审举表", "山中与裴秀才迪书"
        ]
        self.common_authors = [
            "孔子", "孟子", "老子", "庄子", "司马迁", "班固", "潘岳", "王粲",
            "方苞", "郑日奎", "刘义庆", "王世祯", "朱彝尊", "高启", "曹植",
            "王维", "纪昀", "罗洪先", "方濬颐", "胡承珙", "薛瑄"
        ]
    
    def get_all_cards(self):
        """获取所有卡片（给导出功能用）"""
        return self.cards
    
    def import_cards_from_text(self, text, allow_duplicates=False, interactive=False):
        """从文本导入卡片（核心：多格式兼容解析）"""
        stats = {"total": 0, "added": 0, "merged": 0, "failed": 0}
        if not text:
            return stats
        
        # 预处理：按行拆分，统一分隔符
        lines = [self._preprocess_line(line) for line in text.splitlines() if line.strip()]
        
        for line_num, line_parts in enumerate(lines, 1):
            try:
                # 过滤空字段
                line_parts = [part.strip() for part in line_parts if part.strip()]
                if len(line_parts) < 3:  # 至少需要3个字段（关键词+释义+出处/原文）
                    stats["failed"] += 1
                    continue
                
                # 语义匹配字段（核心逻辑）
                card_data = self._match_fields_by_semantics(line_parts)
                if not card_data:
                    stats["failed"] += 1
                    continue
                
                # 提取字段
                keyword = card_data["keyword"]
                definition = card_data["definition"]
                source = card_data["source"]
                original_text = card_data["original_text"]
                comment = card_data.get("comment", "")
                
                # 关键词为空则无效
                if not keyword:
                    stats["failed"] += 1
                    continue
                
                # 处理重复卡片
                duplicate = False
                if not allow_duplicates:
                    for existing in self.cards:
                        if existing["keyword"] == keyword and existing["source"] == source:
                            duplicate = True
                            stats["merged"] += 1
                            break
                if duplicate:
                    continue
                
                # 添加新卡片
                self.cards.append({
                    "keyword": keyword,
                    "definition": definition,
                    "source": source,
                    "original_text": original_text,
                    "comment": comment
                })
                stats["added"] += 1
                stats["total"] += 1
                
            except Exception as e:
                print(f"解析失败（第{line_num}行）：{str(e)}")
                stats["failed"] += 1
        
        return stats
    
    def export_cards_to_text(self, group_by_keyword=False):
        """导出卡片为文本格式（支持按关键词分组）"""
        text = ""
        if group_by_keyword:
            # 按关键词分组
            keyword_groups = {}
            for card in self.cards:
                key = card["keyword"]
                if key not in keyword_groups:
                    keyword_groups[key] = []
                keyword_groups[key].append(card)
            
            for keyword, cards in keyword_groups.items():
                text += f"{keyword}\n"
                for card in cards:
                    text += f"  {card['definition']}：{card['source']}：“{card['original_text']}”。\n"
                text += "\n"
        else:
            # 标准格式（释义：关键词。出处：“原文”。）
            for card in self.cards:
                text += f"{card['definition']}：{card['keyword']}。{card['source']}：“{card['original_text']}”。\n"
        
        return text.strip()
    
    def _preprocess_line(self, line):
        """预处理行：统一拆分分隔符（，、。、；）"""
        # 替换所有常见分隔符为统一标记
        line = re.sub(r"[，。；]", "|", line)
        # 按标记拆分字段
        return line.split("|")
    
    def _match_fields_by_semantics(self, parts):
        """语义匹配字段：支持无《》、多分隔符"""
        card_data = {}
        
        # 1. 识别“关键词：释义”（必含冒号，兼容中英文）
        for i, part in enumerate(parts):
            if "：" in part or ":" in part:
                separator = "：" if "：" in part else ":"
                key_def = part.split(separator, 1)  # 只拆1次，避免字段内冒号干扰
                if len(key_def) == 2:
                    candidate_key = key_def[0].strip()
                    candidate_def = key_def[1].strip()
                    # 语义判断：关键词通常是1-4字短词，释义是描述性文字
                    if len(candidate_key) <= 4 and len(candidate_def) > 1:
                        card_data["keyword"] = candidate_key
                        card_data["definition"] = candidate_def
                    else:
                        card_data["keyword"] = candidate_def
                        card_data["definition"] = candidate_key
                    # 剩余部分找出处和原文
                    remaining_parts = parts[:i] + parts[i+1:]
                    break
        else:
            # 无冒号，无法区分关键词和释义→失败
            return None
        
        # 2. 识别出处（优先级：有《》→ 作者+典籍→ 纯典籍→ 无出处）
        source = ""
        original_parts = []
        for i, part in enumerate(remaining_parts):
            part_stripped = part.strip()
            # 规则1：有《》包裹
            if re.search(r"《[^》]+》", part_stripped):
                source = part_stripped
                original_parts = remaining_parts[:i] + remaining_parts[i+1:]
                break
            # 规则2：含常见作者名
            elif any(author in part_stripped for author in self.common_authors):
                source = part_stripped
                original_parts = remaining_parts[:i] + remaining_parts[i+1:]
                break
            # 规则3：含常见典籍名
            elif any(book in part_stripped for book in self.common_books):
                source = part_stripped
                original_parts = remaining_parts[:i] + remaining_parts[i+1:]
                break
        
        # 3. 未识别到出处→剩余部分全为原文
        if not source:
            source = ""
            original_parts = remaining_parts
        
        # 4. 繁简转换（可选，无库则跳过）
        try:
            from opencc import OpenCC
            cc = OpenCC('t2s')
            card_data["keyword"] = cc.convert(card_data["keyword"])
            card_data["definition"] = cc.convert(card_data["definition"])
            source = cc.convert(source)
            original_text = cc.convert("".join(original_parts).strip())
        except ImportError:
            original_text = "".join(original_parts).strip()
        
        # 5. 整合结果
        card_data["source"] = source
        card_data["original_text"] = original_text
        
        return card_data

# -------------------------- 导入导出对话框（原GUI逻辑不变）--------------------------
class ImportExportDialog:
    """导入导出对话框类"""
    def __init__(self, parent, card_manager, main_window, mode: str = "both"):
        self.parent = parent
        self.card_manager = card_manager
        self.main_window = main_window
        self.colors = main_window.colors
        self.mode = mode
        
        if parent == main_window.root:
            self.create_modal_dialog()
        else:
            self.create_embedded_view()
    
    def create_modal_dialog(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("导入导出卡片")
        self.dialog.geometry("600x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.create_dialog_content(self.dialog)
    
    def create_embedded_view(self):
        self.view_frame = ttk.Frame(self.parent)
        self.view_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.create_dialog_content(self.view_frame)
    
    def create_dialog_content(self, parent):
        tab_control = ttk.Notebook(parent)
        
        if self.mode in ["import", "both"]:
            import_tab = ttk.Frame(tab_control)
            tab_control.add(import_tab, text="导入卡片")
            self.create_import_tab(import_tab)
        
        if self.mode in ["export", "both"]:
            export_tab = ttk.Frame(tab_control)
            tab_control.add(export_tab, text="导出卡片")
            self.create_export_tab(export_tab)
        
        tab_control.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_import_tab(self, parent):
        # 导入说明
        import_info = ttk.Label(
            parent,
            text="请选择导入方式或文件格式",
            font=("SimHei", 12, "bold")
        )
        import_info.pack(anchor=tk.W, pady=(10, 20))
        
        # 导入方式选择
        options_frame = ttk.Frame(parent)
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.import_method = tk.StringVar(value="text")
        text_format_radio = ttk.Radiobutton(
            options_frame,
            text="文本格式（支持复制粘贴）",
            variable=self.import_method,
            value="text",
            command=self.on_import_method_change
        )
        text_format_radio.pack(anchor=tk.W, pady=(0, 10))
        
        file_import_radio = ttk.Radiobutton(
            options_frame,
            text="从文件导入",
            variable=self.import_method,
            value="file",
            command=self.on_import_method_change
        )
        file_import_radio.pack(anchor=tk.W, pady=(0, 10))
        
        # 文本输入框
        self.text_input_frame = ttk.Frame(parent)
        self.text_input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.import_text = tk.Text(
            self.text_input_frame,
            width=60,
            height=10,
            font=("SimHei", 12),
            wrap=tk.WORD
        )
        self.import_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        text_scrollbar = ttk.Scrollbar(
            self.text_input_frame,
            command=self.import_text.yview
        )
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.import_text.config(yscrollcommand=text_scrollbar.set)
        
        # 文件选择框架（初始隐藏）
        self.file_select_frame = ttk.Frame(parent)
        self.file_path_var = tk.StringVar()
        file_path_entry = ttk.Entry(
            self.file_select_frame,
            textvariable=self.file_path_var,
            width=50,
            font=("SimHei", 12)
        )
        file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        file_select_button = ttk.Button(
            self.file_select_frame,
            text="浏览...",
            command=self.select_import_file
        )
        file_select_button.pack(side=tk.LEFT)
        
        # 格式说明
        format_info_frame = ttk.Frame(parent)
        format_info_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            format_info_frame,
            text="文本格式说明:",
            font=("SimHei", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))
        
        format_example = """
支持多种格式（自动兼容分隔符、有无《》）：
1. 标准格式：释义：关键词。出处:“原文”。
2. 逗号分隔：关键词：释义，出处，原文
3. 无《》格式：关键词：释义，作者 典籍，原文
4. 分组格式：
关键词
  释义1：出处1:“原文1”。
  释义2：出处2:“原文2”。

示例：
黑色：黝。《闲居赋》:“浮梁黝以径度”。
釣：掛，潘岳 闲居赋，陸擿紫房，水掛赪鯉
補衣：補輟，沈氏姑生壙銘，姑老矣，偶袒內襦，補輟無間
        """
        
        format_info_text = tk.Text(
            format_info_frame,
            width=60,
            height=6,
            font=("SimHei", 10),
            wrap=tk.WORD
        )
        format_info_text.pack(fill=tk.BOTH, expand=True)
        format_info_text.insert(tk.END, format_example)
        format_info_text.config(state=tk.DISABLED)
        
        format_scrollbar = ttk.Scrollbar(
            format_info_frame,
            command=format_info_text.yview
        )
        format_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        format_info_text.config(yscrollcommand=format_scrollbar.set)
        
        # 按钮框架
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        import_options_frame = ttk.Frame(button_frame)
        import_options_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.allow_duplicates = tk.BooleanVar(value=False)
        allow_duplicates_check = ttk.Checkbutton(
            import_options_frame,
            text="允许重复卡片",
            variable=self.allow_duplicates
        )
        allow_duplicates_check.pack(side=tk.LEFT)
        
        # 重置按钮
        reset_button = ttk.Button(
            button_frame,
            text="重置",
            command=self.reset_import_form
        )
        reset_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        import_button = ttk.Button(
            button_frame,
            text="导入",
            command=self.import_cards,
            style="Accent.TButton"
        )
        import_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        if hasattr(self, 'dialog'):
            cancel_button = ttk.Button(
                button_frame,
                text="取消",
                command=self.dialog.destroy
            )
            cancel_button.pack(side=tk.RIGHT)
    
    def create_export_tab(self, parent):
        # 导出说明
        export_info = ttk.Label(
            parent,
            text="请选择导出格式和目标",
            font=("SimHei", 12, "bold")
        )
        export_info.pack(anchor=tk.W, pady=(10, 20))
        
        # 导出方式选择
        options_frame = ttk.Frame(parent)
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.export_method = tk.StringVar(value="text")
        text_format_radio = ttk.Radiobutton(
            options_frame,
            text="文本格式（显示在界面上）",
            variable=self.export_method,
            value="text",
            command=self.on_export_method_change
        )
        text_format_radio.pack(anchor=tk.W, pady=(0, 10))
        
        file_export_radio = ttk.Radiobutton(
            options_frame,
            text="导出到文件",
            variable=self.export_method,
            value="file",
            command=self.on_export_method_change
        )
        file_export_radio.pack(anchor=tk.W, pady=(0, 10))
        
        # 导出格式选项
        export_format_frame = ttk.Frame(options_frame)
        export_format_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(
            export_format_frame,
            text="导出格式:",
            font=("SimHei", 10)
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.group_by_keyword = tk.BooleanVar(value=False)
        group_by_keyword_check = ttk.Checkbutton(
            export_format_frame,
            text="按关键词分组",
            variable=self.group_by_keyword
        )
        group_by_keyword_check.pack(side=tk.LEFT)
        
        # 文本输出框
        self.text_output_frame = ttk.Frame(parent)
        self.text_output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.export_text = tk.Text(
            self.text_output_frame,
            width=60,
            height=10,
            font=("SimHei", 12),
            wrap=tk.WORD
        )
        self.export_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.export_text.config(state=tk.DISABLED)
        
        text_scrollbar = ttk.Scrollbar(
            self.text_output_frame,
            command=self.export_text.yview
        )
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.export_text.config(yscrollcommand=text_scrollbar.set)
        
        # 文件保存框架（初始隐藏）
        self.file_save_frame = ttk.Frame(parent)
        self.save_path_var = tk.StringVar()
        save_path_entry = ttk.Entry(
            self.file_save_frame,
            textvariable=self.save_path_var,
            width=50,
            font=("SimHei", 12)
        )
        save_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        save_select_button = ttk.Button(
            self.file_save_frame,
            text="浏览...",
            command=self.select_export_file
        )
        save_select_button.pack(side=tk.LEFT)
        
        # 按钮框架
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.copy_button = ttk.Button(
            button_frame,
            text="复制到剪贴板",
            command=self.copy_to_clipboard
        )
        
        export_button = ttk.Button(
            button_frame,
            text="导出",
            command=self.export_cards,
            style="Accent.TButton"
        )
        export_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        if hasattr(self, 'dialog'):
            cancel_button = ttk.Button(
                button_frame,
                text="取消",
                command=self.dialog.destroy
            )
            cancel_button.pack(side=tk.RIGHT)
        
        self.copy_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    def on_import_method_change(self):
        self.text_input_frame.pack_forget()
        self.file_select_frame.pack_forget()
        if self.import_method.get() == "text":
            self.text_input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        else:
            self.file_select_frame.pack(fill=tk.X, pady=(0, 20))
    
    def on_export_method_change(self):
        self.text_output_frame.pack_forget()
        self.file_save_frame.pack_forget()
        self.copy_button.pack_forget()
        if self.export_method.get() == "text":
            self.text_output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            self.copy_button.pack(side=tk.RIGHT, padx=(0, 10))
        else:
            self.file_save_frame.pack(fill=tk.X, pady=(0, 20))
    
    def select_import_file(self):
        file_path = filedialog.askopenfilename(
            title="选择导入文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def select_export_file(self):
        file_path = filedialog.asksaveasfilename(
            title="选择导出文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.save_path_var.set(file_path)
    
    def import_cards(self):
        try:
            if self.import_method.get() == "text":
                text = self.import_text.get(1.0, tk.END).strip()
                if not text:
                    messagebox.showwarning("警告", "请输入要导入的文本")
                    return
            else:
                file_path = self.file_path_var.get().strip()
                if not file_path:
                    messagebox.showwarning("警告", "请选择要导入的文件")
                    return
                if not os.path.exists(file_path):
                    messagebox.showerror("错误", "指定的文件不存在")
                    return
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                if not text:
                    messagebox.showwarning("警告", "选择的文件为空")
                    return
            
            allow_duplicates = self.allow_duplicates.get()
            stats = self.card_manager.import_cards_from_text(text, allow_duplicates, interactive=False)
            
            message = f"导入完成！\n" \
                      f"总计: {stats['total']} 张卡片\n" \
                      f"新增: {stats['added']} 张卡片\n" \
                      f"合并: {stats['merged']} 张卡片\n" \
                      f"失败: {stats['failed']} 张卡片"
            messagebox.showinfo("导入结果", message)
            
            # 导入完成后返回概览页面并刷新列表
            self.main_window.show_overview()
            
            if hasattr(self, 'dialog'):
                self.dialog.destroy()
        
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {str(e)}")
    
    def export_cards(self):
        try:
            group_by_keyword = self.group_by_keyword.get()
            text = self.card_manager.export_cards_to_text(group_by_keyword)
            
            if self.export_method.get() == "text":
                self.export_text.config(state=tk.NORMAL)
                self.export_text.delete(1.0, tk.END)
                self.export_text.insert(tk.END, text)
                self.export_text.config(state=tk.DISABLED)
                self.copy_button.config(state=tk.NORMAL)
                messagebox.showinfo("成功", f"成功导出 {len(self.card_manager.get_all_cards())} 张卡片")
            else:
                file_path = self.save_path_var.get().strip()
                if not file_path:
                    messagebox.showwarning("警告", "请选择要保存的文件")
                    return
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                messagebox.showinfo("成功", f"成功导出 {len(self.card_manager.get_all_cards())} 张卡片到文件")
                
                # 导出完成后返回概览页面
                self.main_window.show_overview()
                
                if hasattr(self, 'dialog'):
                    self.dialog.destroy()
        
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def copy_to_clipboard(self):
        text = self.export_text.get(1.0, tk.END)
        self.parent.clipboard_clear()
        self.parent.clipboard_append(text)
        messagebox.showinfo("成功", "已复制到剪贴板")
    
    def reset_import_form(self):
        """重置导入表单"""
        # 清空文本输入框
        if hasattr(self, 'import_text'):
            self.import_text.delete(1.0, tk.END)
        
        # 清空文件路径
        if hasattr(self, 'file_path_var'):
            self.file_path_var.set("")
        
        # 重置选项
        if hasattr(self, 'allow_duplicates'):
            self.allow_duplicates.set(False)
        
        # 重置导入方式为文本格式
        if hasattr(self, 'import_method'):
            self.import_method.set("text")
            self.on_import_method_change()
        
        # 显示提示信息
        if hasattr(self.main_window, 'status_var'):
            self.main_window.status_var.set("导入表单已重置")

# -------------------------- 主窗口框架（确保软件能独立运行）--------------------------
class CardView:
    """卡片视图（简化版，仅用于刷新界面）"""
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(self.frame, text="古文卡片列表（导入后刷新显示）", font=("SimHei", 14)).pack(pady=20)
    
    def refresh(self):
        """刷新卡片列表（这里简化为提示，可按需扩展）"""
        messagebox.showinfo("提示", "卡片列表已刷新！")

class MainWindow:
    """主窗口"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("古文卡片学习软件")
        self.root.geometry("800x600")
        
        # 主题颜色（给导入导出对话框用）
        self.colors = {
            "primary": "#2196F3",
            "secondary": "#4CAF50",
            "text": "#333333"
        }
        
        # 初始化卡片管理器和视图
        self.card_manager = CardManager()
        self.card_view = CardView(self.root)
        
        # 顶部按钮栏
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # 导入导出按钮
        self.import_export_btn = ttk.Button(
            btn_frame,
            text="导入导出卡片",
            command=self.open_import_export_dialog,
            style="Accent.TButton"
        )
        self.import_export_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 运行主循环
        self.root.mainloop()
    
    def open_import_export_dialog(self):
        """打开导入导出对话框"""
        ImportExportDialog(self.root, self.card_manager, self, mode="both")

# -------------------------- 运行软件 --------------------------
if __name__ == "__main__":
    # 注册ttk主题（确保按钮样式正常）
    style = ttk.Style()
    style.configure("Accent.TButton", foreground="white", background="#2196F3")
    # 启动主窗口
    MainWindow()