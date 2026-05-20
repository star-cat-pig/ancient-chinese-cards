#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_manager_proxy.py
- 由主程序调用，负责与 update.exe 交互（check / download / install）
- 负责 ignore_version (不要再提醒我)、force_show（手动检查绕过 ignore）
- 仅负责调用 update.exe；UI 弹窗由 proxy 展示（tk），下载实际由 update.exe 处理（GUI自动下载模式）
"""
import os
import sys
import json
import tempfile
import subprocess
import threading
import shlex
# helper version utilities
import re

def _norm_version(v: str) -> str:
    if not v:
        return ""
    return str(v).strip().lstrip("v").lstrip("V")

def _compare_version(v1: str, v2: str) -> int:
    try:
        a = [int(x) for x in re.findall(r'\d+', _norm_version(v1))]
        b = [int(x) for x in re.findall(r'\d+', _norm_version(v2))]
        max_len = max(len(a), len(b))
        a += [0] * (max_len - len(a))
        b += [0] * (max_len - len(b))
        for x, y in zip(a, b):
            if x > y:
                return 1
            if x < y:
                return -1
        return 0
    except Exception:
        nv1 = _norm_version(v1)
        nv2 = _norm_version(v2)
        if nv1 == nv2:
            return 0
        return 1 if nv1 > nv2 else -1

class UpdateManagerProxy:
    def __init__(self, app):
        """
        app: 主程序实例，要求提供:
            - settings_manager: 有 get_setting(section, key, default) / set_setting(section, key, value) / save_preferences()
            - root: tkinter 主窗口 (可选，仅用于定位弹窗)
            - icon_path 或者 _set_window_icon 方法 (可选，用于窗口图标)
        """
        self.app = app
        # location of update.exe: try helper function or assume same dir as main
        try:
            from config import get_update_exe_path
            self.update_exe_path = get_update_exe_path()
        except Exception:
            # fallback: expect update.exe in same dir as main exe or script
            base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
            self.update_exe_path = os.path.join(base, "update.exe")
            # also allow update.py for dev
            if not os.path.exists(self.update_exe_path) and os.path.exists(os.path.join(base, "update.py")):
                self.update_exe_path = os.path.join(base, "update.py")
        # temp info path - keep consistent with update.py
        self.update_info_file = os.path.join(tempfile.gettempdir(), "card_update_info.json")

    @property
    def has_pending_update(self) -> bool:
        """检查是否有已下载但未安装的更新包"""
        if not os.path.exists(self.update_info_file):
            return False
        try:
            with open(self.update_info_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
            downloaded = info.get('downloaded', False)
            file_path = info.get('file_path', '')
            return downloaded and os.path.exists(file_path)
        except Exception:
            return False

    def _is_update_exe_available(self) -> bool:
        return os.path.exists(self.update_exe_path)

    def _build_cmd(self, *args):
        if self.update_exe_path.endswith(".py"):
            return [sys.executable, self.update_exe_path] + list(args)
        else:
            return [self.update_exe_path] + list(args)
    
    def _format_release_note(self, note: str) -> list:
        """
        将Markdown格式的更新说明转换为带格式标记的列表
        # 一级标题 -> 标题内容（大字体）
        ## 二级标题 -> 标题内容（中字体）
        - 列表项 -> ● 列表项
        返回格式：[(text, font_size), ...]
        """
        # 处理空字符串或只包含空格的情况
        if not note or not note.strip():
            return [("暂无更新说明", "normal")]
        
        lines = note.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 处理一级标题 - 大字体
            if line.startswith('# '):
                title = line[2:].strip()
                if title:  # 确保标题不为空
                    formatted_lines.append((title, "large"))
                    formatted_lines.append(("", "normal"))  # 添加空行
                
            # 处理二级标题 - 中字体
            elif line.startswith('## '):
                title = line[3:].strip()
                if title:  # 确保标题不为空
                    formatted_lines.append((title, "medium"))
                    formatted_lines.append(("", "normal"))  # 添加空行
                
            # 处理列表项
            elif line.startswith('- '):
                item = line[2:].strip()
                if item:  # 确保列表项不为空
                    formatted_lines.append((f"● {item}", "normal"))
                
            # 处理空行
            elif not line:
                if formatted_lines and formatted_lines[-1][0]:  # 避免连续空行
                    formatted_lines.append(("", "normal"))
                    
            # 保留其他内容
            else:
                formatted_lines.append((line, "normal"))
        
        # 移除末尾的空行
        while formatted_lines and not formatted_lines[-1][0]:
            formatted_lines.pop()
        
        # 如果处理后没有内容，返回默认说明
        if not formatted_lines:
            return [("暂无更新说明", "normal")]
            
        return formatted_lines

    def check_for_updates(self, timeout: int = 30):
        """
        Call update.exe --check --silent and parse JSON from stdout.
        Return dict with fields: has_update, latest_version, current_version, release_note, download_url, error (optional)
        """
        if not self._is_update_exe_available():
            return {"has_update": False, "error": "update program not found"}
        cmd = self._build_cmd("--check", "--silent")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            if stderr:
                # keep logs on stderr for debugging
                print(f"[update.exe stderr] {stderr}", file=sys.stderr)
            if not stdout:
                return {"has_update": False, "error": "no output from update program"}
            try:
                info = json.loads(stdout)
                # normalize versions
                info["latest_version"] = _norm_version(info.get("latest_version") or info.get("version") or "")
                info["current_version"] = _norm_version(info.get("current_version") or "")
                return info
            except Exception as e:
                return {"has_update": False, "error": f"解析 update.exe 输出失败: {e}", "raw": stdout}
        except subprocess.TimeoutExpired:
            return {"has_update": False, "error": "update.exe check timeout"}
        except Exception as e:
            return {"has_update": False, "error": str(e)}

    def is_update_available(self):
        info = self.check_for_updates()
        return info.get("has_update", False)

    # GUI prompt shown by proxy (not update.exe). force_show True will bypass saved ignore_version.
    def show_update_prompt(self, force_show: bool = False):
        """
        Display a prompt to the user (tkinter) asking whether to update.
        Respects ignore_version saved in settings_manager unless force_show=True.
        On user confirm, launches update.exe GUI with auto-download mode.
        """
        info = self.check_for_updates()
        if info.get("error"):
            # optionally show error to user if GUI available
            try:
                import tkinter as tk
                from tkinter import messagebox
                messagebox.showerror("检查更新失败", info.get("error"))
            except Exception:
                pass
            return False
        if not info.get("has_update"):
            if force_show:
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    messagebox.showinfo("无更新", f"当前已是最新版本（v{info.get('current_version')}）")
                except Exception:
                    pass
            return False
        latest = info.get("latest_version")
        # check ignore_version
        ignored = ""
        try:
            if hasattr(self.app, "settings_manager"):
                ignored = self.app.settings_manager.get_setting("update", "ignore_version", "").strip()
        except Exception:
            ignored = ""
        if not force_show and ignored and _compare_version(latest, ignored) == 0:
            # user has ignored exactly this version
            return False
        # show tk prompt
        if not hasattr(self.app, "root") or self.app.root is None:
            # create a temporary root for the dialog
            try:
                import tkinter as tk
                from tkinter import ttk, messagebox
                tmp_root = tk.Tk()
                tmp_root.withdraw()
                parent = tmp_root
            except Exception:
                tmp_root = None
                parent = None
        else:
            tmp_root = None
            parent = self.app.root
        try:
            import tkinter as tk
            from tkinter import ttk, messagebox
        except Exception:
            # no GUI available
            return False
        # root for variables
        if tmp_root:
            root_for_vars = tmp_root
        else:
            root_for_vars = parent
        var_ignore = tk.BooleanVar(master=root_for_vars, value=(ignored == latest))
        # create dialog
        dlg = tk.Toplevel(parent) if parent else tk.Toplevel()
        dlg.title(f"发现新版本 v{latest}")
        dlg.geometry("800x500")  # 增大窗口尺寸
        dlg.transient(parent)
        dlg.grab_set()
        
        # 窗口居中显示
        dlg.update_idletasks()
        width = dlg.winfo_width()
        height = dlg.winfo_height()
        x = (dlg.winfo_screenwidth() - width) // 2
        y = (dlg.winfo_screenheight() - height) // 2
        dlg.geometry(f"+{x}+{y}")
        
        # icon
        try:
            if hasattr(self.app, "_set_window_icon"):
                try:
                    self.app._set_window_icon(dlg)
                except Exception:
                    pass
        except Exception:
            pass
        frame = ttk.Frame(dlg, padding=20)  # 增大内边距
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"检测到新版本 v{latest}", font=("SimHei", 16, "bold")).pack(anchor="w", pady=(0,12))  # 增大字体
        nn = info.get("release_note", "") or ""
        # 将Markdown格式转换为带格式的内容
        formatted_note = self._format_release_note(nn)
        
        # 创建Text控件
        text = tk.Text(frame, height=10, wrap=tk.WORD)
        
        # 定义不同字体大小的标签（增大字体）
        text.tag_configure("large", font=("SimHei", 18, "bold"))
        text.tag_configure("medium", font=("SimHei", 16))
        text.tag_configure("normal", font=("SimHei", 14))
        
        # 插入带格式的内容
        current_pos = "1.0"
        for line, font_size in formatted_note:
            if line:  # 非空行
                text.insert(current_pos, line + "\n", font_size)
            else:  # 空行
                text.insert(current_pos, "\n")
            current_pos = text.index("end")
        
        text.config(state="disabled")
        text.pack(fill="both", expand=True, pady=(0,8))
        bottom = ttk.Frame(frame)
        bottom.pack(fill="x")
        chk = ttk.Checkbutton(bottom, text="不要再提醒我此版本更新", variable=var_ignore)
        chk.pack(side="left")
        btns = ttk.Frame(bottom)
        btns.pack(side="right")
        # actions
        def do_cancel():
            # save ignore if checked
            try:
                if hasattr(self.app, "settings_manager"):
                    if var_ignore.get():
                        self.app.settings_manager.set_setting("update", "ignore_version", latest)
                    else:
                        cur_ignored = self.app.settings_manager.get_setting("update", "ignore_version", "")
                        if cur_ignored == latest:
                            self.app.settings_manager.set_setting("update", "ignore_version", "")
                    self.app.settings_manager.save_preferences()
            except Exception:
                pass
            dlg.destroy()
            if tmp_root:
                tmp_root.destroy()
        
        def do_update():
            # if user checked ignore, still save (consistent with UI)
            try:
                if hasattr(self.app, "settings_manager"):
                    if var_ignore.get():
                        self.app.settings_manager.set_setting("update", "ignore_version", latest)
                    else:
                        cur_ignored = self.app.settings_manager.get_setting("update", "ignore_version", "")
                        if cur_ignored == latest:
                            self.app.settings_manager.set_setting("update", "ignore_version", "")
                    self.app.settings_manager.save_preferences()
            except Exception:
                pass
            dlg.destroy()
            if tmp_root:
                tmp_root.destroy()
            # 核心修改：启动update.exe的GUI自动下载模式，而非后台命令行
            try:
                cmd = self._build_cmd("--auto-start-download")
                # Windows下直接启动GUI程序，窗口正常显示
                if sys.platform == "win32":
                    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)
            except Exception as e:
                print(f"[ERROR] 启动更新程序失败: {e}", file=sys.stderr)
                # 启动失败弹出错误提示
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    messagebox.showerror("启动失败", f"无法启动更新程序：{str(e)}")
                except Exception:
                    pass
            return
        
        b_cancel = ttk.Button(btns, text="取消", command=do_cancel)
        b_cancel.pack(side="right", padx=6)
        b_update = ttk.Button(btns, text="立即更新", command=do_update)
        b_update.pack(side="right", padx=6)
        dlg.protocol("WM_DELETE_WINDOW", do_cancel)
        try:
            dlg.wait_window()
        except Exception:
            pass
        return True

    def check_update_manually(self):
        """Manual check (force_prompt=True to ignore ignore_version)"""
        return self.show_update_prompt(force_show=True)

    def start_download_detached(self):
        """Start download by launching update.exe GUI auto-download mode"""
        if not self._is_update_exe_available():
            print("[ERROR] update program not found", file=sys.stderr)
            return False
        cmd = self._build_cmd("--auto-start-download")
        try:
            if sys.platform == "win32":
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)
            return True
        except Exception as e:
            print(f"[ERROR] 启动 update.exe 失败: {e}", file=sys.stderr)
            return False

    def on_app_exit(self):
        """
        Call on application exit to check if downloaded update exists (update_info_file)
        If found, prompt user to install now.
        """
        try:
            # check info file
            if os.path.exists(self.update_info_file):
                try:
                    with open(self.update_info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                except Exception:
                    info = {}
                if info.get("downloaded") and info.get("file_path"):
                    # prompt user
                    try:
                        import tkinter as tk
                        from tkinter import messagebox
                        parent = getattr(self.app, "root", None)
                        # create temp root if needed
                        tmp = None
                        if parent is None:
                            tmp = tk.Tk()
                            tmp.withdraw()
                            parent = tmp
                        if messagebox.askyesno("安装更新", "发现已下载的更新包，是否现在安装？"):
                            # call update.exe --install --silent (detached)
                            cmd = self._build_cmd("--install", "--silent")
                            if sys.platform == "win32":
                                subprocess.Popen(cmd, creationflags=subprocess.DETACHED_PROCESS)
                            else:
                                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)
                            if tmp:
                                tmp.destroy()
                            return True
                        if tmp:
                            tmp.destroy()
                    except Exception:
                        pass
        except Exception:
            pass
        return False