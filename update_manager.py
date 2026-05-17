#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新管理器：负责版本检测、后台下载、更新提示（简化版：下载后直接打开安装包）"""
import requests
import json
import os
import sys
import threading
import tempfile
import subprocess
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import time
import re

class UpdateChecker:
    def __init__(self, app):
        self.app = app  # 应用实例（用于访问设置、主窗口）
        self.current_version = self._get_version_from_setup()  # 从setup.py读取版本
        self.github_owner = "star-cat-pig"  # 统一GitHub仓库所有者
        self.github_repo = "ancient-chinese-cards"  # 统一GitHub仓库名
        self.download_url = None  # 最新版本下载地址
        self.latest_version = None  # 最新版本号
        self.release_note = ""  # 版本更新说明
        self.download_thread = None  # 后台下载线程
        self.is_downloading = False  # 下载状态
        self.temp_dir = tempfile.gettempdir()  # 临时下载目录
        self.download_progress = 0  # 下载进度（百分比）
        self.download_size = 0  # 已下载大小
        self.total_size = 0  # 总大小
        self.progress_window = None  # 进度窗口
        self.progress_var = None  # 进度条变量
        self.progress_label = None  # 进度标签
        self.skip_update = False  # 是否跳过本次更新
        self.retry_count = 0  # 下载重试次数
        self.max_retries = 3  # 最大重试次数
        self.update_file_path = None  # 下载的更新包路径
        
        # 从设置中恢复已下载的更新包路径
        if hasattr(self.app, 'settings_manager'):
            self.update_file_path = self.app.settings_manager.get_setting("update", "downloaded_path", "")
            # 检查保存的路径是否仍然有效
            if self.update_file_path and not os.path.exists(self.update_file_path):
                self.update_file_path = None
                # 清除无效的路径记录
                self.app.settings_manager.set_setting("update", "downloaded_path", "")
                self.app.settings_manager.save_preferences()

    def _get_version_from_setup(self):
        """获取当前版本号 - 修复打包后版本读取问题"""
        return "1.4.0"

    def _center_window(self, window, parent_window=None):
        """通用窗口居中方法"""
        if parent_window is None and hasattr(self.app, 'root'):
            parent_window = self.app.root
        window.update_idletasks()
        window_width = window.winfo_width()
        window_height = window.winfo_height()
        if parent_window and parent_window.winfo_exists():
            parent_x = parent_window.winfo_x()
            parent_y = parent_window.winfo_y()
            parent_width = parent_window.winfo_width()
            parent_height = parent_window.winfo_height()
            x = parent_x + (parent_width - window_width) // 2
            y = parent_y + (parent_height - window_height) // 2
        else:
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
        window.geometry(f"+{x}+{y}")

    def _normalize_version(self, ver):
        """
        将版本号归一化为三位数格式，例如：
        "1.4" -> "1.4.0"
        "v1.4" -> "1.4.0"
        "1.4.0" -> "1.4.0"
        """
        ver = str(ver).strip().lstrip("v")
        parts = ver.split(".")
        # 补齐到三位
        while len(parts) < 3:
            parts.append("0")
        return ".".join(parts[:3])  # 只取前三位

    def _compare_version(self, v1, v2):
        """
        版本号对比：1-v1>v2，0-相等，-1-v1<v2
        内部先归一化，确保 "1.4" 和 "1.4.0" 被判断为相等
        """
        try:
            v1_norm = self._normalize_version(v1)
            v2_norm = self._normalize_version(v2)
            v1_parts = list(map(int, v1_norm.split(".")))
            v2_parts = list(map(int, v2_norm.split(".")))
            for a, b in zip(v1_parts, v2_parts):
                if a > b:
                    return 1
                elif a < b:
                    return -1
            return 0
        except Exception as e:
            print(f"版本号对比失败: {e}")
            return 0

    def get_current_version(self):
        """获取当前软件版本"""
        return self.current_version

    def _get_requests_session(self):
        """获取配置了代理的requests会话"""
        session = requests.Session()
        
        # 尝试从系统环境变量获取代理设置
        proxy_env = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        if proxy_env:
            session.proxies = {
                'http': proxy_env,
                'https': proxy_env
            }
        
        return session

    def fetch_latest_release(self):
        """从GitHub获取最新release信息（优先API，失败降级+统一版本格式）"""
        api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/releases/latest"
        try:
            session = self._get_requests_session()
            response = session.get(api_url, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                # 统一格式：移除v前缀并补齐为三位数
                raw_tag = release_data["tag_name"].strip()
                self.latest_version = self._normalize_version(raw_tag)
                self.release_note = release_data["body"]
                
                # ========== 核心修改：Windows平台exe文件选择逻辑 ==========
                if sys.platform == "win32":
                    # 筛选所有有效exe安装包（.exe结尾，排除.zip文件）
                    valid_exes = []
                    for asset in release_data["assets"]:
                        if asset["name"].endswith(".exe") and not asset["name"].endswith(".zip"):
                            valid_exes.append({
                                "name": asset["name"],
                                "url": asset["browser_download_url"]
                            })
                    
                    # 按规则选择下载链接
                    if len(valid_exes) == 1:
                        # 只有一个exe，直接使用
                        self.download_url = valid_exes[0]["url"]
                    elif len(valid_exes) > 1:
                        # 多个exe，优先选择名称包含"cards"的（不区分大小写）
                        cards_exe = None
                        for exe in valid_exes:
                            if "cards" in exe["name"].lower():
                                cards_exe = exe
                                break
                        if cards_exe:
                            self.download_url = cards_exe["url"]
                        else:
                            # 没有找到cards.exe，提示用户手动选择
                            self._show_multi_exe_choice(valid_exes)
                # ======================================================
                elif sys.platform == "darwin":
                    # Mac平台：匹配.dmg文件
                    for asset in release_data["assets"]:
                        if asset["name"].endswith(".dmg"):
                            self.download_url = asset["browser_download_url"]
                elif sys.platform.startswith("linux"):
                    # Linux平台：匹配.tar.gz文件
                    for asset in release_data["assets"]:
                        if asset["name"].endswith(".tar.gz"):
                            self.download_url = asset["browser_download_url"]
                return True
        except requests.exceptions.ConnectionError:
            if hasattr(self.app, 'root') and self.app.root:
                self.app.root.after(0, lambda: messagebox.showinfo(
                    "网络提示",
                    "检查更新时网络连接失败，请检查网络设置后手动检查更新。"
                ))
            return False
        except Exception as e:
            print(f"API获取失败，降级解析页面: {e}")
            # 降级方案：强制匹配exe，不下载zip
            releases_page = f"https://github.com/{self.github_owner}/{self.github_repo}/releases"
            try:
                response = requests.get(releases_page, timeout=10)
                if response.status_code == 200:
                    version_match = re.search(r"releases/tag/v?(\d+\.\d+(?:\.\d+)?)", response.text)
                    if version_match:
                        raw_tag = version_match.group(1)
                        self.latest_version = self._normalize_version(raw_tag)
                        self.release_note = "请访问GitHub查看详细更新说明"
                        
                        # ========== 降级方案也应用相同选择逻辑 ==========
                        if sys.platform == "win32":
                            # 降级时优先拼接cards.exe（兼容已知命名）
                            self.download_url = f"https://github.com/{self.github_owner}/{self.github_repo}/releases/download/v{raw_tag}/cards.exe"
                        elif sys.platform == "darwin":
                            self.download_url = f"https://github.com/{self.github_owner}/{self.github_repo}/releases/download/v{raw_tag}/ancient-chinese-cards-mac.dmg"
                        elif sys.platform.startswith("linux"):
                            self.download_url = f"https://github.com/{self.github_owner}/{self.github_repo}/releases/download/v{raw_tag}/ancient-chinese-cards-linux.tar.gz"
                        return True
            except Exception as e2:
                print(f"页面解析失败: {e2}")
        return False

    def _show_multi_exe_choice(self, valid_exes):
        """多个exe文件时，显示选择对话框让用户手动选择"""
        if not hasattr(self.app, 'root') or not self.app.root:
            return
        
        choice_window = tk.Toplevel(self.app.root)
        choice_window.title("选择更新包")
        choice_window.geometry("400x300")
        choice_window.transient(self.app.root)
        choice_window.grab_set()
        self._center_window(choice_window)
        
        # 图标设置
        if hasattr(self.app, 'icon_path') and os.path.exists(self.app.icon_path):
            try:
                if self.app.icon_path.endswith(".ico"):
                    choice_window.iconbitmap(self.app.icon_path)
                else:
                    icon_image = tk.PhotoImage(file=self.app.icon_path)
                    choice_window.iconphoto(True, icon_image)
                    choice_window.icon_image = icon_image
            except:
                pass
        
        # 提示标签
        label = tk.Label(choice_window, text="发现多个Windows更新包，请选择一个：", font=("SimHei", 11))
        label.pack(pady=15)
        
        # 列表框显示可选exe
        listbox = tk.Listbox(choice_window, font=("SimHei", 10), height=6)
        for i, exe in enumerate(valid_exes):
            listbox.insert(i, exe["name"])
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        listbox.select_set(0)  # 默认选中第一个
        
        # 确认按钮
        def on_confirm():
            selected_idx = listbox.curselection()
            if selected_idx:
                self.download_url = valid_exes[selected_idx[0]]["url"]
                choice_window.destroy()
        
        confirm_btn = ttk.Button(choice_window, text="确认下载", command=on_confirm)
        confirm_btn.pack(pady=15)

    def is_update_available(self):
        """检查是否有更新（统一版本格式，相同版本不提示）"""
        if not self.fetch_latest_release():
            return False
        # 归一化当前版本和远程版本
        current_norm = self._normalize_version(self.current_version)
        latest_norm = self._normalize_version(self.latest_version)
        ignored_norm = self._normalize_version(self.app.settings_manager.get_setting("update", "ignore_version", ""))
        
        # 如果当前版本已经等于最新版本，则没有更新
        if current_norm == latest_norm:
            print(f"当前版本 {current_norm} 已是最新，无需更新")
            return False
        
        # 如果有忽略版本且忽略版本等于最新版本（且当前版本低于忽略版本），则也跳过
        if ignored_norm and self._compare_version(latest_norm, ignored_norm) == 0:
            print(f"已忽略版本 {ignored_norm}，当前远程最新版本 {latest_norm}，跳过更新提示")
            return False
        
        # 否则检查最新版本是否大于当前版本
        return self._compare_version(current_norm, latest_norm) == -1

    def _update_progress_gui(self):
        """更新进度条GUI显示"""
        if self.progress_window and self.progress_var and self.progress_label:
            percentage = int((self.download_size / self.total_size) * 100) if self.total_size > 0 else 0
            self.progress_var.set(percentage)
            downloaded_mb = self.download_size / (1024 * 1024)
            total_mb = self.total_size / (1024 * 1024)
            self.progress_label.config(text=f"下载进度: {percentage}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)")
            if self.is_downloading:
                self.progress_window.after(100, self._update_progress_gui)

    def _show_download_progress(self):
        """显示下载进度窗口"""
        if self.progress_window:
            return
        self.progress_window = tk.Toplevel(self.app.root)
        self.progress_window.title("下载更新中")
        self.progress_window.geometry("400x200")
        self.progress_window.transient(self.app.root)
        self.progress_window.grab_set()
        # 图标设置（保持原逻辑）
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.progress_window.iconbitmap(icon_path)
        elif hasattr(self.app, 'icon_path') and os.path.exists(self.app.icon_path):
            self.progress_window.iconbitmap(self.app.icon_path)
        self._center_window(self.progress_window)
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(self.progress_window, variable=self.progress_var, maximum=100, length=350)
        progress_bar.pack(pady=20)
        self.progress_label = tk.Label(self.progress_window, text="准备下载...", font=("SimHei", 10))
        self.progress_label.pack(pady=10)
        
        # 按钮框架
        buttons_frame = ttk.Frame(self.progress_window)
        buttons_frame.pack(pady=5)
        
        # 后台下载按钮
        background_btn = ttk.Button(buttons_frame, text="后台下载", command=self._background_download)
        background_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 取消下载按钮
        cancel_btn = ttk.Button(buttons_frame, text="取消下载", command=self._cancel_download)
        cancel_btn.pack(side=tk.LEFT)
        self._update_progress_gui()

    def _cancel_download(self):
        """取消下载"""
        self.is_downloading = False
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None
        messagebox.showinfo("提示", "下载已取消")
    
    def _background_download(self):
        """后台下载"""
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None
        messagebox.showinfo("提示", "更新包将在后台继续下载，完成后会通知您")
    
    def _check_existing_update_package(self):
        """检查是否已存在完整的更新包"""
        if not self.download_url or not isinstance(self.download_url, str):
            print("下载链接为空或无效，跳过更新包检查")
            return False
        
        filename = os.path.basename(self.download_url)
        self.update_file_path = os.path.join(self.temp_dir, filename)
        
        if not os.path.exists(self.update_file_path):
            return False
        
        # 获取文件大小
        try:
            file_size = os.path.getsize(self.update_file_path)
            
            if self.total_size > 0:
                if file_size == self.total_size:
                    print(f"发现完整的更新包，大小: {file_size} 字节")
                    return True
                else:
                    print(f"更新包不完整，期望大小: {self.total_size}，实际大小: {file_size}")
                    os.remove(self.update_file_path)
                    return False
            
            # 如果未知总大小，尝试从服务器获取
            session = self._get_requests_session()
            try:
                response = session.head(self.download_url, timeout=10)
                response.raise_for_status()
            except Exception as e:
                print(f"获取文件大小失败: {e}")
                return True  # 降级处理：假设文件完整
            
            if response.status_code == 200:
                content_length = response.headers.get("content-length")
                if content_length:
                    self.total_size = int(content_length)
                    if file_size == self.total_size:
                        print(f"发现完整的更新包，大小: {file_size} 字节")
                        return True
                    else:
                        print(f"更新包不完整，期望大小: {self.total_size}，实际大小: {file_size}")
                        os.remove(self.update_file_path)
            return False
        except Exception as e:
            print(f"检查更新包完整性失败: {e}")
            return False

    def download_update_in_background(self):
        """后台下载更新（不阻塞主线程）"""
        if not self.download_url:
            messagebox.showerror("错误", "未找到对应平台的更新包（仅支持exe/dmg/tar.gz）")
            return
        
        # 前置校验：Windows必须是exe
        if sys.platform == "win32" and not self.download_url.endswith(".exe"):
            messagebox.showerror("错误", "下载的更新包不是Windows可执行文件（.exe），无法更新")
            return
        
        # 检查是否已有完整的更新包
        if self._check_existing_update_package():
            if self.progress_window:
                self.app.root.after(0, self.progress_window.destroy)
                self.progress_window = None
            self.app.root.after(0, self.show_restart_prompt)
            return
        
        self.is_downloading = True
        self.download_progress = 0
        self.download_size = 0
        self.total_size = 0
        
        if hasattr(self.app, 'root') and self.app.root:
            self.app.root.after(0, self._show_download_progress)
        
        filename = os.path.basename(self.download_url)
        self.update_file_path = os.path.join(self.temp_dir, filename)
        
        # 删除可能存在的不完整文件
        if os.path.exists(self.update_file_path):
            try:
                os.remove(self.update_file_path)
                print(f"删除不完整的更新包: {self.update_file_path}")
            except Exception as e:
                print(f"删除不完整文件失败: {e}")
        
        self.retry_count = 0
        
        while self.retry_count < self.max_retries:
            try:
                session = self._get_requests_session()
                response = session.get(self.download_url, stream=True, timeout=120)
                
                if response.status_code != 200:
                    raise requests.exceptions.HTTPError(f"HTTP错误状态码: {response.status_code}")
                
                self.total_size = int(response.headers.get("content-length", 0))
                self.download_size = 0
                
                with open(self.update_file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not self.is_downloading:
                            break
                        if chunk:
                            f.write(chunk)
                            self.download_size += len(chunk)
                
                if not self.is_downloading:
                    # 用户取消下载
                    if os.path.exists(self.update_file_path):
                        os.remove(self.update_file_path)
                    break
                
                # 校验文件大小
                if os.path.exists(self.update_file_path):
                    file_size = os.path.getsize(self.update_file_path)
                    if self.total_size > 0 and file_size == self.total_size:
                        print(f"更新包下载完成，大小: {file_size} 字节")
                        if self.progress_window:
                            self.app.root.after(0, self.progress_window.destroy)
                            self.progress_window = None
                        self.app.root.after(0, self.show_restart_prompt)
                        # 保存下载路径到设置
                        if hasattr(self.app, 'settings_manager'):
                            self.app.settings_manager.set_setting("update", "downloaded_path", self.update_file_path)
                            self.app.settings_manager.save_preferences()
                        return
                    else:
                        print(f"更新包下载不完整，期望大小: {self.total_size}，实际大小: {file_size}")
                        self.retry_count += 1
                        if self.retry_count < self.max_retries:
                            print(f"第 {self.retry_count} 次重试下载...")
                            os.remove(self.update_file_path)
                            continue
                        else:
                            raise Exception(f"更新包下载不完整，已重试 {self.max_retries} 次")
                else:
                    raise Exception("更新包文件不存在")
                    
            except requests.exceptions.ConnectionError:
                self.retry_count += 1
                if self.retry_count < self.max_retries:
                    print(f"网络连接失败，第 {self.retry_count} 次重试...")
                    time.sleep(2)
                else:
                    self.is_downloading = False
                    if self.progress_window:
                        self.app.root.after(0, self.progress_window.destroy)
                        self.progress_window = None
                    self.app.root.after(0, lambda: messagebox.showerror(
                        "网络错误", 
                        f"下载过程中网络连接失败，已重试 {self.max_retries} 次，请检查网络设置后重试。"
                    ))
                    break
                    
            except requests.exceptions.Timeout:
                self.retry_count += 1
                if self.retry_count < self.max_retries:
                    print(f"下载超时，第 {self.retry_count} 次重试...")
                    time.sleep(2)
                else:
                    self.is_downloading = False
                    if self.progress_window:
                        self.app.root.after(0, self.progress_window.destroy)
                        self.progress_window = None
                    self.app.root.after(0, lambda: messagebox.showerror(
                        "下载超时", 
                        f"更新包下载超时，已重试 {self.max_retries} 次，请检查网络带宽或稍后重试。"
                    ))
                    break
                    
            except requests.exceptions.HTTPError as e:
                self.is_downloading = False
                if self.progress_window:
                    self.app.root.after(0, self.progress_window.destroy)
                    self.progress_window = None
                self.app.root.after(0, lambda: messagebox.showerror(
                    "下载失败", 
                    f"链接无效（状态码：{e.response.status_code if hasattr(e, 'response') else '未知'}），请联系开发者确认更新包地址"
                ))
                break
                
            except PermissionError:
                self.is_downloading = False
                if self.progress_window:
                    self.app.root.after(0, self.progress_window.destroy)
                    self.progress_window = None
                self.app.root.after(0, lambda: messagebox.showerror(
                    "权限不足", 
                    "无法写入临时目录，请以管理员身份运行软件"
                ))
                break
                
            except Exception as e:
                self.retry_count += 1
                if self.retry_count < self.max_retries:
                    print(f"下载出错: {e}，第 {self.retry_count} 次重试...")
                    time.sleep(2)
                else:
                    self.is_downloading = False
                    if self.progress_window:
                        self.app.root.after(0, self.progress_window.destroy)
                        self.progress_window = None
                    self.app.root.after(0, lambda: messagebox.showerror(
                        "下载失败", 
                        f"更新包下载出错: {str(e)}，已重试 {self.max_retries} 次"
                    ))
                    break
        
        if self.is_downloading:
            self.is_downloading = False
        
        # 如果下载失败且文件存在，删除不完整文件
        if os.path.exists(self.update_file_path):
            try:
                file_size = os.path.getsize(self.update_file_path)
                if self.total_size > 0 and file_size != self.total_size:
                    os.remove(self.update_file_path)
                    print(f"删除不完整的更新包: {self.update_file_path}")
            except Exception as e:
                print(f"清理不完整文件失败: {e}")

    def start_background_download(self):
        """启动后台下载线程"""
        if not self.is_downloading and self.download_url:
            self.download_thread = threading.Thread(target=self.download_update_in_background, daemon=True)
            self.download_thread.start()

    def show_update_prompt(self, force_show=False):
        """显示更新提示窗口（修复勾选状态记忆）
        
        Args:
            force_show: 是否强制显示，True时忽略版本检查
        """
        ignored_version = self.app.settings_manager.get_setting("update", "ignore_version", "").lstrip("v")
        current_latest_version = self.latest_version  # 已经是归一化后的三位数
        
        # 核心修复：根据已忽略版本自动同步勾选状态
        ignore_var = tk.BooleanVar(value=(ignored_version == current_latest_version))
        
        # 非强制模式下，已忽略当前版本且无新版本，直接返回
        if not force_show and ignored_version and self._compare_version(current_latest_version, ignored_version) != 1:
            return
        
        # 检查是否已有完整的更新包
        if self._check_existing_update_package():
            self.show_restart_prompt()
            return
        
        prompt_window = tk.Toplevel(self.app.root)
        prompt_window.title(f"发现更新 v{self.latest_version}")
        prompt_window.geometry("700x700")
        prompt_window.transient(self.app.root)
        prompt_window.grab_set()
        # 图标设置
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.ico")
        if os.path.exists(icon_path):
            prompt_window.iconbitmap(icon_path)
        elif hasattr(self.app, 'icon_path') and os.path.exists(self.app.icon_path):
            prompt_window.iconbitmap(self.app.icon_path)
        self._center_window(prompt_window)
        # 添加更新推荐文字
        welcome_label = ttk.Label(prompt_window, 
                                 text="亲爱的用户，为了改进软件体验，我们带来了最新的版本。我们建议您及时更新，以享受最新的体验！",
                                 font=("SimHei", 14),
                                 foreground="#2c3e50",
                                 justify=tk.LEFT,
                                 wraplength=650)
        welcome_label.pack(pady=(10, 5))
        
        # 版本更新说明
        note_text = tk.Text(prompt_window, font=("SimHei", 16))
        note_text.insert(tk.END, self.release_note or "本次更新优化了多项功能，提升稳定性和用户体验")
        note_text.config(state=tk.DISABLED, wrap=tk.WORD)
        note_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        ignore_check = ttk.Checkbutton(prompt_window, text="不要再提醒我", variable=ignore_var)
        ignore_check.pack(anchor=tk.W, padx=10, pady=5)
        btn_frame = ttk.Frame(prompt_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 取消按钮（忽略本次更新）
        cancel_btn = ttk.Button(btn_frame, text="取消", command=lambda: self.on_update_cancel(prompt_window, ignore_var))
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # 立即更新按钮
        update_btn = ttk.Button(btn_frame, text="立即更新", command=lambda: self.on_update_confirm(prompt_window, ignore_var))
        update_btn.pack(side=tk.RIGHT, padx=5)
        
        # 绑定窗口关闭事件
        prompt_window.protocol("WM_DELETE_WINDOW", lambda: self.on_update_cancel(prompt_window, ignore_var))

    def on_update_confirm(self, prompt_window, ignore_var):
        """用户确认更新"""
        prompt_window.destroy()
        if ignore_var.get():
            # 保存忽略版本时统一格式（移除v前缀）
            self.app.settings_manager.set_setting("update", "ignore_version", self.latest_version)
            self.app.settings_manager.save_preferences()
            print(f"已保存忽略版本设置: {self.latest_version}")
        else:
            # 用户取消选择"不要再提醒我"，清除忽略版本设置
            current_ignored = self.app.settings_manager.get_setting("update", "ignore_version", "")
            if current_ignored == self.latest_version:
                self.app.settings_manager.set_setting("update", "ignore_version", "")
                self.app.settings_manager.save_preferences()
                print(f"已清除忽略版本设置: {self.latest_version}")
        self.skip_update = False
        self.start_background_download()
    
    def on_update_later(self, prompt_window):
        """用户选择稍后更新"""
        if prompt_window:
            prompt_window.destroy()
        self.skip_update = False
        # 保存稍后更新标记
        if hasattr(self.app, 'settings_manager'):
            self.app.settings_manager.set_setting("update", "pending_update", self.latest_version)
            self.app.settings_manager.save_preferences()
            print(f"已保存稍后更新标记: {self.latest_version}")
    
    def on_update_cancel(self, prompt_window, ignore_var):
        """用户取消更新"""
        prompt_window.destroy()
        if ignore_var.get():
            # 保存忽略版本时统一格式（移除v前缀）
            self.app.settings_manager.set_setting("update", "ignore_version", self.latest_version)
            self.app.settings_manager.save_preferences()
            print(f"已保存忽略版本设置: {self.latest_version}")
        else:
            # 用户取消选择"不要再提醒我"，清除忽略版本设置
            current_ignored = self.app.settings_manager.get_setting("update", "ignore_version", "")
            if current_ignored == self.latest_version:
                self.app.settings_manager.set_setting("update", "ignore_version", "")
                self.app.settings_manager.save_preferences()
                print(f"已清除忽略版本设置: {self.latest_version}")
        self.skip_update = True
    
    def on_app_exit(self):
        """程序退出时的处理"""
        # 重新读取设置（避免内存中值不一致）
        pending_version = ""
        if hasattr(self.app, 'settings_manager'):
            pending_version = self.app.settings_manager.get_setting("update", "pending_update", "").strip()
        
        # 补全判断条件：确保所有条件都满足才弹窗
        has_valid_update = (
            pending_version  # 有稍后更新标记
            and not self.skip_update  # 未跳过
            and self.update_file_path  # 有更新包路径
            and os.path.exists(self.update_file_path)  # 更新包存在
            and os.path.getsize(self.update_file_path) > 1024  # 确保文件不为空（大于1KB）
        )
        
        if has_valid_update:
            # 询问用户是否更新
            result = messagebox.askyesno("更新提醒", f"有新版本 v{pending_version} 可用，是否现在打开安装程序？")
            if result:
                # 清除稍后更新标记
                self.app.settings_manager.set_setting("update", "pending_update", "")
                self.app.settings_manager.save_preferences()
                # 直接打开安装包
                if sys.platform == "win32":
                    os.startfile(self.update_file_path)
                else:
                    subprocess.Popen([self.update_file_path])
                # 等待一下确保安装包启动
                time.sleep(0.5)
        
        # 正常退出程序（确保销毁窗口）
        if hasattr(self.app, 'root') and self.app.root.winfo_exists():
            self.app.root.destroy()

    def show_restart_prompt(self):
        """下载完成，启动安装包"""
        if not self.update_file_path or not os.path.exists(self.update_file_path):
            return
        
        result = messagebox.askyesno(
            "更新完成", 
            f"更新包已下载完成！\n是否立即打开安装程序？（v{self.latest_version}）\n\n建议：安装前先关闭当前程序"
        )
        
        if result:
            if sys.platform == "win32":
                os.startfile(self.update_file_path)
            else:
                subprocess.Popen([self.update_file_path])
            # 延迟退出，确保安装包启动
            self.app.root.after(1000, self.app.root.destroy)
        else:
            # 用户选择稍后更新
            self.on_update_later(None)

    def check_update_manually(self):
        """手动检查更新（强制弹窗，无视跳过标记）"""
        print("手动触发更新检查...")
        # 核心：强制清空版本缓存，不依赖 is_update_available（避免被忽略版本拦截）
        self.latest_version = None
        self.download_url = None
        
        # 1. 直接获取最新版本信息（不经过 is_update_available 的忽略判断）
        if self.fetch_latest_release():
            # 归一化当前版本和远程版本
            current_norm = self._normalize_version(self.current_version)
            latest_norm = self._normalize_version(self.latest_version)
            
            # 2. 手动对比版本：只要最新版本 > 当前版本，就强制弹窗
            if self._compare_version(current_norm, latest_norm) == -1:
                # 强制显示更新提示框，传入force_show=True确保绕过忽略版本检查
                self.show_update_prompt(force_show=True)
            else:
                # 版本相等或更低时显示无更新
                messagebox.showinfo("无更新", f"当前已是最新版本（v{self.current_version}）！")
        else:
            messagebox.showwarning("检测失败", "无法获取最新版本信息，请检查网络连接后重试。")