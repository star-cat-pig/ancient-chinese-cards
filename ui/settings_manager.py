#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
设置管理器，负责设置的保存、加载和应用
"""

import json
import os
from datetime import datetime
import tkinter as tk
from tkinter import font, ttk
from tkinter import messagebox


class SettingsManager:
    """设置管理器类"""
    
    def __init__(self, app):
        """
        初始化设置管理器
        
        Args:
            app: 应用程序实例
        """
        self.app = app
        
        # 获取用户数据目录（与CardManager保持一致）
        self.user_data_dir = self._get_user_data_dir()
        # 用户偏好文件路径
        self.preferences_file = os.path.join(self.user_data_dir, 'user_preferences.json')
        
        # 默认设置
        self.default_settings = {
            'data': {
                # 数据相关设置
            },
            'sort': {
                'column': None,
                'order': 'asc',
                'is_time_sort': True
            },
            'ui': {
                'theme': 'default',
                'window_position': None,
                'window_size': None
            },
            'last_used': {
                'export_format': 'txt',
                'last_export_time': None
            },
            'update': {
                'auto_check_update': True,
                'ignore_version': ''
            }
        }
        
        # 当前设置
        self.settings = self.default_settings.copy()
        
        # 加载设置
        self.load_preferences()
    
    def _get_user_data_dir(self):
        """
        获取用户数据目录（跨平台兼容）
        与CardManager保持一致的目录结构
        """
        if os.name == 'nt':  # Windows
            app_data = os.environ.get('APPDATA')
            if app_data:
                return os.path.join(app_data, 'ancient_chinese_cards')
        elif os.name == 'posix':  # macOS/Linux
            home = os.path.expanduser('~')
            if os.path.exists(os.path.join(home, '.config')):  # Linux
                return os.path.join(home, '.config', 'ancient_chinese_cards')
            else:  # macOS
                return os.path.join(home, 'Library', 'Application Support', 'ancient_chinese_cards')
        
        # 默认回退到当前目录的data文件夹
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(current_dir, 'data')
    
    def load_preferences(self):
        """从用户偏好文件加载设置"""
        try:
            if os.path.exists(self.preferences_file):
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    loaded_preferences = json.load(f)
                    # 合并加载的设置和默认设置
                    self._merge_settings(loaded_preferences)
                print(f"已从 {self.preferences_file} 加载用户偏好")
            else:
                print(f"用户偏好文件不存在，使用默认设置: {self.preferences_file}")
        except json.JSONDecodeError as e:
            print(f"用户偏好文件格式错误: {str(e)}")
            # 使用默认设置
            self.settings = self.default_settings.copy()
        except Exception as e:
            print(f"加载用户偏好失败: {str(e)}")
            # 使用默认设置
            self.settings = self.default_settings.copy()
    
    def save_preferences(self):
        """保存用户偏好到文件"""
        try:
            # 确保用户数据目录存在
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            print(f"已保存用户偏好到: {self.preferences_file}")
            return True
        except Exception as e:
            print(f"保存用户偏好失败: {str(e)}")
            return False
    
    def _merge_settings(self, loaded_settings):
        """合并加载的设置和默认设置"""
        # 合并排序设置
        if 'sort' in loaded_settings:
            self.settings['sort'].update(loaded_settings['sort'])
        
        # 合并更新设置
        if 'update' in loaded_settings:
            self.settings['update'].update(loaded_settings['update'])
        
        # 合并UI设置
        if 'ui' in loaded_settings:
            self.settings['ui'].update(loaded_settings['ui'])
        
        # 合并最后使用设置
        if 'last_used' in loaded_settings:
            self.settings['last_used'].update(loaded_settings['last_used'])
    
    def apply_settings(self):
        """应用设置到应用程序"""
        # 应用字体设置
        self._apply_font_settings()
        
        # 应用数据设置
        self._apply_data_settings()
    
    def _apply_font_settings(self):
        """应用字体设置"""
        font_family = self.settings['font']['family']
        font_size = self.settings['font']['size']
        
        try:
            # 设置全局字体
            default_font = font.Font(family=font_family, size=font_size)
            self.app.root.option_add("*Font", default_font)
            
            # 更新UI字体
            if hasattr(self.app, 'main_window'):
                # 更新按钮字体
                for button in self.app.main_window.nav_buttons.values():
                    try:
                        button.config(font=(font_family, font_size))
                    except:
                        pass
                
                # 更新状态栏字体
                if hasattr(self.app.main_window, 'status_bar'):
                    try:
                        self.app.main_window.status_bar.config(font=(font_family, font_size))
                    except:
                        pass
                
                # 更新列表视图字体
                if hasattr(self.app.main_window, 'card_tree'):
                    try:
                        # 直接设置字体，避免使用font对象
                        # 更新列表列标题字体
                        for col in self.app.main_window.card_tree["columns"]:
                            self.app.main_window.card_tree.heading(col, font=(font_family, font_size))
                        
                        # 更新列表内容字体
                        self.app.main_window.card_tree.config(font=(font_family, font_size))
                        
                        # 确保文本颜色为黑色
                        self.app.main_window.card_tree.config(foreground="#000000")
                        
                        # 刷新列表视图以应用新字体
                        if hasattr(self.app.main_window, 'refresh_list_view'):
                            self.app.main_window.refresh_list_view()
                    except Exception as e:
                        print(f"更新列表字体失败: {str(e)}")
                        
                # 更新其他标签字体
                for widget in self.app.main_window.main_frame.winfo_children():
                    try:
                        if isinstance(widget, ttk.Label) or isinstance(widget, tk.Label):
                            widget.config(font=(font_family, font_size))
                    except:
                        pass
        except Exception as e:
            print(f"应用字体设置失败: {str(e)}")
    
    def _update_widget_font(self, widget, font_family, font_size):
        """递归更新所有子部件的字体"""
        try:
            widget.config(font=(font_family, font_size))
        except:
            pass
        
        for child in widget.winfo_children():
            self._update_widget_font(child, font_family, font_size)
    
    def _apply_data_settings(self):
        """应用数据设置"""
        # 自动保存功能已移除
        pass
    
    def get_setting(self, section, key):
        """获取设置值"""
        if section in self.settings and key in self.settings[section]:
            return self.settings[section][key]
        return None
    
    def set_setting(self, section, key, value):
        """设置设置值"""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
    
    def reset_settings(self):
        """重置设置为默认值"""
        self.settings = self.default_settings.copy()
        self.save_preferences()
        self.apply_settings()
    
    def save_sort_settings(self, column, order, is_time_sort):
        """保存排序设置
        
        Args:
            column: 排序列名
            order: 排序顺序 ('asc' 或 'desc')
            is_time_sort: 是否按时间排序
        """
        self.settings['sort']['column'] = column
        self.settings['sort']['order'] = order
        self.settings['sort']['is_time_sort'] = is_time_sort
        return self.save_preferences()
    
    def get_sort_settings(self):
        """获取排序设置
        
        Returns:
            tuple: (column, order, is_time_sort)
        """
        return (
            self.settings['sort']['column'],
            self.settings['sort']['order'],
            self.settings['sort']['is_time_sort']
        )
    
    def get_setting(self, category, key, default=None):
        """获取设置值
        
        Args:
            category: 设置分类
            key: 设置键名
            default: 默认值
        
        Returns:
            设置值或默认值
        """
        if category in self.settings and key in self.settings[category]:
            return self.settings[category][key]
        return default
    
    def set_setting(self, category, key, value):
        """设置设置值
        
        Args:
            category: 设置分类
            key: 设置键名
            value: 设置值
        """
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
    
    def save_export_format(self, export_format):
        """保存上次使用的导出格式
        
        Args:
            export_format: 导出格式 ('txt', 'json', 'ancc')
        """
        self.settings['last_used']['export_format'] = export_format
        self.settings['last_used']['last_export_time'] = datetime.now().isoformat()
        return self.save_preferences()
    
    def get_last_export_format(self):
        """获取上次使用的导出格式
        
        Returns:
            str: 上次使用的导出格式
        """
        return self.settings['last_used']['export_format']
    
    def save_window_position(self, x, y):
        """保存窗口位置
        
        Args:
            x: 窗口X坐标
            y: 窗口Y坐标
        """
        self.settings['ui']['window_position'] = (x, y)
        return self.save_preferences()
    
    def get_window_position(self):
        """获取窗口位置
        
        Returns:
            tuple: (x, y) 或 None
        """
        return self.settings['ui']['window_position']
    
    def save_window_size(self, width, height):
        """保存窗口大小
        
        Args:
            width: 窗口宽度
            height: 窗口高度
        """
        self.settings['ui']['window_size'] = (width, height)
        return self.save_preferences()
    
    def get_window_size(self):
        """获取窗口大小
        
        Returns:
            tuple: (width, height) 或 None
        """
        return self.settings['ui']['window_size']
    
    def save_theme(self, theme):
        """保存主题设置
        
        Args:
            theme: 主题名称
        """
        self.settings['ui']['theme'] = theme
        return self.save_preferences()
    
    def get_theme(self):
        """获取主题设置
        
        Returns:
            str: 主题名称
        """
        return self.settings['ui']['theme']
    
    def get_preferences_file_path(self):
        """获取用户偏好文件路径
        
        Returns:
            str: 文件路径
        """
        return self.preferences_file
    
    def show_settings_window(self):
        """显示设置窗口（新增基本设置标签页）"""
        settings_window = tk.Toplevel(self.app.root)
        settings_window.title("设置")
        settings_window.geometry("800x600")
        settings_window.resizable(True, True)
        settings_window.transient(self.app.root)
        settings_window.grab_set()
        
        # 居中显示
        settings_window.update_idletasks()
        width = settings_window.winfo_width()
        height = settings_window.winfo_height()
        x = (self.app.root.winfo_width() // 2) - (width // 2) + self.app.root.winfo_x()
        y = (self.app.root.winfo_height() // 2) - (height // 2) + self.app.root.winfo_y()
        settings_window.geometry(f"+{x}+{y}")
        
        # 设置图标
        if hasattr(self.app, 'icon_path') and os.path.exists(self.app.icon_path):
            settings_window.iconbitmap(self.app.icon_path)
        
        # 创建标签页控制器
        tab_control = ttk.Notebook(settings_window)
        
        # 1. 数据管理标签页
        data_tab = ttk.Frame(tab_control)
        tab_control.add(data_tab, text="数据管理")
        data_page = self._create_data_page(data_tab)
        data_page.pack(fill=tk.BOTH, expand=True)
        
        # 2. 基本设置标签页（新增）
        basic_tab = ttk.Frame(tab_control)
        tab_control.add(basic_tab, text="基本设置")
        self._create_basic_settings_page(basic_tab)  # 新增方法
        
        tab_control.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 底部按钮
        bottom_frame = ttk.Frame(settings_window, padding="10")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        close_button = ttk.Button(bottom_frame, text="关闭", command=settings_window.destroy)
        close_button.pack(side=tk.RIGHT, padx=5)
    
    def _update_nav_buttons_style(self, nav_buttons, current_page):
        """更新导航按钮样式"""
        for page_id, button in nav_buttons.items():
            if page_id == current_page:
                button.state(["selected"])
            else:
                button.state(["!selected"])
    
    def _switch_settings_page(self, current_page_var, page_id, content_frame):
        """切换设置页面"""
        current_page_var.set(page_id)
    
    def _create_basic_settings_page(self, parent):
        """创建基本设置页面（新增方法）"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 页面标题
        title_label = ttk.Label(frame, text="基本设置", font=("SimHei", 14, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 20))
        
        # 更新设置区域
        update_frame = ttk.LabelFrame(frame, text="更新设置", padding="15")
        update_frame.pack(fill=tk.X, pady=10)
        
        # 自动检测更新勾选框
        auto_check_var = tk.BooleanVar(value=self.get_setting("update", "auto_check_update"))
        auto_check_var.trace_add("write", lambda *args: self._save_update_setting("auto_check_update", auto_check_var.get()))
        ttk.Checkbutton(
            update_frame,
            text="启动时自动检测更新",
            variable=auto_check_var
        ).pack(anchor=tk.W, pady=5)
        
        # 手动检查更新按钮
        ttk.Button(
            update_frame,
            text="手动检查更新",
            command=self.app.update_checker.check_update_manually,  # 绑定手动更新方法
            style="Accent.TButton"
        ).pack(anchor=tk.W, pady=10)
        
        # 补充：初始化默认设置（如果不存在）
        if "update" not in self.settings:
            self.settings["update"] = {
                "auto_check_update": True,
                "ignore_version": ""
            }
            self.save_preferences()
    
    def _save_update_setting(self, key, value):
        """保存更新相关设置并立即写入文件
        
        Args:
            key: 设置键名
            value: 设置值
        """
        self.set_setting("update", key, value)
        self.save_preferences()
        print(f"已保存更新设置: {key} = {value}")
    

    

    
    def _create_data_page(self, parent):
        """创建数据管理页面"""
        frame = ttk.Frame(parent, padding="10")
        
        # 页面标题
        title_label = ttk.Label(frame, text="数据管理", font=("SimHei", 14, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        # ANCC格式导入导出
        ancc_frame = ttk.LabelFrame(frame, text="ANCC格式导入导出")
        ancc_frame.pack(fill=tk.X, pady=10)
        
        # 导出ANCC按钮
        export_ancc_btn = ttk.Button(
            ancc_frame,
            text="导出ANCC格式(*.ancc)",
            command=self._export_ancc,
            width=30
        )
        export_ancc_btn.pack(pady=10)
        
        # 导入ANCC按钮
        import_ancc_btn = ttk.Button(
            ancc_frame,
            text="导入ANCC格式(*.ancc)",
            command=self._import_ancc,
            width=30
        )
        import_ancc_btn.pack(pady=10)
        
        # ANCC格式说明
        ancc_info_frame = ttk.Frame(ancc_frame)
        ancc_info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            ancc_info_frame,
            text="ANCC格式为软件专属加密格式，支持完整的卡片数据备份和恢复。",
            font=("SimHei", 10),
            foreground="#000000",
            justify=tk.LEFT,
            wraplength=400
        ).pack(anchor=tk.W)
        
        ttk.Label(
            ancc_info_frame,
            text="注：ANCC格式仅本软件可解析，支持标点符号和空格。",
            font=("SimHei", 9),
            foreground="#000000",
            justify=tk.LEFT,
            wraplength=400
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # 状态提示
        status_var = tk.StringVar(value="数据管理功能已就绪")
        status_label = ttk.Label(frame, textvariable=status_var, foreground="#000000")
        status_label.pack(anchor=tk.W, padx=10, pady=10)
        
        return frame
    

    

    

    

    
    def _export_ancc(self):
        """导出ANCC格式文件"""
        try:
            from tkinter import filedialog
            
            # 调用主窗口的导出ANCC方法
            if hasattr(self.app.main_window, 'export_ancc'):
                self.app.main_window.export_ancc()
            else:
                messagebox.showerror("错误", "导出功能不可用")
        except Exception as e:
            messagebox.showerror("错误", f"导出ANCC文件失败: {str(e)}")
    
    def _import_ancc(self):
        """导入ANCC格式文件"""
        try:
            from tkinter import filedialog
            
            # 调用主窗口的导入ANCC方法
            if hasattr(self.app.main_window, 'import_ancc'):
                self.app.main_window.import_ancc()
            else:
                messagebox.showerror("错误", "导入功能不可用")
        except Exception as e:
            messagebox.showerror("错误", f"导入ANCC文件失败: {str(e)}")
    
