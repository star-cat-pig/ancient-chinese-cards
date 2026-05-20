#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
古文卡片学习软件主程序入口
onedir打包专用
"""
import tkinter as tk
from tkinter import messagebox, font, ttk
import sys
import os
import re
import socket
import threading
import json
import ctypes

# 导入全局配置
from config import CURRENT_VERSION, get_icon_path, APP_NAME

# 导入自定义模块
from ui.main_window import MainWindow
from ui.settings_manager import SettingsManager
from card_manager import CardManager
from update_manager_proxy import UpdateManagerProxy


class SingleInstanceApp:
    """单实例应用管理器"""

    def __init__(self, port=12346):
        self.port = port
        self.is_running = False
        self.server = None
        self.server_thread = None
        self.app = None

    def check_single_instance(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(('127.0.0.1', self.port))
            sock.send(b'ACTIVATE')
            sock.close()
            print("已有实例在运行，正在激活现有窗口...")
            return False
        except (ConnectionRefusedError, socket.timeout, ConnectionError):
            self.start_server()
            return True

    def start_server(self):
        def server_thread():
            try:
                self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server.bind(('127.0.0.1', self.port))
                self.server.listen(1)
                self.server.settimeout(1)

                while self.is_running:
                    try:
                        conn, addr = self.server.accept()
                        data = conn.recv(1024)
                        if data == b'ACTIVATE' and self.app:
                            self.activate_window()
                        conn.close()
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"服务器错误: {e}")
                        break
            finally:
                if self.server:
                    self.server.close()

        self.is_running = True
        self.server_thread = threading.Thread(target=server_thread, daemon=True)
        self.server_thread.start()

    def activate_window(self):
        if self.app and self.app.root:
            try:
                if self.app.root.state() == 'iconic':
                    self.app.root.deiconify()
                self.app.root.lift()
                self.app.root.focus_force()
                if os.name == 'nt':
                    self.app.root.attributes('-topmost', True)
                    self.app.root.after(100, lambda: self.app.root.attributes('-topmost', False))
                print("窗口已激活！")
            except Exception as e:
                print(f"激活窗口失败: {e}")

    def set_app(self, app):
        self.app = app


class AncientChineseCardsApp:
    """古文卡片学习软件主应用类"""

    def __init__(self):
        # 设置任务栏图标（必须在创建任何窗口之前调用）
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{APP_NAME}.1.0")
                print("已设置 AppUserModelID，任务栏图标将正确显示")
            except Exception as e:
                print(f"设置 AppUserModelID 失败: {e}")

        self.single_instance = SingleInstanceApp()
        if not self.single_instance.check_single_instance():
            sys.exit(0)

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1024x768")
        self.root.minsize(width=1000, height=600)

        # 先加载配置
        self.settings_manager = SettingsManager(self)

        # 窗口状态相关
        self._save_window_job = None
        self._ignore_window_configure = True
        self._last_normal_geometry = self.root.geometry()

        self.single_instance.set_app(self)
        self.icon_path = get_icon_path()
        self._set_window_icon(self.root)

        self.root.bind("<Create>", self._on_window_create)
        self.root.bind("<Configure>", self._on_window_configure)

        self.card_manager = CardManager()
        self.update_checker = UpdateManagerProxy(self)

        self.setup_fonts()
        self.main_window = MainWindow(self.root, self.card_manager, self)

        # 让设置管理器把字体等设置真正应用到已经创建好的界面
        self.settings_manager.apply_settings()

        self.load_cards()
        self.apply_window_settings()

        if self.settings_manager.get_setting("update", "auto_check_update", True):
            ignore_version = self.settings_manager.get_setting("update", "ignore_version", "")
            if not ignore_version or ignore_version != self.update_checker.check_for_updates().get('latest_version', ''):
                self.root.after(1000, self._auto_check_update)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_fonts(self):
        try:
            family = self.settings_manager.get_setting("font", "family", "Microsoft YaHei")
            size = self.settings_manager.get_setting("font", "size", 12)
            default_font = font.Font(family=family, size=size)
            self.root.option_add("*Font", default_font)
        except Exception as e:
            print(f"字体设置失败: {e}")

    def load_cards(self):
        try:
            self.card_manager.load_cards()
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.config(text=f"已加载 {len(self.card_manager.cards)} 张卡片")
        except Exception as e:
            messagebox.showerror("错误", f"加载卡片失败: {str(e)}")

    def save_cards(self):
        try:
            self.card_manager.save_cards()
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存卡片失败: {str(e)}")
            return False

    def _auto_check_update(self):
        def check():
            if self.update_checker.is_update_available():
                self.root.after(0, self.update_checker.show_update_prompt)
        threading.Thread(target=check, daemon=True).start()

    def _set_window_icon(self, window):
        """设置窗口左上角图标（不影响任务栏）"""
        if not os.path.exists(self.icon_path):
            return
        try:
            if self.icon_path.endswith(".ico"):
                window.iconbitmap(self.icon_path)
            else:
                icon_image = tk.PhotoImage(file=self.icon_path)
                window.iconphoto(True, icon_image)
                window.icon_image = icon_image
        except Exception as e:
            print(f"设置窗口图标失败: {str(e)}")

    def _on_window_create(self, event):
        if isinstance(event.widget, tk.Toplevel):
            event.widget.after(10, lambda: self._set_window_icon(event.widget))

    def _geometry_to_tuple(self, geometry_str):
        """
        解析 geometry 字符串，例如 '1024x768+100+100'
        返回 (w, h, x, y)，解析失败返回 None
        """
        if not geometry_str:
            return None
        match = re.match(r"^(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?$", geometry_str.strip())
        if not match:
            return None
        w, h, x, y = match.groups()
        return int(w), int(h), (int(x) if x is not None else None), (int(y) if y is not None else None)

    def _on_window_configure(self, event):
        if event.widget != self.root:
            return
        if self._ignore_window_configure:
            return

        current_state = self.root.state()

        # 记录“正常状态”下最后一次有效几何信息，最大化时用于恢复
        if current_state == "normal":
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            if w > 100 and h > 100:
                self._last_normal_geometry = f"{w}x{h}+{x}+{y}"

        # 防抖：窗口停止变化 3 秒后再保存
        if self._save_window_job is not None:
            try:
                self.root.after_cancel(self._save_window_job)
            except Exception:
                pass
        self._save_window_job = self.root.after(3000, self._save_window_state)

    def _save_window_state(self):
        try:
            current_state = self.root.state()
            
            # 获取旧值
            old_state = self.settings_manager.get_setting("ui", "window_state", "normal")
            old_size = self.settings_manager.get_setting("ui", "window_size", None)
            old_pos = self.settings_manager.get_setting("ui", "window_position", None)
            
            # 保存正常状态的位置和大小
            if current_state == "zoomed" and self._last_normal_geometry:
                parsed = self._geometry_to_tuple(self._last_normal_geometry)
                if parsed:
                    w, h, x, y = parsed
                else:
                    w = self.root.winfo_width()
                    h = self.root.winfo_height()
                    x = self.root.winfo_x()
                    y = self.root.winfo_y()
            else:
                w = self.root.winfo_width()
                h = self.root.winfo_height()
                x = self.root.winfo_x()
                y = self.root.winfo_y()
            
            # 只在值真正改变时才设置和保存
            has_change = False
            
            if current_state != old_state:
                self.settings_manager.set_setting("ui", "window_state", current_state)
                has_change = True
            
            if old_size != (w, h):
                self.settings_manager.set_setting("ui", "window_size", (w, h))
                has_change = True
            
            if old_pos != (x, y):
                self.settings_manager.set_setting("ui", "window_position", (x, y))
                has_change = True
            
            # 只在有变化时才保存文件
            if has_change:
                self.settings_manager.save_preferences()
                print(f"已保存窗口状态: {current_state} 尺寸: {w}x{h} 位置: {x},{y}")
        except Exception as e:
            print(f"保存窗口状态失败: {e}")

    def _enable_window_config_save(self):
        """允许窗口 Configure 事件开始参与防抖保存"""
        self._ignore_window_configure = False

    def apply_window_settings(self):
        try:
            # 兼容读取：优先 ui，必要时读取旧键
            window_state = self.settings_manager.get_setting("ui", "window_state", "normal")
            size = self.settings_manager.get_setting("ui", "window_size", None)
            position = self.settings_manager.get_setting("ui", "window_position", None)

            print(f"读取到配置状态: {window_state}")

            # 避免启动阶段自身触发保存
            self._ignore_window_configure = True

            # 先恢复到普通状态，再应用 geometry
            try:
                self.root.state("normal")
            except Exception:
                pass

            if size and isinstance(size, (list, tuple)) and len(size) >= 2:
                width, height = int(size[0]), int(size[1])
                width = max(width, 800)
                height = max(height, 600)
                self.root.geometry(f"{width}x{height}")
            else:
                self.root.geometry("1024x768")

            if position and isinstance(position, (list, tuple)) and len(position) >= 2:
                x, y = int(position[0]), int(position[1])
                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight()
                if 0 <= x < sw and 0 <= y < sh:
                    self.root.geometry(f"+{x}+{y}")

            self._last_normal_geometry = self.root.geometry()

            # 真正恢复最大化
            if window_state == "zoomed":
                self.root.after(50, lambda: self.root.state("zoomed"))
                print("已应用窗口状态: zoomed (最大化)")
            else:
                print("已应用窗口状态: normal")

            # 稍后再允许保存，避免初始化过程产生误写
            self.root.after(1000, self._enable_window_config_save)

        except Exception as e:
            print(f"应用窗口设置失败: {e}")
            self.root.after(1000, self._enable_window_config_save)

    def on_closing(self):
        # 关闭前先取消窗口防抖任务，并立即保存一次
        if self._save_window_job is not None:
            try:
                self.root.after_cancel(self._save_window_job)
            except Exception:
                pass
            self._save_window_job = None
        self._save_window_state()

        if self.card_manager.has_modified_cards():
            dialog = tk.Toplevel(self.root)
            dialog.title("退出")
            dialog.geometry("300x120")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.resizable(False, False)

            dialog.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() // 2 - 150)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2 - 60)
            dialog.geometry(f'+{x}+{y}')

            tk.Label(dialog, text="是否保存更改后退出？", font=("SimHei", 12)).pack(pady=20)
            button_frame = tk.Frame(dialog)
            button_frame.pack(pady=10)

            def save_and_close():
                dialog.destroy()
                if self.save_cards():
                    self.update_checker.on_app_exit()
                    self.root.destroy()

            tk.Button(button_frame, text="保存(S)", command=save_and_close, width=10).pack(side=tk.LEFT, padx=5)
            tk.Button(
                button_frame,
                text="不保存(N)",
                command=lambda: [dialog.destroy(), self.update_checker.on_app_exit(), self.root.destroy()],
                width=10
            ).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        else:
            self.update_checker.on_app_exit()
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = AncientChineseCardsApp()
    app.run()