#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
导入导出对话框类，负责卡片数据的导入和导出
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from typing import Optional

class ImportExportDialog:
    """导入导出对话框类"""
    
    def __init__(self, parent, card_manager, main_window, mode: str = "both"):
        """
        初始化导入导出对话框
        
        Args:
            parent: 父窗口组件
            card_manager: 卡片管理器实例
            main_window: 主窗口实例
            mode: 对话框模式，可选值："import", "export", "both"
        """
        self.parent = parent
        self.card_manager = card_manager
        self.main_window = main_window
        
        # 设置主题颜色
        self.colors = main_window.colors
        
        # 对话框模式
        self.mode = mode
        
        # 如果父窗口是主窗口，则创建模态对话框
        if parent == main_window.root:
            self.create_modal_dialog()
        else:
            # 否则创建嵌入视图
            self.create_embedded_view()
    
    def create_modal_dialog(self):
        """创建模态对话框"""
        # 创建对话框窗口
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("导入导出卡片")
        self.dialog.geometry("600x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 创建对话框内容
        self.create_dialog_content(self.dialog)
    
    def create_embedded_view(self):
        """创建嵌入视图"""
        # 创建视图框架
        self.view_frame = ttk.Frame(self.parent)
        self.view_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建对话框内容
        self.create_dialog_content(self.view_frame)
    
    def create_dialog_content(self, parent):
        """创建对话框内容"""
        # 创建选项卡控件
        tab_control = ttk.Notebook(parent)
        
        # 如果模式包含导入，创建导入选项卡
        if self.mode in ["import", "both"]:
            import_tab = ttk.Frame(tab_control)
            tab_control.add(import_tab, text="导入卡片")
            self.create_import_tab(import_tab)
        
        # 如果模式包含导出，创建导出选项卡
        if self.mode in ["export", "both"]:
            export_tab = ttk.Frame(tab_control)
            tab_control.add(export_tab, text="导出卡片")
            self.create_export_tab(export_tab)
        
        # 显示选项卡控件
        tab_control.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_import_tab(self, parent):
        """创建导入选项卡"""
        # 创建导入说明
        import_info = ttk.Label(
            parent,
            text="请选择导入方式或文件格式",
            font=("SimHei", 12, "bold")
        )
        import_info.pack(anchor=tk.W, pady=(10, 20))
        
        # 创建导入选项框架
        options_frame = ttk.Frame(parent)
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 导入方式选择
        self.import_method = tk.StringVar(value="text")
        
        # 文本格式选项
        text_format_radio = ttk.Radiobutton(
            options_frame,
            text="文本格式（支持复制粘贴）",
            variable=self.import_method,
            value="text",
            command=self.on_import_method_change
        )
        text_format_radio.pack(anchor=tk.W, pady=(0, 10))
        
        # 文件导入选项
        file_import_radio = ttk.Radiobutton(
            options_frame,
            text="从文件导入",
            variable=self.import_method,
            value="file",
            command=self.on_import_method_change
        )
        file_import_radio.pack(anchor=tk.W, pady=(0, 10))
        
        # 创建文本输入框架
        self.text_input_frame = ttk.Frame(parent)
        self.text_input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 创建文本输入框
        self.import_text = tk.Text(
            self.text_input_frame,
            width=60,
            height=10,
            font=("SimHei", 12),
            wrap=tk.WORD
        )
        self.import_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        text_scrollbar = ttk.Scrollbar(
            self.text_input_frame,
            command=self.import_text.yview
        )
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.import_text.config(yscrollcommand=text_scrollbar.set)
        
        # 创建文件选择框架（初始隐藏）
        self.file_select_frame = ttk.Frame(parent)
        
        # 文件路径输入框
        self.file_path_var = tk.StringVar()
        file_path_entry = ttk.Entry(
            self.file_select_frame,
            textvariable=self.file_path_var,
            width=50,
            font=("SimHei", 12)
        )
        file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 文件选择按钮
        file_select_button = ttk.Button(
            self.file_select_frame,
            text="浏览...",
            command=self.select_import_file
        )
        file_select_button.pack(side=tk.LEFT)
        
        # 创建格式说明框架
        format_info_frame = ttk.Frame(parent)
        format_info_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 格式说明标题
        ttk.Label(
            format_info_frame,
            text="文本格式说明:",
            font=("SimHei", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))
        
        # 格式说明文本
        format_example = """
支持多种格式：

格式1 - 标准格式：
释义：关键词。出处:“原文”。

格式2 - 多行注释：
释义：关键词。出处:“原文”。
这里是额外的注释内容，
可以包含多行。

格式3 - 关键词分组：
关键词
  释义1：出处1:“原文1”。
  释义2：出处2:“原文2”。

示例：
黑色：黝。《闲居赋》:“浮梁黝以径度”。

bu
  補衣：清方苞《沈氏姑生壙銘》：“姑老矣，偶袒內襦，補輟無間咫搹者。”
  補助：補苴。方苞《與徐司空蝶園書二》：“多方補苴，始能貲給。”
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
        
        # 添加滚动条
        format_scrollbar = ttk.Scrollbar(
            format_info_frame,
            command=format_info_text.yview
        )
        format_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        format_info_text.config(yscrollcommand=format_scrollbar.set)
        
        # 创建按钮框架
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 导入选项
        import_options_frame = ttk.Frame(button_frame)
        import_options_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        # 允许重复卡片选项
        self.allow_duplicates = tk.BooleanVar(value=False)
        allow_duplicates_check = ttk.Checkbutton(
            import_options_frame,
            text="允许重复卡片",
            variable=self.allow_duplicates
        )
        allow_duplicates_check.pack(side=tk.LEFT)
        
        # 导入按钮
        import_button = ttk.Button(
            button_frame,
            text="导入",
            command=self.import_cards,
            style="Accent.TButton"
        )
        import_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 取消按钮
        if hasattr(self, 'dialog'):
            cancel_button = ttk.Button(
                button_frame,
                text="取消",
                command=self.dialog.destroy
            )
            cancel_button.pack(side=tk.RIGHT)
    
    def create_export_tab(self, parent):
        """创建导出选项卡"""
        # 创建导出说明
        export_info = ttk.Label(
            parent,
            text="请选择导出格式和目标",
            font=("SimHei", 12, "bold")
        )
        export_info.pack(anchor=tk.W, pady=(10, 20))
        
        # 创建导出选项框架
        options_frame = ttk.Frame(parent)
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 导出方式选择
        self.export_method = tk.StringVar(value="text")
        
        # 文本格式选项
        text_format_radio = ttk.Radiobutton(
            options_frame,
            text="文本格式（显示在界面上）",
            variable=self.export_method,
            value="text",
            command=self.on_export_method_change
        )
        text_format_radio.pack(anchor=tk.W, pady=(0, 10))
        
        # 文件导出选项
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
        
        # 按关键词分组选项
        self.group_by_keyword = tk.BooleanVar(value=False)
        group_by_keyword_check = ttk.Checkbutton(
            export_format_frame,
            text="按关键词分组",
            variable=self.group_by_keyword
        )
        group_by_keyword_check.pack(side=tk.LEFT)
        
        # 创建文本输出框架
        self.text_output_frame = ttk.Frame(parent)
        self.text_output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 创建文本输出框
        self.export_text = tk.Text(
            self.text_output_frame,
            width=60,
            height=10,
            font=("SimHei", 12),
            wrap=tk.WORD
        )
        self.export_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.export_text.config(state=tk.DISABLED)
        
        # 添加滚动条
        text_scrollbar = ttk.Scrollbar(
            self.text_output_frame,
            command=self.export_text.yview
        )
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.export_text.config(yscrollcommand=text_scrollbar.set)
        
        # 创建文件保存框架（初始隐藏）
        self.file_save_frame = ttk.Frame(parent)
        
        # 文件路径输入框
        self.save_path_var = tk.StringVar()
        save_path_entry = ttk.Entry(
            self.file_save_frame,
            textvariable=self.save_path_var,
            width=50,
            font=("SimHei", 12)
        )
        save_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 文件选择按钮
        save_select_button = ttk.Button(
            self.file_save_frame,
            text="浏览...",
            command=self.select_export_file
        )
        save_select_button.pack(side=tk.LEFT)
        
        # 创建按钮框架
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 复制按钮（仅文本模式）
        self.copy_button = ttk.Button(
            button_frame,
            text="复制到剪贴板",
            command=self.copy_to_clipboard
        )
        
        # 导出按钮
        export_button = ttk.Button(
            button_frame,
            text="导出",
            command=self.export_cards,
            style="Accent.TButton"
        )
        export_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 取消按钮
        if hasattr(self, 'dialog'):
            cancel_button = ttk.Button(
                button_frame,
                text="取消",
                command=self.dialog.destroy
            )
            cancel_button.pack(side=tk.RIGHT)
        
        # 默认显示复制按钮
        self.copy_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    def on_import_method_change(self):
        """导入方式变更事件处理"""
        # 隐藏所有输入框架
        self.text_input_frame.pack_forget()
        self.file_select_frame.pack_forget()
        
        # 根据选择的导入方式显示对应的输入框架
        if self.import_method.get() == "text":
            self.text_input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        else:
            self.file_select_frame.pack(fill=tk.X, pady=(0, 20))
    
    def on_export_method_change(self):
        """导出方式变更事件处理"""
        # 隐藏所有输出框架
        self.text_output_frame.pack_forget()
        self.file_save_frame.pack_forget()
        self.copy_button.pack_forget()
        
        # 根据选择的导出方式显示对应的输出框架
        if self.export_method.get() == "text":
            self.text_output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            self.copy_button.pack(side=tk.RIGHT, padx=(0, 10))
        else:
            self.file_save_frame.pack(fill=tk.X, pady=(0, 20))
    
    def select_import_file(self):
        """选择导入文件"""
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择导入文件",
            filetypes=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        
        # 如果用户选择了文件，更新文件路径
        if file_path:
            self.file_path_var.set(file_path)
    
    def select_export_file(self):
        """选择导出文件"""
        # 打开文件保存对话框
        file_path = filedialog.asksaveasfilename(
            title="选择导出文件",
            defaultextension=".txt",
            filetypes=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        
        # 如果用户选择了文件，更新文件路径
        if file_path:
            self.save_path_var.set(file_path)
    
    def import_cards(self):
        """导入卡片"""
        try:
            # 根据选择的导入方式获取数据
            if self.import_method.get() == "text":
                # 从文本框获取数据
                text = self.import_text.get(1.0, tk.END).strip()
                if not text:
                    messagebox.showwarning("警告", "请输入要导入的文本")
                    return
            else:
                # 从文件获取数据
                file_path = self.file_path_var.get().strip()
                if not file_path:
                    messagebox.showwarning("警告", "请选择要导入的文件")
                    return
                
                if not os.path.exists(file_path):
                    messagebox.showerror("错误", "指定的文件不存在")
                    return
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                
                if not text:
                    messagebox.showwarning("警告", "选择的文件为空")
                    return
            
            # 获取是否允许重复卡片的选项
            allow_duplicates = self.allow_duplicates.get()
            
            # 导入卡片（GUI模式下禁用交互式解析）
            stats = self.card_manager.import_cards_from_text(text, allow_duplicates, interactive=False)
            
            # 显示导入成功消息
            message = f"导入完成！\n" \
                      f"总计: {stats['total']} 张卡片\n" \
                      f"新增: {stats['added']} 张卡片\n" \
                      f"合并: {stats['merged']} 张卡片\n" \
                      f"失败: {stats['failed']} 张卡片"
            
            messagebox.showinfo("导入结果", message)
            
            # 刷新主窗口
            self.main_window.card_view.refresh()
            
            # 如果是对话框模式，关闭对话框
            if hasattr(self, 'dialog'):
                self.dialog.destroy()
        
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {str(e)}")
    
    def export_cards(self):
        """导出卡片"""
        try:
            # 获取是否按关键词分组的选项
            group_by_keyword = self.group_by_keyword.get()
            
            # 导出卡片为文本格式
            text = self.card_manager.export_cards_to_text(group_by_keyword)
            
            # 根据选择的导出方式处理数据
            if self.export_method.get() == "text":
                # 显示在文本框中
                self.export_text.config(state=tk.NORMAL)
                self.export_text.delete(1.0, tk.END)
                self.export_text.insert(tk.END, text)
                self.export_text.config(state=tk.DISABLED)
                
                # 启用复制按钮
                self.copy_button.config(state=tk.NORMAL)
                
                messagebox.showinfo("成功", f"成功导出 {len(self.card_manager.get_all_cards())} 张卡片")
            else:
                # 保存到文件
                file_path = self.save_path_var.get().strip()
                if not file_path:
                    messagebox.showwarning("警告", "请选择要保存的文件")
                    return
                
                # 写入文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                messagebox.showinfo("成功", f"成功导出 {len(self.card_manager.get_all_cards())} 张卡片到文件")
                
                # 如果是对话框模式，关闭对话框
                if hasattr(self, 'dialog'):
                    self.dialog.destroy()
        
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def copy_to_clipboard(self):
        """复制到剪贴板"""
        # 获取导出文本
        text = self.export_text.get(1.0, tk.END)
        
        # 复制到剪贴板
        self.parent.clipboard_clear()
        self.parent.clipboard_append(text)
        
        messagebox.showinfo("成功", "已复制到剪贴板")