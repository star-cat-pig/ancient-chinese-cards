#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出处分类视图类，负责按出处（书本）分类展示卡片
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any

class SourceCategoryView:
    """出处分类视图类"""
    
    def __init__(self, parent, card_manager, main_window):
        """
        初始化出处分类视图
        
        Args:
            parent: 父窗口组件
            card_manager: 卡片管理器实例
            main_window: 主窗口实例
        """
        self.parent = parent
        self.card_manager = card_manager
        self.main_window = main_window
        self.font = main_window.app.settings_manager.get_font 

        # 设置主题颜色（和主窗口完全一致）
        self.colors = main_window.colors
        
        # 视图状态
        self.current_source = None  # 当前选中的出处，None=显示出处列表
        self.source_list = []       # 所有出处列表
        self.current_cards = []     # 当前出处下的卡片列表
        
        # 创建视图界面
        self.create_view()
    
    def create_view(self):
        """创建出处分类视图主界面"""
        # 主框架
        self.category_frame = ttk.Frame(self.parent)
        self.category_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 顶部标题栏（带返回按钮）
        self.create_title_bar()
        
        # 内容容器（切换出处列表/卡片列表）
        self.content_frame = ttk.Frame(self.category_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 1. 出处列表界面
        self.create_source_list_view()
        
        # 2. 出处下的卡片列表界面（初始隐藏）
        self.create_source_card_view()
        
        # 初始显示出处列表
        self.show_source_list()
    
    def create_title_bar(self):
        """创建顶部标题栏（带返回按钮）"""
        self.title_bar = ttk.Frame(self.category_frame)
        self.title_bar.pack(fill=tk.X, pady=(0, 10))
        
        # 标题（靠左）
        self.title_var = tk.StringVar()
        self.title_var.set("出处分类")
        
        self.title_label = ttk.Label(
            self.title_bar,
            textvariable=self.title_var,
            font=self.font(16, bold=True)
        )
        self.title_label.pack(side=tk.LEFT, anchor=tk.W)
        
        # 返回按钮（靠右，初始隐藏）
        self.back_btn = ttk.Button(
            self.title_bar,
            text="返回",
            command=self.show_source_list,
            width=8
        )
        # 先不pack，等需要时再pack到右边
    
    def create_source_list_view(self):
        """创建出处列表界面"""
        self.source_list_frame = ttk.Frame(self.content_frame)
        
        # 列表框架
        tree_frame = ttk.Frame(self.source_list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建出处列表Treeview
        columns = ("source_name", "card_count")
        self.source_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        
        # 设置列标题
        self.source_tree.heading("source_name", text="出处（书本）名称", anchor=tk.W)
        self.source_tree.heading("card_count", text="卡片数量", anchor=tk.W)
        
        # 设置列宽
        self.source_tree.column("source_name", width=500, minwidth=300)
        self.source_tree.column("card_count", width=100, minwidth=80, anchor=tk.CENTER)
        
        # 垂直滚动条
        yscrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.source_tree.yview)
        self.source_tree.configure(yscroll=yscrollbar.set)
        yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.source_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定事件：双击进入对应出处的卡片列表
        self.source_tree.bind("<Double-1>", self.on_source_double_click)
        # 绑定回车事件
        self.source_tree.bind("<Return>", self.on_source_double_click)
    
    def create_source_card_view(self):
        """创建出处下的卡片列表界面（和主界面概览页完全一致）"""
        self.card_list_frame = ttk.Frame(self.content_frame)
        
        # 列表框架
        tree_frame = ttk.Frame(self.card_list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建卡片列表Treeview（和主界面完全对齐）
        columns = ("keyword", "definition", "source", "quote")
        self.source_card_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )
        
        # 设置列标题（和主界面一致）
        self.source_card_tree.heading("keyword", text="关键词", anchor=tk.W)
        self.source_card_tree.heading("definition", text="释义", anchor=tk.W)
        self.source_card_tree.heading("source", text="出处", anchor=tk.W)
        self.source_card_tree.heading("quote", text="原文", anchor=tk.W)
        
        # 设置列宽（和主界面一致）
        self.source_card_tree.column("keyword", width=150)
        self.source_card_tree.column("definition", width=250)
        self.source_card_tree.column("source", width=150)
        self.source_card_tree.column("quote", width=300)
        
        # 垂直滚动条
        yscrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.source_card_tree.yview)
        self.source_card_tree.configure(yscroll=yscrollbar.set)
        yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.source_card_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定事件（和主界面完全一致）
        self.source_card_tree.bind("<Double-1>", self.on_card_double_click)
        self.source_card_tree.bind("<Button-3>", self.show_card_context_menu)
        
        # 创建右键菜单（和主界面完全一致）
        self.create_card_context_menu()
    
    def create_card_context_menu(self):
        """创建卡片右键菜单（和主界面完全对齐）"""
        self.card_context_menu = tk.Menu(self.parent, tearoff=0)
        self.card_context_menu.add_command(label="编辑  \tCtrl+O", command=self.edit_selected_card)
        self.card_context_menu.add_separator()
        self.card_context_menu.add_command(label="删除  \tDel", command=self.delete_selected_card)
    
    # ------------------- 视图切换逻辑 -------------------
    def show_source_list(self):
        """显示出处列表（主视图）"""
        # 解绑 Esc 键
        self.parent.unbind("<Escape>")
        
        # 隐藏卡片列表
        self.card_list_frame.pack_forget()
        # 显示出处列表
        self.source_list_frame.pack(fill=tk.BOTH, expand=True)
        # 隐藏返回按钮
        self.back_btn.pack_forget()
        # 更新标题
        self.title_var.set("出处分类")
        # 刷新出处列表数据
        self.refresh_source_list()
        # 重置当前选中出处
        self.current_source = None
    
    def show_source_cards(self, source_name: str):
        """显示指定出处下的卡片列表"""
        # 记录当前出处
        self.current_source = source_name
        # 隐藏出处列表
        self.source_list_frame.pack_forget()
        # 显示卡片列表
        self.card_list_frame.pack(fill=tk.BOTH, expand=True)
        # 显示返回按钮（靠右）
        self.back_btn.pack(side=tk.RIGHT, padx=(0, 0))
        # 更新标题
        self.title_var.set(f"出处：{source_name}")
        # 刷新卡片列表
        self.refresh_source_card_list(source_name)
        
        # 绑定 Esc 键返回（绑定到整个父窗口）
        self.parent.bind("<Escape>", lambda e: self.show_source_list())
    
    # ------------------- 数据刷新逻辑 -------------------
    def refresh_source_list(self):
        """刷新出处列表数据"""
        # 清空现有列表
        for item in self.source_tree.get_children():
            self.source_tree.delete(item)
        
        # 从卡片管理器获取所有出处
        self.source_list = self.card_manager.get_all_sources()
        
        # 插入数据
        for source in self.source_list:
            self.source_tree.insert("", tk.END, values=(
                source["source_name"],
                source["card_count"]
            ), tags=(source["source_name"],))
    
    def refresh_source_card_list(self, source_name: str):
        """刷新指定出处的卡片列表"""
        # 清空现有列表
        for item in self.source_card_tree.get_children():
            self.source_card_tree.delete(item)
        
        # 从卡片管理器获取该出处的卡片
        self.current_cards = self.card_manager.get_cards_by_source(source_name)
        
        # 插入数据（和主界面格式一致）
        for card in self.current_cards:
            values = (
                card['keyword'],
                card['definition'][:50] + "..." if len(card['definition']) > 50 else card['definition'],
                card['source'],
                card['quote'][:50] + "..." if len(card['quote']) > 50 else card['quote']
            )
            self.source_card_tree.insert("", tk.END, values=values, tags=(card['id'],))
    
    def refresh(self):
        """对外暴露的刷新方法（导航栏点击时调用）"""
        if self.current_source:
            self.refresh_source_card_list(self.current_source)
        else:
            self.refresh_source_list()
    
    # ------------------- 事件处理逻辑 -------------------
    def on_source_double_click(self, event):
        """双击出处项，进入对应卡片列表"""
        selected_items = self.source_tree.selection()
        if selected_items:
            item = selected_items[0]
            source_name = self.source_tree.item(item, "tags")[0]
            self.show_source_cards(source_name)
    
    def on_card_double_click(self, event):
        """双击卡片，打开编辑窗口（和主界面一致）"""
        selected_items = self.source_card_tree.selection()
        if selected_items:
            item = selected_items[0]
            card_id = self.source_card_tree.item(item, "tags")[0]
            self.main_window.show_edit_card(card_id)
    
    def show_card_context_menu(self, event):
        """显示卡片右键菜单"""
        selected_items = self.source_card_tree.selection()
        if not selected_items:
            return
        
        # 右键点击时选中对应行
        item = self.source_card_tree.identify_row(event.y)
        if item and item not in selected_items:
            self.source_card_tree.selection_set(item)
        
        # 菜单可用性
        self.card_context_menu.entryconfig("编辑  \tCtrl+O", state="normal" if len(selected_items) == 1 else "disabled")
        
        # 显示菜单
        self.card_context_menu.post(event.x_root + 10, event.y_root + 10)
    
    def edit_selected_card(self):
        """编辑选中的卡片"""
        selected_items = self.source_card_tree.selection()
        if selected_items:
            item = selected_items[0]
            card_id = self.source_card_tree.item(item, "tags")[0]
            self.main_window.show_add_card()
            self.main_window.card_editor.load_card(card_id)
    
    def delete_selected_card(self):
        """删除选中的卡片（批量支持）"""
        selected_items = self.source_card_tree.selection()
        if not selected_items:
            return
        
        # 批量删除确认
        if len(selected_items) > 1:
            if tk.messagebox.askyesno("确认批量删除", f"确定要删除选中的{len(selected_items)}张卡片吗？"):
                for item in selected_items:
                    card_id = self.source_card_tree.item(item, "tags")[0]
                    self.card_manager.delete_card(card_id)
                # 刷新列表
                self.refresh()
        else:
            # 单个删除
            item = selected_items[0]
            card_id = self.source_card_tree.item(item, "tags")[0]
            card = self.card_manager.get_card(card_id)
            if card and tk.messagebox.askyesno("确认删除", f"确定要删除卡片 '{card['keyword']}' 吗？"):
                if self.card_manager.delete_card(card_id):
                    self.refresh()