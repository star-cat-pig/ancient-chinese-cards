#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主窗口界面类
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import json
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ui.card_view import CardView
from ui.card_editor import CardEditor
from ui.search_panel import SearchPanel


class MainWindow:
    """主窗口界面类"""
    
    def __init__(self, root, card_manager, app=None):
        """
        初始化主窗口
        
        Args:
            root: tkinter根窗口
            card_manager: 卡片管理器实例
            app: 应用程序实例
        """
        self.root = root
        self.card_manager = card_manager
        self.app = app
        
        # 获取设置管理器
        self.settings_manager = app.settings_manager if app else None
        
        # 设置主题颜色
        self.colors = {
            'bg': '#F5F2E9',      # 米黄色背景
            'text': '#3A2E21',    # 深棕色文字
            'accent': '#C44536',  # 朱砂红强调色
            'card_bg': '#FFFFFF', # 卡片背景色
            'border': '#D3C5A9',  # 边框颜色
            'hover': '#E8E0D5'    # 悬停颜色
        }
        
        # 记录鼠标按键（用于区分左键和右键）
        self.last_mouse_button = 1  # 默认是左键
        self.selected_card_id = None  # 当前选中的卡片ID
        
        # 创建主框架
        self.create_main_frame()
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建左侧导航栏
        self.create_navigation()
        
        # 创建右侧内容区
        self.create_content_area()
        
        # 初始化视图
        self.show_overview()
        
        # 绑定事件
        self.bind_events()
        
        # 应用保存的窗口设置
        self.apply_window_settings()
        
        # 绑定窗口关闭事件以保存设置
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
    
    def create_main_frame(self):
        """创建主框架"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TFrame", background=self.colors['bg'])
        self.style.configure("TButton", 
                            background=self.colors['card_bg'],
                            foreground="#000000",  # 改为黑色字体
                            bordercolor=self.colors['border'])
        self.style.configure("TLabel", 
                            background=self.colors['bg'],
                            foreground=self.colors['text'])
        self.style.configure("TEntry", 
                            fieldbackground=self.colors['card_bg'],
                            foreground=self.colors['text'],
                            bordercolor=self.colors['border'])
        self.style.configure("Text", 
                            background=self.colors['card_bg'],
                            foreground=self.colors['text'])
        
        # 创建自定义样式
        self.style.configure("Accent.TButton",
                            background=self.colors['accent'],
                            foreground="#000000",  # 改为黑色字体
                            bordercolor=self.colors['accent'])
        self.style.map("Accent.TButton",
                      background=[("active", self.colors['accent']),
                                ("!active", self.colors['accent'])],
                      foreground=[("active", "#000000"),  # 改为黑色字体
                                ("!active", "#000000")])  # 改为黑色字体
        
        # 确保选中状态的文本颜色为黑色
        self.style.map("TEntry",
                      foreground=[("focus", "#000000"),
                                ("!focus", "#000000")])
        self.style.map("TCombobox",
                      foreground=[("focus", "#000000"),
                                ("!focus", "#000000")])
        
        self.style.configure("Card.TFrame",
                            background=self.colors['card_bg'],
                            borderwidth=1,
                            relief="raised")
        self.style.configure("CardHover.TFrame",
                            background=self.colors['hover'],
                            borderwidth=1,
                            relief="raised")
    
    def create_menu(self):
        """创建菜单栏"""
        self.menu_bar = tk.Menu(self.root)
        
        # 文件菜单
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        # 暂时移除保存和退出选项
        # self.file_menu.add_command(label="保存", command=self.save_cards)
        # self.file_menu.add_separator()
        # self.file_menu.add_command(label="退出", command=self.root.quit)
        self.menu_bar.add_cascade(label="文件", menu=self.file_menu)
        
        # 编辑菜单
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.edit_menu.add_command(label="添加卡片", command=self.show_add_card)
        self.menu_bar.add_cascade(label="编辑", menu=self.edit_menu)
        
        # 设置菜单
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.settings_menu.add_command(label="设置", command=self.show_settings)
        self.menu_bar.add_cascade(label="设置", menu=self.settings_menu)
        
        # 帮助菜单
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="使用帮助", command=self.show_help)
        self.help_menu.add_command(label="更新日志", command=self.show_update_log)
        self.help_menu.add_command(label="关于", command=self.show_about)
        self.menu_bar.add_cascade(label="帮助", menu=self.help_menu)
        
        # 设置菜单栏
        self.root.config(menu=self.menu_bar)
    
    def create_navigation(self):
        """创建左侧导航栏"""
        self.nav_frame = ttk.Frame(self.main_frame, width=200)
        self.nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 导航标题
        nav_title = ttk.Label(self.nav_frame, text="导航", font=("SimHei", 14, "bold"))
        nav_title.pack(pady=(0, 15))
        
        # 导航按钮
        self.nav_buttons = {}
        
        # 概览按钮
        self.nav_buttons['overview'] = ttk.Button(
            self.nav_frame, 
            text="卡片概览", 
            command=self.show_overview,
            width=15
        )
        self.nav_buttons['overview'].pack(pady=5)
        
        # 添加卡片按钮
        self.nav_buttons['add_card'] = ttk.Button(
            self.nav_frame, 
            text="添加卡片", 
            command=self.show_add_card,
            width=15
        )
        self.nav_buttons['add_card'].pack(pady=5)
        
        # 搜索按钮
        self.nav_buttons['search'] = ttk.Button(
            self.nav_frame, 
            text="搜索卡片", 
            command=self.show_search,
            width=15
        )
        self.nav_buttons['search'].pack(pady=5)
        
        # 导入按钮（暂时注释）
        # self.nav_buttons['import'] = ttk.Button(
        #     self.nav_frame, 
        #     text="导入卡片", 
        #     command=self.show_import_dialog,
        #     width=15
        # )
        # self.nav_buttons['import'].pack(pady=5)
        
        # 导出按钮
        self.nav_buttons['export'] = ttk.Button(
            self.nav_frame, 
            text="导出卡片", 
            command=self.show_import_export_dialog,
            width=15
        )
        self.nav_buttons['export'].pack(pady=5)
        
        # 设置当前选中的导航按钮
        self.current_nav = 'overview'
        self.highlight_nav_button(self.current_nav)
    
    def create_content_area(self):
        """创建右侧内容区"""
        # 创建主内容框架
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 创建状态栏区域
        self.status_frame = ttk.Frame(self.content_frame, height=30)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        # 创建状态栏
        self.status_bar = ttk.Label(
            self.status_frame,
            text="就绪",
            anchor=tk.W,
            background=self.colors['bg'],
            foreground=self.colors['text']
        )
        self.status_bar.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)
        
        # 创建内容区域
        self.content_area = ttk.Frame(self.content_frame)
        self.content_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 创建各个视图的容器
        self.views = {}
        
        # 概览视图 - 使用列表形式
        self.views['overview'] = ttk.Frame(self.content_area)
        
        # 添加卡片视图
        self.views['add_card'] = ttk.Frame(self.content_area)
        
        # 编辑卡片视图
        self.views['edit_card'] = ttk.Frame(self.content_area)
        
        # 搜索视图
        self.views['search'] = ttk.Frame(self.content_area)
        
        # 批量编辑视图
        # 批量编辑视图已移除
        
        # 初始化列表视图（替代卡片视图）
        self.create_list_view()
        
        # 初始化卡片编辑器
        self.card_editor = CardEditor(self.views['add_card'], self.card_manager, self)
        
        # 初始化搜索面板
        self.search_panel = SearchPanel(self.views['search'], self.card_manager, self)
    
    def highlight_nav_button(self, nav_name):
        """高亮显示当前选中的导航按钮"""
        # 重置所有按钮样式
        for name, button in self.nav_buttons.items():
            button.config(style="TButton")
        
        # 高亮当前选中的按钮
        if nav_name in self.nav_buttons:
            self.nav_buttons[nav_name].config(style="Accent.TButton")
            self.current_nav = nav_name
    
    def show_view(self, view_name):
        """显示指定的视图"""
        # 隐藏所有视图
        for view in self.views.values():
            view.pack_forget()
        
        # 显示指定的视图
        if view_name in self.views:
            self.views[view_name].pack(fill=tk.BOTH, expand=True)
        
        # 高亮对应的导航按钮
        self.highlight_nav_button(view_name)
    
    def show_overview(self):
        """显示卡片概览视图"""
        self.show_view('overview')
        self.refresh_list_view()
    
    def show_add_card(self):
        """显示添加卡片视图"""
        self.show_view('add_card')
        self.card_editor.reset_form()
    
    def show_edit_card(self, card_id):
        """显示编辑卡片视图 - 使用卡片形式的详情窗口"""
        card = self.card_manager.get_card(card_id)
        if not card:
            messagebox.showerror("错误", "找不到指定的卡片")
            return
        
        # 保存原始卡片数据用于比较
        original_card = card.copy()
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"编辑卡片 - {card['keyword']}")
        edit_window.geometry("600x500")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # 设置窗口图标（确保编辑窗口有图标）
        if hasattr(self.app, '_set_window_icon'):
            self.app._set_window_icon(edit_window)
        
        # 居中显示
        edit_window.update_idletasks()
        width = edit_window.winfo_width()
        height = edit_window.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2)
        y = (self.root.winfo_height() // 2) - (height // 2)
        edit_window.geometry('+{}+{}'.format(x, y))
        
        # 创建卡片框架
        card_frame = ttk.Frame(edit_window, padding=20, style="Card.TFrame")
        card_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建表单字段
        fields = []
        
        # 关键词
        ttk.Label(card_frame, text="关键词:", font=("SimHei", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        keyword_var = tk.StringVar(value=card['keyword'])
        keyword_entry = ttk.Entry(card_frame, textvariable=keyword_var, width=40)
        keyword_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        fields.append(('keyword', keyword_var))
        
        # 释义
        ttk.Label(card_frame, text="释义:", font=("SimHei", 12, "bold")).grid(row=1, column=0, sticky=tk.NW, pady=5)
        definition_text = tk.Text(card_frame, height=4, width=40, wrap=tk.WORD)
        definition_text.insert(tk.END, card['definition'])
        definition_text.grid(row=1, column=1, sticky=tk.W, pady=5)
        fields.append(('definition', definition_text))
        
        # 出处
        ttk.Label(card_frame, text="出处:", font=("SimHei", 12, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        source_var = tk.StringVar(value=card['source'])
        source_entry = ttk.Entry(card_frame, textvariable=source_var, width=40)
        source_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        fields.append(('source', source_var))
        
        # 原文
        ttk.Label(card_frame, text="原文:", font=("SimHei", 12, "bold")).grid(row=3, column=0, sticky=tk.NW, pady=5)
        quote_text = tk.Text(card_frame, height=3, width=40, wrap=tk.WORD)
        quote_text.insert(tk.END, card['quote'])
        quote_text.grid(row=3, column=1, sticky=tk.W, pady=5)
        fields.append(('quote', quote_text))
        
        # 注释
        ttk.Label(card_frame, text="注释:", font=("SimHei", 12, "bold")).grid(row=4, column=0, sticky=tk.NW, pady=5)
        notes_text = tk.Text(card_frame, height=3, width=40, wrap=tk.WORD)
        notes_text.insert(tk.END, card.get('notes', ''))
        notes_text.grid(row=4, column=1, sticky=tk.W, pady=5)
        fields.append(('notes', notes_text))
        
        # 标记是否有更改
        has_changes = [False]
        
        # 检查是否有更改的函数
        def check_changes(*args):
            current_card = {
                'keyword': keyword_var.get(),
                'definition': definition_text.get("1.0", tk.END).strip(),
                'source': source_var.get(),
                'quote': quote_text.get("1.0", tk.END).strip(),
                'notes': notes_text.get("1.0", tk.END).strip()
            }
            
            changed = False
            for key, value in current_card.items():
                if key in original_card and value != original_card[key]:
                    changed = True
                    break
            
            has_changes[0] = changed
            save_button.config(state=tk.NORMAL if changed else tk.DISABLED)
        
        # 绑定变量变化事件
        keyword_var.trace_add('write', check_changes)
        source_var.trace_add('write', check_changes)
        
        # 绑定文本框变化事件
        def on_text_change(event):
            check_changes()
        
        definition_text.bind('<<Modified>>', on_text_change)
        quote_text.bind('<<Modified>>', on_text_change)
        notes_text.bind('<<Modified>>', on_text_change)
        
        # 按钮框架
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(pady=10)
        
        # 保存按钮
        def save_changes():
            try:
                # 收集表单数据
                updated_card = {
                    'id': card['id'],
                    'keyword': keyword_var.get(),
                    'definition': definition_text.get("1.0", tk.END).strip(),
                    'source': source_var.get(),
                    'quote': quote_text.get("1.0", tk.END).strip(),
                    'notes': notes_text.get("1.0", tk.END).strip(),
                    'created_at': card['created_at'],
                    'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 验证必填字段
                if not updated_card['keyword'] or not updated_card['definition']:
                    messagebox.showerror("错误", "关键词和释义为必填项")
                    return
                
                # 更新卡片
                if self.card_manager.update_card(updated_card):
                    # 刷新列表视图
                    self.refresh_list_view()
                    # 关闭窗口
                    edit_window.destroy()
                else:
                    messagebox.showerror("错误", "更新卡片失败")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
        
        save_button = ttk.Button(button_frame, text="保存", command=save_changes, style="Accent.TButton", state=tk.DISABLED)
        save_button.pack(side=tk.LEFT, padx=10)
        
        # 确定按钮
        def confirm_changes():
            if has_changes[0]:
                # 询问是否保存更改
                result = messagebox.askyesnocancel("保存更改", "您对卡片进行了修改，是否保存这些更改？")
                if result is None:  # 取消
                    return
                elif result:  # 是，保存
                    save_changes()
                else:  # 否，不保存
                    edit_window.destroy()
            else:
                # 没有更改，直接关闭
                edit_window.destroy()
        
        confirm_button = ttk.Button(button_frame, text="确定", command=confirm_changes)
        confirm_button.pack(side=tk.RIGHT, padx=10)
    
    def show_search(self):
        """显示搜索视图"""
        self.show_view('search')
        self.search_panel.focus_search_entry()
    
    # 批量编辑功能已移除
    
    def show_import_export_dialog(self):
        """显示导出卡片对话框（支持多种格式选择）"""
        try:
            # 获取所有卡片
            all_cards = self.card_manager.get_all_cards()
            if not all_cards:
                messagebox.showwarning("警告", "暂无卡片数据可导出")
                return
            
            # 弹出格式选择对话框
            format_window = tk.Toplevel(self.root)
            format_window.title("选择导出格式")
            format_window.geometry("400x300")
            format_window.transient(self.root)
            format_window.grab_set()
            
            # 设置窗口图标
            if hasattr(self.app, '_set_window_icon'):
                self.app._set_window_icon(format_window)
            
            # 居中显示
            format_window.update_idletasks()
            width = format_window.winfo_width()
            height = format_window.winfo_height()
            x = (self.root.winfo_width() // 2) - (width // 2)
            y = (self.root.winfo_height() // 2) - (height // 2)
            format_window.geometry('+{}+{}'.format(x, y))
            
            # 创建主框架
            main_frame = ttk.Frame(format_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 创建标题
            ttk.Label(
                main_frame, 
                text="请选择导出格式", 
                font=("SimHei", 14, "bold")
            ).pack(pady=(0, 15))
            
            # 格式选择变量
            format_var = tk.StringVar(value="txt")
            
            # 创建单选按钮
            ttk.Radiobutton(
                main_frame,
                text="文本格式 (*.txt) - 简单易读",
                variable=format_var,
                value="txt"
            ).pack(anchor=tk.W, pady=5)
            
            ttk.Radiobutton(
                main_frame,
                text="JSON格式 (*.json) - 结构化数据",
                variable=format_var,
                value="json"
            ).pack(anchor=tk.W, pady=5)
            

            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(pady=15)
            
            def on_export():
                """执行导出操作"""
                selected_format = format_var.get()
                format_window.destroy()
                
                # 根据选择的格式执行导出
                if selected_format == "txt":
                    # 直接导出为文本格式
                    self.export_txt_format()
                elif selected_format == "json":
                    # 直接导出为JSON格式
                    self.export_json_format()
                
                # 保存用户的导出格式偏好
                self.settings_manager.save_export_format(selected_format)
            
            # 导出按钮
            ttk.Button(
                button_frame,
                text="导出",
                command=on_export,
                width=10
            ).pack(side=tk.LEFT, padx=5)
            
            # 取消按钮
            ttk.Button(
                button_frame,
                text="取消",
                command=format_window.destroy,
                width=10
            ).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
古文卡片学习软件使用帮助

1. 卡片概览：查看所有卡片，按字母顺序排列
2. 添加卡片：创建新的古文学习卡片
3. 搜索卡片：搜索卡片内容
4. 导出：支持导出卡片数据

卡片格式说明：
- 关键词：古文中的生僻字或词汇
- 释义：关键词的现代解释
- 出处：引用的古籍名称
- 原文：包含关键词的原文句子
- 注释：额外的解释或说明

祝您学习愉快！
        """
        messagebox.showinfo("使用帮助", help_text)
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
古文卡片学习软件 v1.0

一款专为古文学习设计的卡片管理工具，
帮助用户制作、管理和搜索古文学习卡片。

邮箱：jumaozhixing@outlook.com

© 橘猫
        """
        messagebox.showinfo("关于", about_text)
    
    def show_settings(self):
        """显示IDM风格的设置窗口"""
        if self.settings_manager:
            self.settings_manager.show_settings_window()
        else:
            messagebox.showerror("错误", "设置管理器未初始化")
    
    def export_ancc(self):
        """导出ANCC格式文件"""
        try:
            from tkinter import filedialog
            import json
            import base64
            
            # 获取保存文件路径
            file_path = filedialog.asksaveasfilename(
                title="导出ANCC格式文件",
                defaultextension=".ancc",
                filetypes=[("ANCC文件", "*.ancc"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
            
            # 获取所有卡片数据
            cards_data = self.card_manager.get_all_cards()
            
            # 创建ANCC格式数据
            ancc_data = {
                'version': '1.0',
                'type': 'ancient_chinese_cards',
                'data': cards_data,
                'export_time': datetime.now().isoformat()
            }
            
            # 转换为JSON并编码为base64
            json_data = json.dumps(ancc_data, ensure_ascii=False, indent=2)
            encoded_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encoded_data)
            
            messagebox.showinfo("成功", f"卡片数据已成功导出到:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出ANCC文件失败: {str(e)}")
    
    def import_ancc(self):
        """导入ANCC格式文件"""
        try:
            from tkinter import filedialog
            import json
            import base64
            
            # 获取文件路径
            file_path = filedialog.askopenfilename(
                title="导入ANCC格式文件",
                filetypes=[("ANCC文件", "*.ancc"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                encoded_data = f.read()
            
            # 解码base64并解析JSON
            json_data = base64.b64decode(encoded_data).decode('utf-8')
            ancc_data = json.loads(json_data)
            
            # 验证ANCC格式
            if ancc_data.get('type') != 'ancient_chinese_cards':
                messagebox.showerror("错误", "无效的ANCC文件格式")
                return
            
            # 获取卡片数据
            cards_data = ancc_data.get('data', [])
            
            if not cards_data:
                messagebox.showinfo("提示", "ANCC文件中没有卡片数据")
                return
            
            # 询问是否合并或替换现有卡片
            result = messagebox.askyesnocancel(
                "导入选项",
                f"发现 {len(cards_data)} 张卡片。\n\n是否将这些卡片添加到现有卡片中？\n\n选择'是'合并卡片，选择'否'替换所有现有卡片。",
                icon=messagebox.QUESTION
            )
            
            if result is None:  # 用户取消
                return
            
            if result:  # 合并卡片
                # 计算新增卡片数量
                original_count = len(self.card_manager.get_all_cards())
                self.card_manager.add_cards(cards_data)
                new_count = len(self.card_manager.get_all_cards())
                added_count = new_count - original_count
                
                messagebox.showinfo(
                    "成功", 
                    f"成功导入 {added_count} 张卡片。\n\n当前总卡片数: {new_count}"
                )
            else:  # 替换卡片
                # 清空现有卡片
                self.card_manager.clear_cards()
                # 添加新卡片
                self.card_manager.add_cards(cards_data)
                
                messagebox.showinfo(
                    "成功", 
                    f"成功导入 {len(cards_data)} 张卡片，已替换所有现有卡片。"
                )
            
            # 刷新列表视图
            self.refresh_list_view()
            
        except json.JSONDecodeError:
            messagebox.showerror("错误", "ANCC文件格式错误，无法解析")
        except base64.binascii.Error:
            messagebox.showerror("错误", "ANCC文件编码错误")
        except Exception as e:
            messagebox.showerror("错误", f"导入ANCC文件失败: {str(e)}")
    

    
    def save_cards(self):
        """保存卡片数据"""
        try:
            self.card_manager.save_cards()
            messagebox.showinfo("提示", "卡片数据已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def bind_events(self):
        """绑定事件"""
        # 绑定Ctrl+S保存快捷键
        self.root.bind("<Control-s>", lambda event: self.save_cards())
        # 绑定F1帮助快捷键
        self.root.bind("<F1>", lambda event: self.show_help())
        
        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', self.on_window_configure)
    
    def create_list_view(self):
        """初始化列表视图（替代卡片视图）"""
        # 创建列表框架
        list_frame = ttk.Frame(self.views['overview'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建列表标题
        title_frame = ttk.Frame(list_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="卡片列表", font=("SimHei", 16, "bold"))
        title_label.pack(side=tk.LEFT, padx=10)
        
        # 初始化搜索变量（用于排序）
        self.search_var = tk.StringVar()
        
        # 创建列表框架
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # 创建列表（Treeview）
        columns = ("keyword", "definition", "source", "quote")
        self.card_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        
        # 设置列标题并绑定点击事件
        self.card_tree.heading("keyword", text="关键词", command=lambda: self.on_header_click("keyword"))
        self.card_tree.heading("definition", text="释义", command=lambda: self.on_header_click("definition"))
        self.card_tree.heading("source", text="出处", command=lambda: self.on_header_click("source"))
        self.card_tree.heading("quote", text="原文", command=lambda: self.on_header_click("quote"))
        
        # 设置列宽
        self.card_tree.column("keyword", width=150)
        self.card_tree.column("definition", width=250)
        self.card_tree.column("source", width=150)
        self.card_tree.column("quote", width=300)
        
        # 设置行高（通过字体大小间接设置行高）
        style = ttk.Style()
        style.configure("Treeview", rowheight=30)  # 增加行高，约等于1.5mm
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.card_tree.yview)
        self.card_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.card_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定双击事件
        self.card_tree.bind("<Double-1>", self.on_item_double_click)
        
        # 绑定左键点击事件（新增）
        self.card_tree.bind('<Button-1>', self.on_treeview_click)
        # 绑定Ctrl+左键点击事件（新增）
        self.card_tree.bind('<Control-Button-1>', self.on_treeview_ctrl_click)
        # 绑定Shift+左键点击事件（新增）
        self.card_tree.bind('<Shift-Button-1>', self.on_treeview_ctrl_click)
        # 绑定选中变化事件（新增）
        self.card_tree.bind('<<TreeviewSelect>>', self.on_treeview_select)
        
        # 绑定右键菜单
        self.card_tree.bind("<Button-3>", self.show_context_menu)
        
        # 创建右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="编辑", command=self.edit_selected_card)
        self.context_menu.add_command(label="删除", command=self.delete_selected_card)
        
        # 初始化拖拽选择相关变量
        self.drag_start_item = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_selecting = False
        
        # 绑定鼠标移动和释放事件（用于拖拽选择）
        self.card_tree.bind('<B1-Motion>', self.on_treeview_drag)
        self.card_tree.bind('<ButtonRelease-1>', self.on_treeview_release)
        # self.context_menu.add_separator()
        # self.context_menu.add_command(label="查看详情", command=self.view_card_details)
        
        # 排序相关变量
        self.sort_column = "keyword"  # 当前排序列
        self.sort_order = "asc"  # 当前排序顺序
        self.sort_indicators = {}  # 存储各列的排序指示器
        
        # 从设置管理器加载排序设置
        self._load_sort_settings()
    
    def _load_sort_settings(self):
        """从设置管理器加载排序设置"""
        if hasattr(self, 'settings_manager') and self.settings_manager:
            try:
                sort_column, sort_order, is_time_sort = self.settings_manager.get_sort_settings()
                if sort_column:
                    self.sort_column = sort_column
                if sort_order:
                    self.sort_order = sort_order
                print(f"已加载排序设置: 列={self.sort_column}, 顺序={self.sort_order}")
            except Exception as e:
                print(f"加载排序设置失败: {str(e)}")
    
    def on_header_click(self, column):
        """表头点击事件处理 - 实现类似Windows的点击排序功能"""
        # 如果点击的是当前排序列，则切换排序顺序
        if column == self.sort_column:
            self.sort_order = "desc" if self.sort_order == "asc" else "asc"
        else:
            # 否则切换到新列，默认升序
            self.sort_column = column
            self.sort_order = "asc"
        
        # 保存排序设置到设置管理器
        if hasattr(self, 'settings_manager') and self.settings_manager:
            try:
                # 判断是否为时间排序（这里简化处理，实际根据需要调整）
                is_time_sort = self.sort_column in ['created_at', 'updated_at']
                self.settings_manager.save_sort_settings(self.sort_column, self.sort_order, is_time_sort)
                print(f"已保存排序设置: 列={self.sort_column}, 顺序={self.sort_order}")
            except Exception as e:
                print(f"保存排序设置失败: {str(e)}")
        
        # 刷新列表
        self.refresh_list_view()
    
    def get_pinyin(self, text):
        """获取中文字符串的拼音，用于排序"""
        try:
            # 尝试导入pypinyin库
            from pypinyin import lazy_pinyin
            return ''.join(lazy_pinyin(text))
        except ImportError:
            # 如果没有安装pypinyin，使用备选方案
            # 检查是否需要显示提示
            if not hasattr(self, '_pypinyin_warning_shown'):
                self._pypinyin_warning_shown = True
                # 显示建议安装pypinyin的提示
                messagebox.showinfo(
                    "排序优化建议",
                    "建议安装 pypinyin 库以获得更精准的中文拼音排序。\n"
                    "请在命令行中运行: pip install pypinyin"
                )
            return text
    
    def refresh_list_view(self):
        """刷新列表视图"""
        # 清空现有列表
        for item in self.card_tree.get_children():
            self.card_tree.delete(item)
        
        # 获取卡片数据
        cards = self.card_manager.get_all_cards()
        
        # 根据当前排序字段和顺序排序
        reverse = self.sort_order == "desc"
        
        # 根据不同列使用不同的排序方法
        if self.sort_column == "keyword":
            # 关键词列使用拼音排序
            cards.sort(key=lambda x: self.get_pinyin(x.get("keyword", "")), reverse=reverse)
        elif self.sort_column in ["definition", "source", "quote"]:
            # 其他文本列也使用拼音排序
            cards.sort(key=lambda x: self.get_pinyin(x.get(self.sort_column, "")), reverse=reverse)
        
        # 添加卡片到列表
        for card in cards:
            values = (
                card['keyword'],
                card['definition'][:50] + "..." if len(card['definition']) > 50 else card['definition'],
                card['source'],
                card['quote'][:50] + "..." if len(card['quote']) > 50 else card['quote']
            )
            self.card_tree.insert("", tk.END, values=values, tags=(card['id'],))
        
        # 更新列标题，添加排序指示器
        self._update_sort_indicators()
        
        # 更新状态栏
        if hasattr(self, 'status_bar'):
            if len(cards) == 0:
                # 空卡片时的友好提示
                self.status_bar.config(text="暂无卡片数据，可通过「添加卡片」或「导入卡片」创建")
            else:
                # 有卡片时显示排序信息
                sort_direction = "递减" if reverse else "递增"
                field_names = {
                    "keyword": "关键词",
                    "definition": "释义",
                    "source": "出处",
                    "quote": "原文"
                }
                field_name = field_names.get(self.sort_column, "关键词")
                self.status_bar.config(text=f"显示 {len(cards)} 张卡片 (按{field_name}{sort_direction}排序)")
    
    def _update_sort_indicators(self):
        """更新列标题的排序指示器"""
        # 移除所有列的排序指示器
        for col in self.card_tree["columns"]:
            current_text = self.card_tree.heading(col)["text"]
            # 移除现有的排序指示器
            if current_text.endswith(" ↑") or current_text.endswith(" ↓"):
                self.card_tree.heading(col, text=current_text[:-2])
        
        # 为当前排序列添加排序指示器
        indicator = " ↑" if self.sort_order == "asc" else " ↓"
        field_names = {
            "keyword": "关键词",
            "definition": "释义",
            "source": "出处",
            "quote": "原文"
        }
        field_name = field_names.get(self.sort_column, self.sort_column)
        self.card_tree.heading(self.sort_column, text=f"{field_name}{indicator}")
    
    def on_item_double_click(self, event):
        """双击列表项事件处理"""
        self.edit_selected_card()
    
    def on_treeview_click(self, event):
        """Treeview点击事件处理（右键禁止自动选中）"""
        # 记录鼠标按键（1=左键，3=右键）
        self.last_mouse_button = event.num
        
        # 右键点击：直接阻止所有选中相关行为，保留原多选状态
        if event.num == 3:
            # 清空选中锚点，阻止Treeview自动选中单个项
            event.widget.selection_anchor("")
            # 阻止事件传播，不让后续触发单选
            return "break"
        
        # 左键处理逻辑
        region = self.card_tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.card_tree.identify_row(event.y)
            if item:
                # 检查是否是Ctrl或Shift组合键
                if not (event.state & 0x0004) and not (event.state & 0x0001):
                    self.card_tree.selection_set(item)
                    self.card_tree.focus(item)
                
                # 记录拖拽选择的起始点
                self.drag_start_item = item
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.drag_selecting = True
    
    def on_treeview_ctrl_click(self, event):
        """Treeview Ctrl+点击事件处理"""
        # 记录鼠标按键
        self.last_mouse_button = event.num
        
        # Ctrl+点击，切换选中状态
        region = self.card_tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.card_tree.identify_row(event.y)
            if item:
                if item in self.card_tree.selection():
                    self.card_tree.selection_remove(item)
                else:
                    self.card_tree.selection_add(item)
                self.card_tree.focus(item)
                # 阻止默认的选择行为
                return "break"
    
    def on_treeview_release(self, event):
        """Treeview鼠标释放事件处理（结束拖拽选择）"""
        # 重置拖拽状态
        self.drag_selecting = False
        self.drag_start_item = None
    
    def on_treeview_drag(self, event):
        """Treeview拖拽选择事件处理"""
        # 检查是否正在拖拽选择
        if not self.drag_selecting or not self.drag_start_item:
            return
        
        # 获取当前鼠标位置的项
        region = self.card_tree.identify_region(event.x, event.y)
        if region == "cell":
            current_item = self.card_tree.identify_row(event.y)
            if current_item and current_item != self.drag_start_item:
                # 获取所有项
                all_items = self.card_tree.get_children()
                
                try:
                    # 找到起始项和当前项的索引
                    start_idx = all_items.index(self.drag_start_item)
                    current_idx = all_items.index(current_item)
                    
                    # 选择从起始项到当前项的所有项
                    start = min(start_idx, current_idx)
                    end = max(start_idx, current_idx)
                    
                    # 清空当前选择并选择新的范围
                    self.card_tree.selection_set(all_items[start:end+1])
                    self.card_tree.focus(current_item)
                except ValueError:
                    pass
    
    def on_treeview_select(self, event):
        """选中事件处理（过滤右键触发的伪选中）"""
        # 右键触发的选中事件直接跳过，保留原多选
        if self.last_mouse_button == 3:
            return
        
        # 只有左键触发的选中才更新状态
        selection = self.card_tree.selection()
        if selection:
            item = selection[0]
            card_id = self.card_tree.item(item, "tags")[0]
            self.selected_card_id = card_id
    
    def show_context_menu(self, event):
        """显示右键菜单（保留多选状态）"""
        # 记录鼠标按键为右键
        self.last_mouse_button = 3
        
        # 获取当前真实的多选状态（右键点击前的状态）
        selected_items = self.card_tree.selection()
        if not selected_items:
            return
        
        # 获取点击的项目
        item = self.card_tree.identify_row(event.y)
        if item and item not in selected_items:
            # 支持右键点击时"追加选中"（和左键Ctrl+点击一致）
            self.card_tree.selection_add(item)
        
        # 显示菜单（位置微调，避免遮挡）
        self.context_menu.post(event.x_root + 10, event.y_root + 10)
    
    def edit_selected_card(self):
        """编辑选中的卡片"""
        selected_items = self.card_tree.selection()
        if selected_items:
            item = selected_items[0]
            card_id = self.card_tree.item(item, "tags")[0]
            self.show_edit_card(card_id)
    
    def delete_selected_card(self):
        """删除选中的卡片（批量支持）"""
        selected_items = self.card_tree.selection()
        if not selected_items:
            return
        
        # 批量删除逻辑
        if len(selected_items) > 1:
            if messagebox.askyesno("确认批量删除", f"确定要删除选中的{len(selected_items)}张卡片吗？"):
                deleted_count = 0
                for item in selected_items:
                    card_id = self.card_tree.item(item, "tags")[0]
                    if self.card_manager.delete_card(card_id):
                        deleted_count += 1
                self.refresh_list_view()
                # 移除成功提示窗口
        else:
            # 单个删除逻辑（保留原有）
            item = selected_items[0]
            card_id = self.card_tree.item(item, "tags")[0]
            card = self.card_manager.get_card(card_id)
            if card and messagebox.askyesno("确认删除", f"确定要删除卡片 '{card['keyword']}' 吗？"):
                if self.card_manager.delete_card(card_id):
                    self.refresh_list_view()
                    # 移除成功提示窗口
                else:
                    messagebox.showerror("错误", "删除卡片失败")
    

    
    def show_update_log(self):
        """显示更新日志窗口"""
        try:
            # 读取更新日志文件
            update_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "update.txt")
            
            with open(update_file_path, 'r', encoding='utf-8') as f:
                update_content = f.read()
            
            # 创建更新日志窗口
            update_window = tk.Toplevel(self.root)
            update_window.title("更新日志")
            update_window.geometry("800x690")
            update_window.resizable(True, True)
            
            # 设置窗口图标
            if hasattr(self.app, '_set_window_icon'):
                self.app._set_window_icon(update_window)
            
            # 居中显示
            update_window.update_idletasks()
            width = update_window.winfo_width()
            height = update_window.winfo_height()
            x = (self.root.winfo_width() // 2) - (width // 2)
            y = (self.root.winfo_height() // 2) - (height // 2)
            update_window.geometry('+{}+{}'.format(x, y))
            
            # 创建主框架
            main_frame = ttk.Frame(update_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 创建标题
            title_label = ttk.Label(main_frame, text="更新日志", font=("SimHei", 16, "bold"))
            title_label.pack(pady=(0, 15))
            
            # 创建文本框框架（固定大小）
            text_frame = ttk.Frame(main_frame, height=300)
            text_frame.pack(fill=tk.X, pady=(0, 15))
            
            # 创建文本框
            text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("SimSun", 16))
            text_widget.insert(tk.END, update_content)
            text_widget.config(state=tk.DISABLED)  # 只读状态，防止编辑
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 创建滚动条
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 绑定滚动条
            text_widget.config(yscrollcommand=scrollbar.set)
            
            # 创建按钮框架（始终显示在底部）
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=15)
            
            # 创建确定按钮
            ok_button = ttk.Button(
                button_frame,
                text="确定",
                command=update_window.destroy,
                width=15
            )
            ok_button.pack()
            
        except Exception as e:
            messagebox.showerror("错误", f"读取更新日志失败: {str(e)}")
    
    def export_ancc(self):
        """导出ANCC格式（默认文件名cards.ancc）"""
        # 1. 获取所有卡片
        all_cards = self.card_manager.get_all_cards()
        if not all_cards:
            messagebox.showwarning("警告", "暂无卡片数据可导出")
            return
        
        # 2. 弹出文件选择框（默认文件名cards.ancc）
        file_path = filedialog.asksaveasfilename(
            title="导出ANCC文件",
            defaultextension=".ancc",
            initialfile="cards",  # 默认文件名
            filetypes=[("专属卡片格式", "*.ancc"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        
        # 3. 加密并保存
        try:
            encrypted_data = self.card_manager.encrypt_card_lines(all_cards)
            with open(file_path, "wb") as f:
                f.write(encrypted_data)
            messagebox.showinfo("成功", f"已导出{len(all_cards)}张卡片到\n{os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")
    
    def export_txt_format(self):
        """直接导出为文本格式"""
        # 1. 获取所有卡片
        all_cards = self.card_manager.get_all_cards()
        if not all_cards:
            messagebox.showwarning("警告", "暂无卡片数据可导出")
            return
        
        # 2. 弹出Windows文件保存框
        file_path = filedialog.asksaveasfilename(
            title="导出文本文件",
            defaultextension=".txt",
            initialfile="cards",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        
        # 3. 生成文本内容
        lines = []
        lines.append("=== 古文卡片数据 ===")
        lines.append(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"卡片数量: {len(all_cards)}")
        lines.append("=" * 50)
        lines.append("")
        
        for i, card in enumerate(all_cards, 1):
            lines.append(f"【卡片 {i}】")
            lines.append(f"关键词: {card.get('keyword', '').strip()}")
            lines.append(f"释义: {card.get('definition', '').strip()}")
            lines.append(f"出处: {card.get('source', '').strip()}")
            lines.append(f"原文: {card.get('quote', '').strip()}")
            if card.get('notes', '').strip():
                lines.append(f"注释: {card.get('notes', '').strip()}")
            lines.append("-" * 30)
            lines.append("")
        
        # 4. 保存文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            messagebox.showinfo("成功", f"已导出{len(all_cards)}张卡片到\n{os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")
    
    def export_json_format(self):
        """直接导出为JSON格式"""
        # 1. 获取所有卡片
        all_cards = self.card_manager.get_all_cards()
        if not all_cards:
            messagebox.showwarning("警告", "暂无卡片数据可导出")
            return
        
        # 2. 弹出Windows文件保存框
        file_path = filedialog.asksaveasfilename(
            title="导出JSON文件",
            defaultextension=".json",
            initialfile="cards",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        
        # 3. 保存JSON文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(all_cards, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", f"已导出{len(all_cards)}张卡片到\n{os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")
    
    def import_ancc(self):
        """导入ANCC格式文件"""
        # 1. 弹出文件选择框
        file_path = filedialog.askopenfilename(
            title="导入ANCC文件",
            filetypes=[("专属卡片格式", "*.ancc"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        
        # 2. 解密并导入
        try:
            with open(file_path, "rb") as f:
                encrypted_data = f.read()
            # 解密得到卡片列表
            new_cards = self.card_manager.decrypt_to_cards(encrypted_data)
            if not new_cards:
                messagebox.showwarning("警告", "文件中无有效卡片（或已全部重复）")
                return
            
            # 3. 添加到软件中
            imported_count = 0
            for card in new_cards:
                self.card_manager.add_card(card)
                imported_count += 1
            
            # 4. 刷新列表
            self.refresh_list_view()
            messagebox.showinfo("成功", f"已导入{imported_count}张新卡片")
        except ValueError as e:
            messagebox.showerror("错误", f"非法文件：{str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败：{str(e)}")
    
    def on_window_configure(self, event):
        """窗口大小或位置变化时的回调"""
        # 避免在窗口初始化时触发
        if event.widget == self.root and hasattr(self, '_window_initialized'):
            # 保存窗口位置和大小
            x, y = self.root.winfo_x(), self.root.winfo_y()
            width, height = self.root.winfo_width(), self.root.winfo_height()
            
            # 只在窗口正常显示时保存（避免最小化等状态）
            if width > 100 and height > 100:
                self.settings_manager.save_window_position(x, y)
                self.settings_manager.save_window_size(width, height)
        else:
            # 标记窗口已初始化
            self._window_initialized = True
    
    def apply_window_settings(self):
        """应用保存的窗口设置"""
        if self.settings_manager:
            # 应用窗口位置
            position = self.settings_manager.get_window_position()
            if position:
                x, y = position
                # 检查位置是否有效（避免窗口显示在屏幕外）
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                if 0 <= x < screen_width and 0 <= y < screen_height:
                    self.root.geometry(f"+{x}+{y}")
            
            # 应用窗口大小
            size = self.settings_manager.get_window_size()
            if size:
                width, height = size
                # 限制最小大小
                min_width, min_height = 800, 600
                width = max(width, min_width)
                height = max(height, min_height)
                self.root.geometry(f"{width}x{height}")
    
    def on_window_close(self):
        """窗口关闭时的回调"""
        # 保存窗口位置和大小
        if self.settings_manager:
            x, y = self.root.winfo_x(), self.root.winfo_y()
            width, height = self.root.winfo_width(), self.root.winfo_height()
            
            self.settings_manager.save_window_position(x, y)
            self.settings_manager.save_window_size(width, height)
        
        # 保存卡片数据
        self.save_cards()
        
        # 关闭窗口
        self.root.destroy()
    
    # def view_card_details(self):
    #     """查看卡片详情"""
    #     selected_items = self.card_tree.selection()
    #     if selected_items:
    #         item = selected_items[0]
    #         card_id = self.card_tree.item(item, "tags")[0]
    #         card = self.card_manager.get_card(card_id)
    #         
    #         if card:
    #             # 创建详情窗口
    #             detail_window = tk.Toplevel(self.root)
    #             detail_window.title(f"卡片详情 - {card['keyword']}")
    #             detail_window.geometry("600x400")
    #             detail_window.transient(self.root)
    #             
    #             # 创建详情框架
    #             detail_frame = ttk.Frame(detail_window, padding=20)
    #             detail_frame.pack(fill=tk.BOTH, expand=True)
    #             
    #             # 显示卡片信息
    #             ttk.Label(detail_frame, text="关键词:", font=("SimHei", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
    #             ttk.Label(detail_frame, text=card['keyword']).grid(row=0, column=1, sticky=tk.W, pady=5)
    #             
    #             ttk.Label(detail_frame, text="释义:", font=("SimHei", 12, "bold")).grid(row=1, column=0, sticky=tk.NW, pady=5)
    #             ttk.Label(detail_frame, text=card['definition'], wraplength=500).grid(row=1, column=1, sticky=tk.W, pady=5)
    #             
    #             ttk.Label(detail_frame, text="出处:", font=("SimHei", 12, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
    #             ttk.Label(detail_frame, text=card['source']).grid(row=2, column=1, sticky=tk.W, pady=5)
    #             
    #             ttk.Label(detail_frame, text="原文:", font=("SimHei", 12, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
    #             ttk.Label(detail_frame, text=card['quote']).grid(row=3, column=1, sticky=tk.W, pady=5)
    #             
    #             if card['notes']:
    #                 ttk.Label(detail_frame, text="注释:", font=("SimHei", 12, "bold")).grid(row=4, column=0, sticky=tk.NW, pady=5)
    #                 ttk.Label(detail_frame, text=card['notes'], wraplength=500).grid(row=4, column=1, sticky=tk.W, pady=5)