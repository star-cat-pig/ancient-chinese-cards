#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
搜索面板类，负责卡片的搜索功能
"""

import tkinter as tk
from tkinter import ttk, font
import re
from typing import List, Dict, Any

class SearchPanel:
    """搜索面板类"""
    
    def __init__(self, parent, card_manager, main_window):
        """
        初始化搜索面板
        
        Args:
            parent: 父窗口组件
            card_manager: 卡片管理器实例
            main_window: 主窗口实例
        """
        self.parent = parent
        self.card_manager = card_manager
        self.main_window = main_window
        
        # 设置主题颜色
        self.colors = main_window.colors
        
        # 搜索结果
        self.search_results = []
        
        # 创建搜索面板界面
        self.create_search_panel()
    
    def create_search_panel(self):
        """创建搜索面板界面"""
        # 创建主框架
        self.search_frame = ttk.Frame(self.parent)
        self.search_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建搜索框框架
        search_box_frame = ttk.Frame(self.search_frame)
        search_box_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 搜索输入框
        ttk.Label(
            search_box_frame,
            text="搜索:",
            font=("SimHei", 12)
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_box_frame,
            textvariable=self.search_var,
            width=50,
            font=("SimHei", 12)
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 搜索按钮
        search_button = ttk.Button(
            search_box_frame,
            text="搜索",
            command=self.perform_search,
            style="Accent.TButton"
        )
        search_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清除按钮
        clear_button = ttk.Button(
            search_box_frame,
            text="清除",
            command=self.clear_search
        )
        clear_button.pack(side=tk.LEFT)
        
        # 搜索选项框架
        options_frame = ttk.Frame(self.search_frame)
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 搜索范围选项
        ttk.Label(
            options_frame,
            text="搜索范围:",
            font=("SimHei", 12)
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # 创建搜索范围复选框
        self.search_in_keyword = tk.BooleanVar(value=True)
        self.search_in_definition = tk.BooleanVar(value=True)
        self.search_in_source = tk.BooleanVar(value=True)
        self.search_in_quote = tk.BooleanVar(value=True)
        self.search_in_notes = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(
            options_frame,
            text="关键词",
            variable=self.search_in_keyword
        ).grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        ttk.Checkbutton(
            options_frame,
            text="释义",
            variable=self.search_in_definition
        ).grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        
        ttk.Checkbutton(
            options_frame,
            text="出处",
            variable=self.search_in_source
        ).grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        
        ttk.Checkbutton(
            options_frame,
            text="原文",
            variable=self.search_in_quote
        ).grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        
        ttk.Checkbutton(
            options_frame,
            text="注释",
            variable=self.search_in_notes
        ).grid(row=0, column=5, sticky=tk.W, padx=(0, 10))
        
        # 搜索选项
        ttk.Label(
            options_frame,
            text="搜索选项:",
            font=("SimHei", 12)
        ).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        # 区分大小写
        self.case_sensitive = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="区分大小写",
            variable=self.case_sensitive
        ).grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        # 正则表达式
        self.use_regex = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="使用正则表达式",
            variable=self.use_regex
        ).grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        # 搜索结果框架
        results_frame = ttk.Frame(self.search_frame)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # 结果标题
        self.results_title_var = tk.StringVar()
        self.results_title_var.set("搜索结果")
        
        ttk.Label(
            results_frame,
            textvariable=self.results_title_var,
            font=("SimHei", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # 结果列表框架
        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建结果列表
        self.results_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            width=80,
            height=15,
            font=("SimHei", 10)
        )
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定滚动条
        scrollbar.config(command=self.results_listbox.yview)
        
        # 绑定列表框事件
        self.results_listbox.bind('<<ListboxSelect>>', self.on_result_select)
        self.results_listbox.bind('<Double-1>', self.on_result_double_click)
        
        # 绑定搜索框事件
        self.search_entry.bind('<Return>', lambda event: self.perform_search())
        
        # 结果操作按钮框架
        buttons_frame = ttk.Frame(results_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            buttons_frame,
            text="查看详情",
            command=self.view_selected_result
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            buttons_frame,
            text="编辑选中",
            command=self.edit_selected_result
        ).pack(side=tk.LEFT, padx=(0, 10))
    
    def perform_search(self):
        """执行搜索"""
        # 获取搜索关键词
        query = self.search_var.get().strip()
        if not query:
            return
        
        # 获取搜索选项
        case_sensitive = self.case_sensitive.get()
        use_regex = self.use_regex.get()
        
        # 获取搜索范围
        search_fields = []
        if self.search_in_keyword.get():
            search_fields.append('keyword')
        if self.search_in_definition.get():
            search_fields.append('definition')
        if self.search_in_source.get():
            search_fields.append('source')
        if self.search_in_quote.get():
            search_fields.append('quote')
        if self.search_in_notes.get():
            search_fields.append('notes')
        
        # 如果没有选择搜索范围，默认搜索所有字段
        if not search_fields:
            search_fields = ['keyword', 'definition', 'source', 'quote', 'notes']
        
        # 获取所有卡片
        all_cards = self.card_manager.get_all_cards()
        
        # 执行搜索
        self.search_results = []
        
        try:
            for card in all_cards:
                # 检查每个字段
                for field in search_fields:
                    field_value = card.get(field, '')
                    if not field_value:
                        continue
                    
                    # 转换为字符串
                    field_value = str(field_value)
                    
                    # 根据搜索选项执行搜索
                    if use_regex:
                        # 使用正则表达式搜索
                        flags = 0 if case_sensitive else re.IGNORECASE
                        if re.search(query, field_value, flags):
                            self.search_results.append(card)
                            break
                    else:
                        # 使用普通文本搜索
                        if case_sensitive:
                            if query in field_value:
                                self.search_results.append(card)
                                break
                        else:
                            if query.lower() in field_value.lower():
                                self.search_results.append(card)
                                break
            
            # 更新结果列表
            self.update_results_list()
            
            # 更新结果标题
            self.results_title_var.set(f"搜索结果: 找到 {len(self.search_results)} 项")
        
        except Exception as e:
            # 处理正则表达式错误
            if use_regex:
                tk.messagebox.showerror("错误", f"正则表达式错误: {str(e)}")
            else:
                tk.messagebox.showerror("错误", f"搜索错误: {str(e)}")
    
    def update_results_list(self):
        """更新结果列表"""
        # 清空列表
        self.results_listbox.delete(0, tk.END)
        
        # 添加搜索结果
        for card in self.search_results:
            # 格式化显示内容
            display_text = f"{card['keyword']} - {card['definition']}"
            self.results_listbox.insert(tk.END, display_text)
    
    def on_result_select(self, event):
        """结果选中事件处理"""
        # 获取选中的索引
        selection = self.results_listbox.curselection()
        if not selection:
            return
        
        # 获取选中的卡片
        index = selection[0]
        if index < len(self.search_results):
            card = self.search_results[index]
            # 这里可以显示卡片预览
            pass
    
    def on_result_double_click(self, event):
        """结果双击事件处理"""
        # 获取选中的索引
        selection = self.results_listbox.curselection()
        if not selection:
            return
        
        # 获取选中的卡片
        index = selection[0]
        if index < len(self.search_results):
            card = self.search_results[index]
            # 查看卡片详情
            self.view_card_detail(card)
    
    def view_selected_result(self):
        """查看选中的结果"""
        # 获取选中的索引
        selection = self.results_listbox.curselection()
        if not selection:
            return
        
        # 获取选中的卡片
        index = selection[0]
        if index < len(self.search_results):
            card = self.search_results[index]
            # 查看卡片详情
            self.view_card_detail(card)
    
    def edit_selected_result(self):
        """编辑选中的结果"""
        # 获取选中的索引
        selection = self.results_listbox.curselection()
        if not selection:
            return
        
        # 获取选中的卡片
        index = selection[0]
        if index < len(self.search_results):
            card = self.search_results[index]
            # 编辑卡片
            self.main_window.show_add_card()
            self.main_window.card_editor.load_card(card['id'])
    
    def view_card_detail(self, card):
        """查看卡片详情"""
        # 创建详情对话框
        detail_window = tk.Toplevel(self.parent)
        detail_window.title(f"卡片详情: {card['keyword']}")
        detail_window.geometry("600x400")
        detail_window.transient(self.parent)
        detail_window.grab_set()
        
        # 设置主题颜色
        detail_window.configure(bg=self.colors['bg'])
        
        # 创建详情框架
        detail_frame = ttk.Frame(detail_window, padding=20)
        detail_frame.pack(fill=tk.BOTH, expand=True)
        
        # 关键词
        ttk.Label(
            detail_frame,
            text="关键词:",
            font=("SimHei", 12, "bold"),
            background=self.colors['bg']
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(
            detail_frame,
            text=card['keyword'],
            font=("SimHei", 12),
            background=self.colors['bg']
        ).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # 释义
        ttk.Label(
            detail_frame,
            text="释义:",
            font=("SimHei", 12, "bold"),
            background=self.colors['bg']
        ).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(
            detail_frame,
            text=card['definition'],
            font=("SimHei", 12),
            background=self.colors['bg']
        ).grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # 出处
        ttk.Label(
            detail_frame,
            text="出处:",
            font=("SimHei", 12, "bold"),
            background=self.colors['bg']
        ).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(
            detail_frame,
            text=card['source'],
            font=("SimHei", 12),
            background=self.colors['bg']
        ).grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # 原文引用
        ttk.Label(
            detail_frame,
            text="原文引用:",
            font=("SimHei", 12, "bold"),
            background=self.colors['bg']
        ).grid(row=3, column=0, sticky=tk.NW, pady=(0, 5))
        
        ttk.Label(
            detail_frame,
            text=card['quote'],
            font=("SimHei", 12),
            background=self.colors['bg'],
            wraplength=400
        ).grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        
        # 注释
        ttk.Label(
            detail_frame,
            text="注释:",
            font=("SimHei", 12, "bold"),
            background=self.colors['bg']
        ).grid(row=4, column=0, sticky=tk.NW, pady=(0, 5))
        
        notes_text = tk.Text(
            detail_frame,
            width=50,
            height=6,
            font=("SimHei", 12),
            wrap=tk.WORD
        )
        notes_text.grid(row=4, column=1, sticky=tk.NSEW, pady=(0, 5))
        notes_text.insert(tk.END, card.get('notes', ''))
        notes_text.config(state=tk.DISABLED)
        
        # 添加滚动条
        notes_scrollbar = ttk.Scrollbar(
            detail_frame,
            command=notes_text.yview
        )
        notes_scrollbar.grid(row=4, column=2, sticky=tk.NS)
        notes_text.config(yscrollcommand=notes_scrollbar.set)
        
        # 设置列权重
        detail_frame.columnconfigure(1, weight=1)
        detail_frame.rowconfigure(4, weight=1)
        
        # 按钮框架
        button_frame = ttk.Frame(detail_window)
        button_frame.pack(fill=tk.X, pady=(20, 0), padx=20)
        
        # 编辑按钮
        edit_button = ttk.Button(
            button_frame,
            text="编辑",
            command=lambda: self.edit_card(card['id'], detail_window)
        )
        edit_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 关闭按钮
        close_button = ttk.Button(
            button_frame,
            text="关闭",
            command=detail_window.destroy
        )
        close_button.pack(side=tk.RIGHT)
    
    def edit_card(self, card_id, window):
        """编辑卡片"""
        # 关闭详情窗口
        window.destroy()
        
        # 切换到编辑视图
        self.main_window.show_add_card()
        self.main_window.card_editor.load_card(card_id)
    
    def clear_search(self):
        """清除搜索"""
        # 清空搜索框
        self.search_var.set("")
        
        # 清空结果列表
        self.results_listbox.delete(0, tk.END)
        
        # 重置结果标题
        self.results_title_var.set("搜索结果")
        
        # 清空搜索结果
        self.search_results = []
    
    def focus_search_entry(self):
        """聚焦搜索输入框"""
        self.search_entry.focus_set()