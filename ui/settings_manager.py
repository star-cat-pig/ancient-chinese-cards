#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置管理器，负责设置的保存、加载和应用（合并完整功能）
"""
import json
import os
import copy
from datetime import datetime
import tkinter as tk
from tkinter import font, ttk
from tkinter import messagebox

class SettingsManager:
    """设置管理器类（完整功能版）"""
    def __init__(self, app):
        self.app = app
        self.user_data_dir = self._get_user_data_dir()
        self.preferences_file = os.path.join(self.user_data_dir, 'user_preferences.json')
        
        # 默认设置（保留所有分类）
        self.default_settings = {
            'editor': {'auto_fill_source': False, 'last_source': ''},
            'data': {},
            'sort': {'column': None, 'order': 'asc', 'is_time_sort': True},
            'ui': {'theme': 'default', 'window_position': None, 'window_size': None},
            'last_used': {'export_format': 'txt', 'last_export_time': None},
            'update': {'auto_check_update': True, 'ignore_version': ''},
            'font': {'family': 'Microsoft YaHei', 'size': 12},
            'clip': {'hotkey_enabled': True}
        }
        self.settings = copy.deepcopy(self.default_settings)
        self.load_preferences()

    def _get_user_data_dir(self):
        """跨平台获取用户数据目录"""
        if os.name == 'nt':  # Windows
            app_data = os.environ.get('APPDATA')
            return os.path.join(app_data, 'ancient_chinese_cards') if app_data else self._get_fallback_dir()
        elif os.name == 'posix':  # macOS/Linux
            home = os.path.expanduser('~')
            if os.path.exists(os.path.join(home, '.config')):  # Linux
                return os.path.join(home, '.config', 'ancient_chinese_cards')
            else:  # macOS
                return os.path.join(home, 'Library', 'Application Support', 'ancient_chinese_cards')
        return self._get_fallback_dir()

    def _get_fallback_dir(self):
        """默认回退目录"""
        from config import get_main_exe_dir
        return os.path.join(get_main_exe_dir(), 'data')

    def load_preferences(self):
        """加载用户偏好"""
        try:
            if os.path.exists(self.preferences_file):
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self._merge_settings(loaded)
                print(f"已加载偏好：{self.preferences_file}")
            else:
                print("偏好文件不存在，使用默认设置")
        except Exception as e:
            print(f"加载偏好失败：{str(e)}")
            self.settings = self.default_settings.copy()

    def save_preferences(self):
        """保存用户偏好"""
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            print(f"已保存偏好：{self.preferences_file}")
            return True
        except Exception as e:
            print(f"保存偏好失败：{str(e)}")
            return False

    def _merge_settings(self, loaded_settings):
        """合并加载的设置与默认设置"""
        for category in self.default_settings.keys():
            if category in loaded_settings:
                self.settings[category].update(loaded_settings[category])

    def apply_settings(self):
        """应用所有设置"""
        self._apply_font_settings()
        self._apply_data_settings()

    def get_font(self, size=None, bold=False):
        """获取字体配置（主窗口调用）"""
        family = self.get_setting('font', 'family', 'Microsoft YaHei')
        base_size = self.get_setting('font', 'size', 12)
        return (family, size or base_size, "bold" if bold else "normal")

    def _apply_font_settings(self):
        """应用字体设置 - 极简稳定版（不再用 heading(font=...)）"""
        try:
            font_family = self.settings['font']['family']
            font_size = self.settings['font']['size']

            style = ttk.Style()

            # 核心样式配置
            style.configure(".", font=(font_family, font_size))
            style.configure("TButton", font=(font_family, font_size))
            style.configure("TLabel", font=(font_family, font_size))
            style.configure("TEntry", font=(font_family, font_size))
            style.configure("TCombobox", font=(font_family, font_size))

            # Treeview 配置（最容易出错的地方，已修复）
            style.configure("Treeview", 
                          font=(font_family, font_size), 
                          rowheight=max(34, font_size + 16))

            style.configure("Treeview.Heading", 
                          font=(font_family, font_size, "bold"))

            # 刷新主界面列表
            if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'refresh_list_view'):
                self.app.main_window.refresh_list_view()

            print(f"字体设置已应用：{font_family} {font_size}pt")
            
        except Exception as e:
            print(f"应用字体失败：{str(e)}")

    def _apply_data_settings(self):
        """应用数据设置（自动保存功能已移除）"""
        pass

    def get_setting(self, category, key, default=None):
        """获取设置值（统一方法）"""
        return self.settings.get(category, {}).get(key, default)

    def set_setting(self, category, key, value, auto_save=False):
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
        
        if auto_save:
            self.save_preferences()

    def reset_settings(self):
        """重置为默认设置"""
        self.settings = self.default_settings.copy()
        self.save_preferences()
        self.apply_settings()

    # ---------------------- 排序相关方法 ----------------------
    def save_sort_settings(self, column, order, is_time_sort):
        self.settings['sort']['column'] = column
        self.settings['sort']['order'] = order
        self.settings['sort']['is_time_sort'] = is_time_sort
        return self.save_preferences()

    def get_sort_settings(self):
        return (
            self.settings['sort']['column'],
            self.settings['sort']['order'],
            self.settings['sort']['is_time_sort']
        )

    # ---------------------- 导出相关方法 ----------------------
    def save_export_format(self, export_format):
        self.settings['last_used']['export_format'] = export_format
        self.settings['last_used']['last_export_time'] = datetime.now().isoformat()
        return self.save_preferences()

    def get_last_export_format(self):
        return self.settings['last_used']['export_format']

    # ---------------------- 窗口相关方法 ----------------------
    def save_window_position(self, x, y):
        self.settings['ui']['window_position'] = (x, y)
        return self.save_preferences()

    def get_window_position(self):
        return self.settings['ui']['window_position']

    def save_window_size(self, width, height):
        self.settings['ui']['window_size'] = (width, height)
        return self.save_preferences()

    def get_window_size(self):
        return self.settings['ui']['window_size']

    # ---------------------- 主题相关方法 ----------------------
    def save_theme(self, theme):
        self.settings['ui']['theme'] = theme
        return self.save_preferences()

    def get_theme(self):
        return self.settings['ui']['theme']

    def _get_colors(self):
        """获取当前主题配色（供设置窗口的文字颜色使用）"""
        try:
            return self.app.main_window.colors
        except Exception:
            return {'text': '#000000', 'sub_text': '#8A7A5F', 'bg': '#F5F2E9'}

    def _make_scrollable(self, parent):
        """创建可滚动容器（Canvas + 滚动条 + 鼠标滚轮），返回内容 frame 供填充"""
        colors = self._get_colors()
        canvas = tk.Canvas(parent, highlightthickness=0, bd=0,
                           bg=colors.get('bg', '#F5F2E9'))
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=inner, anchor='nw')

        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))
        inner.bind('<Configure>', _on_inner_configure)

        def _sync_width(event):
            canvas.itemconfigure(window_id, width=event.width)
        canvas.bind('<Configure>', _sync_width)

        # 鼠标滚轮滚动（绑到全局，窗口销毁时解绑，避免残留影响主窗口）
        def _on_mousewheel(event):
            if not canvas.winfo_exists():
                return
            try:
                num = getattr(event, 'num', None)
                if num == 4:
                    canvas.yview_scroll(-1, 'units')
                elif num == 5:
                    canvas.yview_scroll(1, 'units')
                else:
                    canvas.yview_scroll(-1 * (event.delta // 120), 'units')
            except Exception:
                pass

        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        canvas.bind_all('<Button-4>', _on_mousewheel)
        canvas.bind_all('<Button-5>', _on_mousewheel)

        def _cleanup(event):
            try:
                canvas.unbind_all('<MouseWheel>')
                canvas.unbind_all('<Button-4>')
                canvas.unbind_all('<Button-5>')
            except Exception:
                pass
        canvas.bind('<Destroy>', _cleanup)

        return inner

    # ---------------------- 设置窗口 ----------------------
    def show_settings_window(self):
        """显示设置窗口（含基本设置、外观布局、数据管理）"""
        settings_window = tk.Toplevel(self.app.root)
        settings_window.title("设置")
        settings_window.geometry("800x600")
        settings_window.resizable(False, False)
        settings_window.transient(self.app.root)
        settings_window.grab_set()

        from config import get_main_exe_dir
        icon_path = os.path.join(get_main_exe_dir(), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                settings_window.iconbitmap(icon_path)
            except Exception as e:
                print(f"设置窗口图标加载失败：{str(e)}")

        # 居中显示
        settings_window.update_idletasks()
        x = (self.app.root.winfo_width()//2 - settings_window.winfo_width()//2) + self.app.root.winfo_x()
        y = (self.app.root.winfo_height()//2 - settings_window.winfo_height()//2) + self.app.root.winfo_y()
        settings_window.geometry(f"+{x}+{y}")

        # 标签页控制器
        tab_control = ttk.Notebook(settings_window)

        # 1. 基本设置标签页（内容可滚动）
        basic_tab = ttk.Frame(tab_control)
        tab_control.add(basic_tab, text="基本设置")
        self._create_basic_settings_page(self._make_scrollable(basic_tab))

        # 2. 外观布局标签页（内容可滚动）
        appearance_tab = ttk.Frame(tab_control)
        tab_control.add(appearance_tab, text="外观布局")
        self._create_appearance_layout_page(self._make_scrollable(appearance_tab))

        # 3. 数据管理标签页（内容可滚动）
        data_tab = ttk.Frame(tab_control)
        tab_control.add(data_tab, text="数据管理")
        self._create_data_page(self._make_scrollable(data_tab)).pack(fill=tk.BOTH, expand=True)

        # 底部按钮：先 pack 固定在底部，避免被内容挤掉
        bottom_frame = ttk.Frame(settings_window, padding="10")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # 内容区后 pack，填充剩余空间
        tab_control.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 0))

        # 取消按钮
        ttk.Button(bottom_frame, text="取消", command=settings_window.destroy).pack(side=tk.RIGHT, padx=5)

        # 确定按钮（保存设置）
        def on_confirm():
            try:
                # 保存基本设置
                self.set_setting("update", "auto_check_update", self._auto_check_var.get())
                self.set_setting("editor", "auto_fill_source", self._auto_fill_source_var.get())
                # 保存外观设置
                self.set_setting("font", "family", self._font_family_var.get())
                self.set_setting("font", "size", self._font_size_var.get())
                # 主题：保存 + 若变化则即时切换
                new_theme = self._theme_var.get()
                old_theme = self.get_theme() or 'default'
                self.set_setting("ui", "theme", new_theme)
                # 应用并保存
                self.apply_settings()
                self.save_preferences()
                if new_theme != old_theme:
                    try:
                        self.app.main_window.apply_theme(new_theme)
                    except Exception as e:
                        print(f"切换主题失败：{e}")
                settings_window.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存设置失败：{str(e)}")

        ttk.Button(bottom_frame, text="确定", command=on_confirm, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

    def _create_basic_settings_page(self, parent):
        """创建基本设置页面（更新+编辑设置）"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(frame, text="基本设置", font=("SimHei", 14, "bold")).pack(anchor=tk.W, pady=(0, 20))

        # 更新设置区域
        update_frame = ttk.LabelFrame(frame, text="更新设置", padding="15")
        update_frame.pack(fill=tk.X, pady=10)
        self._auto_check_var = tk.BooleanVar(value=self.get_setting("update", "auto_check_update"))
        ttk.Checkbutton(
            update_frame,
            text="启动时自动检测更新",
            variable=self._auto_check_var
        ).pack(anchor=tk.W, pady=5)
        ttk.Button(
            update_frame,
            text="手动检查更新",
            command=self.app.update_checker.check_update_manually,
            style="Accent.TButton"
        ).pack(anchor=tk.W, pady=10)

        # 编辑设置区域
        editor_frame = ttk.LabelFrame(frame, text="卡片编辑设置", padding="15")
        editor_frame.pack(fill=tk.X, pady=10)
        self._auto_fill_source_var = tk.BooleanVar(value=self.get_setting("editor", "auto_fill_source", False))
        ttk.Checkbutton(
            editor_frame,
            text="自动填充上一次添加卡片使用的\"出处\"说明",
            variable=self._auto_fill_source_var
        ).pack(anchor=tk.W, pady=5)

        # 划词收集设置区（2.1 新增；Windows 全局热键 Ctrl+Alt+C）
        clip_frame = ttk.LabelFrame(frame, text="划词收集（Windows）", padding="15")
        clip_frame.pack(fill=tk.X, pady=10)
        self._clip_hotkey_var = tk.BooleanVar(
            value=self.get_setting("clip", "hotkey_enabled", True))

        def _toggle_clip_hotkey():
            self.set_setting("clip", "hotkey_enabled",
                             bool(self._clip_hotkey_var.get()), auto_save=True)
            try:
                collector = self.app.main_window.clip_collector
                if self._clip_hotkey_var.get():
                    collector.start()
                else:
                    collector.stop()
            except Exception:
                pass

        ttk.Checkbutton(
            clip_frame,
            text="启用全局热键 Ctrl+Alt+C 划词收集",
            variable=self._clip_hotkey_var,
            command=_toggle_clip_hotkey
        ).pack(anchor=tk.W, pady=5)
        ttk.Label(
            clip_frame,
            text="任意窗口划选文字后按 Ctrl+Alt+C，即可收进「暂存箱」（需软件在运行；非 Windows 自动忽略）。",
            foreground=self._get_colors()['sub_text']
        ).pack(anchor=tk.W)

        # 初始化默认设置（兼容旧版本）
        if "update" not in self.settings:
            self.settings["update"] = {"auto_check_update": True, "ignore_version": ""}
            self.save_preferences()

    def _create_appearance_layout_page(self, parent):
        """创建外观布局页面（字体设置：纯中文常用+更多字体弹窗）"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        # 标题
        ttk.Label(frame, text="外观布局", font=("SimHei", 14, "bold")).pack(anchor=tk.W, pady=(0, 20))
        # 主题设置区域
        theme_frame = ttk.LabelFrame(frame, text="主题设置", padding="15")
        theme_frame.pack(fill=tk.X, pady=10)
        self._theme_var = tk.StringVar(value=self.get_theme() or 'default')
        ttk.Label(theme_frame, text="界面主题:").pack(anchor=tk.W, pady=(0, 5))
        ttk.Radiobutton(theme_frame, text="浅色（米黄）", variable=self._theme_var, value='default').pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(theme_frame, text="深色", variable=self._theme_var, value='dark').pack(anchor=tk.W, pady=2)
        # 字体设置区域
        font_frame = ttk.LabelFrame(frame, text="字体设置", padding="15")
        font_frame.pack(fill=tk.X, pady=10)
        
        # 纯中文字体映射：显示中文名 → 系统真实名（无任何英文）
        self.CHINESE_FONT_MAP = {
            "微软雅黑": "Microsoft YaHei",
            "微软雅黑 UI": "Microsoft YaHei UI",
            "黑体": "SimHei",
            "宋体": "SimSun",
            "楷体": "KaiTi",
            "仿宋": "FangSong",
            "幼圆": "YouYuan",
            "隶书": "LiSu",
            "华文细黑": "STXihei",
            "华文楷体": "STKaiti",
            "华文宋体": "STSong",
            "华文仿宋": "STFangsong",
            "华文琥珀": "STHupo",
            "华文隶书": "STLiti",
            "方正舒体": "FZShuTi",
            "方正姚体": "FZYaoti",
        }

        self.available_cn_fonts = list(self.CHINESE_FONT_MAP.keys())
        self.available_cn_fonts.append("────────")
        self.available_cn_fonts.append("更多字体")
        
        # 初始化字体变量：预设表能反查 → 显示中文名；反查不到（之前用"更多字体"选的）
        # → 把真实字体名加到下拉顶部并回显，不再退回"微软雅黑"（修复回显 bug）
        saved_family = self.get_setting("font", "family", "Microsoft YaHei") or "Microsoft YaHei"
        matched_cn = [k for k, v in self.CHINESE_FONT_MAP.items() if v == saved_family]
        if matched_cn:
            init_font = matched_cn[0]
        else:
            init_font = saved_family
            if saved_family not in self.available_cn_fonts:
                self.available_cn_fonts.insert(0, saved_family)
        self._font_family_var = tk.StringVar(value=init_font)
        self._font_size_var = tk.IntVar(value=self.get_setting("font", "size", 12))
        
        # 字体下拉框（纯中文+更多字体）
        ttk.Label(font_frame, text="界面字体:").pack(anchor=tk.W, pady=(0, 5))
        self.font_combo = ttk.Combobox(
            font_frame,
            textvariable=self._font_family_var,
            values=self.available_cn_fonts,
            state="readonly"
        )
        self.font_combo.pack(fill=tk.X, pady=(0, 10))
        # 绑定下拉框选择事件（判断是否点击更多字体）
        self.font_combo.bind("<<ComboboxSelected>>", self._on_font_select)
        
        # 字号设置
        ttk.Label(font_frame, text="字号:").pack(anchor=tk.W, pady=(0, 5))
        ttk.Spinbox(
            font_frame,
            from_=8,
            to=30,
            textvariable=self._font_size_var
        ).pack(fill=tk.X, pady=(0, 10))
        
        # 预览区域
        preview_frame = ttk.LabelFrame(frame, text="预览", padding="15")
        preview_frame.pack(fill=tk.X, pady=10)
        self._preview_label = ttk.Label(
            preview_frame,
            text="预览文本：学而时习之，不亦说乎？有朋自远方来，不亦乐乎？",
            font=self.get_font(size=self._font_size_var.get())
        )
        self._preview_label.pack(anchor=tk.W, pady=5)
        
        # 实时预览绑定（字号/字体变化都刷新）
        def update_preview(*args):
            self._preview_label.config(font=self.get_font(size=self._font_size_var.get()))
        self._font_size_var.trace_add("write", update_preview)
        self._font_family_var.trace_add("write", update_preview)
    
    def _on_font_select(self, event):
        selected = self._font_family_var.get()
        if selected == "更多字体":
            self._show_font_dialog()
            return

        if selected == "────────":
             return

        # 仅预设表中的"中文名→真实名"才保存；映射外的是已保存的真实字体名（更多字体选的），
        # 点它不应把字体改回微软雅黑
        if selected in self.CHINESE_FONT_MAP:
            self.set_setting("font", "family", self.CHINESE_FONT_MAP[selected])
            self.apply_settings()

    def _show_font_dialog(self):
        win = tk.Toplevel(self.app.root)
        win.title("选择系统字体")
        win.geometry("400x500")
    
        win.transient(self.app.root)
        win.grab_set()

        from config import get_main_exe_dir
        icon_path = os.path.join(get_main_exe_dir(), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                win.iconbitmap(icon_path)
            except:
                pass
    
        # 居中一点
        win.update_idletasks()
        x = self.app.root.winfo_x() + 150
        y = self.app.root.winfo_y() + 100
        win.geometry(f"+{x}+{y}")
    
        # 获取系统字体
        all_fonts = sorted(set(font.families()))
    
        listbox = tk.Listbox(win)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        for f in all_fonts:
            listbox.insert(tk.END, f)
    
        def on_select():
            selected_font = listbox.get(tk.ACTIVE)
    
            self.set_setting("font", "family", selected_font)
            # 把自定义字体加进下拉选项并回显（否则下次重开又退回微软雅黑）
            if selected_font not in self.available_cn_fonts:
                self.available_cn_fonts.insert(0, selected_font)
                self.font_combo.config(values=self.available_cn_fonts)
            self._font_family_var.set(selected_font)
    
            win.destroy()
    
        ttk.Button(win, text="确定", command=on_select).pack(pady=10)

    def _show_more_fonts_window(self):
        """弹出更多字体窗口：显示系统所有字体，支持选择+实时生效"""
        # 新建顶级窗口，模态化（锁定主设置窗口）
        more_fonts_win = tk.Toplevel(self.app.root)
        more_fonts_win.title("更多字体选择")
        more_fonts_win.geometry("500x400")
        more_fonts_win.resizable(True, True)
        more_fonts_win.transient(self.app.root)
        more_fonts_win.grab_set()
        # 窗口居中
        more_fonts_win.update_idletasks()
        x = (self.app.root.winfo_width()//2 - more_fonts_win.winfo_width()//2) + self.app.root.winfo_x()
        y = (self.app.root.winfo_height()//2 - more_fonts_win.winfo_height()//2) + self.app.root.winfo_y()
        more_fonts_win.geometry(f"+{x}+{y}")
        
        # 窗口布局
        main_frame = ttk.Frame(more_fonts_win, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        # 标题
        ttk.Label(main_frame, text="选择系统所有字体", font=("SimHei", 12, "bold")).pack(anchor=tk.W, pady=(0, 15))
        
        # 获取系统全部字体并排序
        all_sys_fonts = sorted(list(font.families()))
        # 字体选择下拉框（显示系统原名，支持搜索/滚动）
        font_var = tk.StringVar(value=self.settings['font']['family'])
        ttk.Label(main_frame, text="所有字体:").pack(anchor=tk.W, pady=(0, 5))
        font_combo = ttk.Combobox(
            main_frame,
            textvariable=font_var,
            values=all_sys_fonts,
            state="readonly",
            height=10
        )
        font_combo.pack(fill=tk.X, pady=(0, 10))
        
        # 预览区域（实时预览选中的字体）
        preview_frame = ttk.LabelFrame(main_frame, text="字体预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        preview_label = ttk.Label(
            preview_frame,
            text="预览：学而时习之 ",
            font=(font_var.get(), self._font_size_var.get())
        )
        preview_label.pack(anchor=tk.W, pady=5)
        
        # 实时预览绑定
        def update_more_preview(*args):
            preview_label.config(font=(font_var.get(), self._font_size_var.get()))
        font_var.trace_add("write", update_more_preview)
        self._font_size_var.trace_add("write", update_more_preview)
        
        # 底部按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        # 取消按钮
        ttk.Button(btn_frame, text="取消", command=more_fonts_win.destroy).pack(side=tk.RIGHT, padx=5)
        # 确认选择按钮（保存+应用+关闭窗口）
        def confirm_more_font():
            selected_font = font_var.get()
            # 更新设置并保存
            self.settings['font']['family'] = selected_font
            self.set_setting("font", "size", self._font_size_var.get())
            # 立即应用字体+保存偏好
            self.apply_settings()
            self.save_preferences()
            # 把自定义字体加进下拉选项并回显，刷新预览
            if selected_font not in self.available_cn_fonts:
                self.available_cn_fonts.insert(0, selected_font)
                self.font_combo.config(values=self.available_cn_fonts)
            self._font_family_var.set(selected_font)
            self._preview_label.config(font=self.get_font(size=self._font_size_var.get()))
            # 关闭更多字体窗口
            more_fonts_win.destroy()
        ttk.Button(btn_frame, text="确认选择", command=confirm_more_font, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

    def _create_data_page(self, parent):
        """创建数据管理页面（ANCC导入导出）"""
        frame = ttk.Frame(parent, padding="10")

        # 标题
        ttk.Label(frame, text="数据管理", font=("SimHei", 14, "bold")).pack(anchor=tk.W, pady=(0, 15))

        # ANCC导入导出区域
        ancc_frame = ttk.LabelFrame(frame, text="ANCC格式导入导出")
        ancc_frame.pack(fill=tk.X, pady=10)
        ttk.Button(
            ancc_frame,
            text="导出ANCC格式(*.ancc)",
            command=self._export_ancc,
            width=30
        ).pack(pady=10)
        ttk.Button(
            ancc_frame,
            text="导入ANCC格式(*.ancc)",
            command=self._import_ancc,
            width=30
        ).pack(pady=10)

        # 格式说明
        ancc_info_frame = ttk.Frame(ancc_frame)
        ancc_info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(
            ancc_info_frame,
            text="ANCC格式为软件专属加密格式，支持完整的卡片数据备份和恢复。",
            font=("SimHei", 10),
            foreground=self._get_colors()['text'],
            justify=tk.LEFT,
            wraplength=400
        ).pack(anchor=tk.W)
        ttk.Label(
            ancc_info_frame,
            text="注：ANCC格式仅本软件可解析，支持标点符号和空格。",
            font=("SimHei", 9),
            foreground=self._get_colors()['text'],
            justify=tk.LEFT,
            wraplength=400
        ).pack(anchor=tk.W, pady=(5, 0))

        # 状态提示
        ttk.Label(
            frame,
            text="数据管理功能已就绪",
            foreground=self._get_colors()['text']
        ).pack(anchor=tk.W, padx=10, pady=10)

        return frame

    def _export_ancc(self):
        """调用主窗口导出ANCC"""
        try:
            if hasattr(self.app.main_window, 'export_ancc'):
                self.app.main_window.export_ancc()
            else:
                messagebox.showerror("错误", "导出功能不可用")
        except Exception as e:
            messagebox.showerror("错误", f"导出ANCC失败：{str(e)}")

    def _import_ancc(self):
        """调用主窗口导入ANCC"""
        try:
            if hasattr(self.app.main_window, 'import_ancc'):
                self.app.main_window.import_ancc()
            else:
                messagebox.showerror("错误", "导入功能不可用")
        except Exception as e:
            messagebox.showerror("错误", f"导入ANCC失败：{str(e)}")