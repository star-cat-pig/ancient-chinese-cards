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
        """显示简化的设置窗口，只保留数据管理和字体设置"""
        # 创建设置窗口
        settings_window = tk.Toplevel(self.app.root)
        settings_window.title("设置")
        settings_window.geometry("800x600")
        settings_window.resizable(True, True)
        settings_window.transient(self.app.root)
        settings_window.grab_set()
        
        # 设置窗口图标
        if hasattr(self.app, 'icon_path') and os.path.exists(self.app.icon_path):
            settings_window.iconbitmap(self.app.icon_path)
        
        # 创建主框架
        main_frame = ttk.Frame(settings_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧导航面板
        nav_frame = ttk.Frame(main_frame, width=180)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 创建右侧内容面板
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 创建分隔线
        separator = ttk.Separator(main_frame, orient=tk.VERTICAL)
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 当前选中的页面
        current_page = tk.StringVar(value="font")
        
        # 创建导航按钮
        nav_buttons = {}
        nav_pages = [
            ("font", "字体设置", "🔤"),
            ("data", "数据管理", "💾")
        ]
        
        for page_id, page_name, icon in nav_pages:
            button = ttk.Button(
                nav_frame,
                text=f"{icon} {page_name}",
                width=18,
                style="Nav.TButton",
                command=lambda p=page_id: self._switch_settings_page(current_page, p, content_frame)
            )
            button.pack(fill=tk.X, pady=5)
            nav_buttons[page_id] = button
        
        # 创建样式 - 确保所有状态下文本都是黑色
        style = ttk.Style()
        style.configure("Nav.TButton", font=("SimHei", 10), foreground="#000000")
        style.map("Nav.TButton", 
                  background=[("selected", "#4a86e8"), ("active", "#d9e8ff")],
                  foreground=[("selected", "#000000"), ("active", "#000000"), ("!active", "#000000")])
        
        # 应用选中样式到当前页面按钮
        self._update_nav_buttons_style(nav_buttons, current_page.get())
        
        # 绑定页面切换事件
        current_page.trace_add("write", lambda *args: self._update_nav_buttons_style(nav_buttons, current_page.get()))
        
        # 创建页面内容
        pages = {
            "font": self._create_data_page,
            "data": self._create_data_page
        }
        
        # 显示初始页面
        page_frame = pages[current_page.get()](content_frame)
        page_frame.pack(fill=tk.BOTH, expand=True)
        
        # 保存页面引用
        current_page_frame = [page_frame]
        
        # 更新页面切换函数
        def switch_page(page_id):
            current_page.set(page_id)
            # 移除当前页面
            current_page_frame[0].pack_forget()
            current_page_frame[0].destroy()
            # 创建新页面
            new_page = pages[page_id](content_frame)
            new_page.pack(fill=tk.BOTH, expand=True)
            current_page_frame[0] = new_page
        
        # 更新导航按钮命令
        for page_id, button in nav_buttons.items():
            button.config(command=lambda p=page_id: switch_page(p))
        
        # 创建底部按钮
        bottom_frame = ttk.Frame(settings_window, padding="10")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 保存按钮
        save_button = ttk.Button(
            bottom_frame,
            text="保存设置",
            command=lambda: self._save_settings(settings_window)
        )
        save_button.pack(side=tk.RIGHT, padx=5)
        
        # 取消按钮
        cancel_button = ttk.Button(
            bottom_frame,
            text="取消",
            command=settings_window.destroy
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # 应用按钮
        apply_button = ttk.Button(
            bottom_frame,
            text="应用",
            command=self._apply_settings
        )
        apply_button.pack(side=tk.RIGHT, padx=5)
    
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
    
