#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
古文卡片学习软件主程序入口
"""

import tkinter as tk
from tkinter import messagebox, font, ttk
import json
import sys
import os
from datetime import datetime

# 导入自定义模块
from ui.main_window import MainWindow
from ui.settings_manager import SettingsManager
from card_manager import CardManager
from update_manager import UpdateChecker

class AncientChineseCardsApp:
    """古文卡片学习软件主应用类"""
    
    def __init__(self):
        """初始化应用程序"""
        self.root = tk.Tk()
        self.root.title("古文卡片学习软件")
        self.root.geometry("1024x768")
        
        # 初始化图标路径（关键：兼容脚本运行和打包后）
        self.icon_path = self._get_icon_path()
        
        # 设置主窗口图标
        self._set_window_icon(self.root)
        
        # 自动绑定子窗口创建事件，所有新窗口自动应用图标
        self.root.bind("<Create>", self._on_window_create)
        
        # 初始化卡片管理器
        self.card_manager = CardManager()
        
        # 初始化设置管理器
        self.settings_manager = SettingsManager(self)
        
        # 初始化更新管理器（新增）
        self.update_checker = UpdateChecker(self)
        
        # 设置中文字体
        self.setup_fonts()
        
        # 创建主窗口
        self.main_window = MainWindow(self.root, self.card_manager, self)
        
        # 加载卡片数据
        
        # 启动时自动检测更新（根据设置）
        if self.settings_manager.get_setting("update", "auto_check_update"):
            self.root.after(1000, self._auto_check_update)  # 延迟1秒检测，不阻塞启动
        self.load_cards()
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        """设置应用程序字体"""
        # 尝试使用系统中文字体
        try:
            # 对于Windows
            default_font = font.Font(family="SimHei", size=10)
            self.root.option_add("*Font", default_font)
        except:
            try:
                # 对于macOS
                default_font = font.Font(family="Heiti TC", size=10)
                self.root.option_add("*Font", default_font)
            except:
                # 对于Linux
                default_font = font.Font(family="WenQuanYi Micro Hei", size=10)
                self.root.option_add("*Font", default_font)
        
        # 应用设置（不再包含字体设置）
        # self.settings_manager.apply_settings()
    
    def load_cards(self):
        """加载卡片数据（后台加载，无加载窗口）"""
        try:
            # 直接加载卡片数据
            self.card_manager.load_cards()
            
            # 更新状态栏显示加载结果
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.config(text=f"已加载 {len(self.card_manager.cards)} 张卡片")
            
            # 移除重复的刷新调用，因为show_overview已经会刷新列表
            # if hasattr(self.main_window, 'refresh_list_view'):
            #     self.main_window.refresh_list_view()
        except Exception as e:
            messagebox.showerror("错误", f"加载卡片失败: {str(e)}")
    
    # 加载窗口相关功能已移除
    
    def save_cards(self):
        """保存卡片数据"""
        try:
            self.card_manager.save_cards()
            messagebox.showinfo("成功", "卡片数据已保存")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存卡片失败: {str(e)}")
            return False
    
    def on_closing(self):
        """窗口关闭事件处理"""
        # 检查是否有卡片被修改
        has_modified_cards = self.card_manager.has_modified_cards()
        
        if not has_modified_cards:
            # 如果没有修改，检查更新后退出
            self._check_update_before_exit()
            return
        
        # 如果有修改，显示保存提示
        # 创建自定义对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("退出")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2)
        y = (self.root.winfo_height() // 2) - (height // 2)
        dialog.geometry('+{}+{}'.format(x, y))
        
        # 提示标签
        label = tk.Label(dialog, text="是否保存更改后退出？", font=("SimHei", 12))
        label.pack(pady=20)
        
        # 按钮框架
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        # 保存按钮
        save_btn = tk.Button(
            button_frame, 
            text="保存(S)", 
            command=lambda: self._close_app(dialog, True),
            width=10,
            bg="#C44536",
            fg="#000000"
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # 不保存按钮
        no_save_btn = tk.Button(
            button_frame, 
            text="不保存(N)", 
            command=lambda: self._close_app(dialog, False),
            width=10
        )
        no_save_btn.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮
        cancel_btn = tk.Button(
            button_frame, 
            text="取消", 
            command=dialog.destroy,
            width=10
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def _check_update_before_exit(self):
        """退出前检查更新"""
        # 调用更新管理器的退出检查
        if hasattr(self, 'update_checker') and self.update_checker:
            if hasattr(self.update_checker, 'on_app_exit'):
                self.update_checker.on_app_exit()
                return  # 关键：让update_checker负责销毁窗口
        
        # 如果没有更新管理器或没有待处理的更新，直接退出
        if self.root.winfo_exists():
            self.root.destroy()
    
    def _close_app(self, dialog, save_data):
        """关闭应用程序"""
        dialog.destroy()
        
        # 先处理保存逻辑
        if save_data:
            success = self.save_cards()
            if not success:
                # 如果保存失败，不退出程序
                return
        
        # 检查更新后退出
        self._check_update_before_exit()
    
    def _get_icon_path(self):
        """获取图标路径（兼容脚本运行和打包后）"""
        # 优先查找项目根目录的 assets 文件夹
        base_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_path, "assets", "icon.ico")
        
        # 如果.ico文件不存在，尝试.png格式
        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_path, "assets", "icon.png")
        
        # 调试用：打印图标路径，方便排查问题
        print(f"图标路径：{icon_path}（存在：{os.path.exists(icon_path)}）")
        return icon_path
    
    def _auto_check_update(self):
        """自动检测更新（后台执行）"""
        def check():
            if self.update_checker.is_update_available():
                self.root.after(0, self.update_checker.show_update_prompt)  # 回到主线程显示窗口
        # 后台线程检测，不阻塞UI
        import threading
        threading.Thread(target=check, daemon=True).start()
    
    def _set_window_icon(self, window):
        """给单个窗口设置图标（兼容不同格式和系统）"""
        if not os.path.exists(self.icon_path):
            return  # 图标文件不存在时不报错
        
        try:
            # Windows 优先使用 .ico 格式
            if self.icon_path.endswith(".ico"):
                window.iconbitmap(self.icon_path)
            else:
                # 其他格式（如.png）使用 iconphoto
                icon_image = tk.PhotoImage(file=self.icon_path)
                window.iconphoto(True, icon_image)
                # 保存引用，避免被垃圾回收
                window.icon_image = icon_image
        except Exception as e:
            print(f"设置窗口图标失败：{str(e)}")
    
    def _on_window_create(self, event):
        """窗口创建时自动设置图标（包括子窗口）"""
        # 只处理 Toplevel 子窗口（主窗口已单独设置）
        if isinstance(event.widget, tk.Toplevel):
            print(f"检测到新窗口创建：{event.widget.winfo_class()}")
            # 立即设置图标
            self._set_window_icon(event.widget)
            # 延迟再次设置作为备份，确保窗口完全创建后图标正确显示
            event.widget.after(10, lambda: self._set_window_icon(event.widget))
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = AncientChineseCardsApp()
    app.run()