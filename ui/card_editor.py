#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
卡片编辑器类，负责卡片的创建和编辑
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional

class CardEditor:
    """卡片编辑器类"""
    
    def __init__(self, parent, card_manager, main_window):
        """
        初始化卡片编辑器
        
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
        
        # 当前编辑的卡片ID
        self.current_card_id = None
        
        # 从设置管理器加载上次使用的出处
        self.last_source = self._load_last_source()
        
        # 创建编辑器界面
        self.create_editor()
        

    
    def create_editor(self):
        """创建编辑器界面"""
        # 创建主框架
        self.editor_frame = ttk.Frame(self.parent)
        self.editor_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建标题
        title_frame = ttk.Frame(self.editor_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.title_var = tk.StringVar()
        self.title_var.set("添加新卡片")
        
        title_label = ttk.Label(
            title_frame,
            textvariable=self.title_var,
            font=("SimHei", 16, "bold")
        )
        title_label.pack(anchor=tk.W)
        
        # 创建表单框架
        form_frame = ttk.Frame(self.editor_frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # 关键词
        self.create_form_field(
            form_frame,
            "关键词（原文）:",
            "keyword",
            "请输入古文中的关键词或生僻字",
            row=0
        )
        
        # 释义
        self.create_form_field(
            form_frame,
            "释义（卡片正面）:",
            "definition",
            "请输入关键词的现代解释",
            row=1
        )
        
        # 出处
        self.create_form_field(
            form_frame,
            "出处:",
            "source",
            "请输入引用的古籍名称，如《论语》",
            row=2
        )
        
        # 原文引用
        self.create_form_field(
            form_frame,
            "原文引用:",
            "quote",
            "请输入包含关键词的原文句子",
            row=3
        )
        
        # 注释
        ttk.Label(
            form_frame,
            text="注释（可选）:",
            font=("SimHei", 12)
        ).grid(row=4, column=0, sticky=tk.W, pady=(15, 5))
        
        self.notes_text = tk.Text(
            form_frame,
            width=60,
            height=4,  # 减小高度
            font=("SimHei", 11),  # 减小字体
            wrap=tk.WORD
        )
        self.notes_text.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW, pady=(0, 15))
        
        # 添加滚动条
        notes_scrollbar = ttk.Scrollbar(
            form_frame,
            command=self.notes_text.yview
        )
        notes_scrollbar.grid(row=5, column=2, sticky=tk.NS)
        self.notes_text.config(yscrollcommand=notes_scrollbar.set)
        
        # 设置表单框架的列权重和行权重，使其能够自适应窗口大小
        form_frame.columnconfigure(1, weight=1)
        form_frame.rowconfigure(1, weight=1)  # 关键词
        form_frame.rowconfigure(3, weight=1)  # 释义
        form_frame.rowconfigure(5, weight=1)  # 注释
        form_frame.rowconfigure(7, weight=1)  # 原文引用
        form_frame.rowconfigure(9, weight=1)  # 出处
        
        # 创建按钮框架
        button_frame = ttk.Frame(self.editor_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 取消按钮
        cancel_button = ttk.Button(
            button_frame,
            text="取消",
            command=self.cancel_edit
        )
        cancel_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 保存按钮
        save_button = ttk.Button(
            button_frame,
            text="保存",
            command=self.save_card,
            style="Accent.TButton"
        )
        save_button.pack(side=tk.RIGHT)
        
        # 创建底部说明文字
        bottom_frame = ttk.Frame(self.editor_frame)
        bottom_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.status_var = tk.StringVar()
        self.status_var.set("添加新的卡片（enter换行）")
        
        status_label = ttk.Label(
            bottom_frame,
            textvariable=self.status_var,
            font=("SimHei", 10),
            foreground="#666666"
        )
        status_label.pack(anchor=tk.W)
    
    def create_form_field(self, parent, label_text, field_name, placeholder, row):
        """
        创建表单字段
        
        Args:
            parent: 父窗口组件
            label_text: 标签文本
            field_name: 字段名称
            placeholder: 占位符文本
            row: 行号
        """
        # 创建标签
        ttk.Label(
            parent,
            text=label_text,
            font=("SimHei", 12)
        ).grid(row=row, column=0, sticky=tk.W, pady=(10, 5))
        
        # 创建输入框
        field_var = tk.StringVar()
        setattr(self, f"{field_name}_var", field_var)
        
        field_entry = ttk.Entry(
            parent,
            textvariable=field_var,
            width=60,
            font=("SimHei", 12)
        )
        field_entry.grid(row=row, column=1, sticky=tk.NSEW, pady=(10, 5))
        
        # 保存输入框引用
        setattr(self, f"{field_name}_entry", field_entry)
        
        # 添加占位符效果
        field_entry.bind("<FocusIn>", lambda event, var=field_var, txt=placeholder: self.on_entry_focus_in(event, var, txt))
        field_entry.bind("<FocusOut>", lambda event, var=field_var, txt=placeholder: self.on_entry_focus_out(event, var, txt))
        
        # 添加回车键导航功能
        field_entry.bind("<Return>", lambda event, name=field_name: self.on_entry_return(event, name))
        
        # 为每个输入框单独绑定Ctrl+A全选快捷键（不区分大小写）
        field_entry.bind("<Control-a>", self.on_ctrl_a)
        field_entry.bind("<Control-A>", self.on_ctrl_a)
        
        # 设置默认占位符文本
        field_var.set(placeholder)
        field_entry.config(foreground="#999999")
    
    def on_entry_focus_in(self, event, var, placeholder):
        """输入框获得焦点事件处理"""
        if var.get() == placeholder:
            var.set("")
            event.widget.config(foreground="#000000")
    
    def on_entry_focus_out(self, event, var, placeholder):
        """输入框失去焦点事件处理"""
        if not var.get():
            var.set(placeholder)
            event.widget.config(foreground="#999999")
    
    def on_entry_return(self, event, field_name):
        """处理输入框的回车键事件，实现导航功能"""
        try:
            # 定义输入框的导航顺序
            navigation_order = ['keyword', 'definition', 'source', 'quote']
            
            # 找到当前字段在导航顺序中的索引
            if field_name in navigation_order:
                current_index = navigation_order.index(field_name)
                
                # 特殊处理：从释义到出处
                if field_name == 'definition' and current_index + 1 < len(navigation_order):
                    next_field = navigation_order[current_index + 1]  # source
                    next_entry = getattr(self, f"{next_field}_entry", None)
                    next_var = getattr(self, f"{next_field}_var", None)
                    
                    if next_entry and next_var:
                        # 检查是否启用了自动填充出处（简化版本，直接检查设置）
                        auto_fill_source = self.get_auto_fill_setting()
                        
                        # 如果启用了自动填充且有上次的出处
                        if auto_fill_source and self.last_source:
                            placeholder = self.get_placeholder_for_field(next_field)
                            current_value = next_var.get()
                            
                            print(f"自动填充检查: 启用={auto_fill_source}, 上次出处='{self.last_source}', 当前值='{current_value}', 占位符='{placeholder}'")
                            
                            if current_value == placeholder or not current_value:
                                # 填充上次的出处
                                next_var.set(self.last_source)
                                next_entry.config(foreground="#000000")
                                # 全选内容
                                next_entry.select_range(0, tk.END)
                                next_entry.icursor(tk.END)
                                print("已自动填充出处并全选")
                        else:
                            # 正常清除占位符
                            placeholder = self.get_placeholder_for_field(next_field)
                            if next_var.get() == placeholder:
                                next_var.set("")
                                next_entry.config(foreground="#000000")
                        
                        # 设置焦点
                        next_entry.focus_set()
                # 其他字段的正常导航
                elif current_index < len(navigation_order) - 1:
                    next_field = navigation_order[current_index + 1]
                    next_entry = getattr(self, f"{next_field}_entry", None)
                    if next_entry:
                        # 清除占位符文本
                        next_var = getattr(self, f"{next_field}_var", None)
                        placeholder = self.get_placeholder_for_field(next_field)
                        if next_var and next_var.get() == placeholder:
                            next_var.set("")
                            next_entry.config(foreground="#000000")
                        # 设置焦点
                        next_entry.focus_set()
                else:
                    # 如果是最后一个字段（原文引用），直接保存
                    self.save_card()
        except Exception as e:
            print(f"导航错误: {str(e)}")
        
        # 阻止默认的回车键行为
        return "break"
    
    def get_placeholder_for_field(self, field_name):
        """获取字段对应的占位符文本"""
        placeholders = {
            'keyword': '请输入古文中的关键词或生僻字',
            'definition': '请输入关键词的现代解释',
            'source': '请输入引用的古籍名称，如《论语》',
            'quote': '请输入包含关键词的原文句子'
        }
        return placeholders.get(field_name, '')
    
    def get_auto_fill_setting(self):
        """获取自动填充设置"""
        try:
            # 首先尝试从主窗口获取设置管理器
            if hasattr(self.main_window, 'app') and hasattr(self.main_window.app, 'settings_manager'):
                return self.main_window.app.settings_manager.get_setting("editor", "auto_fill_source", False)
            
            # 如果主窗口没有app属性，尝试直接从主窗口获取设置
            elif hasattr(self.main_window, 'settings_manager'):
                return self.main_window.settings_manager.get_setting("editor", "auto_fill_source", False)
            
            # 如果都不行，尝试从卡片管理器获取
            elif hasattr(self.card_manager, 'settings_manager'):
                return self.card_manager.settings_manager.get_setting("editor", "auto_fill_source", False)
        except Exception as e:
            print(f"获取自动填充设置错误: {str(e)}")
        
        # 默认返回False
        return False
    
    def _load_last_source(self):
        """从设置管理器加载上次使用的出处"""
        try:
            # 首先尝试从主窗口获取设置管理器
            if hasattr(self.main_window, 'app') and hasattr(self.main_window.app, 'settings_manager'):
                return self.main_window.app.settings_manager.get_setting("editor", "last_source", "")
            
            # 如果主窗口没有app属性，尝试直接从主窗口获取设置
            elif hasattr(self.main_window, 'settings_manager'):
                return self.main_window.settings_manager.get_setting("editor", "last_source", "")
            
            # 如果都不行，尝试从卡片管理器获取
            elif hasattr(self.card_manager, 'settings_manager'):
                return self.card_manager.settings_manager.get_setting("editor", "last_source", "")
        except Exception as e:
            print(f"加载上次出处错误: {str(e)}")
        
        # 默认返回空字符串
        return ""
    
    def _save_last_source(self, source):
        """保存上次使用的出处到设置管理器"""
        try:
            # 首先尝试从主窗口获取设置管理器
            if hasattr(self.main_window, 'app') and hasattr(self.main_window.app, 'settings_manager'):
                self.main_window.app.settings_manager.set_setting("editor", "last_source", source)
                self.main_window.app.settings_manager.save_preferences()
                return True
            
            # 如果主窗口没有app属性，尝试直接从主窗口获取设置
            elif hasattr(self.main_window, 'settings_manager'):
                self.main_window.settings_manager.set_setting("editor", "last_source", source)
                self.main_window.settings_manager.save_preferences()
                return True
            
            # 如果都不行，尝试从卡片管理器获取
            elif hasattr(self.card_manager, 'settings_manager'):
                self.card_manager.settings_manager.set_setting("editor", "last_source", source)
                self.card_manager.settings_manager.save_preferences()
                return True
        except Exception as e:
            print(f"保存上次出处错误: {str(e)}")
        
        return False
    
    def on_ctrl_a(self, event):
        """处理Ctrl+A全选快捷键"""
        # 获取当前焦点所在的输入框
        focused_widget = self.parent.focus_get()
        if focused_widget and hasattr(focused_widget, 'select_range'):
            # 全选输入框内容
            focused_widget.select_range(0, tk.END)
            focused_widget.icursor(tk.END)
            # 阻止默认行为
            return "break"
        return None
    
    def on_field_change(self, var, field_name):
        """
        输入框内容变化事件处理
        
        Args:
            var: StringVar对象
            field_name: 字段名称
        """
        # 获取当前值
        current_value = var.get()
        
        # 获取占位符文本
        placeholders = {
            'keyword': '请输入古文中的关键词或生僻字',
            'definition': '请输入关键词的现代解释',
            'source': '请输入引用的古籍名称，如《论语》',
            'quote': '请输入包含关键词的原文句子'
        }
        
        # 如果是占位符文本，不执行任何操作
        if field_name in placeholders and current_value == placeholders[field_name]:
            return
    
    def on_text_change(self):
        """文本框内容变化事件处理"""
        # 文本框变化时不需要特殊处理
        pass
    

    

    
    def load_card(self, card_id: str):
        """
        加载卡片数据进行编辑
        
        Args:
            card_id: 卡片ID
        """
        # 获取卡片数据
        card = self.card_manager.get_card(card_id)
        if not card:
            messagebox.showerror("错误", "找不到指定的卡片")
            return
        
        # 设置当前编辑的卡片ID
        self.current_card_id = card_id
        
        # 更新标题
        self.title_var.set("编辑卡片")
        
        # 填充表单数据
        self.keyword_var.set(card['keyword'])
        self.definition_var.set(card['definition'])
        self.source_var.set(card['source'])
        self.quote_var.set(card['quote'])
        self.notes_text.delete(1.0, tk.END)
        self.notes_text.insert(tk.END, card['notes'])
        
        # 确保文本框显示正常颜色
        for field_name in ['keyword', 'definition', 'source', 'quote']:
            field_var = getattr(self, f"{field_name}_var")
            # 使用之前保存的输入框引用
            field_entry = getattr(self, f"{field_name}_entry", None)
            if field_entry:
                # 直接设置为正常颜色，因为这是从数据库加载的实际内容
                field_entry.config(foreground="#000000")
    
    def reset_form(self):
        """重置表单"""
        # 清除当前编辑的卡片ID
        self.current_card_id = None
        
        # 重置标题
        self.title_var.set("添加新卡片")
        
        # 清除表单数据
        placeholders = {
            'keyword': '请输入古文中的关键词或生僻字',
            'definition': '请输入关键词的现代解释',
            'source': '请输入引用的古籍名称，如《论语》',
            'quote': '请输入包含关键词的原文句子'
        }
        
        for field_name, placeholder in placeholders.items():
            field_var = getattr(self, f"{field_name}_var")
            field_var.set(placeholder)
            # 使用保存的输入框引用
            field_entry = getattr(self, f"{field_name}_entry")
            field_entry.config(foreground="#999999")
        
        self.notes_text.delete(1.0, tk.END)
    
    def focus_first_field(self):
        """聚焦到第一个输入字段（关键词字段）"""
        try:
            keyword_entry = getattr(self, "keyword_entry", None)
            if keyword_entry:
                # 给界面一点时间更新，然后聚焦
                self.parent.after(100, lambda: self.activate_keyword_field())
        except Exception as e:
            print(f"聚焦到第一个字段时出错: {str(e)}")
    
    def activate_keyword_field(self):
        """激活关键词字段并清除占位符"""
        try:
            keyword_entry = getattr(self, "keyword_entry", None)
            keyword_var = getattr(self, "keyword_var", None)
            
            if keyword_entry and keyword_var:
                # 聚焦到关键词输入框
                keyword_entry.focus_set()
                
                # 如果当前是占位符文本，则清除
                placeholder = '请输入古文中的关键词或生僻字'
                if keyword_var.get() == placeholder:
                    keyword_var.set("")
                    keyword_entry.config(foreground="#000000")
        except Exception as e:
            print(f"激活关键词字段时出错: {str(e)}")
    
    def validate_form(self) -> bool:
        """
        验证表单数据
        
        Returns:
            bool: 表单数据是否有效
        """
        # 获取表单数据
        keyword = self.keyword_var.get().strip()
        definition = self.definition_var.get().strip()
        source = self.source_var.get().strip()
        quote = self.quote_var.get().strip()
        
        # 检查必填字段
        if not keyword or keyword == '请输入古文中的关键词或生僻字':
            messagebox.showwarning("警告", "请输入关键词")
            return False
        
        if not definition or definition == '请输入关键词的现代解释':
            messagebox.showwarning("警告", "请输入释义")
            return False
        
        if not source or source == '请输入引用的古籍名称，如《论语》':
            messagebox.showwarning("警告", "请输入出处")
            return False
        
        if not quote or quote == '请输入包含关键词的原文句子':
            messagebox.showwarning("警告", "请输入原文引用")
            return False
        
        return True
    
    def get_form_data(self) -> Dict[str, Any]:
        """
        获取表单数据
        
        Returns:
            Dict[str, Any]: 表单数据
        """
        # 获取表单数据
        keyword = self.keyword_var.get().strip()
        definition = self.definition_var.get().strip()
        source = self.source_var.get().strip()
        quote = self.quote_var.get().strip()
        notes = self.notes_text.get(1.0, tk.END).strip()
        
        # 处理占位符文本
        if keyword == '请输入古文中的关键词或生僻字':
            keyword = ''
        
        if definition == '请输入关键词的现代解释':
            definition = ''
        
        if source == '请输入引用的古籍名称，如《论语》':
            source = ''
        
        if quote == '请输入包含关键词的原文句子':
            quote = ''
        
        # 返回表单数据
        return {
            'keyword': keyword,
            'definition': definition,
            'source': source,
            'quote': quote,
            'notes': notes,
            'tags': []
        }
    
    def save_card(self):
        """保存卡片"""
        # 验证表单
        if not self.validate_form():
            return
        
        # 获取表单数据
        card_data = self.get_form_data()
        
        try:
            if self.current_card_id:
                # 更新卡片
                if self.card_manager.update_card(self.current_card_id, card_data):
                    # 保存上次使用的出处到设置管理器
                    if card_data.get('source'):
                        self.last_source = card_data['source']
                        self._save_last_source(card_data['source'])
                    # 不显示成功弹窗，直接返回概览页面
                    self.reset_form()
                    self.main_window.show_overview()
                else:
                    messagebox.showerror("错误", "更新卡片失败")
            else:
                # 添加新卡片
                card_id = self.card_manager.add_card(card_data)
                if card_id:
                    # 保存上次使用的出处到设置管理器
                    if card_data.get('source'):
                        self.last_source = card_data['source']
                        self._save_last_source(card_data['source'])
                    # 不显示成功弹窗，直接返回概览页面
                    self.reset_form()
                    self.main_window.show_overview()
                else:
                    messagebox.showerror("错误", "添加卡片失败")
        except Exception as e:
            messagebox.showerror("错误", f"保存卡片失败: {str(e)}")
    
    def cancel_edit(self):

        """取消编辑"""
        # 询问是否放弃更改
        if self.has_form_changes():
            if messagebox.askyesno("确认", "是否放弃当前的更改？"):
                self.reset_form()
                self.main_window.show_overview()
        else:
            self.reset_form()
            self.main_window.show_overview()
    
    def has_form_changes(self) -> bool:
        """
        检查表单是否有更改
        
        Returns:
            bool: 表单是否有更改
        """
        # 如果是新卡片，检查是否有输入
        if not self.current_card_id:
            keyword = self.keyword_var.get().strip()
            definition = self.definition_var.get().strip()
            source = self.source_var.get().strip()
            quote = self.quote_var.get().strip()
            notes = self.notes_text.get(1.0, tk.END).strip()
            
            # 检查是否有非占位符的输入
            placeholders = [
                '请输入古文中的关键词或生僻字',
                '请输入关键词的现代解释',
                '请输入引用的古籍名称，如《论语》',
                '请输入包含关键词的原文句子'
            ]
            
            return (keyword and keyword not in placeholders) or \
                   (definition and definition not in placeholders) or \
                   (source and source not in placeholders) or \
                   (quote and quote not in placeholders) or \
                   notes
        
        # 如果是编辑卡片，检查是否与原数据不同
        else:
            card = self.card_manager.get_card(self.current_card_id)
            if not card:
                return False
            
            form_data = self.get_form_data()
            
            return form_data['keyword'] != card['keyword'] or \
                   form_data['definition'] != card['definition'] or \
                   form_data['source'] != card['source'] or \
                   form_data['quote'] != card['quote'] or \
                   form_data['notes'] != card['notes']