#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
划词收集器（Windows 全局热键版）
- 全局热键：Ctrl + Alt + C（任何窗口下生效）
- 取词流程（后台线程，纯 Win32，不卡 UI）：
    热键触发 → 等 Ctrl/Alt 完全抬起(避免变成 Ctrl+Alt+C 被目标忽略)
           → Win32 清空剪贴板 → SendInput 整批注入 Ctrl+C
           → 轮询剪贴板等待新文本(最长 ~1.2s) → 空则自动重试一次
           → 结果送回主线程 → 弹出收集浮窗 / 提示未检测到
- 参考成熟方案：Quicker/划词翻译的 Ctrl+C 模拟（等待修饰键释放 + SendInput
  批量注入 + 轮询剪贴板而非固定延时），规避 keybd_event 与时序/焦点陷阱。
- 纯 ctypes 实现（不依赖 pywin32，ARM64 Windows 同样可用）
- 非 Windows 平台自动禁用（start 返回 False，不影响程序运行）
"""
import ctypes
import os
import queue
import sys
import threading
import time

try:
    from clips_store import FIELD_ORDER, FIELD_LABELS
except ImportError:
    from cards.clips_store import FIELD_ORDER, FIELD_LABELS

# ---------- Windows 常量 ----------
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
VK_CONTROL = 0x11
VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1
CF_UNICODETEXT = 13
CF_TEXT = 1
HOTKEY_ID = 0xCA10

# ---------- 浮窗 / 提示配色（随主窗口主题切换；浅色为原硬编码观感） ----------
POPUP_LIGHT = {
    'chrome': '#3A3126',        # 浮窗边框/外壳
    'head': '#C44536',          # 顶栏（朱砂红）
    'head_active': '#A93A2D',   # 顶栏按钮悬停
    'head_fg': '#FFFFFF',
    'content': '#FFFDF7',       # 内容区（米白）
    'label': '#7A6A55',         # 内容区说明文字
    'entry_bg': '#FFFFFF',
    'entry_fg': '#3A3126',
    'btn_primary': '#C44536',   # 1.关键词 按钮
    'btn_primary_active': '#A93A2D',
    'btn_other': '#8A7A5F',     # 其余字段按钮（棕灰）
    'btn_other_active': '#6B5D4F',
    'btn_fg': '#FFFFFF',
    'toast_bg': '#3A3126',      # 右下角状态提示
    'toast_fg': '#FFFDF7',
}
POPUP_DARK = {
    'chrome': '#26221C',
    'head': '#D4695A',
    'head_active': '#B85548',
    'head_fg': '#FFFFFF',
    'content': '#2A2621',
    'label': '#B0A58E',
    'entry_bg': '#33302B',
    'entry_fg': '#E8DFCF',
    'btn_primary': '#D4695A',
    'btn_primary_active': '#B85548',
    'btn_other': '#4A443B',
    'btn_other_active': '#5A5348',
    'btn_fg': '#FFFFFF',
    'toast_bg': '#26221C',
    'toast_fg': '#E8DFCF',
}


class ClipCollector:
    """全局划词收集：注册热键 → 抓词 → 弹收集浮窗"""

    def __init__(self, root, store, settings_manager=None):
        self.root = root
        self.store = store
        self.settings_manager = settings_manager

        self._q = queue.Queue()
        self._thread = None
        self._stop_event = threading.Event()
        self._running = False
        self._collecting = False          # 防重复触发
        self._popup = None                # 当前浮窗
        self._last_old_text = None        # 触发前剪贴板文本（无划词时还原用）

        import tkinter as tk
        self._tk = tk

        # 浮窗配色：默认浅色；set_theme 后按主窗口深浅主题切换
        self._popup_colors = dict(POPUP_LIGHT)

    def set_theme(self, is_dark):
        """按主窗口主题切换浮窗/提示配色（下次弹出生效）"""
        self._popup_colors = dict(POPUP_DARK if is_dark else POPUP_LIGHT)

    # ================= Win32 剪贴板 / 按键辅助（后台线程可用） =================
    @staticmethod
    def _is_key_down(vk):
        try:
            return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
        except Exception:
            return False

    @staticmethod
    def _win32_clear_clipboard():
        """Win32 清空剪贴板（立即生效，无 tk 时序问题）"""
        try:
            user32 = ctypes.windll.user32
            if user32.OpenClipboard(None):
                try:
                    user32.EmptyClipboard()
                finally:
                    user32.CloseClipboard()
        except Exception:
            pass

    @staticmethod
    def _win32_get_text():
        """Win32 读剪贴板文本：优先 CF_UNICODETEXT，无则回退 CF_TEXT；均无返回 None"""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            # 64 位句柄必须声明 restype，否则被 ctypes 按 32 位截断（读不到数据的元凶）
            user32.GetClipboardData.argtypes = [ctypes.c_uint]
            user32.GetClipboardData.restype = ctypes.c_void_p
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalSize.argtypes = [ctypes.c_void_p]
            kernel32.GlobalSize.restype = ctypes.c_size_t
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            if not user32.OpenClipboard(None):
                return None
            try:
                for cf, encoding in ((CF_UNICODETEXT, "utf-16-le"), (CF_TEXT, "gbk")):
                    if not user32.IsClipboardFormatAvailable(cf):
                        continue
                    h = user32.GetClipboardData(cf)
                    if not h:
                        continue
                    p = kernel32.GlobalLock(h)
                    if not p:
                        continue
                    try:
                        size = kernel32.GlobalSize(h)
                        if size <= 0:
                            continue
                        buf = ctypes.create_string_buffer(size)
                        ctypes.memmove(buf, p, size)
                        raw = buf.raw
                        if cf == CF_UNICODETEXT:
                            text = raw.decode("utf-16-le", "ignore").rstrip("\x00")
                        else:
                            text = raw.split(b"\x00", 1)[0].decode("gbk", "ignore")
                        text = text.strip()
                        if text:
                            return text
                    finally:
                        kernel32.GlobalUnlock(h)
                return None
            finally:
                user32.CloseClipboard()
        except Exception:
            return None

    @staticmethod
    def _send_ctrl_c():
        """SendInput 整批模拟 Ctrl+C（等待修饰键抬起后由调用方保证）"""
        try:
            user32 = ctypes.windll.user32

            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [("wVk", ctypes.c_ushort),
                            ("wScan", ctypes.c_ushort),
                            ("dwFlags", ctypes.c_ulong),
                            ("time", ctypes.c_ulong),
                            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                            ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                            ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

            class HARDWAREINPUT(ctypes.Structure):
                _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short),
                            ("wParamH", ctypes.c_ushort)]

            class _INPUTUNION(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

            class INPUT(ctypes.Structure):
                _fields_ = [("type", ctypes.c_ulong), ("union", _INPUTUNION)]

            def key(vk, up=False):
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.union.ki.wVk = vk
                inp.union.ki.wScan = user32.MapVirtualKeyW(vk, 0)
                if up:
                    inp.union.ki.dwFlags = KEYEVENTF_KEYUP
                return inp

            vk_c = ord("C")
            seq = [key(VK_CONTROL), key(vk_c), key(vk_c, up=True), key(VK_CONTROL, up=True)]
            arr = (INPUT * len(seq))(*seq)
            # 一次 SendInput 批量发送，避免与真实输入交织
            user32.SendInput(len(seq), ctypes.byref(arr), ctypes.sizeof(INPUT))
        except Exception as e:
            print(f"SendInput Ctrl+C 失败: {e}", file=sys.stderr)

    # ================= 生命周期 =================
    def enabled_by_settings(self) -> bool:
        if not self.settings_manager:
            return True
        try:
            return bool(self.settings_manager.get_setting("clip", "hotkey_enabled", True))
        except Exception:
            return True

    def start(self):
        """注册全局热键（仅 Windows）。返回是否成功注册。"""
        if os.name != "nt":
            return False
        if self._running:
            return True
        if not self.enabled_by_settings():
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._hook_loop, daemon=True)
        self._thread.start()
        self._running = True
        self._drain_queue()
        return True

    def stop(self):
        if not self._running:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._running = False

    # ================= 热键线程 =================
    def _hook_loop(self):
        try:
            user32 = ctypes.windll.user32
            # MOD_NOREPEAT：按住热键不连续触发
            ok = user32.RegisterHotKey(None, HOTKEY_ID, MOD_ALT | MOD_CONTROL | MOD_NOREPEAT, ord("C"))
            if not ok:
                print("划词收集热键 Ctrl+Alt+C 注册失败（可能被其它程序占用）", file=sys.stderr)
                self._q.put(("error", "热键注册失败"))
                return
            print("划词收集热键已注册: Ctrl+Alt+C", file=sys.stderr)
        except Exception as e:
            print(f"划词收集初始化失败: {e}", file=sys.stderr)
            return

        try:
            from ctypes import wintypes
            MSG = wintypes.MSG
            user32 = ctypes.windll.user32
            while not self._stop_event.is_set():
                msg = MSG()
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                    if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                        self._q.put(("hotkey", None))
                else:
                    time.sleep(0.05)
        finally:
            try:
                ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
            except Exception:
                pass

    # ================= 主线程队列处理 =================
    def _drain_queue(self):
        if not self._running:
            return
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "hotkey":
                    self._trigger_collect()
                elif kind == "result":
                    self._on_collect_result(*payload)
                elif kind == "error":
                    self._notify_error(payload)
        except queue.Empty:
            pass
        self.root.after(150, self._drain_queue)

    def _notify_error(self, message):
        try:
            from tkinter import messagebox
            messagebox.showwarning("划词收集",
                                   f"{message}\n可在 设置 → 基本设置 里关闭此功能。")
        except Exception:
            pass

    # ================= 取词（后台线程执行，不卡 UI） =================
    def _trigger_collect(self):
        if self._collecting:
            return
        if not self.enabled_by_settings():
            return
        self._collecting = True
        threading.Thread(target=self._collect_worker, daemon=True).start()

    def _collect_worker(self):
        """后台取词：等待修饰键抬起 → 清剪贴板 → SendInput Ctrl+C → 轮询/重试"""
        try:
            if os.name != "nt":
                self._q.put(("result", (None, None)))
                return
            # 1) 等 Ctrl/Alt 完全抬起（热键刚触发时按键可能未释放，
            #    否则注入会变成 Ctrl+Alt+C 被目标程序忽略——划词取词经典坑）
            deadline = time.time() + 1.0
            while time.time() < deadline:
                if not (self._is_key_down(VK_CONTROL) or self._is_key_down(VK_MENU)):
                    break
                time.sleep(0.02)
            time.sleep(0.05)  # 留一点释放抖动余量

            # 2) 记旧文本（用于无划词时还原）
            old = self._win32_get_text()

            text = None
            for attempt in (1, 2):
                self._win32_clear_clipboard()
                self._send_ctrl_c()
                text = self._poll_clipboard(timeout=1.2 if attempt == 1 else 0.8)
                if text:
                    break
                time.sleep(0.12)  # 重试前稍候

            # 后备：SendInput 无效时，直接给前台焦点控件发 WM_COPY（Edit/WebView2 等支持）
            if not text:
                self._win32_clear_clipboard()
                self._send_wm_copy()
                text = self._poll_clipboard(timeout=0.8)

            # 3) 回主线程处理（弹窗/还原剪贴板都要 tk）
            self._q.put(("result", (old, text)))
        except Exception as e:
            print(f"划词取词异常: {e}", file=sys.stderr)
            self._q.put(("result", (None, None)))

    @staticmethod
    def _send_wm_copy():
        """后备取词：向前台窗口的焦点控件直发 WM_COPY(0x0301)，不依赖按键注入"""
        try:
            user32 = ctypes.windll.user32
            fg = user32.GetForegroundWindow()
            if not fg:
                return
            tid = user32.GetWindowThreadProcessId(fg, None)
            focus = None
            try:
                from ctypes import wintypes
                from ctypes import wintypes as _wt
                class GUITHREADINFO(ctypes.Structure):
                    _fields_ = [("cbSize", _wt.DWORD), ("flags", _wt.DWORD),
                                ("hwndActive", _wt.HWND), ("hwndFocus", _wt.HWND),
                                ("hwndCapture", _wt.HWND), ("hwndMenuOwner", _wt.HWND),
                                ("hwndMoveSize", _wt.HWND), ("hwndCaret", _wt.HWND),
                                ("rcCaret", _wt.RECT)]
                gui = GUITHREADINFO()
                gui.cbSize = ctypes.sizeof(GUITHREADINFO)
                if user32.GetGUIThreadInfo(tid, ctypes.byref(gui)) and gui.hwndFocus:
                    focus = gui.hwndFocus
            except Exception:
                pass
            user32.SendMessageW(focus or fg, 0x0301, 0, 0)
        except Exception as e:
            print(f"WM_COPY 发送失败: {e}", file=sys.stderr)

    def _poll_clipboard(self, timeout=1.2):
        """轮询等待剪贴板出现新文本（目标程序写入有快慢，固定延时不可靠）"""
        end = time.time() + timeout
        last = None
        while time.time() < end:
            t = self._win32_get_text()
            if t:
                last = t
                break
            time.sleep(0.06)
        return last

    def _on_collect_result(self, old, text):
        """主线程：拿到取词结果 → 弹浮窗或还原剪贴板提示"""
        self._collecting = False
        if text and (not old or text != old):
            # 划到新内容
            if len(text) > 500:
                text = text[:500] + "…"
            self._show_popup(text)
            return
        # 没有划到新词：还原旧剪贴板内容，避免白清用户数据
        if old:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(old)
            except Exception:
                pass
        self._flash_message("未检测到划选的文字\n请先划选文字，再按 Ctrl+Alt+C\n（网页/PDF 若未复制成功可多试一次）")

    # ================= 浮窗 =================
    def _show_popup(self, text):
        """鼠标下方弹无边框收集浮窗（字段拆分版）：可编辑划词内容 + 5 字段路由按钮"""
        self._close_popup()
        tk = self._tk
        P = self._popup_colors  # 当前主题配色（浅色 / 深色）
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        try:
            popup.attributes("-topmost", True)
        except Exception:
            pass
        popup.configure(bg=P['chrome'])

        def close():
            self._close_popup()

        popup.bind("<Escape>", lambda e: close())

        body = tk.Frame(popup, bg=P['chrome'])
        body.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        head = tk.Frame(body, bg=P['head'])
        head.pack(fill=tk.X)
        tk.Label(head, text=" 划词收集  Ctrl+Alt+C", bg=P['head'], fg=P['head_fg'],
                 font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(head, text="✕", bg=P['head'], fg=P['head_fg'], bd=0, activebackground=P['head_active'],
                  activeforeground=P['head_fg'], command=close,
                  font=("Microsoft YaHei", 9)).pack(side=tk.RIGHT, padx=4)

        inner = tk.Frame(body, bg=P['content'])
        inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # 可编辑的划词内容
        tk.Label(inner, text="划词内容（可改）:", bg=P['content'], fg=P['label'],
                 anchor=tk.W, font=("Microsoft YaHei", 9)).pack(fill=tk.X)
        text_var = tk.StringVar(value=text)
        entry = tk.Entry(inner, textvariable=text_var, font=("Microsoft YaHei", 10),
                         relief=tk.SOLID, bd=1, bg=P['entry_bg'], fg=P['entry_fg'],
                         insertbackground=P['entry_fg'])
        entry.pack(fill=tk.X, pady=(2, 8))

        tk.Label(inner, text="保存到（点按钮或按 1-5 键）:", bg=P['content'], fg=P['label'],
                 anchor=tk.W, font=("Microsoft YaHei", 9)).pack(fill=tk.X)

        def save_as(field_type):
            value = text_var.get().strip()
            if not value:
                self._close_popup()
                self._flash_message("内容为空，未保存")
                return
            try:
                self.store.add_field(field_type, value)
            except Exception as e:
                print(f"保存划词条目失败: {e}", file=sys.stderr)
                self._close_popup()
                return
            label = FIELD_LABELS.get(field_type, field_type)
            self._close_popup()
            self._flash_message(f"已保存到「{label}」")
            self._notify_inbox_changed()

        def make_btn(parent, field_type, idx):
            label = f"{idx}.{FIELD_LABELS.get(field_type, field_type)}"
            if idx == 1:
                bg, act = P['btn_primary'], P['btn_primary_active']
            else:
                bg, act = P['btn_other'], P['btn_other_active']
            return tk.Button(parent, text=label, bg=bg, fg=P['btn_fg'], bd=0,
                             activebackground=act, activeforeground=P['btn_fg'],
                             command=lambda f=field_type: save_as(f),
                             font=("Microsoft YaHei", 10), padx=10, pady=4)

        r1 = tk.Frame(inner, bg=P['content'])
        r1.pack(fill=tk.X, pady=(4, 4))
        for i, f in enumerate(("keyword", "definition", "source"), start=1):
            make_btn(r1, f, i).pack(side=tk.LEFT, padx=(0, 6))

        r2 = tk.Frame(inner, bg=P['content'])
        r2.pack(fill=tk.X, pady=(0, 6))
        for i, f in enumerate(("quote", "comment"), start=4):
            make_btn(r2, f, i).pack(side=tk.LEFT, padx=(0, 6))

        # 快捷键：1-5 直接保存对应字段；Enter 保存到关键词
        def bind_key(field_type):
            def handler(e):
                save_as(field_type)
                return "break"
            return handler

        for i, f in enumerate(FIELD_ORDER, start=1):
            entry.bind(str(i), bind_key(f))
            popup.bind(str(i), bind_key(f))
        entry.bind("<Return>", bind_key("keyword"))
        popup.bind("<Return>", bind_key("keyword"))

        try:
            x, y = self.root.winfo_pointerxy()
        except Exception:
            x, y = 300, 200
        popup.update_idletasks()
        w = popup.winfo_reqwidth()
        h = popup.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        px = min(x + 18, sw - w - 8)
        py = min(y + 24, sh - h - 8)
        if px < 0:
            px = 8
        if py < 0:
            py = 8
        popup.geometry(f"+{px}+{py}")
        self._popup = popup

        # overrideredirect 窗口默认拿不到键盘焦点，导致 1-5 快捷键无效；
        # 延迟一帧后强制焦点（窗口映射完成后才能稳定获取）
        def _grab_focus():
            try:
                popup.lift()
                popup.focus_force()
                entry.focus_force()
                entry.select_range(0, tk.END)
            except Exception:
                pass
        popup.after(40, _grab_focus)

    def _close_popup(self):
        if self._popup is not None:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None

    # ================= 状态提示与回调 =================
    def _flash_message(self, message, duration_ms=2600):
        """屏幕右下角闪现一条状态提示（不打扰）"""
        try:
            import tkinter as tk
            P = self._popup_colors
            tip = tk.Toplevel(self.root)
            tip.overrideredirect(True)
            try:
                tip.attributes("-topmost", True)
            except Exception:
                pass
            tk.Label(tip, text=message, bg=P['toast_bg'], fg=P['toast_fg'],
                     font=("Microsoft YaHei", 9), padx=12, pady=6,
                     justify=tk.LEFT).pack()
            tip.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            w = tip.winfo_reqwidth()
            h = tip.winfo_reqheight()
            tip.geometry(f"+{sw - w - 16}+{sh - h - 70}")

            def kill():
                try:
                    tip.destroy()
                except Exception:
                    pass
            self.root.after(duration_ms, kill)
        except Exception:
            pass

    def _notify_inbox_changed(self):
        """通知主窗口刷新暂存箱（若有回调）"""
        cb = getattr(self.root, "_on_clip_saved", None)
        if callable(cb):
            try:
                cb()
            except Exception:
                pass
