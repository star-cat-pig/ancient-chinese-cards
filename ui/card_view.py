#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡片视图类，负责卡片的展示和交互
"""
import tkinter as tk
from tkinter import ttk, font, messagebox
from typing import Dict, Any, List

class CardView:
    """卡片视图类"""
    
    def __init__(self, parent, card_manager, main_window):
        """
        初始化卡片视图
        
        Args:
            parent: 父窗口组件
            card_manager: 卡片管理器实例
            main_window: 主窗口实例
        """
        self.parent = parent
        self.card_manager = card_manager
        self.main_window = main_window
        
        # 获取设置管理器
        self.settings_manager = main_window.settings_manager
        
        # 设置主题颜色
        self.colors = main_window.colors
        
        # 当前显示的卡片列表
        self.current_cards = []
        
        # 当前选中的卡片ID
        self.selected_card_id = None
        
        # 记录最近一次鼠标按键（用于判断选中事件来源）
        self.last_mouse_button = 1  # 默认是左键
        
        # 标记是否正在处理右键菜单（阻止选中事件）
        self.is_right_clicking = False
        
        # 记录最近的多选状态（用于右键时恢复）
        self.last_multi_selection = []
        
        # 排序相关状态
        self.is_time_sort = False
        self.is_pinyin_sort = False
        self.sort_column = None
        self.sort_order = 'asc'
        
        # 创建视图
        self.create_view()
    
    def create_view(self):
        """创建卡片视图界面"""
        # 创建主框架
        self.view_frame = ttk.Frame(self.parent)
        self.view_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建顶部工具栏
        self.create_toolbar()
        
        # 创建卡片展示区域
        self.create_card_display()
        
        # 创建底部状态栏
        self.create_status_bar()
    
    def create_toolbar(self):
        """创建顶部工具栏"""
        self.toolbar = ttk.Frame(self.view_frame)
        self.toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # 字体设置
        font_frame = ttk.Frame(self.toolbar)
        font_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(font_frame, text="字体:").pack(side=tk.LEFT, padx=(0, 5))
        
        # 字体大小选择
        self.font_size_var = tk.StringVar()
        self.font_size_var.set("12")
        
        size_menu = ttk.OptionMenu(
            font_frame,
            self.font_size_var,
            "12", "10", "14", "16", "18", "20",
            command=self.on_font_change
        )
        size_menu.pack(side=tk.LEFT, padx=5)
        
        # 字体类型选择
        self.font_family_var = tk.StringVar()
        self.font_family_var.set("SimHei")
        
        family_menu = ttk.OptionMenu(
            font_frame,
            self.font_family_var,
            "SimHei", "SimSun", "Microsoft YaHei", "KaiTi", "FangSong",
            command=self.on_font_change
        )
        family_menu.pack(side=tk.LEFT, padx=5)
        
        # 排序选项
        sort_frame = ttk.Frame(self.toolbar)
        sort_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(sort_frame, text="排序:").pack(side=tk.LEFT, padx=(0, 5))
        
        # 创建排序下拉菜单
        self.sort_menu_var = tk.StringVar()
        self.sort_menu_var.set("按列标题点击排序")
        
        sort_menu = ttk.OptionMenu(
            sort_frame,
            self.sort_menu_var,
            "按列标题点击排序",
            "按创建时间（新→旧）",
            "按创建时间（旧→新）",
            "按拼音排序（A→Z）",
            "按拼音排序（Z→A）",
            command=self.on_sort_menu_change
        )
        sort_menu.pack(side=tk.LEFT, padx=5)
        
        # 视图切换
        view_frame = ttk.Frame(self.toolbar)
        view_frame.pack(side=tk.LEFT, padx=(20, 5))
        
        ttk.Label(view_frame, text="视图:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.view_var = tk.StringVar()
        self.view_var.set("list")
        
        ttk.Radiobutton(
            view_frame, 
            text="列表", 
            variable=self.view_var, 
            value="list",
            command=self.switch_view
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            view_frame, 
            text="卡片", 
            variable=self.view_var, 
            value="card",
            command=self.switch_view
        ).pack(side=tk.LEFT, padx=5)
        
        # 右侧按钮
        button_frame = ttk.Frame(self.toolbar)
        button_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="编辑选中", 
            command=self.edit_selected_card
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="删除选中", 
            command=self.delete_selected_card
        ).pack(side=tk.LEFT, padx=5)
    
    def create_card_display(self):
        """创建卡片展示区域"""
        # 创建卡片展示框架
        self.card_display_frame = ttk.Frame(self.view_frame)
        self.card_display_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建列表视图
        self.create_list_view()
        
        # 创建卡片视图
        self.create_card_view()
        
        # 默认显示列表视图
        self.switch_view()
    
    def create_list_view(self):
        """创建列表视图（使用Treeview实现多列显示）"""
        self.list_view_frame = ttk.Frame(self.card_display_frame)
        
        # 创建滚动条
        yscrollbar = ttk.Scrollbar(self.list_view_frame)
        yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        xscrollbar = ttk.Scrollbar(self.list_view_frame, orient=tk.HORIZONTAL)
        xscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建Treeview作为多列列表
        self.card_treeview = ttk.Treeview(
            self.list_view_frame,
            yscrollcommand=yscrollbar.set,
            xscrollcommand=xscrollbar.set,
            columns=('keyword', 'definition', 'source', 'quote'),
            show='headings',
            selectmode="extended"  # 开启真正的多选模式
        )
        
        # 从设置管理器加载排序设置
        sort_column, sort_order, is_time_sort = self.settings_manager.get_sort_settings()
        self.sort_column = sort_column or 'keyword'
        self.sort_order = sort_order or 'asc'
        self.is_time_sort = is_time_sort
        
        # 定义排序函数
        def sort_by_column(col):
            # 切换到列排序模式
            self.is_time_sort = False
            
            if self.sort_column == col:
                # 切换排序顺序
                self.sort_order = 'desc' if self.sort_order == 'asc' else 'asc'
            else:
                self.sort_column = col
                self.sort_order = 'asc'
            
            # 保存排序设置
            self.settings_manager.save_sort_settings(self.sort_column, self.sort_order, self.is_time_sort)
            
            # 更新列标题显示
            self.update_column_headings()
            
            # 重新排序并更新视图
            self.refresh()
        
        # 设置列标题和点击事件
        self.card_treeview.heading('keyword', text='关键词', anchor=tk.W, command=lambda: sort_by_column('keyword'))
        self.card_treeview.heading('definition', text='释义', anchor=tk.W, command=lambda: sort_by_column('definition'))
        self.card_treeview.heading('source', text='出处', anchor=tk.W, command=lambda: sort_by_column('source'))
        self.card_treeview.heading('quote', text='原文引用', anchor=tk.W, command=lambda: sort_by_column('quote'))
        
        # 设置Treeview样式，增加行间距
        self.style = ttk.Style()
        self.update_treeview_font()
        
        # 初始化字体设置
        self.current_font_size = 12
        self.current_font_family = "SimHei"
        
        # 设置列宽
        self.card_treeview.column('keyword', width=100, minwidth=80)
        self.card_treeview.column('definition', width=200, minwidth=150)
        self.card_treeview.column('source', width=120, minwidth=100)
        self.card_treeview.column('quote', width=300, minwidth=200)
        
        self.card_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定滚动条
        yscrollbar.config(command=self.card_treeview.yview)
        xscrollbar.config(command=self.card_treeview.xview)
        
        # 绑定事件
        self.card_treeview.bind('<<TreeviewSelect>>', self.on_treeview_select)
        self.card_treeview.bind('<Double-1>', self.on_treeview_double_click)
        
        # 支持多选的事件绑定
        self.card_treeview.bind('<Button-1>', self.on_treeview_click)
        self.card_treeview.bind('<Control-Button-1>', self.on_treeview_ctrl_click)
        self.card_treeview.bind('<Shift-Button-1>', self.on_treeview_shift_click)
        
        # 绑定右键菜单
        self.card_treeview.bind('<Button-3>', self.show_context_menu)
        
        # 创建右键菜单
        self.create_context_menu()
    
    def create_card_view(self):
        """创建卡片视图"""
        self.card_view_frame = ttk.Frame(self.card_display_frame)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(self.card_view_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建画布
        self.card_canvas = tk.Canvas(
            self.card_view_frame,
            yscrollcommand=scrollbar.set,
            bg=self.colors['bg']
        )
        self.card_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定滚动条
        scrollbar.config(command=self.card_canvas.yview)
        
        # 创建卡片容器
        self.card_container = ttk.Frame(self.card_canvas)
        self.card_canvas.create_window((0, 0), window=self.card_container, anchor=tk.NW)
        
        # 绑定事件
        self.card_container.bind("<Configure>", self.on_card_container_configure)
    
    def create_status_bar(self):
        """创建底部状态栏"""
        self.status_bar = ttk.Frame(self.view_frame)
        self.status_bar.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar()
        self.status_var.set("准备就绪")
        
        ttk.Label(
            self.status_bar, 
            textvariable=self.status_var, 
            anchor=tk.W
        ).pack(fill=tk.X, padx=10, pady=5)
    
    def refresh(self):
        """刷新卡片视图（已修复：不再过滤缺失字段的卡片）"""
        # 获取所有卡片
        cards = self.card_manager.get_all_cards()
        
        # 根据排序方式排序（注意：不过滤卡片，缺失字段使用空字符串）
        if self.view_var.get() == "list":
            if self.is_time_sort:
                # 时间排序（安全，无需过滤）
                sort_text = self.sort_menu_var.get()
                reverse = "新→旧" in sort_text
                self.current_cards = sorted(cards, key=lambda x: x.get('created_at', ''), reverse=reverse)
            elif self.is_pinyin_sort:
                # 拼音排序：缺失 keyword 的卡片使用空字符串作为排序键
                sort_text = self.sort_menu_var.get()
                reverse = "Z→A" in sort_text
                try:
                    import pypinyin
                    self.current_cards = sorted(
                        cards,
                        key=lambda x: (pypinyin.lazy_pinyin(x.get('keyword', '') or '')[0].lower() 
                                       if x.get('keyword') else ''),
                        reverse=reverse
                    )
                except ImportError:
                    self.current_cards = sorted(
                        cards,
                        key=lambda x: (x.get('keyword', '') or '').lower(),
                        reverse=reverse
                    )
            elif self.sort_column:
                # 列排序：缺失该列的卡片使用空字符串
                reverse = (self.sort_order == 'desc')
                self.current_cards = sorted(
                    cards,
                    key=lambda x: x.get(self.sort_column, '') or '',
                    reverse=reverse
                )
            else:
                # 默认按关键词排序，缺失则用空字符串
                self.current_cards = sorted(cards, key=lambda x: x.get('keyword', '') or '')
        else:
            # 卡片视图默认按创建时间降序排序（安全）
            self.current_cards = sorted(cards, key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 更新视图
        if self.view_var.get() == "list":
            self.update_list_view()
        else:
            self.update_card_view()
        
        # 更新状态栏
        self.status_var.set(f"共 {len(self.current_cards)} 张卡片")
    
    def switch_view(self):
        """切换视图模式"""
        # 隐藏所有视图
        self.list_view_frame.pack_forget()
        self.card_view_frame.pack_forget()
        
        # 显示当前选中的视图
        if self.view_var.get() == "list":
            self.list_view_frame.pack(fill=tk.BOTH, expand=True)
            self.update_list_view()
            self.update_column_headings()
            try:
                self.parent.unbind('<Configure>', self.resize_callback)
            except:
                pass
        else:
            self.card_view_frame.pack(fill=tk.BOTH, expand=True)
            self.update_card_view()
            self.resize_callback = self.parent.bind('<Configure>', self.on_window_resize)
    
    def update_list_view(self):
        """更新列表视图"""
        # 清空Treeview
        for item in self.card_treeview.get_children():
            self.card_treeview.delete(item)
        
        # 添加卡片数据到Treeview
        for card in self.current_cards:
            keyword = card.get('keyword', '') or ''
            definition = card.get('definition', '') or ''
            source = card.get('source', '') or ''
            quote = card.get('quote', '') or ''
            
            self.card_treeview.insert('', tk.END, 
                                     values=(keyword, definition, source, quote),
                                     tags=(card['id'],))
        
        # 更新列标题显示
        self.update_column_headings()
    
    def update_card_view(self):
        """更新卡片视图（支持自适应列数）"""
        # 清空卡片容器
        for widget in self.card_container.winfo_children():
            widget.destroy()
        
        # 根据窗口宽度自动调整列数
        window_width = self.card_display_frame.winfo_width()
        card_width = 270
        columns = max(2, min(4, window_width // card_width))
        
        for i, card in enumerate(self.current_cards):
            row = i // columns
            col = i % columns
            
            # 创建卡片
            card_frame = self.create_card_widget(card, row, col)
            card_frame.grid(row=row, column=col, padx=10, pady=10, sticky=tk.NSEW)
        
        # 更新画布滚动区域
        self.card_canvas.update_idletasks()
        self.card_canvas.config(scrollregion=self.card_canvas.bbox("all"))
    
    def on_window_resize(self, event=None):
        """窗口大小改变时更新卡片视图"""
        if self.view_var.get() == "card":
            self.update_card_view()
    
    def create_card_widget(self, card, row, col):
        """创建单个卡片组件"""
        card_frame = ttk.Frame(
            self.card_container,
            width=250,
            height=180,
            relief=tk.RAISED,
            padding=10
        )
        card_frame.configure(style="Card.TFrame")
        
        keyword_label = ttk.Label(
            card_frame,
            text=card.get('keyword', '') or '',
            font=("SimHei", 16, "bold"),
            foreground=self.colors['accent']
        )
        keyword_label.pack(pady=(0, 10))
        
        definition_label = ttk.Label(
            card_frame,
            text=card.get('definition', '') or '',
            font=("SimHei", 12),
            wraplength=220
        )
        definition_label.pack(pady=(0, 10))
        
        source_label = ttk.Label(
            card_frame,
            text=card.get('source', '') or '',
            font=("SimHei", 10, "italic"),
            foreground=self.colors['text']
        )
        source_label.pack(anchor=tk.W)
        
        quote_label = ttk.Label(
            card_frame,
            text=card.get('quote', '') or '',
            font=("SimHei", 10),
            wraplength=220
        )
        quote_label.pack(anchor=tk.W, pady=(5, 0))
        
        card_frame.bind("<Button-1>", lambda event, c=card: self.on_card_click(c))
        card_frame.bind("<Enter>", lambda event: self.on_card_enter(event))
        card_frame.bind("<Leave>", lambda event: self.on_card_leave(event))
        
        return card_frame
    
    def on_card_click(self, card):
        """卡片点击事件处理"""
        self.selected_card_id = card['id']
        self.highlight_selected_card()
    
    def on_card_enter(self, event):
        """鼠标进入卡片事件处理"""
        event.widget.configure(style="CardHover.TFrame")
    
    def on_card_leave(self, event):
        """鼠标离开卡片事件处理"""
        event.widget.configure(style="Card.TFrame")
    
    def on_treeview_select(self, event):
        """Treeview选中事件处理（同时同步主窗口和CardView的右键）"""
        if self.is_right_clicking:
            if self.last_multi_selection:
                self.card_treeview.selection_clear()
                self.card_treeview.selection_add(self.last_multi_selection)
                if hasattr(self.main_window, 'card_tree'):
                    self.main_window.card_tree.selection_clear()
                    self.main_window.card_tree.selection_add(self.last_multi_selection)
            return
        
        if self.last_mouse_button != 1:
            return
        
        self.last_multi_selection = self.card_treeview.selection()
        
        if hasattr(self.main_window, 'card_tree'):
            self.main_window.card_tree.selection_clear()
            self.main_window.card_tree.selection_add(self.last_multi_selection)
        
        selection = self.card_treeview.selection()
        if selection:
            item_id = selection[0]
            tags = self.card_treeview.item(item_id, 'tags')
            if tags:
                self.selected_card_id = tags[0]
    
    def on_treeview_click(self, event):
        """Treeview点击事件处理（右键直接返回，不做任何选中处理）"""
        self.last_mouse_button = event.num
        
        if event.num != 1:
            event.widget.selection_anchor("")
            return "break"
        
        region = self.card_treeview.identify_region(event.x, event.y)
        if region == "cell":
            item = self.card_treeview.identify_row(event.y)
            if item:
                if not (event.state & 0x0004) and not (event.state & 0x0001):
                    self.card_treeview.selection_set(item)
                    self.card_treeview.focus(item)
    
    def on_treeview_ctrl_click(self, event):
        """Treeview Ctrl+点击事件处理"""
        region = self.card_treeview.identify_region(event.x, event.y)
        if region == "cell":
            item = self.card_treeview.identify_row(event.y)
            if item:
                if item in self.card_treeview.selection():
                    self.card_treeview.selection_remove(item)
                else:
                    self.card_treeview.selection_add(item)
                self.card_treeview.focus(item)
                return "break"
    
    def on_treeview_shift_click(self, event):
        """Treeview Shift+点击事件处理"""
        region = self.card_treeview.identify_region(event.x, event.y)
        if region == "cell":
            item = self.card_treeview.identify_row(event.y)
            if item and self.card_treeview.selection():
                focus_item = self.card_treeview.focus()
                if focus_item:
                    all_items = self.card_treeview.get_children()
                    focus_idx = all_items.index(focus_item)
                    try:
                        click_idx = all_items.index(item)
                        start_idx = min(focus_idx, click_idx)
                        end_idx = max(focus_idx, click_idx)
                        self.card_treeview.selection_set(all_items[start_idx:end_idx+1])
                    except ValueError:
                        pass
                return "break"
    
    def on_treeview_double_click(self, event):
        """Treeview双击事件处理"""
        selection = self.card_treeview.selection()
        if selection:
            item_id = selection[0]
            tags = self.card_treeview.item(item_id, 'tags')
            if tags:
                card_id = tags[0]
                for card in self.current_cards:
                    if card['id'] == card_id:
                        self.show_card_detail(card)
                        break
    
    def on_card_container_configure(self, event):
        """卡片容器配置变化事件处理"""
        self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all"))
    
    def highlight_selected_card(self):
        """高亮显示选中的卡片"""
        if self.selected_card_id:
            self.card_treeview.selection_remove(self.card_treeview.selection())
            for item in self.card_treeview.get_children():
                tags = self.card_treeview.item(item, 'tags')
                if tags and tags[0] == self.selected_card_id:
                    self.card_treeview.selection_add(item)
                    self.card_treeview.see(item)
                    break
    
    def edit_selected_card(self):
        """编辑选中的卡片"""
        selected_items = self.card_treeview.selection()
        if len(selected_items) == 1:
            tags = self.card_treeview.item(selected_items[0], 'tags')
            if tags:
                self.edit_card(tags[0])
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.parent, tearoff=0)
        self.context_menu.add_command(label="编辑", command=self.edit_selected_card)
        self.context_menu.add_command(label="删除", command=self.delete_selected_card)
        self.context_menu.add_separator()
        
        sort_menu = tk.Menu(self.context_menu, tearoff=0)
        sort_menu.add_command(label="按关键词排序（A→Z）", command=lambda: self.sort_by_column('keyword', 'asc'))
        sort_menu.add_command(label="按关键词排序（Z→A）", command=lambda: self.sort_by_column('keyword', 'desc'))
        sort_menu.add_command(label="按创建时间（新→旧）", command=lambda: self.set_sort_mode('time', True))
        sort_menu.add_command(label="按创建时间（旧→新）", command=lambda: self.set_sort_mode('time', False))
        sort_menu.add_command(label="按拼音排序（A→Z）", command=lambda: self.set_sort_mode('pinyin', False))
        sort_menu.add_command(label="按拼音排序（Z→A）", command=lambda: self.set_sort_mode('pinyin', True))
        
        self.context_menu.add_cascade(label="排序", menu=sort_menu)
    
    def show_context_menu(self, event):
        """显示右键菜单（同步主窗口状态，底部保证多选）"""
        self.is_right_clicking = True
        self.last_mouse_button = event.num
        
        if hasattr(self.main_window, 'card_tree'):
            self.last_multi_selection = self.main_window.card_tree.selection()
        else:
            self.last_multi_selection = self.card_treeview.selection()
        
        event.widget.focus_set()
        event.widget.selection_anchor("")
        
        region = self.card_treeview.identify_region(event.x, event.y)
        if region == "cell":
            selected_items = self.last_multi_selection
            self.context_menu.entryconfig("编辑", state="normal" if len(selected_items) == 1 else "disabled")
            self.context_menu.post(event.x_root + 10, event.y_root + 10)
        
        def reset_right_click_flag(event=None):
            self.is_right_clicking = False
            if hasattr(self.main_window, 'card_tree') and self.last_multi_selection:
                self.main_window.card_tree.selection_clear()
                self.main_window.card_tree.selection_add(self.last_multi_selection)
        
        self.context_menu.bind("<Unmap>", reset_right_click_flag)
        return "break"
    
    def sort_by_column(self, column, order='asc'):
        """按列排序"""
        self.is_time_sort = False
        self.is_pinyin_sort = False
        self.sort_column = column
        self.sort_order = order
        self.sort_menu_var.set("按列标题点击排序")
        self.update_column_headings()
        self.refresh()
    
    def set_sort_mode(self, mode, reverse=False):
        """设置排序模式"""
        if mode == 'time':
            self.is_time_sort = True
            self.is_pinyin_sort = False
            self.sort_column = None
            self.sort_menu_var.set("按创建时间（新→旧）" if reverse else "按创建时间（旧→新）")
        elif mode == 'pinyin':
            self.is_pinyin_sort = True
            self.is_time_sort = False
            self.sort_column = None
            self.sort_menu_var.set("按拼音排序（Z→A）" if reverse else "按拼音排序（A→Z）")
        self.refresh()
    
    def edit_card(self, card_id):
        """编辑指定的卡片"""
        self.main_window.show_add_card()
        self.main_window.card_editor.load_card(card_id)
    
    def delete_selected_card(self):
        """删除选中的卡片"""
        selected_items = self.card_treeview.selection()
        if not selected_items:
            return
        
        if len(selected_items) == 1:
            if tk.messagebox.askyesno("确认删除", "确定要删除选中的卡片吗？"):
                tags = self.card_treeview.item(selected_items[0], 'tags')
                if tags:
                    card_id = tags[0]
                    if self.card_manager.delete_card(card_id):
                        self.refresh()
                        self.selected_card_id = None
                        self.status_var.set("已删除1张卡片")
                    else:
                        tk.messagebox.showerror("错误", "删除卡片失败")
        else:
            if tk.messagebox.askyesno("确认删除", f"确定要删除选中的{len(selected_items)}张卡片吗？"):
                deleted_count = 0
                for item in selected_items:
                    tags = self.card_treeview.item(item, 'tags')
                    if tags:
                        card_id = tags[0]
                        if self.card_manager.delete_card(card_id):
                            deleted_count += 1
                self.refresh()
                self.selected_card_id = None
                self.status_var.set(f"已删除{deleted_count}张卡片")
    
    def update_treeview_font(self):
        """更新Treeview字体设置"""
        if hasattr(self, 'current_font_size') and hasattr(self, 'current_font_family'):
            rowheight = max(30, self.current_font_size + 10)
            self.style.configure("Treeview", 
                               rowheight=rowheight,
                               font=(self.current_font_family, self.current_font_size))
            self.style.configure("Treeview.Heading", 
                               font=(self.current_font_family, self.current_font_size, "bold"))
    
    def on_font_change(self, *args):
        """字体设置改变处理"""
        try:
            self.current_font_size = int(self.font_size_var.get())
            self.current_font_family = self.font_family_var.get()
            self.update_treeview_font()
            if self.view_var.get() == "list":
                self.update_list_view()
            else:
                self.update_card_view()
            self.status_var.set(f"字体已更新为: {self.current_font_family} {self.current_font_size}px")
        except Exception as e:
            self.status_var.set(f"字体设置错误: {str(e)}")
    
    def update_column_headings(self):
        """更新列标题显示，添加排序标记"""
        if not self.sort_column:
            return
        
        columns = {
            'keyword': '关键词',
            'definition': '释义',
            'source': '出处',
            'quote': '原文引用'
        }
        
        for col, title in columns.items():
            if self.sort_column == col:
                mark = ' ↑' if self.sort_order == 'asc' else ' ↓'
                self.card_treeview.heading(col, text=title + mark)
            else:
                self.card_treeview.heading(col, text=title)
    
    def on_sort_menu_change(self, value):
        """排序菜单改变处理"""
        if "创建时间" in value:
            self.is_time_sort = True
            self.is_pinyin_sort = False
            self.sort_column = None
            self.refresh()
        elif "拼音排序" in value:
            self.is_pinyin_sort = True
            self.is_time_sort = False
            self.sort_column = None
            self.refresh()
        else:
            self.is_time_sort = False
            self.is_pinyin_sort = False
            if self.sort_column:
                self.refresh()
            else:
                self.sort_by_column('keyword')
    
    def show_card_detail(self, card):
        """显示卡片详情窗口"""
        detail_window = tk.Toplevel(self.parent)
        detail_window.title(f"卡片详情 - {card['keyword']}")
        detail_window.geometry("600x500")
        detail_window.resizable(True, True)
        
        detail_window.update_idletasks()
        width = detail_window.winfo_width()
        height = detail_window.winfo_height()
        x = (detail_window.winfo_screenwidth() // 2) - (width // 2)
        y = (detail_window.winfo_screenheight() // 2) - (height // 2)
        detail_window.geometry(f"+{x}+{y}")
        
        detail_window.configure(bg=self.colors['bg'])
        
        detail_frame = ttk.Frame(detail_window, padding=20)
        detail_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            detail_frame,
            text="关键词（原文）:",
            font=("SimHei", 12, "bold"),
            background=self.colors['bg']
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        keyword_text = tk.Text(
            detail_frame,
            width=50,
            height=2,
            font=("SimHei", 14, "bold"),
            bg=self.colors['card_bg'],
            fg=self.colors['accent']
        )
        keyword_text.grid(row=0, column=1, sticky=tk.NSEW, pady=(0, 10))
        keyword_text.insert(tk.END, card.get('keyword', '') or '')
        keyword_text.config(state=tk.DISABLED)
        
        ttk.Label(
            detail_frame,
            text="释义（卡片正面）:",
            font=("SimHei", 12, "bold"),
            background=self.colors['bg']
        ).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        definition_text = tk.Text(
            detail_frame,
            width=50,
            height=4,
            font=("SimHei", 12),
            bg=self.colors['card_bg']
        )
        definition_text.grid(row=1, column=1, sticky=tk.NSEW, pady=(0, 10))
        definition_text.insert(tk.END, card.get('definition', '') or '')
        definition_text.config(state=tk.DISABLED)
        
        ttk.Label(
            detail_frame,
            text="出处:",
            font=("SimHei", 12, "bold"),
            background=self.colors['bg']
        ).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        source_text = tk.Text(
            detail_frame,
            width=50,
            height=1,
            font=("SimHei", 12, "italic"),
            bg=self.colors['card_bg']
        )
        source_text.grid(row=2, column=1, sticky=tk.NSEW, pady=(0, 10))
        source_text.insert(tk.END, card.get('source', '') or '')
        source_text.config(state=tk.DISABLED)
        
        ttk.Label(
            detail_frame,
            text="原文引用:",
            font=("SimHei", 12, "bold"),
            background=self.colors['bg']
        ).grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        quote_text = tk.Text(
            detail_frame,
            width=50,
            height=4,
            font=("SimHei", 12),
            bg=self.colors['card_bg']
        )
        quote_text.grid(row=3, column=1, sticky=tk.NSEW, pady=(0, 10))
        quote_text.insert(tk.END, card.get('quote', '') or '')
        quote_text.config(state=tk.DISABLED)
        
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
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text']
        )
        notes_text.grid(row=4, column=1, sticky=tk.NSEW, pady=(0, 10))
        
        notes_content = card.get('notes', '') or ''
        if notes_content:
            notes_text.insert(tk.END, notes_content)
        else:
            notes_text.insert(tk.END, "暂无注释")
            notes_text.config(foreground=self.colors['sub_text'])
        notes_text.config(state=tk.DISABLED)
        
        notes_scrollbar = ttk.Scrollbar(
            detail_frame,
            command=notes_text.yview
        )
        notes_scrollbar.grid(row=4, column=2, sticky=tk.NS, pady=(0, 10))
        notes_text.config(yscrollcommand=notes_scrollbar.set)
        
        detail_frame.columnconfigure(1, weight=1)
        detail_frame.rowconfigure(1, weight=1)
        detail_frame.rowconfigure(3, weight=1)
        detail_frame.rowconfigure(4, weight=1)
        
        detail_window.transient(self.parent)
        detail_window.grab_set()
        self.parent.wait_window(detail_window)