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
import threading
from ui.card_view import CardView
from ui.card_editor import CardEditor
from ui.search_panel import SearchPanel
from ui.source_category_view import SourceCategoryView

# 图片加载兼容处理（支持jpg格式）
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("警告：未安装Pillow库，将降级为文字导航。安装命令：pip install pillow")

import tkinter.font as tkfont

def get_font_family():
    available = list(tkfont.families())
    for font in ["Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC"]:
        if font in available:
            return font
    return "Arial"


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

        if self.settings_manager:
            self.get_font = self.settings_manager.get_font
        else:
            # 如果没有设置管理器，使用默认字体
            self.get_font = lambda size=12, bold=False: (
                "Microsoft YaHei", 
                size, 
                "bold" if bold else "normal"
            )

        # 记录鼠标按键（用于区分左键和右键）
        self.last_mouse_button = 1  # 默认是左键
        self.selected_card_id = None  # 当前选中的卡片ID
        
        # 收藏功能相关状态
        self.is_favorites_view = False  # 当前是否在收藏视图模式
        
        # 当前过滤后的卡片列表（用于搜索/收藏视图排序）
        self.current_filtered_cards = None
        
        # 导航相关存储
        self.nav_items = {}  # 导航项控件字典
        self.nav_images = {}  # 图片强引用，防止被垃圾回收
        self.current_nav = None  # 当前选中的导航项
        
        # 导航展开/收缩相关状态（和上面代码同缩进层级）
        self.nav_expanded = False  # 导航栏是否展开（默认收缩，只显示图片）
        self.nav_width_collapsed = 100  # 收缩状态宽度（原有宽度）
        self.nav_width_expanded = 200   # 展开状态宽度（增加文字后的宽度）

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
    
        if self.settings_manager:
            self.settings_manager.apply_settings()

    def create_main_frame(self):
        """创建主框架"""
        self.main_frame = ttk.Frame(self.root, padding=(0, 0, 10, 10))
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TLabel", font=self.get_font(11))
        self.style.configure("TButton", font=self.get_font(10))
        self.style.configure("Treeview", font=self.get_font(11), rowheight=32)
        self.style.configure("Treeview.Heading", font=self.get_font(14, bold=True))
        
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
        
        # 收藏相关选项
        self.file_menu.add_command(label="收藏", command=self.toggle_favorites_view, state="normal", compound=tk.RIGHT)
        self.favorites_menu_index = 0
        self.file_menu.entryconfig(self.favorites_menu_index, label="收藏  \tAlt+D")
        
        self.file_menu.add_command(label="导出卡片", command=self.show_import_export_dialog)
        
        self.menu_bar.add_cascade(label="文件", menu=self.file_menu)
        
        # 编辑菜单
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.edit_menu.add_command(label="添加卡片", command=self.show_add_card)
        self.menu_bar.add_cascade(label="编辑", menu=self.edit_menu)
        
        # 帮助菜单
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="使用帮助  \tF1", command=self.show_help)
        self.help_menu.add_command(label="更新日志", command=self.show_update_log)
        self.help_menu.add_command(label="关于", command=self.show_about)
        self.menu_bar.add_cascade(label="帮助", menu=self.help_menu)
        
        self.root.config(menu=self.menu_bar)
    
    def create_navigation(self):
        """创建左侧可展开/收缩的图片+文字导航栏"""
        self.nav_frame = tk.Frame(
            self.main_frame, 
            width=60,
            bg=self.colors['bg'],
            bd=0,
            highlightthickness=0
        )
        self.nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        self.nav_frame.pack_propagate(False)
        self.nav_frame.config(padx=0, pady=0)

        # 资源目录解析（修复打包后图标丢失）：
        # 打包成 onedir 后 ui/main_window.py 位于 <根>/_internal/ui/ 下，
        # 若用 __file__ 往上两级会指到 _internal/ 而找不到 exe 旁边的 file/。
        # 改为：开发时用源码根；打包(frozen)后用 exe 所在目录；再做多重候选兜底。
        dev_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 开发 = 源码根
        try:
            from config import get_main_exe_dir
            exe_root = get_main_exe_dir()   # frozen: exe 所在目录；开发: 源码根
        except Exception:
            exe_root = dev_root
        icon_candidates = [
            os.path.join(exe_root, "file", "navigation", "icons"),      # 正确布局：onedir 根 / 安装根 {app}\file
            os.path.join(exe_root, "assets", "navigation", "icons"),    # 兼容 2.0 iss 曾把 file 装进 {app}\assets 的历史安装
            os.path.join(dev_root, "file", "navigation", "icons"),      # 直接跑源码的兜底
        ]
        self.icons_dir = next((p for p in icon_candidates if os.path.isdir(p)), icon_candidates[0])

        nav_configs = [
            {
                "icon_file": "cards.png",
                "text": "卡片列表",
                "click_func": self.show_overview,
                "view_name": "overview"
            },
            {
                "icon_file": "new.png",
                "text": "新建卡片",
                "click_func": self.show_add_card,
                "view_name": "add_card"
            },
            {
                "icon_file": "search.png",
                "text": "搜索卡片",
                "click_func": self.show_search,
                "view_name": "search"
            },
            {
                "icon_file": "book.png",
                "text": "书籍名称",
                "click_func": self.show_source_category,
                "view_name": "source_category"
            },
        ]
    
        icon_size = (48, 48)
        for config in nav_configs:
            view_name = config["view_name"]
            icon_path = os.path.join(self.icons_dir, config["icon_file"])
            image_obj = None
    
            item_frame = tk.Frame(self.nav_frame, bg=self.colors['bg'])
            item_frame.pack(fill=tk.X, pady=0, ipady=5, anchor='n')
    
            img_label = tk.Label(
                item_frame,
                bg=self.colors['bg'],
                cursor="hand2",
                borderwidth=0,
                highlightthickness=0
            )
            img_label.pack(side=tk.LEFT, padx=(10, 5), pady=0, anchor='center')
    
            text_label = tk.Label(
                item_frame,
                text=config["text"],
                bg=self.colors['bg'],
                fg=self.colors['text'],
                font=self.get_font(11),
                cursor="hand2"
            )
            text_label.pack(side=tk.LEFT, padx=5, pady=0, anchor='center')
            text_label.pack_forget()
    
            if PIL_AVAILABLE and os.path.exists(icon_path):
                try:
                    img = Image.open(icon_path)
                    img.thumbnail(icon_size, Image.Resampling.LANCZOS)
                    image_obj = ImageTk.PhotoImage(img)
                    self.nav_images[view_name] = image_obj
                    img_label.config(image=image_obj)
                except Exception as e:
                    print(f"图标{config['icon_file']}加载失败：{str(e)}")
                    img_label.config(text="图标", fg=self.colors['text'], font=("SimHei", 8))
            else:
                img_label.config(text="图标", fg=self.colors['text'], font=("SimHei", 8))
    
            def on_nav_click(event, func=config["click_func"]):
                func()
            img_label.bind("<Button-1>", on_nav_click)
            text_label.bind("<Button-1>", on_nav_click)
            item_frame.bind("<Button-1>", on_nav_click)
    
            def on_frame_enter(event, frame=item_frame, img=img_label, txt=text_label):
                frame.config(bg=self.colors['hover'])
                img.config(bg=self.colors['hover'])
                txt.config(bg=self.colors['hover'])
    
            def on_frame_leave(event, frame=item_frame, img=img_label, txt=text_label, view=view_name):
                frame.config(bg=self.colors['bg'])
                img.config(bg=self.colors['bg'])
                txt.config(bg=self.colors['bg'])
    
            item_frame.bind("<Enter>", on_frame_enter)
            item_frame.bind("<Leave>", on_frame_leave)
    
            self.nav_items[view_name] = {
                "img": img_label,
                "text": text_label,
                "frame": item_frame
            }
    
        fill_frame = tk.Frame(self.nav_frame, bg=self.colors['bg'])
        fill_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
        bottom_frame = tk.Frame(self.nav_frame, bg=self.colors['bg'])
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=0, ipady=0)
    
        expand_frame = tk.Frame(bottom_frame, bg=self.colors['bg'])
        expand_frame.pack(side=tk.TOP, fill=tk.X, pady=0, ipady=5)
    
        self.expand_img_label = tk.Label(
            expand_frame,
            bg=self.colors['bg'],
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0
        )
        self.expand_img_label.pack(side=tk.LEFT, padx=(10, 0), pady=0, anchor='center')
    
        expand_icon_path = os.path.join(self.icons_dir, "expand.png")
        if PIL_AVAILABLE and os.path.exists(expand_icon_path):
            try:
                img = Image.open(expand_icon_path)
                img.thumbnail((48, 48), Image.Resampling.LANCZOS)
                self.expand_image = ImageTk.PhotoImage(img)
                self.nav_images["expand"] = self.expand_image
                self.expand_img_label.config(image=self.expand_image)
            except Exception as e:
                print(f"展开图标加载失败：{str(e)}")
                self.expand_img_label.config(text="展开", fg=self.colors['text'], font=("SimHei", 8))
        else:
            self.expand_img_label.config(text="展开", fg=self.colors['text'], font=("SimHei", 8))
    
        self.expand_img_label.bind("<Button-1>", self.on_expand_click)
    
        setting_frame = tk.Frame(bottom_frame, bg=self.colors['bg'])
        setting_frame.pack(side=tk.TOP, fill=tk.X, pady=0, ipady=5)
        setting_content = tk.Frame(setting_frame, bg=self.colors['bg'])
        setting_content.pack(side=tk.LEFT, fill=tk.Y)

        self.setting_img_label = tk.Label(
            setting_content,
            bg=self.colors['bg'],
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0,
            width=48,
            height=48,
            anchor='center'
        )
        self.setting_img_label.pack(side=tk.LEFT, padx=(10, 5), pady=0, anchor='center')

        self.setting_text_label = tk.Label(
            setting_content,
            text="设置",
            bg=self.colors['bg'],
            fg=self.colors['text'],
            font=self.get_font(11),
            cursor="hand2"
        )
        self.setting_text_label.pack(side=tk.LEFT, padx=5, pady=0, anchor='center')
        self.setting_text_label.pack_forget()

        self.collapse_img_label = tk.Label(
            setting_frame,
            bg=self.colors['bg'],
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0,
            width=48,
            height=48,
            anchor='center'
        )
        self.collapse_img_label.pack(side=tk.RIGHT, padx=5, pady=0, anchor='center')
        self.collapse_img_label.pack_forget()

        setting_icon_path = os.path.join(self.icons_dir, "setting.png")
        if PIL_AVAILABLE and os.path.exists(setting_icon_path):
            try:
                img = Image.open(setting_icon_path)
                img.thumbnail((48, 48), Image.Resampling.LANCZOS)
                self.setting_image = ImageTk.PhotoImage(img)
                self.nav_images["setting"] = self.setting_image
                self.setting_img_label.config(image=self.setting_image)
            except Exception as e:
                print(f"设置图标加载失败：{str(e)}")
                self.setting_img_label.config(text="设", fg=self.colors['text'], font=("SimHei", 10))
        else:
            self.setting_img_label.config(text="设", fg=self.colors['text'], font=("SimHei", 10))

        collapse_icon_path = os.path.join(self.icons_dir, "collapse.png")
        if PIL_AVAILABLE and os.path.exists(collapse_icon_path):
            try:
                img = Image.open(collapse_icon_path)
                img.thumbnail((48, 48), Image.Resampling.LANCZOS)
                self.collapse_image = ImageTk.PhotoImage(img)
                self.nav_images["collapse"] = self.collapse_image
                self.collapse_img_label.config(image=self.collapse_image)
                self.collapse_img_label.update_idletasks()
                setting_frame.update_idletasks()
            except Exception as e:
                print(f"收缩图标加载失败：{str(e)}")
                self.collapse_img_label.config(text="←", fg=self.colors['text'], font=self.get_font(11))
        else:
            self.collapse_img_label.config(text="←", fg=self.colors['text'], font=self.get_font(11))

        def on_setting_click(event):
            self.show_settings()
        self.setting_img_label.bind("<Button-1>", on_setting_click)
        self.setting_text_label.bind("<Button-1>", on_setting_click)
        self.collapse_img_label.bind("<Button-1>", self.on_collapse_click)

        def on_setting_frame_enter(event):
            setting_content.config(bg=self.colors['hover'])
            self.setting_img_label.config(bg=self.colors['hover'])
            self.setting_text_label.config(bg=self.colors['hover'])

        def on_setting_frame_leave(event):
            setting_content.config(bg=self.colors['bg'])
            self.setting_img_label.config(bg=self.colors['bg'])
            self.setting_text_label.config(bg=self.colors['bg'])

        setting_content.bind("<Enter>", on_setting_frame_enter)
        setting_content.bind("<Leave>", on_setting_frame_leave)
    
    def highlight_nav_button(self, nav_name):
        """仅重置导航项背景色，取消选中高亮"""
        for name, items in self.nav_items.items():
            items["frame"].config(bg=self.colors['bg'])
            items["img"].config(bg=self.colors['bg'])
            items["text"].config(bg=self.colors['bg'])
    
    def create_content_area(self):
        """创建右侧内容区"""
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=0)
        
        self.content_area = ttk.Frame(self.content_frame)
        self.content_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.views = {}
        
        self.views['overview'] = ttk.Frame(self.content_area)
        self.views['add_card'] = ttk.Frame(self.content_area)
        self.views['edit_card'] = ttk.Frame(self.content_area)
        self.views['search'] = ttk.Frame(self.content_area)
        self.views['source_category'] = ttk.Frame(self.content_area)
        
        self.create_list_view()
        
        self.card_editor = CardEditor(self.views['add_card'], self.card_manager, self)
        self.search_panel = SearchPanel(self.views['search'], self.card_manager, self)
        self.source_category_view = SourceCategoryView(self.views['source_category'], self.card_manager, self)
    
    def show_view(self, view_name):
        """显示指定的视图"""
        for view in self.views.values():
            view.pack_forget()
        
        if view_name in self.views:
            self.views[view_name].pack(fill=tk.BOTH, expand=True)
        
        self.current_view = view_name
        self.highlight_nav_button(view_name)
    
    def show_overview(self, filtered_cards=None):
        """显示卡片概览视图"""
        self.show_view('overview')
        self.current_filtered_cards = filtered_cards
        if filtered_cards is not None:
            self.refresh_list_view(filtered_cards=filtered_cards)
        else:
            self.refresh_list_view()

    def show_source_category(self):
        """显示出处分类视图"""
        self.show_view('source_category')
        self.source_category_view.refresh()
    
    def show_add_card(self):
        """显示添加卡片视图"""
        self.show_view('add_card')
        self.card_editor.reset_form()
        self.card_editor.focus_first_field()
    
    def show_edit_card(self, card_id):
        """显示编辑卡片视图"""
        card = self.card_manager.get_card(card_id)
        if not card:
            messagebox.showerror("错误", "找不到指定的卡片")
            return
        
        original_card = card.copy()
        
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"编辑卡片 - {card['keyword']}")
        edit_window.geometry("600x500")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        if hasattr(self.app, '_set_window_icon'):
            self.app._set_window_icon(edit_window)
        
        edit_window.update_idletasks()
        width = edit_window.winfo_width()
        height = edit_window.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2)
        y = (self.root.winfo_height() // 2) - (height // 2)
        edit_window.geometry('+{}+{}'.format(x, y))
        
        card_frame = ttk.Frame(edit_window, padding=20, style="Card.TFrame")
        card_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        fields = []
        
        ttk.Label(card_frame, text="关键词:", font=("SimHei", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        keyword_var = tk.StringVar(value=card['keyword'])
        keyword_entry = ttk.Entry(card_frame, textvariable=keyword_var, width=40)
        keyword_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        fields.append(('keyword', keyword_var))
        
        ttk.Label(card_frame, text="释义:", font=("SimHei", 12, "bold")).grid(row=1, column=0, sticky=tk.NW, pady=5)
        definition_text = tk.Text(card_frame, height=4, width=40, wrap=tk.WORD)
        definition_text.insert(tk.END, card['definition'])
        definition_text.grid(row=1, column=1, sticky=tk.W, pady=5)
        fields.append(('definition', definition_text))
        
        ttk.Label(card_frame, text="出处:", font=("SimHei", 12, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        source_var = tk.StringVar(value=card['source'])
        source_entry = ttk.Entry(card_frame, textvariable=source_var, width=40)
        source_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        fields.append(('source', source_var))
        
        ttk.Label(card_frame, text="原文:", font=("SimHei", 12, "bold")).grid(row=3, column=0, sticky=tk.NW, pady=5)
        quote_text = tk.Text(card_frame, height=3, width=40, wrap=tk.WORD)
        quote_text.insert(tk.END, card['quote'])
        quote_text.grid(row=3, column=1, sticky=tk.W, pady=5)
        fields.append(('quote', quote_text))
        
        ttk.Label(card_frame, text="注释:", font=("SimHei", 12, "bold")).grid(row=4, column=0, sticky=tk.NW, pady=5)
        notes_text = tk.Text(card_frame, height=3, width=40, wrap=tk.WORD)
        notes_text.insert(tk.END, card.get('notes', ''))
        notes_text.grid(row=4, column=1, sticky=tk.W, pady=5)
        fields.append(('notes', notes_text))
        
        has_changes = [False]
        
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
        
        keyword_var.trace_add('write', check_changes)
        source_var.trace_add('write', check_changes)
        
        def on_text_change(event):
            check_changes()
        
        definition_text.bind('<<Modified>>', on_text_change)
        quote_text.bind('<<Modified>>', on_text_change)
        notes_text.bind('<<Modified>>', on_text_change)
        
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(pady=10)
        
        def save_changes():
            try:
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
                if not updated_card['keyword'] or not updated_card['definition']:
                    messagebox.showerror("错误", "关键词和释义为必填项")
                    return
                if self.card_manager.update_card(updated_card):
                    self.refresh_list_view(filtered_cards=self.current_filtered_cards)
                    edit_window.destroy()
                else:
                    messagebox.showerror("错误", "更新卡片失败")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
        
        save_button = ttk.Button(button_frame, text="保存", command=save_changes, style="Accent.TButton", state=tk.DISABLED)
        save_button.pack(side=tk.LEFT, padx=10)
        
        def confirm_changes():
            if has_changes[0]:
                result = messagebox.askyesnocancel("保存更改", "您对卡片进行了修改，是否保存这些更改？")
                if result is None:
                    return
                elif result:
                    save_changes()
                else:
                    edit_window.destroy()
            else:
                edit_window.destroy()
        
        confirm_button = ttk.Button(button_frame, text="确定", command=confirm_changes)
        confirm_button.pack(side=tk.RIGHT, padx=10)
    
    def show_search(self):
        """显示搜索视图"""
        self.show_view('search')
        self.search_panel.focus_search_entry()
    
    def show_import_export_dialog(self):
        """显示导出卡片对话框"""
        try:
            all_cards = self.card_manager.get_all_cards()
            if not all_cards:
                messagebox.showwarning("警告", "暂无卡片数据可导出")
                return
            
            format_window = tk.Toplevel(self.root)
            format_window.title("选择导出格式")
            format_window.geometry("400x300")
            format_window.transient(self.root)
            format_window.grab_set()
            
            if hasattr(self.app, '_set_window_icon'):
                self.app._set_window_icon(format_window)
            
            format_window.update_idletasks()
            width = format_window.winfo_width()
            height = format_window.winfo_height()
            x = (self.root.winfo_width() // 2) - (width // 2)
            y = (self.root.winfo_height() // 2) - (height // 2)
            format_window.geometry('+{}+{}'.format(x, y))
            
            main_frame = ttk.Frame(format_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(main_frame, text="请选择导出格式", font=("SimHei", 14, "bold")).pack(pady=(0, 15))
            
            format_var = tk.StringVar(value="txt")
            ttk.Radiobutton(main_frame, text="文本格式 (*.txt) - 简单易读", variable=format_var, value="txt").pack(anchor=tk.W, pady=5)
            ttk.Radiobutton(main_frame, text="JSON格式 (*.json) - 结构化数据", variable=format_var, value="json").pack(anchor=tk.W, pady=5)
            
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(pady=15)
            
            def on_export():
                selected_format = format_var.get()
                format_window.destroy()
                if selected_format == "txt":
                    self.export_txt_format()
                elif selected_format == "json":
                    self.export_json_format()
                if self.settings_manager:
                    self.settings_manager.save_export_format(selected_format)
            
            ttk.Button(button_frame, text="导出", command=on_export, width=10).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=format_window.destroy, width=10).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def show_help(self):
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
        about_text = """
古文卡片学习软件 v2.0
一款专为古文学习设计的卡片管理工具，
帮助用户制作、管理和搜索古文学习卡片。
邮箱：jumaozhixing@outlook.com
© 橘猫
        """
        messagebox.showinfo("关于", about_text)
    
    def show_settings(self):
        if self.settings_manager:
            self.settings_manager.show_settings_window()
        else:
            messagebox.showerror("错误", "设置管理器未初始化")

    def on_expand_click(self, event):
        if self.nav_expanded:
            return
        self.nav_expanded = True
        self.nav_frame.config(width=180)
        for view_name in self.nav_items:
            self.nav_items[view_name]["text"].pack(side=tk.LEFT, padx=5, pady=0, anchor='center')
        self.expand_img_label.pack_forget()
        self.setting_text_label.pack(side=tk.LEFT, padx=5, pady=5, anchor='center')
        self.collapse_img_label.pack(side=tk.LEFT, padx=5, pady=5, anchor='center')
        self.root.update_idletasks()

    def on_collapse_click(self, event):
        if not self.nav_expanded:
            return
        self.nav_expanded = False
        self.nav_frame.config(width=60)
        for view_name in self.nav_items:
            self.nav_items[view_name]["text"].pack_forget()
        self.expand_img_label.pack(side=tk.LEFT, padx=(10, 0), pady=5, anchor='center')
        self.setting_text_label.pack_forget()
        self.collapse_img_label.pack_forget()
        self.root.update_idletasks()
    
    def import_ancc(self):
        """导入ANCC格式文件"""
        file_path = filedialog.askopenfilename(
            title="导入ANCC格式文件",
            filetypes=[("ANCC文件", "*.ancc"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            cards = self.card_manager.decrypt_to_cards(encrypted_data)
            if not cards:
                messagebox.showinfo("提示", "ANCC文件中没有有效的卡片数据")
                return
            result = messagebox.askyesnocancel(
                "导入选项",
                f"发现 {len(cards)} 张卡片。\n\n是否将这些卡片添加到现有卡片中？\n\n选择'是'合并卡片，选择'否'替换所有现有卡片。",
                icon=messagebox.QUESTION
            )
            if result is None:
                return
            if result:
                original_count = len(self.card_manager.get_all_cards())
                self.card_manager.add_cards(cards)
                new_count = len(self.card_manager.get_all_cards())
                added_count = new_count - original_count
                messagebox.showinfo("成功", f"成功导入 {added_count} 张卡片。\n\n当前总卡片数: {new_count}")
            else:
                self.card_manager.clear_cards()
                self.card_manager.add_cards(cards)
                messagebox.showinfo("成功", f"成功导入 {len(cards)} 张卡片，已替换所有现有卡片。")
            self.refresh_list_view(filtered_cards=self.current_filtered_cards)
        except ValueError as e:
            messagebox.showerror("错误", f"文件格式无效: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"导入ANCC文件失败: {str(e)}")
    
    def save_cards(self) -> bool:
        """保存卡片数据，返回是否成功"""
        try:
            return self.card_manager.save_cards()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            return False
    
    def bind_events(self):
        self.root.bind("<Control-s>", lambda event: self.save_cards())
        self.root.bind("<Control-S>", lambda event: self.save_cards())
        self.root.bind("<F1>", lambda event: self.show_help())
        self.root.bind("<Control-d>", lambda event: self.toggle_selected_favorites())
        self.root.bind("<Control-D>", lambda event: self.toggle_selected_favorites())
        self.root.bind("<Alt-d>", lambda event: self.toggle_favorites_view())
        self.root.bind("<Alt-D>", lambda event: self.toggle_favorites_view())
        self.root.bind("<Control-a>", lambda event: self.select_all_cards())
        self.root.bind("<Control-A>", lambda event: self.select_all_cards())
        self.root.bind("<Control-n>", lambda event: self.show_add_card())
        self.root.bind("<Control-N>", lambda event: self.show_add_card())
        self.root.bind("<Control-o>", lambda event: self.edit_selected_card())
        self.root.bind("<Control-O>", lambda event: self.edit_selected_card())
        self.root.bind("<Delete>", lambda event: self.delete_selected_card())
        self.root.bind('<Configure>', self.on_window_configure)
    
    def create_list_view(self):
        list_frame = ttk.Frame(self.views['overview'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.search_var = tk.StringVar()
        
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        columns = ("keyword", "definition", "source", "quote")
        self.card_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        
        self.card_tree.heading("keyword", text="关键词", command=lambda: self.on_header_click("keyword"))
        self.card_tree.heading("definition", text="释义", command=lambda: self.on_header_click("definition"))
        self.card_tree.heading("source", text="出处", command=lambda: self.on_header_click("source"))
        self.card_tree.heading("quote", text="原文", command=lambda: self.on_header_click("quote"))
        
        self.card_tree.column("keyword", width=150)
        self.card_tree.column("definition", width=250)
        self.card_tree.column("source", width=150)
        self.card_tree.column("quote", width=300)
        
        style = ttk.Style()
        style.configure("Treeview", rowheight=30)

        if hasattr(self, 'settings_manager') and self.settings_manager:
            font_family = self.settings_manager.get_setting('font', 'family', 'Microsoft YaHei')
            font_size = self.settings_manager.get_setting('font', 'size', 12)
            style.configure("Treeview", font=(font_family, font_size), rowheight=max(30, font_size + 12))
            style.configure("Treeview.Heading", font=(font_family, font_size, "bold"))
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.card_tree.yview)
        self.card_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.card_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.card_tree.bind("<Double-1>", self.on_item_double_click)
        self.card_tree.bind('<Button-1>', self.on_treeview_click)
        self.card_tree.bind('<Control-Button-1>', self.on_treeview_ctrl_click)
        self.card_tree.bind('<Shift-Button-1>', self.on_treeview_shift_click)
        self.card_tree.bind('<<TreeviewSelect>>', self.on_treeview_select)
        self.card_tree.bind("<Button-3>", self.show_context_menu)
        
        self.context_menu = tk.Menu(self.root, tearoff=0)
        
        self.drag_start_item = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_selecting = False
        
        self.card_tree.bind('<B1-Motion>', self.on_treeview_drag)
        self.card_tree.bind('<ButtonRelease-1>', self.on_treeview_release)
        
        self.sort_column = "keyword"
        self.sort_order = "asc"
        self.sort_indicators = {}
        
        self._load_sort_settings()
    
    def _load_sort_settings(self):
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
        if column == self.sort_column:
            self.sort_order = "desc" if self.sort_order == "asc" else "asc"
        else:
            self.sort_column = column
            self.sort_order = "asc"
        
        if hasattr(self, 'settings_manager') and self.settings_manager:
            try:
                is_time_sort = self.sort_column in ['created_at', 'updated_at']
                self.settings_manager.save_sort_settings(self.sort_column, self.sort_order, is_time_sort)
            except Exception as e:
                print(f"保存排序设置失败: {str(e)}")
        
        self.refresh_list_view(filtered_cards=self.current_filtered_cards)
    
    def get_pinyin(self, text):
        try:
            from pypinyin import lazy_pinyin
            return ''.join(lazy_pinyin(text))
        except ImportError:
            if not hasattr(self, '_pypinyin_warning_shown'):
                self._pypinyin_warning_shown = True
                messagebox.showinfo(
                    "排序优化建议",
                    "建议安装 pypinyin 库以获得更精准的中文拼音排序。\n请在命令行中运行: pip install pypinyin"
                )
            return text
    
    def refresh_list_view(self, filtered_cards=None):
        for item in self.card_tree.get_children():
            self.card_tree.delete(item)

        if filtered_cards is not None:
            cards = filtered_cards
        elif self.is_favorites_view:
            cards = self.card_manager.get_favorite_cards()
        else:
            cards = self.card_manager.get_all_cards()
        
        reverse = self.sort_order == "desc"
        if self.sort_column == "keyword":
            cards.sort(key=lambda x: self.get_pinyin(x.get("keyword", "")), reverse=reverse)
        elif self.sort_column in ["definition", "source", "quote"]:
            cards.sort(key=lambda x: self.get_pinyin(x.get(self.sort_column, "")), reverse=reverse)
        
        for card in cards:
            values = (
                card['keyword'],
                card['definition'][:50] + "..." if len(card['definition']) > 50 else card['definition'],
                card['source'],
                card['quote'][:50] + "..." if len(card['quote']) > 50 else card['quote']
            )
            self.card_tree.insert("", tk.END, values=values, tags=(card['id'],))
    
    def on_item_double_click(self, event):
        selected_items = self.card_tree.selection()
        if selected_items:
            item = selected_items[0]
            card_id = self.card_tree.item(item, "tags")[0]
            self.show_edit_card(card_id)
    
    def on_treeview_click(self, event):
        self.last_mouse_button = event.num
        if event.num == 3:
            event.widget.selection_anchor("")
            return "break"
        region = self.card_tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.card_tree.identify_row(event.y)
            if item:
                if event.state & 0x0004:
                    if item in self.card_tree.selection():
                        self.card_tree.selection_remove(item)
                    else:
                        self.card_tree.selection_add(item)
                    self.card_tree.focus(item)
                elif event.state & 0x0001:
                    current_selection = self.card_tree.selection()
                    if current_selection:
                        all_items = self.card_tree.get_children()
                        try:
                            first_idx = all_items.index(current_selection[0])
                            current_idx = all_items.index(item)
                            start = min(first_idx, current_idx)
                            end = max(first_idx, current_idx)
                            self.card_tree.selection_set(all_items[start:end+1])
                            self.card_tree.focus(item)
                        except ValueError:
                            pass
                else:
                    self.card_tree.selection_set(item)
                    self.card_tree.focus(item)
                self.drag_start_item = item
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.drag_selecting = True
    
    def on_treeview_ctrl_click(self, event):
        self.last_mouse_button = event.num
        region = self.card_tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.card_tree.identify_row(event.y)
            if item:
                if item in self.card_tree.selection():
                    self.card_tree.selection_remove(item)
                else:
                    self.card_tree.selection_add(item)
                self.card_tree.focus(item)
                return "break"
    
    def on_treeview_shift_click(self, event):
        self.last_mouse_button = event.num
        region = self.card_tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.card_tree.identify_row(event.y)
            if item:
                current_selection = self.card_tree.selection()
                if current_selection:
                    all_items = self.card_tree.get_children()
                    try:
                        first_idx = all_items.index(current_selection[0])
                        current_idx = all_items.index(item)
                        start = min(first_idx, current_idx)
                        end = max(first_idx, current_idx)
                        self.card_tree.selection_set(all_items[start:end+1])
                        self.card_tree.focus(item)
                    except ValueError:
                        pass
                return "break"
    
    def on_treeview_release(self, event):
        self.drag_selecting = False
        self.drag_start_item = None
    
    def on_treeview_drag(self, event):
        if not self.drag_selecting or not self.drag_start_item:
            return
        region = self.card_tree.identify_region(event.x, event.y)
        if region == "cell":
            current_item = self.card_tree.identify_row(event.y)
            if current_item and current_item != self.drag_start_item:
                all_items = self.card_tree.get_children()
                try:
                    start_idx = all_items.index(self.drag_start_item)
                    current_idx = all_items.index(current_item)
                    start = min(start_idx, current_idx)
                    end = max(start_idx, current_idx)
                    self.card_tree.selection_set(all_items[start:end+1])
                    self.card_tree.focus(current_item)
                except ValueError:
                    pass
    
    def on_treeview_select(self, event):
        if self.last_mouse_button == 3:
            return
        selection = self.card_tree.selection()
        if selection:
            item = selection[0]
            card_id = self.card_tree.item(item, "tags")[0]
            self.selected_card_id = card_id
    
    def show_context_menu(self, event):
        self.last_mouse_button = 3
        selected_items = self.card_tree.selection()
        if not selected_items:
            return
        item = self.card_tree.identify_row(event.y)
        if item and item not in selected_items:
            self.card_tree.selection_add(item)
            selected_items = self.card_tree.selection()
        
        has_favorites = False
        has_non_favorites = False
        for item in selected_items:
            card_id = self.card_tree.item(item, "tags")[0]
            card = self.card_manager.get_card(card_id)
            if card:
                if card.get('is_favorite', False):
                    has_favorites = True
                else:
                    has_non_favorites = True
        
        self.context_menu.delete(0, tk.END)
        if len(selected_items) == 1:
            self.context_menu.add_command(label="编辑  \tCtrl+O", command=self.edit_selected_card)
        
        if self.is_favorites_view:
            if len(selected_items) == 1:
                try:
                    if self.context_menu.index(tk.END) is not None and self.context_menu.index(tk.END) > 0:
                        self.context_menu.add_separator()
                except:
                    pass
            self.context_menu.add_command(label="取消收藏  \tCtrl+D", command=self.toggle_selected_favorites)
        else:
            if len(selected_items) > 1:
                try:
                    if self.context_menu.index(tk.END) is not None and self.context_menu.index(tk.END) > 0:
                        self.context_menu.add_separator()
                except:
                    pass
                self.context_menu.add_command(label="收藏  \tCtrl+D", command=self.toggle_selected_favorites)
            else:
                try:
                    if self.context_menu.index(tk.END) is not None and self.context_menu.index(tk.END) > 0:
                        self.context_menu.add_separator()
                except:
                    pass
                if has_favorites:
                    self.context_menu.add_command(label="取消收藏  \tCtrl+D", command=self.toggle_selected_favorites)
                else:
                    self.context_menu.add_command(label="收藏  \tCtrl+D", command=self.toggle_selected_favorites)
        
        try:
            if self.context_menu.index(tk.END) is not None and self.context_menu.index(tk.END) > 0:
                self.context_menu.add_separator()
        except:
            pass
        self.context_menu.add_command(label="删除  \tDel", command=self.delete_selected_card)
        self.context_menu.post(event.x_root + 10, event.y_root + 10)
    
    def edit_selected_card(self):
        selected_items = self.card_tree.selection()
        if selected_items:
            item = selected_items[0]
            card_id = self.card_tree.item(item, "tags")[0]
            self.show_add_card()
            self.card_editor.load_card(card_id)
    
    def toggle_selected_favorites(self):
        selected_items = self.card_tree.selection()
        if not selected_items:
            return
        card_ids = []
        for item in selected_items:
            card_id = self.card_tree.item(item, "tags")[0]
            card_ids.append(card_id)
        results = self.card_manager.toggle_favorites(card_ids)
        self.refresh_list_view(filtered_cards=self.current_filtered_cards)
    
    def toggle_favorites_view(self):
        self.is_favorites_view = not self.is_favorites_view
        try:
            if hasattr(self, 'file_menu') and hasattr(self, 'favorites_menu_index'):
                if self.is_favorites_view:
                    self.file_menu.entryconfigure(self.favorites_menu_index, label="全部卡片  \tAlt+D")
                    self.current_filtered_cards = self.card_manager.get_favorite_cards()
                else:
                    self.file_menu.entryconfigure(self.favorites_menu_index, label="收藏  \tAlt+D")
                    self.current_filtered_cards = None
        except Exception as e:
            print(f"更新菜单标签时出错: {str(e)}")
        self.refresh_list_view(filtered_cards=self.current_filtered_cards)
    
    def select_all_cards(self):
        if hasattr(self, 'card_tree'):
            self.card_tree.selection_clear()
            for item in self.card_tree.get_children():
                self.card_tree.selection_add(item)
    
    def undo_action(self):
        if hasattr(self, 'card_manager'):
            success = self.card_manager.undo_last_action()
            if success:
                self.refresh_list_view(filtered_cards=self.current_filtered_cards)
    
    def delete_selected_card(self):
        selected_items = self.card_tree.selection()
        if not selected_items:
            return
        if len(selected_items) > 1:
            if messagebox.askyesno("确认批量删除", f"确定要删除选中的{len(selected_items)}张卡片吗？"):
                for item in selected_items:
                    card_id = self.card_tree.item(item, "tags")[0]
                    self.card_manager.delete_card(card_id)
                self.refresh_list_view(filtered_cards=self.current_filtered_cards)
        else:
            item = selected_items[0]
            card_id = self.card_tree.item(item, "tags")[0]
            card = self.card_manager.get_card(card_id)
            if card and messagebox.askyesno("确认删除", f"确定要删除卡片 '{card['keyword']}' 吗？"):
                if self.card_manager.delete_card(card_id):
                    self.refresh_list_view(filtered_cards=self.current_filtered_cards)
                else:
                    messagebox.showerror("错误", "删除卡片失败")
    
    def show_update_log(self):
        try:
            from config import get_main_exe_dir
            update_file_path = os.path.join(get_main_exe_dir(), "assets", "update.txt")
            with open(update_file_path, 'r', encoding='utf-8') as f:
                update_content = f.read()
            update_window = tk.Toplevel(self.root)
            update_window.title("更新日志")
            update_window.geometry("800x690")
            update_window.resizable(False, False)
            if hasattr(self.app, '_set_window_icon'):
                self.app._set_window_icon(update_window)
            update_window.update_idletasks()
            width = update_window.winfo_width()
            height = update_window.winfo_height()
            x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
            y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
            update_window.geometry('+{}+{}'.format(x, y))
            main_frame = ttk.Frame(update_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            ttk.Label(main_frame, text="更新日志", font=("SimHei", 16, "bold")).pack(pady=(0, 15))
            text_frame = ttk.Frame(main_frame, height=300)
            text_frame.pack(fill=tk.X, pady=(0, 15))
            text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("SimSun", 16))
            text_widget.insert(tk.END, update_content)
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text_widget.config(yscrollcommand=scrollbar.set)
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=15)
            ttk.Button(button_frame, text="确定", command=update_window.destroy, width=15).pack()
        except Exception as e:
            messagebox.showerror("错误", f"读取更新日志失败: {str(e)}")
    
    def export_ancc(self):
        all_cards = self.card_manager.get_all_cards()
        if not all_cards:
            messagebox.showwarning("警告", "暂无卡片数据可导出")
            return
        file_path = filedialog.asksaveasfilename(
            title="导出ANCC文件",
            defaultextension=".ancc",
            initialfile="cards",
            filetypes=[("专属卡片格式", "*.ancc"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        try:
            encrypted_data = self.card_manager.encrypt_card_lines(all_cards)
            with open(file_path, "wb") as f:
                f.write(encrypted_data)
            messagebox.showinfo("成功", f"已导出{len(all_cards)}张卡片到\n{os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")
    
    def export_txt_format(self):
        all_cards = self.card_manager.get_all_cards()
        if not all_cards:
            messagebox.showwarning("警告", "暂无卡片数据可导出")
            return
        file_path = filedialog.asksaveasfilename(
            title="导出文本文件",
            defaultextension=".txt",
            initialfile="cards",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        def do_export():
            try:
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
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.root.after(0, lambda: messagebox.showinfo("成功", f"已导出{len(all_cards)}张卡片到\n{os.path.basename(file_path)}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"导出失败：{str(e)}"))
        threading.Thread(target=do_export, daemon=True).start()
    
    def export_json_format(self):
        all_cards = self.card_manager.get_all_cards()
        if not all_cards:
            messagebox.showwarning("警告", "暂无卡片数据可导出")
            return
        file_path = filedialog.asksaveasfilename(
            title="导出JSON文件",
            defaultextension=".json",
            initialfile="cards",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        def do_export():
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(all_cards, f, ensure_ascii=False, indent=2)
                self.root.after(0, lambda: messagebox.showinfo("成功", f"已导出{len(all_cards)}张卡片到\n{os.path.basename(file_path)}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"导出失败：{str(e)}"))
        threading.Thread(target=do_export, daemon=True).start()
    
    def on_window_configure(self, event):
        if not hasattr(self, '_window_initialized'):
            self._window_initialized = True
    
    def apply_window_settings(self):
        if self.settings_manager:
            position = self.settings_manager.get_window_position()
            if position:
                x, y = position
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                if 0 <= x < screen_width and 0 <= y < screen_height:
                    self.root.geometry(f"+{x}+{y}")
            size = self.settings_manager.get_window_size()
            if size:
                width, height = size
                min_width, min_height = 800, 600
                width = max(width, min_width)
                height = max(height, min_height)
                self.root.geometry(f"{width}x{height}")
    
    def apply_font_settings(self):
        """字体设置变更后刷新列表样式"""
        if hasattr(self, 'card_tree') and self.card_tree and self.settings_manager:
            style = ttk.Style()
            font_family = self.settings_manager.get_setting('font', 'family', 'Microsoft YaHei')
            font_size = self.settings_manager.get_setting('font', 'size', 12)
            style.configure("Treeview", 
                            font=(font_family, font_size), 
                            rowheight=max(30, font_size + 12))
            style.configure("Treeview.Heading", 
                            font=(font_family, font_size, "bold"))
            self.refresh_list_view(filtered_cards=self.current_filtered_cards)
    
    def show_tooltip(self, event):
        widget = event.widget
        if hasattr(widget, '_tooltip'):
            self.tooltip = tk.Toplevel(self.root)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root - 30}")
            label = ttk.Label(
                self.tooltip,
                text=widget._tooltip,
                background="#FFFFE0",
                foreground="#000000",
                relief="solid",
                borderwidth=1,
                padding=(5, 2)
            )
            label.pack()
    
    def hide_tooltip(self):
        if hasattr(self, 'tooltip') and self.tooltip:
            self.tooltip.destroy()
            delattr(self, 'tooltip')
    
    def on_window_close(self):
        # 检查未安装的更新
        if hasattr(self.app, 'update_manager') and self.app.update_manager:
            if self.app.update_manager.has_pending_update:
                result = messagebox.askyesnocancel(
                    "发现新版本",
                    "有新版本可用，是否立即安装更新？\n\n选择'是'立即安装，选择'否'稍后安装，选择'取消'取消操作。",
                    icon=messagebox.QUESTION
                )
                if result is None:
                    return
                elif result:
                    self.app.update_manager.install_update()
                    return
        
        # 保存卡片数据，如果失败则询问是否强制退出
        if hasattr(self, 'card_manager'):
            try:
                success = self.card_manager.save_cards()
                if not success:
                    result = messagebox.askyesnocancel(
                        "保存失败",
                        "卡片数据保存失败，是否仍然退出？\n\n选择“是”强制退出，选择“否”返回程序。",
                        icon=messagebox.WARNING
                    )
                    if result != True:
                        return
            except Exception as e:
                result = messagebox.askyesnocancel(
                    "保存错误",
                    f"保存时发生错误：{str(e)}\n是否仍然退出？",
                    icon=messagebox.WARNING
                )
                if result != True:
                    return

        # 保存窗口位置和大小
        if self.settings_manager:
            x, y = self.root.winfo_x(), self.root.winfo_y()
            width, height = self.root.winfo_width(), self.root.winfo_height()
            self.settings_manager.save_window_position(x, y)
            self.settings_manager.save_window_size(width, height)

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