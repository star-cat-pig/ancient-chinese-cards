#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立更新程序 - Card Manager Update Utility
支持命令行和GUI两种模式，onefile打包专用
"""
import sys
import os
import argparse
import json
import requests
import tempfile
import shutil
import subprocess
import threading
import time
import re
import ctypes
import socket
from ctypes import wintypes
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ========== Windows API 相关常量与定义 ==========
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)

# 定义API参数与返回值类型
kernel32.CreateMutexW.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
user32.MessageBoxW.restype = ctypes.c_int
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

# Windows API 常量
ERROR_ALREADY_EXISTS = 183
MB_OK = 0x00000000
MB_ICONINFORMATION = 0x00000040
MB_TOPMOST = 0x00040000
MB_SETFOREGROUND = 0x00010000
SW_RESTORE = 9


class UpdateSingleInstance:
    """更新程序的单实例管理器 - 使用 Socket 通信"""
    
    def __init__(self, port=12347):  # 使用和主程序不同的端口
        self.port = port
        self.is_running = False
        self.server = None
        self.server_thread = None
        self.root_window = None  # 保存主窗口引用
        
    def set_window(self, window):
        """设置窗口引用，用于激活"""
        self.root_window = window
        
    def check_and_activate(self):
        """
        检查是否有实例在运行
        返回: True=第一个实例，False=已有实例（已激活）
        """
        try:
            # 尝试连接到已存在的实例
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(('127.0.0.1', self.port))
            # 发送激活信号
            sock.send(b'ACTIVATE')
            sock.close()
            
            print("更新程序正在运行，请等待其完成运行或关闭程序！")
            
            # 显示提示
            user32.MessageBoxW(
                None,
                "更新程序正在运行，请等待其完成运行或关闭程序",
                "古文卡片更新程序",
                MB_OK | MB_ICONINFORMATION | MB_TOPMOST | MB_SETFOREGROUND
            )
            return False  # 已有实例，应该退出
            
        except (ConnectionRefusedError, socket.timeout, ConnectionError):
            # 没有现有实例，启动服务器
            self.start_server()
            return True  # 是第一个实例
            
    def start_server(self):
        """启动socket服务器监听激活信号"""
        def server_thread():
            try:
                self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server.bind(('127.0.0.1', self.port))
                self.server.listen(1)
                self.server.settimeout(1)
                
                print(f"更新程序单实例服务器已启动，端口: {self.port}")
                
                while self.is_running:
                    try:
                        conn, addr = self.server.accept()
                        data = conn.recv(1024)
                        if data == b'ACTIVATE':
                            # 收到激活信号，激活窗口
                            self.activate_window()
                        conn.close()
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"服务器错误: {e}")
                        break
            except Exception as e:
                print(f"启动服务器失败: {e}")
            finally:
                if self.server:
                    self.server.close()
                print("更新程序单实例服务器已停止")
            
        self.is_running = True
        self.server_thread = threading.Thread(target=server_thread, daemon=True)
        self.server_thread.start()
        
    def activate_window(self):
        """激活并显示窗口 - 简化版"""
        if self.root_window:
            try:
                print("激活窗口...")
                
                # 如果窗口被最小化，恢复它
                if self.root_window.state() == 'iconic':
                    self.root_window.deiconify()
                
                # 强制更新窗口状态
                self.root_window.update_idletasks()
                
                # 关键：直接设置固定大小 750x700
                self.root_window.geometry("750x700")
                self.root_window.minsize(750, 700)
                self.root_window.maxsize(750, 700)
                
                # 居中显示
                self.root_window.update_idletasks()
                screen_width = self.root_window.winfo_screenwidth()
                screen_height = self.root_window.winfo_screenheight()
                x = (screen_width - 750) // 2
                y = (screen_height - 700) // 2
                self.root_window.geometry(f"750x700+{x}+{y}")
                
                # 确保窗口在前端显示
                self.root_window.lift()
                self.root_window.focus_force()
                
                # Windows 置顶效果
                if os.name == 'nt':
                    self.root_window.attributes('-topmost', True)
                    self.root_window.after(100, lambda: self.root_window.attributes('-topmost', False))
                
                print("窗口已激活，大小已设置为 750x700")
                
            except Exception as e:
                print(f"激活窗口失败: {e}")

def check_single_instance():
    """
    兼容旧接口的函数
    返回 True 表示是第一个实例，False 表示已有实例
    """
    global _single_instance
    _single_instance = UpdateSingleInstance()
    return _single_instance.check_and_activate()


def get_single_instance():
    """获取单实例管理器实例"""
    global _single_instance
    return _single_instance


# ==================== 原有的导入和类定义 ====================
# 统一导入所有模块
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, font
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw, ImageTk
    TRAY_AVAILABLE = True
    PIL_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    PIL_AVAILABLE = False
    print("PIL库不可用，无法显示更新图片轮播", file=sys.stderr)


class UpdateConfig:
    """更新程序配置类 - 全局唯一配置源来自config.py，打包自动内置"""
    
    def __init__(self):
        self.platform_tag = "x64"  # 架构标签，默认 x64；config 中存在 PLATFORM_TAG 则覆盖
        try:
            from config import (
                APP_NAME, MAIN_EXE_NAME, CURRENT_VERSION,
                GITHUB_OWNER, GITHUB_REPO
            )
            self.github_owner = GITHUB_OWNER
            self.github_repo = GITHUB_REPO
            self.current_version = CURRENT_VERSION
            self.app_name = APP_NAME
            self.main_exe_name = MAIN_EXE_NAME
            try:
                from config import PLATFORM_TAG
                self.platform_tag = PLATFORM_TAG
            except ImportError:
                pass  # 老版 config 无架构标签，保持默认 x64
        except ImportError:
            self.github_owner = "star-cat-pig"
            self.github_repo = "ancient-chinese-cards"
            self.current_version = "2.0"
            self.app_name = "古文卡片学习软件"
            self.main_exe_name = "cards.exe"
        
        self.main_exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.update_info_file = os.path.join(tempfile.gettempdir(), 'card_update_info.json')
        self.icon_relative_path = "assets/icon.ico"
        self.ignore_version = ""
        self.force_show = False
        self._load_config()
    
    def _load_config(self):
        config_path = None
        if '--config' in sys.argv:
            try:
                idx = sys.argv.index('--config')
                if idx + 1 < len(sys.argv):
                    config_path = sys.argv[idx + 1]
            except Exception as e:
                print(f"解析配置文件路径失败: {e}", file=sys.stderr)
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key, value in config.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
                print(f"已从配置文件补充配置: {config_path}", file=sys.stderr)
            except Exception as e:
                print(f"加载配置文件失败: {e}", file=sys.stderr)
        
        for key in ['github_owner', 'github_repo', 'current_version', 'ignore_version', 'platform_tag']:
            env_key = f"CARD_UPDATE_{key.upper()}"
            if env_key in os.environ:
                setattr(self, key, os.environ[env_key])
                print(f"已从环境变量覆盖配置 {key}: {os.environ[env_key]}", file=sys.stderr)
        
        if '--force' in sys.argv:
            self.force_show = True
        
        if not all([self.github_owner, self.github_repo, self.current_version, self.app_name, self.main_exe_name]):
            print("警告: 配置不完整，可能影响更新功能", file=sys.stderr)
class UpdateManager:
    """独立更新管理器 - onefile打包专用"""
    
    def __init__(self, config, silent=False):
        self.config = config
        self.silent = silent
        self.temp_dir = tempfile.gettempdir()
        self.download_url = None
        self.latest_version = None
        self.release_note = ""
        self.download_thread = None
        self.is_downloading = False
        self.download_progress = 0
        self.download_size = 0
        self.total_size = 0
        self.update_file_path = None
        self.retry_count = 0
        self.max_retries = 3
        self.root = None
        self.progress_window = None
        self.progress_var = None
        self.progress_label = None
        self.main_exe_path = os.path.join(self.config.main_exe_dir, self.config.main_exe_name)
        self.icon_path = self._get_icon_path()
        self.temp_dir = tempfile.gettempdir()
        self.max_retries = 3
        self.is_downloading = False
        self.download_thread = None
        self.download_session = None
        self.should_cancel_download = False
    
    def _format_release_note(self, note: str) -> list:
        if not note or not note.strip():
            return [("暂无更新说明", "normal")]
        
        lines = note.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                title = line[2:].strip()
                if title:
                    formatted_lines.append((title, "large"))
                    formatted_lines.append(("", "normal"))
            elif line.startswith('## '):
                title = line[3:].strip()
                if title:
                    formatted_lines.append((title, "medium"))
                    formatted_lines.append(("", "normal"))
            elif line.startswith('- '):
                item = line[2:].strip()
                if item:
                    formatted_lines.append((f"● {item}", "normal"))
            elif not line:
                if formatted_lines and formatted_lines[-1][0]:
                    formatted_lines.append(("", "normal"))
            else:
                formatted_lines.append((line, "normal"))
        
        while formatted_lines and not formatted_lines[-1][0]:
            formatted_lines.pop()
        
        if not formatted_lines:
            return [("暂无更新说明", "normal")]
            
        return formatted_lines
    
    def _get_icon_path(self):
        icon_path = os.path.join(self.config.main_exe_dir, self.config.icon_relative_path)
        if not os.path.exists(icon_path):
            icon_path = icon_path.replace('.ico', '.png')
        return icon_path if os.path.exists(icon_path) else None
    
    def _compare_version(self, v1, v2):
        try:
            v1_parts = list(map(int, v1.lstrip("v").split(".")))
            v2_parts = list(map(int, v2.lstrip("v").split(".")))
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts += [0] * (max_len - len(v1_parts))
            v2_parts += [0] * (max_len - len(v2_parts))
            for a, b in zip(v1_parts, v2_parts):
                if a > b:
                    return 1
                elif a < b:
                    return -1
            return 0
        except Exception as e:
            print(f"版本号对比失败: {e}", file=sys.stderr)
            return 0
    
    def _get_requests_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session
    
    def fetch_latest_release(self):
        try:
            api_url = f"https://api.github.com/repos/{self.config.github_owner}/{self.config.github_repo}/releases/latest"
            session = self._get_requests_session()
            response = session.get(api_url, timeout=30)
            response.raise_for_status()
            release_data = response.json()
            self.latest_version = release_data.get("tag_name", "").lstrip("v")
            self.release_note = release_data.get("body", "本次更新优化了多项功能，提升稳定性和用户体验")
            assets = release_data.get("assets", [])

            # ---- 架构感知选包（ARM 支持）----
            # 按打包时内置的 platform_tag 认领对应架构的安装包：
            #   "arm" -> 只认资产名含 "arm" 的 .exe（如 Setup_Cards_ARM_2.0.exe）
            #   "x64" -> 只认资产名不含 "arm" 的 .exe（如 cards.exe / Setup_Cards_2.0.exe）
            # 任何情况下都绝不下载另一架构的包。
            platform_tag = (getattr(self.config, "platform_tag", "") or "").strip().lower() or "x64"
            self.config.platform_tag = platform_tag  # 归一化，供后续逻辑/日志使用
            target_asset = None

            for asset in assets:
                asset_name = asset.get("name", "")
                if not asset_name.lower().endswith(".exe"):
                    continue
                if platform_tag == "arm":
                    if "arm" in asset_name.lower():
                        target_asset = asset
                        break
                else:  # x64 / 其他：排除 ARM 资产
                    if "arm" not in asset_name.lower():
                        target_asset = asset
                        break

            if target_asset:
                self.download_url = target_asset.get("browser_download_url")
            else:
                if not self.silent:
                    arch_desc = "ARM" if platform_tag == "arm" else "x64/通用"
                    print(f"未找到匹配{arch_desc}架构的更新包（GitHub release 可能还未上传对应安装包）", file=sys.stderr)
                return False
            
            if not self.silent:
                arch_desc = "ARM" if platform_tag == "arm" else "x64/通用"
                print(f"获取到最新版本: v{self.latest_version}（{arch_desc}），下载地址: {self.download_url}", file=sys.stderr)
            
            return True
            
        except requests.exceptions.ConnectionError:
            if not self.silent:
                print("网络连接失败", file=sys.stderr)
            return False
        except requests.exceptions.RequestException as e:
            if not self.silent:
                print(f"获取更新信息失败: {e}", file=sys.stderr)
            return False
        except Exception as e:
            if not self.silent:
                print(f"解析更新信息失败: {e}", file=sys.stderr)
            return False
    
    def is_update_available(self):
        if not self.fetch_latest_release():
            return False
        
        current_version = self.config.current_version.lstrip("v")
        latest_version = self.latest_version.lstrip("v")
        ignore_version = self.config.ignore_version.lstrip("v")
        
        has_new_version = self._compare_version(current_version, latest_version) == -1
        if not has_new_version:
            return False
        
        if self.config.force_show:
            return True
        
        if not ignore_version:
            return True
        else:
            return self._compare_version(latest_version, ignore_version) == 1
    
    def check_for_updates(self):
        result = {
            "has_update": False,
            "current_version": self.config.current_version,
            "latest_version": None,
            "release_note": "",
            "download_url": None,
            "error": None,
            "network_error": False
        }
        
        if not self.fetch_latest_release():
            try:
                requests.get("https://www.baidu.com", timeout=5)
                result['error'] = "获取更新信息失败"
            except:
                result['error'] = "网络未连接"
                result['network_error'] = True
            return result
        
        result.update({
            "latest_version": self.latest_version,
            "release_note": self.release_note,
            "download_url": self.download_url
        })
        
        current_version = self.config.current_version.lstrip("v")
        latest_version = self.latest_version.lstrip("v")
        
        if self._compare_version(current_version, latest_version) == -1:
            result['has_update'] = True
        
        try:
            with open(self.config.update_info_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if not self.silent:
                print(f"保存更新信息失败: {e}", file=sys.stderr)
        
        return result
    
    def download_update(self, progress_callback=None):
        if not self.download_url:
            self._show_error("错误", "未找到对应平台的更新包")
            return False
        
        if self._check_existing_update_package():
            return True
        
        self.is_downloading = True
        self.download_progress = 0
        self.download_size = 0
        self.total_size = 0
        
        filename = os.path.basename(self.download_url)
        self.update_file_path = os.path.join(self.temp_dir, filename)
        
        if os.path.exists(self.update_file_path):
            try:
                os.remove(self.update_file_path)
            except Exception as e:
                print(f"删除不完整文件失败: {e}", file=sys.stderr)
        
        self.retry_count = 0
        
        while self.retry_count < self.max_retries:
            try:
                session = self._get_requests_session()
                response = session.get(self.download_url, stream=True, timeout=120)
                response.raise_for_status()
                
                self.total_size = int(response.headers.get("content-length", 0))
                self.download_size = 0
                
                with open(self.update_file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not self.is_downloading:
                            f.close()
                            break
                        if chunk:
                            f.write(chunk)
                            self.download_size += len(chunk)
                            self.download_progress = int((self.download_size / self.total_size) * 100) if self.total_size > 0 else 0
                            if progress_callback:
                                progress_callback(self.download_progress, self.download_size, self.total_size)
                
                if not self.is_downloading:
                    print("下载已被用户取消", file=sys.stderr)
                    return False
                
                if os.path.exists(self.update_file_path):
                    file_size = os.path.getsize(self.update_file_path)
                    if self.total_size > 0 and file_size == self.total_size:
                        if not self.silent:
                            print(f"更新包下载完成，大小: {file_size} 字节", file=sys.stderr)
                        
                        update_info = {
                            "downloaded": True,
                            "file_path": self.update_file_path,
                            "version": self.latest_version,
                            "download_time": datetime.now().isoformat()
                        }
                        try:
                            with open(self.config.update_info_file, 'w', encoding='utf-8') as f:
                                json.dump(update_info, f, ensure_ascii=False, indent=2)
                        except Exception as e:
                            print(f"保存下载信息失败: {e}", file=sys.stderr)
                        
                        return True
                    else:
                        print(f"更新包下载不完整，期望大小: {self.total_size}，实际大小: {file_size}", file=sys.stderr)
                        self.retry_count += 1
                        if self.retry_count < self.max_retries:
                            if not self.silent:
                                print(f"第 {self.retry_count} 次重试下载...", file=sys.stderr)
                            if os.path.exists(self.update_file_path):
                                os.remove(self.update_file_path)
                            continue
                        else:
                            raise Exception(f"更新包下载不完整，已重试 {self.max_retries} 次")
                else:
                    raise Exception("更新包文件不存在")
                    
            except requests.exceptions.ConnectionError:
                self.retry_count += 1
                if self.retry_count < self.max_retries:
                    if not self.silent:
                        print(f"网络连接失败，第 {self.retry_count} 次重试...", file=sys.stderr)
                    time.sleep(2)
                else:
                    self.is_downloading = False
                    return False
            except Exception as e:
                self.is_downloading = False
                if not self.silent:
                    print(f"下载错误: {e}", file=sys.stderr)
                return False
        
        return False
    
    def _check_existing_update_package(self):
        if not self.download_url:
            return False
        
        try:
            if os.path.exists(self.config.update_info_file):
                with open(self.config.update_info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    if info.get('downloaded') and info.get('version') == self.latest_version:
                        file_path = info.get('file_path')
                        if file_path and os.path.exists(file_path):
                            self.update_file_path = file_path
                            return True
        except Exception as e:
            print(f"检查现有更新包失败: {e}", file=sys.stderr)
        
        return False
    
    def open_install_package_and_exit(self):
        """下载完成后打开安装包，等待一下再退出"""
        if not self.update_file_path or not os.path.exists(self.update_file_path):
            self._show_error("错误", "安装包不存在，请先下载更新。")
            return False

        try:
            if sys.platform == "win32":
                # 显示提示
                if GUI_AVAILABLE and self.root:
                    messagebox.showinfo("启动安装", "正在启动安装程序，请稍候...", parent=self.root)
                # 启动安装包
                os.startfile(self.update_file_path)
                print(f"已打开安装包: {self.update_file_path}")

                # 延迟 2 秒退出，给安装程序启动时间
                def delayed_exit():
                    sys.exit(0)

                if GUI_AVAILABLE and self.root:
                    self.root.after(2000, delayed_exit)
                else:
                    time.sleep(2)
                    sys.exit(0)

            else:
                subprocess.Popen([self.update_file_path], cwd=os.path.dirname(self.update_file_path))
                sys.exit(0)

        except Exception as e:
            print(f"打开安装包失败: {e}", file=sys.stderr)
            self._show_error("打开失败", f"无法启动安装包: {str(e)}")
            return False
    
    def run_update_process(self):
        if not self.silent and GUI_AVAILABLE:
            self._show_info("检查更新", "正在检查更新...")
        
        update_info = self.check_for_updates()
        
        if not update_info['has_update']:
            if not self.silent and GUI_AVAILABLE:
                self._show_info("提示", "当前已是最新版本。")
            return False
        
        if not self.silent and GUI_AVAILABLE:
            release_note = update_info['release_note'][:500] + "..." if len(update_info['release_note']) > 500 else update_info['release_note']
            if not messagebox.askyesno(
                f"发现新版本 {update_info['latest_version']}",
                f"当前版本: {update_info['current_version']}\n新版本: {update_info['latest_version']}\n\n更新内容:\n{release_note}\n\n是否下载并打开安装包？"
            ):
                return False
        
        if not self.download_update():
            return False
        
        self.open_install_package_and_exit()
        return True
    
    def _start_main_program(self):
        try:
            subprocess.Popen([self.main_exe_path], cwd=self.config.main_exe_dir)
        except Exception as e:
            print(f"启动主程序失败: {e}", file=sys.stderr)
    
    def _center_window(self, window):
        """居中窗口 - 固定大小 750x700"""
        window.update_idletasks()
        width = 750
        height = 700
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    def _set_window_icon(self, window):
        if self.icon_path and window:
            try:
                if self.icon_path.endswith('.ico'):
                    window.iconbitmap(self.icon_path)
                else:
                    icon_image = tk.PhotoImage(file=self.icon_path)
                    window.iconphoto(True, icon_image)
                    window.icon_image = icon_image
            except Exception as e:
                if not self.silent:
                        print(f"设置图标失败: {e}", file=sys.stderr)
    
    def _show_info(self, title, message):
        if GUI_AVAILABLE:
            messagebox.showinfo(title, message)
        else:
            print(f"[INFO] {title}: {message}")
    
    def _show_error(self, title, message):
        if GUI_AVAILABLE:
            messagebox.showerror(title, message)
        else:
            print(f"[ERROR] {title}: {message}")
    
    def _show_warning(self, title, message):
        if GUI_AVAILABLE:
            messagebox.showwarning(title, message)
        else:
            print(f"[WARNING] {title}: {message}")
    def show_update_prompt(self):
        if not GUI_AVAILABLE:
            print("GUI模块不可用，无法显示更新提示", file=sys.stderr)
            return False
        
        if not self.is_update_available():
            if self.config.force_show:
                self._show_info("无更新", f"当前已是最新版本（v{self.config.current_version}）！")
            return False
        
        latest_version = self.latest_version.lstrip('v')
        ignore_version = self.config.ignore_version.lstrip('v')
        
        self.root = tk.Tk()
        self.root.withdraw()
        ignore_var = tk.BooleanVar(value=(ignore_version == latest_version))
        
        prompt_window = tk.Toplevel(self.root)
        prompt_window.title(f"发现新版本 v{latest_version}")
        prompt_window.geometry("700x550")
        prompt_window.minsize(650, 450)
        prompt_window.resizable(True, True)
        prompt_window.transient(self.root)
        prompt_window.grab_set()
        self._center_window(prompt_window)
        self._set_window_icon(prompt_window)
        
        main_frame = ttk.Frame(prompt_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        welcome_label = ttk.Label(
            main_frame,
            text=f"亲爱的用户，为了改进{self.config.app_name}的使用体验，我们带来了最新的版本。我们建议您及时更新，以享受最新的功能与优化！",
            font=("SimHei", 12),
            foreground="#2c3e50",
            justify=tk.LEFT,
            wraplength=650
        )
        welcome_label.pack(pady=(0, 15), anchor=tk.W)
        
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=(0, 15))
        version_frame.columnconfigure(1, weight=1)
        
        ttk.Label(version_frame, text="当前版本:", font=("SimHei", 11)).grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Label(version_frame, text=f"v{self.config.current_version}", font=("SimHei", 11)).grid(row=0, column=1, sticky=tk.W, padx=10, pady=3)
        ttk.Label(version_frame, text="最新版本:", font=("SimHei", 11)).grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Label(version_frame, text=f"v{latest_version}", font=("SimHei", 11, "bold"), foreground="#C44536").grid(row=1, column=1, sticky=tk.W, padx=10, pady=3)
        
        ttk.Label(main_frame, text="更新内容:", font=("SimHei", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))
        
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        note_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("SimHei", 11),
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=8
        )
        note_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        formatted_lines = []
        for line, _ in self._format_release_note(self.release_note):
            formatted_lines.append(line)
        note_text.insert(tk.END, "\n".join(formatted_lines))
        note_text.config(state=tk.DISABLED)
        scrollbar.config(command=note_text.yview)
        
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ignore_check = ttk.Checkbutton(
            bottom_frame,
            text="不要再提醒我此版本更新",
            variable=ignore_var
        )
        ignore_check.pack(side=tk.LEFT, anchor=tk.W)
        
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        def on_confirm():
            prompt_window.destroy()
            print(f"UPDATE_IGNORE_VERSION=")
            self.root.quit()
            self.run_update_process()
        
        def on_cancel():
            prompt_window.destroy()
            output_ignore_version = latest_version if ignore_var.get() else ""
            print(f"UPDATE_IGNORE_VERSION={output_ignore_version}")
            self.root.quit()
        
        cancel_btn = ttk.Button(
            btn_frame,
            text="取消",
            command=on_cancel,
            width=10
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        update_btn = ttk.Button(
            btn_frame,
            text="立即更新",
            command=on_confirm,
            width=12
        )
        update_btn.pack(side=tk.RIGHT, padx=5)
        
        prompt_window.protocol("WM_DELETE_WINDOW", on_cancel)
        self.root.mainloop()
        return True
class LoadingAnimation(tk.Canvas):
    """基于CSS动画转换的Python加载动画"""
    def __init__(self, parent, width=120, height=30, color="#165DFF", **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.color = color
        self.animation_id = None
        self.time = 0
        self.dot_radius = 5
        self.dot_spacing = 20
        self.start_x = (width - 2 * self.dot_spacing) // 2
        self.center_y = height // 2
        
    def start(self):
        if self.animation_id is None:
            self._animate()
    
    def stop(self):
        if self.animation_id is not None:
            self.after_cancel(self.animation_id)
            self.animation_id = None
            self.delete("all")
    
    def _animate(self):
        self.delete("all")
        t = self.time / 60
        
        for i in range(3):
            phase = t * 2 - i * 0.33
            scale = 1.0
            offset_x = 0
            
            cycle = phase % 1.0
            if cycle < 0.25:
                offset_x = -cycle * 4 * 10
            elif cycle < 0.5:
                offset_x = -10
            elif cycle < 0.75:
                offset_x = -(1 - (cycle - 0.5) * 4) * 10
            else:
                offset_x = 0
            
            x = self.start_x + i * self.dot_spacing + offset_x
            y = self.center_y
            
            self.create_oval(
                x - self.dot_radius, y - self.dot_radius,
                x + self.dot_radius, y + self.dot_radius,
                fill=self.color, outline=""
            )
        
        self.time += 1
        self.animation_id = self.after(33, self._animate)
class StandaloneUpdateGUI:
    """用户直接打开update.exe时的独立GUI流程"""

    #统一图片文本大小
    CONTENT_HEIGHT = 240
    
    def __init__(self, update_manager, auto_start_download=False):
        self.update_manager = update_manager
        self.config = update_manager.config
        self.auto_start_download = auto_start_download
        self.root = None
        self.progress_var = None
        self.progress_bar = None
        self.progress_label = None
        self.status_label = None
        self.tray_icon = None
        self.tray_menu = None
        self.loading_animation = None
        self.sub_status_label = None
        self.progress_frame = None
        self.main_frame = None
        self.status_frame = None
        
        # ==================== 图片轮播相关变量 ====================
        self.gallery_frame = None
        self.gallery_canvas = None
        self.original_images = []   # 存 PIL 原图
        self.current_photo = None   # 存当前显示的 PhotoImage（防回收）
        self.image_index = 0
        self.auto_switch_id = None
        self.pictures_dir = None
        self.content_frame = None
    
    def create_main_window(self):
        if not GUI_AVAILABLE:
            print("GUI模块不可用，无法启动图形界面", file=sys.stderr)
            return False
        
        self.root = tk.Tk()
        self.root.title(f"{self.config.app_name} 更新程序")
        self.root.geometry("750x700")
        self.root.minsize(750, 700)
        self.root.maxsize(750, 700)
        self.root.resizable(False, False)
        
        self.update_manager._set_window_icon(self.root)
        self.update_manager._center_window(self.root)
        
        self.main_frame = ttk.Frame(self.root, padding=40)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(
            self.main_frame,
            text=f"{self.config.app_name} 更新程序",
            font=("SimHei", 20, "bold")
        )
        title_label.pack(pady=(0, 25))
        
        version_label = ttk.Label(
            self.main_frame,
            text=f"当前版本: v{self.config.current_version}",
            font=("SimHei", 12)
        )
        version_label.pack(anchor=tk.W, pady=(0, 15))
        
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, pady=(10, 10))
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="正在检测更新中，请稍候...",
            font=("SimHei", 14),
            foreground="#165DFF"
        )
        self.status_label.pack(pady=(0, 5))
        
        self.loading_animation = LoadingAnimation(self.status_frame, width=120, height=30, color="#165DFF")
        self.loading_animation.pack(pady=(0, 10))
        
        self.sub_status_label = ttk.Label(
            self.status_frame,
            text="",
            font=("SimHei", 11),
            foreground="#666666"
        )
        self.sub_status_label.pack(pady=(0, 5))

        # ==================== 固定高度的 content_frame ====================
        self.content_frame = ttk.Frame(
            self.main_frame,
            height=self.CONTENT_HEIGHT
        )
        self.content_frame.pack(fill=tk.X, pady=15)
        self.content_frame.pack_propagate(False)

        self.note_text = tk.Text(
            self.content_frame,
            height=10,
            wrap=tk.WORD,
            font=("SimHei", 12),
            state=tk.DISABLED
        )
        self.note_text.pack(fill=tk.BOTH, expand=True)

        self.gallery_frame = ttk.Frame(self.content_frame)
        
        self.progress_var = tk.DoubleVar()
        self.btn_frame = ttk.Frame(self.main_frame)
        self.btn_frame.pack(pady=20)
        
        if self.auto_start_download:
            self.root.after(100, self._direct_start_download) 
        else:
            self.root.after(100, self._start_check_update)
        
        return True
    
    def _append_note_text(self, text):
        self.note_text.config(state=tk.NORMAL)
        self.note_text.delete(1.0, tk.END)
        
        self.note_text.tag_configure("large", font=("SimHei", 18, "bold"))
        self.note_text.tag_configure("medium", font=("SimHei", 16))
        self.note_text.tag_configure("normal", font=("SimHei", 14))
        
        formatted_note = self.update_manager._format_release_note(text)
        
        current_pos = "1.0"
        for line, font_size in formatted_note:
            if line:
                self.note_text.insert(current_pos, line + "\n", font_size)
            else:
                self.note_text.insert(current_pos, "\n")
            current_pos = self.note_text.index("end")
        
        self.note_text.config(state=tk.DISABLED)
        self.root.update()
    
    def _update_status(self, text, color="#165DFF", show_loading=False):
        self.status_label.config(text=text, foreground=color)
        if show_loading:
            self.loading_animation.start()
            self.loading_animation.pack(pady=(0, 10), before=self.sub_status_label)
        else:
            self.loading_animation.stop()
            self.loading_animation.pack_forget()
        self.root.update()
    
    def _update_sub_status(self, text=""):
        self.sub_status_label.config(text=text)
        self.root.update()
    
    def _clear_buttons(self):
        for widget in self.btn_frame.winfo_children():
            widget.destroy()
    
    def _start_check_update(self):
        def check_thread():
            update_info = self.update_manager.check_for_updates()
            
            def handle_result():
                if update_info.get('network_error'):
                    self._update_status("网络未连接", color="#F53F3F", show_loading=False)
                    self._append_note_text("请检查您的网络连接后重试。")
                    self._clear_buttons()
                    retry_btn = ttk.Button(
                        self.btn_frame,
                        text="重试",
                        command=self._start_check_update,
                        width=15
                    )
                    retry_btn.pack(side=tk.LEFT, padx=10)
                    exit_btn = ttk.Button(
                        self.btn_frame,
                        text="退出",
                        command=self.root.quit,
                        width=15
                    )
                    exit_btn.pack(side=tk.LEFT, padx=10)
                elif update_info.get('has_update'):
                    self._update_status(f"发现新版本 v{self.update_manager.latest_version}", color="#F53F3F", show_loading=False)
                    self._append_note_text(self.update_manager.release_note)
                    self._clear_buttons()
                    cancel_btn = ttk.Button(
                        self.btn_frame,
                        text="取消更新",
                        command=self.root.quit,
                        width=15
                    )
                    cancel_btn.pack(side=tk.LEFT, padx=10)
                    update_btn = ttk.Button(
                        self.btn_frame,
                        text="现在下载",
                        command=self._start_download,
                        width=15
                    )
                    update_btn.pack(side=tk.LEFT, padx=10)
                    if self.auto_start_download:
                        self.root.after(100, self._start_download)
                else:
                    self._update_status("当前已是最新版本", color="#00B42A", show_loading=False)
                    self._append_note_text("您的软件已经是最新版本，无需更新。")
                    self._clear_buttons()
                    confirm_btn = ttk.Button(
                        self.btn_frame,
                        text="确定",
                        command=self.root.quit,
                        width=20
                    )
                    confirm_btn.pack()
            
            self.root.after(0, handle_result)
        
        self._update_status("正在检测更新中，请稍候...", color="#165DFF", show_loading=True)
        threading.Thread(target=check_thread, daemon=True).start()
    
    def _start_download(self):
        self._clear_buttons()
        #禁用右上角×
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self._update_status("正在下载更新包...", color="#165DFF", show_loading=True)
        self._update_sub_status("正在获取安装包地址…")
        
        if self.progress_frame is not None:
            self.progress_frame.destroy()
        self.progress_frame = ttk.Frame(self.main_frame)
        self.progress_frame.pack(fill=tk.X, pady=(10, 5), before=self.btn_frame)
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(
            self.progress_frame,
            text="",
            font=("SimHei", 11)
        )
        self.progress_label.pack(pady=(5, 10))
        
        cancel_btn = ttk.Button(
            self.btn_frame,
            text="取消下载",
            command=self._on_cancel_download,
            width=15
        )
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        background_btn = ttk.Button(
            self.btn_frame,
            text="后台下载",
            command=self._on_background_download,
            width=15
        )
        background_btn.pack(side=tk.LEFT, padx=10)

        def start_download_thread():
            time.sleep(1.5)
            self.root.after(0, lambda: self._update_sub_status(""))
            
            self.note_text.pack_forget()
            if not self._setup_image_gallery():
                self.note_text.pack(fill=tk.BOTH, expand=True)
            
            def download_thread():
                success = self.update_manager.download_update(
                    progress_callback=self._update_download_progress
                )
                self.root.after(0, lambda: self._on_download_complete(success))
            
            self.update_manager.download_thread = threading.Thread(target=download_thread, daemon=True)
            self.update_manager.download_thread.start()
        
        threading.Thread(target=start_download_thread, daemon=True).start()

    def _direct_start_download(self):
        # 直接开始下载
        self._update_status("正在连接服务器...", color="#165DFF", show_loading=True)
        self._update_sub_status("正在获取安装包地址…")

        def prepare_and_download():
            success = self.update_manager.fetch_latest_release()

            def after_fetch():
                if not success or not self.update_manager.download_url:
                    self._update_status("获取更新信息失败", color="#F53F3F", show_loading=False)
                    return
            
                self._update_status("开始下载更新...", color="#165DFF", show_loading=True)
                self._start_download()

            self.root.after(0, after_fetch)

        threading.Thread(target=prepare_and_download, daemon=True).start()
    # ==================== 1. 加载图片（只存原图） ====================
    def _load_pictures(self):
        self.pictures_dir = os.path.join(
            self.update_manager.config.main_exe_dir,
            "file", "update", "pictures"
        )
        if not os.path.exists(self.pictures_dir):
            print(f"图片目录不存在: {self.pictures_dir}", file=sys.stderr)
            return False

        self.original_images = []
        for i in range(1, 4):
            pic_path = os.path.join(self.pictures_dir, f"pic{i}.jpg")
            if os.path.exists(pic_path):
                try:
                    img = Image.open(pic_path).convert("RGBA")
                    self.original_images.append(img)
                except Exception as e:
                    print(f"加载图片失败 {pic_path}: {e}", file=sys.stderr)
            else:
                print(f"图片文件不存在: {pic_path}", file=sys.stderr)

        if not self.original_images:
            return False
        self.image_index = 0
        return True

    # ==================== 2. 图片自适应缩放 ====================
    def _fit_image_to_box(self, img, max_w, max_h):
        w, h = img.size
        ratio = min(max_w / w, max_h / h, 1.0)
        new_size = (max(1, int(w * ratio)), max(1, int(h * ratio)))
        return img.resize(new_size, Image.LANCZOS)

    # ==================== 3. 圆角处理 ====================
    def _round_corners(self, img, radius=24):
        img = img.convert("RGBA")
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, img.size[0], img.size[1]), radius=radius, fill=255)
        img.putalpha(mask)
        return img

    # ==================== 4. 初始化画板（修复布局） ====================
    def _setup_image_gallery(self):
        if not PIL_AVAILABLE or not self._load_pictures():
            self._update_status("图片加载失败，使用文本说明", color="#F53F3F", show_loading=False)
            return False

        self.gallery_frame.configure(height=self.CONTENT_HEIGHT)
        self.gallery_frame.pack_propagate(False)

        # 关键：expand=False，不抢空间
        self.gallery_frame.pack(fill=tk.X, expand=False)

        self.gallery_canvas = tk.Canvas(
            self.gallery_frame,
            width=650,
            height=240,
            bg="#f8f9fa",
            highlightthickness=0
        )
        self.gallery_canvas.pack(fill=tk.BOTH, expand=True)

        self._show_image_with_fade(self.image_index)
        self.gallery_canvas.bind("<Button-1>", self._handle_canvas_click)

        self._start_auto_switch()
        return True

    # ==================== 5. 淡入动画显示（整合所有效果） ====================
    def _show_image_with_fade(self, index, steps=12, delay=20):
        if not self.original_images or not self.gallery_canvas:
            return

        self.gallery_canvas.delete("image")
        canvas_w = self.gallery_canvas.winfo_width() or 650
        canvas_h = self.gallery_canvas.winfo_height() or 240

        img = self.original_images[index]
        img = self._fit_image_to_box(img, canvas_w - 40, canvas_h - 40)
        img = self._round_corners(img, radius=24)

        def step_alpha(i=0):
            alpha = i / steps
            
            bg_color = (248, 249, 250)
            frame = Image.new("RGBA", img.size, (*bg_color, 255))
            
            blended = Image.blend(frame, img, alpha)
            
            photo = ImageTk.PhotoImage(blended)
            self.current_photo = photo
            
            x = (canvas_w - photo.width()) // 2
            y = (canvas_h - photo.height()) // 2
            
            self.gallery_canvas.create_image(x, y, image=photo, anchor=tk.NW, tags="image")

            if i < steps:
                self.root.after(delay, lambda: step_alpha(i + 1))

        step_alpha()

    # ==================== 6. 点击切换逻辑 ====================
    def _handle_canvas_click(self, event):
        if not self.gallery_canvas:
            return
        w = self.gallery_canvas.winfo_width()
        if event.x < w // 3:
            self._prev_image()
        elif event.x > w * 2 // 3:
            self._next_image()

    def _prev_image(self):
        if self.original_images:
            self.image_index = (self.image_index - 1) % len(self.original_images)
            self._show_image_with_fade(self.image_index)

    def _next_image(self):
        if self.original_images:
            self.image_index = (self.image_index + 1) % len(self.original_images)
            self._show_image_with_fade(self.image_index)

    def _start_auto_switch(self):
        if self.auto_switch_id:
            self.root.after_cancel(self.auto_switch_id)
        self.auto_switch_id = self.root.after(5000, self._auto_switch)

    def _auto_switch(self):
        self._next_image()
        self._start_auto_switch()
    
    def _update_download_progress(self, progress, downloaded_size, total_size):
        def update_gui():
            self.progress_var.set(progress)
            downloaded_mb = downloaded_size / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            self.progress_label.config(text=f"下载进度: {progress}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)")
            
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.title = f"Card Manager 更新下载中 {progress}%"
        
        self.root.after(0, update_gui)
    
    def _show_tray_icon(self):
        print("正在创建系统托盘图标...", file=sys.stderr)
        
        if not TRAY_AVAILABLE:
            print("系统托盘功能不可用：pystray库未安装", file=sys.stderr)
            return
        
        icon_path = None
        possible_paths = [
            os.path.join(os.path.dirname(sys.executable), 'assets/icon.ico'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets/icon.ico')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                icon_path = path
                print(f"找到图标文件: {path}", file=sys.stderr)
                break
        
        tray_image = None
        if not icon_path:
            print("未找到assets/icon.ico文件，使用默认图标", file=sys.stderr)
            try:
                image = Image.new('RGB', (64, 64), color=(0, 123, 255))
                draw = ImageDraw.Draw(image)
                draw.text((10, 20), '更新', fill=(255, 255, 255))
                tray_image = image
            except Exception as e:
                print(f"创建默认图标失败: {e}", file=sys.stderr)
                tray_image = None
        else:
            try:
                tray_image = Image.open(icon_path)
                print("图标文件加载成功", file=sys.stderr)
            except Exception as e:
                print(f"加载图标文件失败: {e}", file=sys.stderr)
                tray_image = None
        
        if not tray_image:
            print("无法创建托盘图标", file=sys.stderr)
            return
        
        def cancel_download_action(icon, item):
            print("用户从托盘取消下载", file=sys.stderr)
            self.update_manager.is_downloading = False
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None
            if hasattr(self, 'auto_switch_id') and self.auto_switch_id:
                self.root.after_cancel(self.auto_switch_id)
            if hasattr(self, 'gallery_frame'):
                self.gallery_frame.pack_forget()
            if hasattr(self, 'gallery_canvas') and self.gallery_canvas:
                self.gallery_canvas.destroy()
            temp_file = self.update_manager.update_file_path
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            self.root.quit()
        
        def exit_app_action(icon, item):
            print("用户从托盘退出程序", file=sys.stderr)
            self.update_manager.is_downloading = False
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None
            temp_file = self.update_manager.update_file_path
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            self.root.quit()
        
        self.tray_menu = pystray.Menu(
            item('打开下载窗口', lambda icon, item: self._restore_from_tray(), default=True),
            item('取消下载', cancel_download_action),
            item('退出', exit_app_action)
        )
        
        self.tray_icon = pystray.Icon(
            "card_update",
            tray_image,
            "Card Manager 更新",
            self.tray_menu
        )
        
        def run_tray():
            try:
                print("托盘图标线程已启动", file=sys.stderr)
                self.tray_icon.run()
            except Exception as e:
                print(f"托盘图标运行错误: {e}", file=sys.stderr)
        
        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()
        
        time.sleep(1)
        print("系统托盘图标已显示", file=sys.stderr)
    
    def _restore_from_tray(self):
        print("用户点击托盘图标，恢复窗口", file=sys.stderr)
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception as e:
            print(f"恢复窗口失败: {e}", file=sys.stderr)
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
    
    def _on_cancel_download(self):
        result = messagebox.askyesno(
            "取消下载",
            "您确定要取消下载安装包吗？取消后将删除已下载的临时文件。",
            parent=self.root
        )
        if not result:
            return
        
        print("用户触发取消下载，正在停止下载...", file=sys.stderr)
        self.update_manager.is_downloading = False
        self._update_status("正在停止下载并清理临时文件...", color="#F53F3F", show_loading=False)
        cancel_retry_count = 0
        MAX_CANCEL_WAIT = 60         

        def wait_for_cancel():
                nonlocal cancel_retry_count
                if (self.update_manager.download_thread and 
                    self.update_manager.download_thread.is_alive() and
                    cancel_retry_count < MAX_CANCEL_WAIT):
                    cancel_retry_count += 1
                    self.root.after(500, wait_for_cancel)   # 间隔 500ms，减轻 UI 负担
                else:
                    # 超时后即使线程仍在运行也强制退出（记录日志）
                    if cancel_retry_count >= MAX_CANCEL_WAIT:
                        print("警告：等待下载线程结束超时，强制退出", file=sys.stderr)
                    # 清理临时文件...
                    temp_file = self.update_manager.update_file_path
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception as e:
                            print(f"删除临时文件失败: {e}", file=sys.stderr)
                    info_file = self.update_manager.config.update_info_file
                    if os.path.exists(info_file):
                        try:
                            os.remove(info_file)
                        except Exception:
                            pass
                    if self.auto_switch_id:
                        self.root.after_cancel(self.auto_switch_id)
                    self.current_photo = None
                    if self.gallery_canvas:
                        self.gallery_canvas.destroy()
                        self.gallery_canvas = None
                    if self.gallery_frame:
                        self.gallery_frame.pack_forget()
                    print("取消下载完成，退出程序", file=sys.stderr)
                    self.root.quit()

        wait_for_cancel()
    
    def _on_background_download(self):
        self.root.withdraw()
        self._show_tray_icon()
        
        def check_download_complete():
            if not self.update_manager.is_downloading:
                if os.path.exists(self.update_manager.update_file_path):
                    if self.tray_icon:
                        self.tray_icon.stop()
                        self.tray_icon = None
                    self.root.deiconify()
                    self.root.after(0, lambda: self._on_download_complete(True))
                else:
                    if self.tray_icon:
                        self.tray_icon.stop()
                        self.tray_icon = None
                    self.root.deiconify()
                    self.root.after(0, lambda: self._on_download_complete(False))
            else:
                self.root.after(1000, check_download_complete)
        
        self.root.after(2000, check_download_complete)
    
    def _on_download_complete(self, success):
        #恢复右上角按钮
        self.root.protocol("WM_DELETE_WINDOW", self.root.quit)

        if self.auto_switch_id:
            self.root.after_cancel(self.auto_switch_id)
            self.auto_switch_id = None
        self.current_photo = None
        if self.gallery_canvas:
            self.gallery_canvas.destroy()
            self.gallery_canvas = None
        if self.gallery_frame:
            self.gallery_frame.pack_forget()
        
        if self.progress_frame is not None:
            self.progress_frame.pack_forget()
            self.progress_frame = None
        self._update_sub_status("")
        self._clear_buttons()
        
        if not success:
            self._update_status("下载失败，请检查网络后重试", color="#F53F3F", show_loading=False)
            retry_btn = ttk.Button(
                self.btn_frame,
                text="重试下载",
                command=self._start_download,
                width=15
            )
            retry_btn.pack(side=tk.LEFT, padx=10)
            
            exit_btn = ttk.Button(
                self.btn_frame,
                text="退出",
                command=self.root.quit,
                width=15
            )
            exit_btn.pack(side=tk.LEFT, padx=10)
            return
        
        self._update_status("下载完成，正在打开安装包...", color="#00B42A", show_loading=False)
        self.update_manager.open_install_package_and_exit()
    
    def run(self):
        if self.root is None:
            if not self.create_main_window():
                return 1
        
        self.root.mainloop()
        return 0

def main():
    # 1. 先创建完整的 ArgumentParser，并添加所有参数
    parser = argparse.ArgumentParser(description=f'{UpdateConfig().app_name} 更新程序')
    parser.add_argument('--check', action='store_true', help='检查更新')
    parser.add_argument('--download', action='store_true', help='下载更新')
    parser.add_argument('--install', action='store_true', help='打开已下载的安装包')
    parser.add_argument('--silent', action='store_true', help='静默模式')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--prompt', action='store_true', help='显示更新提示弹窗（主程序调用）')
    parser.add_argument('--force', action='store_true', help='强制显示弹窗（手动检查用）')
    parser.add_argument('--auto-start-download', action='store_true', help='启动GUI后自动开始下载更新（主程序调用专用）')
    
    args, _ = parser.parse_known_args()   # 只解析已知参数，未知的忽略

    # 2. 判断是否需要 GUI（即会创建窗口的模式）
    need_gui = (args.prompt or args.auto_start_download or
                (not (args.check or args.download or args.install)))

    if need_gui:
        if not check_single_instance():
            return 1

    # 3. 后续处理（创建配置、更新管理器等）
    config = UpdateConfig()
    update_manager = UpdateManager(config, silent=args.silent)

    # 4. 根据不同的参数模式执行相应功能
    if not args.check and not args.download and not args.install and not args.prompt:
        # 默认启动 GUI（无参数或仅 --auto-start-download）
        gui = StandaloneUpdateGUI(update_manager, auto_start_download=args.auto_start_download)
        if gui.create_main_window():
            single = get_single_instance()
            if single:
                single.set_window(gui.root)
            return gui.run()
        return 1

    if args.prompt:
        update_manager.show_update_prompt()
        return 0

    if args.check:
        update_info = update_manager.check_for_updates()
        print(json.dumps(update_info, ensure_ascii=False, indent=2))
        return 0 if update_info['has_update'] else 1

    if args.download:
        if update_manager.check_for_updates()['has_update']:
            if update_manager.download_update():
                print("下载成功")
                return 0
            else:
                print("下载失败")
                return 1
        else:
            print("没有可用更新")
            return 0

    if args.install:
        if not update_manager.update_file_path and not update_manager._check_existing_update_package():
            print("未找到已下载的安装包，请先执行下载")
            return 1
        update_manager.open_install_package_and_exit()
        return 0

    return 0

if __name__ == "__main__":
    sys.exit(main())