#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索面板类，负责卡片搜索功能
搜索结果直接显示在面板下方
"""
import tkinter as tk
from tkinter import ttk, messagebox

class SearchPanel:
    """搜索面板类（内置搜索结果列表）"""
    def __init__(self, parent, card_manager, main_window):
        """
        初始化搜索面板

        Args:
            parent: 父容器（MainWindow的search视图）
            card_manager: 卡片管理器实例（用于查询卡片）
            main_window: 主窗口实例（用于编辑/删除等操作）
        """
        self.parent = parent
        self.card_manager = card_manager
        self.main_window = main_window

        # 复用主窗口字体配置
        if hasattr(main_window, 'get_font'):
            self.font = main_window.get_font
        else:
            self.font = lambda size=12, bold=False: ("Microsoft YaHei", size, "bold" if bold else "normal")

        # 当前搜索结果（卡片列表）
        self.current_results = []

        self.create_search_ui()  # 构建搜索UI

    def create_search_ui(self):
        """创建搜索面板UI组件（包含搜索框和结果列表）"""
        # 主框架（填充父容器）
        search_frame = ttk.Frame(self.parent, padding="20")
        search_frame.pack(fill=tk.BOTH, expand=True)

        # 搜索标题
        title_label = ttk.Label(
            search_frame,
            text="卡片搜索",
            font=self.font(16, bold=True)
        )
        title_label.pack(anchor=tk.W, pady=(0, 15))

        # 搜索输入区
        input_frame = ttk.Frame(search_frame)
        input_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(
            input_frame,
            text="关键词：",
            font=self.font(13)
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 搜索输入框
        self.search_entry = ttk.Entry(
            input_frame,
            width=50,
            font=self.font(13)
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", lambda e: self.do_search())  # 回车触发搜索

        # 搜索按钮
        search_btn = ttk.Button(
            input_frame,
            text="搜索",
            command=self.do_search,
            style="Accent.TButton"
        )
        search_btn.pack(side=tk.LEFT, padx=(10, 0))

        # 结果提示标签（放在列表上方）
        self.result_label = ttk.Label(
            search_frame,
            text="请输入关键词搜索（支持关键词、释义、出处、原文模糊匹配）",
            font=self.font(13)
        )
        self.result_label.pack(anchor=tk.W, pady=(0, 10))

        # ---------- 搜索结果列表（Treeview）----------
        list_frame = ttk.Frame(search_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 创建滚动条
        y_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建表格
        columns = ("keyword", "definition", "source", "quote")
        self.result_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
            yscrollcommand=y_scrollbar.set
        )
        y_scrollbar.config(command=self.result_tree.yview)

        # 设置列标题
        self.result_tree.heading("keyword", text="关键词", anchor=tk.W)
        self.result_tree.heading("definition", text="释义", anchor=tk.W)
        self.result_tree.heading("source", text="出处", anchor=tk.W)
        self.result_tree.heading("quote", text="原文", anchor=tk.W)

        # 设置列宽
        self.result_tree.column("keyword", width=150)
        self.result_tree.column("definition", width=250)
        self.result_tree.column("source", width=150)
        self.result_tree.column("quote", width=300)

        # 设置行高（从主窗口样式继承）
        style = ttk.Style()
        style.configure("SearchTreeview.Treeview", rowheight=30)
        self.result_tree.configure(style="SearchTreeview.Treeview")

        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 绑定事件
        self.result_tree.bind("<Double-1>", self.on_item_double_click)
        self.result_tree.bind("<Button-3>", self.show_context_menu)

        # 右键菜单
        self.context_menu = tk.Menu(self.parent, tearoff=0)
        self.context_menu.add_command(label="编辑  \tCtrl+O", command=self.edit_selected_card)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除  \tDel", command=self.delete_selected_card)

        # 同步主窗口的全局快捷键（可选）
        self.bind_shortcuts()

    def bind_shortcuts(self):
        """绑定一些全局快捷键（当搜索面板可见时有效）"""
        # 注意：这些绑定是针对整个 root 的，可能会与主窗口重复，但无大碍
        root = self.main_window.root
        root.bind("<Control-o>", lambda e: self.edit_selected_card())
        root.bind("<Control-O>", lambda e: self.edit_selected_card())
        root.bind("<Delete>", lambda e: self.delete_selected_card())

    def focus_search_entry(self):
        """让搜索框获取焦点（主窗口调用）"""
        self.search_entry.focus_set()

    def do_search(self):
        """执行搜索并刷新结果列表"""
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.result_label.config(text="请输入关键词后搜索")
            self.clear_results()
            return

        # 搜索所有卡片
        all_cards = self.card_manager.get_all_cards()
        matched_cards = [
            card for card in all_cards
            if (keyword in card.get("keyword", "")
                or keyword in card.get("definition", "")
                or keyword in card.get("source", "")
                or keyword in card.get("quote", ""))
        ]

        self.current_results = matched_cards
        self.result_label.config(text=f"找到 {len(matched_cards)} 条匹配结果")

        # 刷新结果列表
        self.refresh_result_list()

    def refresh_result_list(self):
        """刷新搜索结果列表显示"""
        # 清空现有列表
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        # 插入搜索结果
        for card in self.current_results:
            values = (
                card['keyword'],
                card['definition'][:50] + "..." if len(card['definition']) > 50 else card['definition'],
                card['source'],
                card['quote'][:50] + "..." if len(card['quote']) > 50 else card['quote']
            )
            self.result_tree.insert("", tk.END, values=values, tags=(card['id'],))

    def clear_results(self):
        """清空搜索结果"""
        self.current_results = []
        self.refresh_result_list()

    def on_item_double_click(self, event):
        """双击打开编辑窗口"""
        selected = self.result_tree.selection()
        if selected:
            item = selected[0]
            card_id = self.result_tree.item(item, "tags")[0]
            self.main_window.show_edit_card(card_id)

    def show_context_menu(self, event):
        """显示右键菜单"""
        # 获取点击位置的行
        item = self.result_tree.identify_row(event.y)
        if not item:
            return

        # 如果当前行不在选中列表中，先选中它（单选）
        if item not in self.result_tree.selection():
            self.result_tree.selection_set(item)

        selected_count = len(self.result_tree.selection())
        # 编辑菜单仅在单选时启用
        self.context_menu.entryconfig("编辑  \tCtrl+O", state="normal" if selected_count == 1 else "disabled")
        self.context_menu.post(event.x_root + 10, event.y_root + 10)

    def edit_selected_card(self):
        """编辑选中的卡片"""
        selected = self.result_tree.selection()
        if len(selected) == 1:
            item = selected[0]
            card_id = self.result_tree.item(item, "tags")[0]
            self.main_window.show_add_card()
            self.main_window.card_editor.load_card(card_id)

    def delete_selected_card(self):
        """删除选中的卡片（支持批量）"""
        selected = self.result_tree.selection()
        if not selected:
            return

        # 获取选中的卡片ID和关键词
        card_ids = []
        for item in selected:
            card_id = self.result_tree.item(item, "tags")[0]
            card_ids.append(card_id)

        if len(card_ids) == 1:
            card = self.card_manager.get_card(card_ids[0])
            if not card:
                return
            if not messagebox.askyesno("确认删除", f"确定要删除卡片 '{card['keyword']}' 吗？"):
                return
        else:
            if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(card_ids)} 张卡片吗？"):
                return

        # 执行删除
        deleted = 0
        for cid in card_ids:
            if self.card_manager.delete_card(cid):
                deleted += 1

        # 刷新搜索结果（从最新数据中重新搜索）
        self.do_search()

        # 可选：刷新主窗口的概览列表（保持数据同步）
        if hasattr(self.main_window, 'refresh_list_view'):
            self.main_window.refresh_list_view()

        # 显示状态栏消息（如果有）
        if hasattr(self.main_window, 'status_var'):
            self.main_window.status_var.set(f"已删除 {deleted} 张卡片")