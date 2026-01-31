#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新管理器：负责版本检测、后台下载、更新提示（编码修复版+版本对比修复）"""
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
        self.update_file_path = None  # 下载后的文件路径
        self.download_progress = 0  # 下载进度（百分比）
        self.download_size = 0  # 已下载大小
        self.total_size = 0  # 总大小
        self.progress_window = None  # 进度窗口
        self.progress_var = None  # 进度条变量
        self.progress_label = None  # 进度标签

    def _get_version_from_setup(self):
        """获取当前版本号 - 修复打包后版本读取问题"""
        return "1.2"

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

    def _compare_version(self, v1, v2):
        """版本号对比：1-v1>v2，0-相等，-1-v1<v2"""
        try:
            v1_parts = list(map(int, v1.split(".")))
            v2_parts = list(map(int, v2.split(".")))
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
            print(f"版本号对比失败: {e}")
            return 0

    def get_current_version(self):
        """获取当前软件版本"""
        return self.current_version

    def fetch_latest_release(self):
        """从GitHub获取最新release信息（优先API，失败降级+统一版本格式）"""
        api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/releases/latest"
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                # 统一格式：移除v前缀
                self.latest_version = release_data["tag_name"].strip().lstrip("v")
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
                    version_match = re.search(r"releases/tag/v?(\d+\.\d+\.\d+)", response.text)
                    if version_match:
                        # 统一格式：移除v前缀
                        self.latest_version = version_match.group(1).lstrip("v")
                        self.release_note = "请访问GitHub查看详细更新说明"
                        
                        # ========== 降级方案也应用相同选择逻辑 ==========
                        if sys.platform == "win32":
                            # 降级时优先拼接cards.exe（兼容已知命名）
                            self.download_url = f"https://github.com/{self.github_owner}/{self.github_repo}/releases/download/v{self.latest_version}/cards.exe"
                        elif sys.platform == "darwin":
                            self.download_url = f"https://github.com/{self.github_owner}/{self.github_repo}/releases/download/v{self.latest_version}/ancient-chinese-cards-mac.dmg"
                        elif sys.platform.startswith("linux"):
                            self.download_url = f"https://github.com/{self.github_owner}/{self.github_repo}/releases/download/v{self.latest_version}/ancient-chinese-cards-linux.tar.gz"
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
        """检查是否有更新（修复参数顺序+兼容已忽略版本）"""
        if not self.fetch_latest_release():
            return False
        ignored_version = self.app.settings_manager.get_setting("update", "ignore_version", "").lstrip("v")  # 统一格式
        current_version = self.current_version.lstrip("v")  # 统一格式
        latest_version = self.latest_version.lstrip("v")  # 统一格式
        if not ignored_version:
            # 修复：参数顺序改为（本地版本，远程版本），返回-1表示本地版本更低
            return self._compare_version(current_version, latest_version) == -1
        else:
            latest_vs_ignored = self._compare_version(latest_version, ignored_version)
            if latest_vs_ignored == 1:
                return True
            else:
                print(f"已忽略版本 {ignored_version}，当前远程最新版本 {latest_version}，跳过更新提示")
                return False

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
        cancel_btn = ttk.Button(self.progress_window, text="取消下载", command=self._cancel_download)
        cancel_btn.pack(pady=5)
        self._update_progress_gui()

    def _cancel_download(self):
        """取消下载"""
        self.is_downloading = False
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None
        messagebox.showinfo("提示", "下载已取消")

    def download_update_in_background(self):
        """后台下载更新（不阻塞主线程）"""
        if not self.download_url:
            messagebox.showerror("错误", "未找到对应平台的更新包（仅支持exe/dmg/tar.gz）")
            return
        # 前置校验：Windows必须是exe
        if sys.platform == "win32" and not self.download_url.endswith(".exe"):
            messagebox.showerror("错误", "下载的更新包不是Windows可执行文件（.exe），无法更新")
            return
        self.is_downloading = True
        self.download_progress = 0
        self.download_size = 0
        self.total_size = 0
        if hasattr(self.app, 'root') and self.app.root:
            self.app.root.after(0, self._show_download_progress)
        filename = os.path.basename(self.download_url)
        self.update_file_path = os.path.join(self.temp_dir, filename)
        try:
            # 延长下载超时时间到120秒（避免大文件超时）
            response = requests.get(self.download_url, stream=True, timeout=120)
            self.total_size = int(response.headers.get("content-length", 0))
            self.download_size = 0
            with open(self.update_file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_downloading:
                        break
                    if chunk:
                        f.write(chunk)
                        self.download_size += len(chunk)
            if self.is_downloading and os.path.exists(self.update_file_path):
                # 校验文件大小
                if self.total_size > 0 and os.path.getsize(self.update_file_path) < self.total_size:
                    messagebox.showerror("下载失败", "更新包下载不完整，请重试")
                    os.remove(self.update_file_path)
                    return
                if self.progress_window:
                    self.app.root.after(0, self.progress_window.destroy)
                    self.progress_window = None
                self.show_restart_prompt()
            elif not self.is_downloading and os.path.exists(self.update_file_path):
                os.remove(self.update_file_path)
        except requests.exceptions.ConnectionError:
            self.is_downloading = False
            if self.progress_window:
                self.app.root.after(0, self.progress_window.destroy)
                self.progress_window = None
            messagebox.showerror("网络错误", "下载过程中网络连接失败，请检查网络设置后重试")
        except requests.exceptions.Timeout:
            self.is_downloading = False
            if self.progress_window:
                self.app.root.after(0, self.progress_window.destroy)
                self.progress_window = None
            messagebox.showerror("下载超时", "更新包下载超时，请检查网络带宽或稍后重试")
        except requests.exceptions.HTTPError as e:
            self.is_downloading = False
            if self.progress_window:
                self.app.root.after(0, self.progress_window.destroy)
                self.progress_window = None
            messagebox.showerror("下载失败", f"链接无效（状态码：{e.response.status_code}），请联系开发者确认更新包地址")
        except PermissionError:
            self.is_downloading = False
            if self.progress_window:
                self.app.root.after(0, self.progress_window.destroy)
                self.progress_window = None
            messagebox.showerror("权限不足", "无法写入临时目录，请以管理员身份运行软件")
        except Exception as e:
            self.is_downloading = False
            if self.progress_window:
                self.app.root.after(0, self.progress_window.destroy)
                self.progress_window = None
            messagebox.showerror("下载失败", f"更新包下载出错: {str(e)}")
        finally:
            self.is_downloading = False

    def start_background_download(self):
        """启动后台下载线程"""
        if not self.is_downloading and self.download_url:
            self.download_thread = threading.Thread(target=self.download_update_in_background, daemon=True)
            self.download_thread.start()

    def show_update_prompt(self):
        """显示更新提示窗口"""
        ignored_version = self.app.settings_manager.get_setting("update", "ignore_version", "").lstrip("v")
        if ignored_version and self._compare_version(self.latest_version.lstrip("v"), ignored_version) != 1:
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
        note_text = tk.Text(prompt_window, font=("SimHei", 16))
        note_text.insert(tk.END, self.release_note or "本次更新优化了多项功能，提升稳定性和用户体验")
        note_text.config(state=tk.DISABLED, wrap=tk.WORD)
        note_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        ignore_var = tk.BooleanVar(value=False)
        ignore_check = ttk.Checkbutton(prompt_window, text="不要再提醒我", variable=ignore_var)
        ignore_check.pack(anchor=tk.W, padx=10, pady=5)
        btn_frame = ttk.Frame(prompt_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        cancel_btn = ttk.Button(btn_frame, text="取消", command=prompt_window.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        update_btn = ttk.Button(btn_frame, text="立即更新", command=lambda: self.on_update_confirm(prompt_window, ignore_var))
        update_btn.pack(side=tk.RIGHT, padx=5)

    def on_update_confirm(self, prompt_window, ignore_var):
        """用户确认更新"""
        prompt_window.destroy()
        if ignore_var.get():
            # 保存忽略版本时统一格式（移除v前缀）
            self.app.settings_manager.set_setting("update", "ignore_version", self.latest_version.lstrip("v"))
            self.app.settings_manager.save_preferences()
            print(f"已保存忽略版本设置: {self.latest_version}")
        self.start_background_download()

    def show_restart_prompt(self):
        """下载完成，提示重启替换"""
        if messagebox.askyesno("更新完成", f"更新包已下载完成！\n是否立即重启软件以应用 v{self.latest_version} 更新？"):
            self.replace_and_restart()

    def replace_and_restart(self):
        """替换原文件并重启（编码修复版）"""
        if not self.update_file_path or not os.path.exists(self.update_file_path):
            messagebox.showerror("错误", "更新包不存在，无法应用更新")
            return
        # 最终校验：Windows必须是exe
        if sys.platform == "win32" and not self.update_file_path.endswith(".exe"):
            messagebox.showerror("错误", "更新包不是exe文件，无法启动")
            return
        script_path = os.path.join(self.temp_dir, "update_script.bat" if sys.platform == "win32" else "update_script.sh")
        current_exe_path = sys.executable
        new_exe_path = os.path.join(os.path.dirname(current_exe_path), os.path.basename(self.update_file_path))
        current_pid = os.getpid()
        try:
            if sys.platform == "win32":
                # ====================== 编码兼容版 BAT 脚本（无特殊字符） ======================
                script_content = f"""
@echo off
:: 1. 强制以管理员身份运行（解决权限/文件占用/临时目录访问问题）
>nul 2>&1 "%SYSTEMROOT%\\system32\\cacls.exe" "%SYSTEMROOT%\\system32\\config\\system"
if %errorlevel% neq 0 (
    powershell -Command "Start-Process -FilePath '%0' -Verb RunAs -ArgumentList '{current_pid} {self.update_file_path} {new_exe_path} {os.path.dirname(new_exe_path)}'"
    exit
)
:: 2. 开启延迟扩展 + 切换GBK编码 + 锁定工作目录（核心修复DLL加载）
setlocal enabledelayedexpansion
chcp 936 >nul
cd /d "{os.path.dirname(new_exe_path)}"
cls
echo ==============================================
echo 正在应用 古韵汉字卡 更新 v{self.latest_version}...
echo ==============================================
timeout /t 1 /nobreak >nul
echo [1/5] 正在强制关闭所有应用进程...
:: 双重杀进程：PID精准杀 + 名称兜底杀，确保完全退出
taskkill /f /pid {current_pid} >nul 2>&1
taskkill /f /im "{os.path.basename(current_exe_path)}" >nul 2>&1
:: 关键：等待3秒，让进程彻底退出+释放文件锁
timeout /t 3 /nobreak >nul
echo [2/5] 正在备份当前版本（带时间戳）...
set "bak_time=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "bak_path={current_exe_path}_bak_!bak_time!.exe"
copy /y "{current_exe_path}" "!bak_path!" >nul 2>&1
if exist "!bak_path!" (
    echo 备份成功：!bak_path!
) else (
    echo 备份失败（非致命），继续更新...
)
echo [3/5] 正在替换更新文件（3次重试）...
set "max_attempts=3"
set "attempt=0"
set "copy_ok=0"
:RETRY_COPY
set /a attempt+=1
echo 尝试替换（第 !attempt!/!max_attempts! 次）...
copy /y "{self.update_file_path}" "{new_exe_path}" >nul 2>&1
if !errorlevel! equ 0 (
    set "copy_ok=1"
    goto COPY_DONE
)
if !attempt! lss !max_attempts! (
    echo 替换失败，等待2秒重试...
    timeout /t 2 /nobreak >nul
    goto RETRY_COPY
)
:: 兜底：robocopy强力复制（解决顽固文件占用）
echo 普通复制失败，尝试强力复制...
robocopy "{os.path.dirname(self.update_file_path)}" "{os.path.dirname(new_exe_path)}" "{os.path.basename(self.update_file_path)}" /IS /IT /NFL /NDL /NP /R:2 /W:2 >nul 2>&1
if !errorlevel! leq 1 (
    set "copy_ok=1"
)
:COPY_DONE
if !copy_ok! equ 0 (
    echo ==============================================
    echo 更新失败：文件替换失败
    echo 请手动复制以下文件完成更新：
    echo 源更新包：{self.update_file_path}
    echo 目标位置：{new_exe_path}
    echo ==============================================
    pause
    goto END
)
echo [4/5] 正在清理PyInstaller旧临时目录（解决DLL冲突）...
:: 删除所有_MEI开头的临时目录，避免新exe解压冲突
for /d %%d in ("%temp%\\_MEI*") do (
    rmdir /s /q "%%d" >nul 2>&1
)
echo 旧临时目录清理完成
echo [5/5] 正在启动新版本（管理员权限）...
:: 核心：指定工作目录 + 管理员启动 + 延迟等待
start "" /d "{os.path.dirname(new_exe_path)}" "{new_exe_path}"
:: 等待4秒，确保新exe完成解压+加载DLL
timeout /t 4 /nobreak >nul
echo ==============================================
echo 更新完成！新版本已启动！
echo ==============================================
:END
endlocal
:: 不删除脚本，避免干扰新exe启动，系统会自动清理临时文件
exit
"""
                # 写入BAT文件（GBK编码，内容无特殊字符）
                with open(script_path, "w", encoding="gbk") as f:
                    f.write(script_content)
            else:
                # Mac/Linux脚本（保持原稳定逻辑）
                script_content = f"""
#!/bin/bash
echo "正在准备更新..."
sleep 2
echo "正在关闭所有应用实例..."
pkill -f "{os.path.basename(current_exe_path)}" || true
sleep 1
echo "正在备份当前版本..."
cp -f "{current_exe_path}" "{current_exe_path}.bak" 2>/dev/null || true
echo "正在替换文件..."
MAX_ATTEMPTS=3
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "尝试替换 (第 $ATTEMPT/$MAX_ATTEMPTS 次)..."
    if cp -f "{self.update_file_path}" "{new_exe_path}"; then
        break
    fi
    if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
        echo "替换失败，等待重试..."
        sleep 2
    fi
done
if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "多次替换失败，尝试使用sudo..."
    sudo cp -f "{self.update_file_path}" "{new_exe_path}" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "替换失败，请手动更新"
        echo "新文件位置: {self.update_file_path}"
        echo "目标位置: {new_exe_path}"
        read -p "按Enter键继续..."
        exit 1
    fi
fi
echo "设置执行权限..."
chmod +x "{new_exe_path}"
echo "文件替换成功！"
echo "正在启动新版本..."
sleep 1
"{new_exe_path}" &
rm "$0"
exit 0
"""
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script_content)
                os.chmod(script_path, 0o755)
            # 启动更新脚本
            if sys.platform == "win32":
                os.startfile(script_path)
            else:
                subprocess.Popen([script_path])
            # 等待1秒让脚本启动，然后退出当前应用
            time.sleep(1)
            if hasattr(self.app, 'root'):
                self.app.root.destroy()
        except Exception as e:
            messagebox.showerror(
                "更新失败",
                f"应用更新时出错：{str(e)}\n请手动将更新包复制到：{new_exe_path}"
            )

    def check_update_manually(self):
        """手动检查更新（绑定按钮）"""
        # 手动检查时强制刷新，不缓存忽略版本
        self.latest_version = None
        self.download_url = None
        if self.is_update_available():
            self.show_update_prompt()
        else:
            messagebox.showinfo("无更新", f"当前已是最新版本（v{self.current_version}）！")