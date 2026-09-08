#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暂存箱视图 - 字段拆分版
- 每条暂存可只含单个字段（关键词/释义/出处/原文引用/注释）
- 拖拽合并：按住一条拖到另一条上松手，把字段并入目标条目
- 双击编辑（字段化对话框）、转卡片（按字段映射）、删除/清空、只看待办
"""
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from clips_store import ClipsStore, FIELD_ORDER, FIELD_LABELS
except ImportError:
    from cards.clips_store import ClipsStore, FIELD_ORDER, FIELD_LABELS


class InboxView:
    """暂存箱（划词收集箱）视图，字段拆分 + 拖拽合并"""

    def __init__(self, parent, clips_store, card_manager, app=None):
        self.parent = parent
        self.store = clips_store
        self.card_manager = card_manager
        self.app = app
        self._top = parent.winfo_toplevel()
        self.colors = app.colors if app else {
            'sub_text': '#8A7A5F', 'drop_hl': '#FCE4DB', 'text': '#3A2E21'
        }

        # 拖拽状态
        self._drag_source = None
        self._drag_start_xy = None
        self._dragging = False
        self._drop_target = None
        self._flash_job = None

        self._build_ui()
        self.refresh()

    # ---------------- UI ----------------
    def _build_ui(self):
        # 标题行：暂存箱 + ?帮助按钮（长段说明折叠进帮助，不再常驻占空间）
        head = ttk.Frame(self.parent)
        head.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(head, text="暂存箱",
                  font=("SimHei", 16, "bold")).pack(side=tk.LEFT)
        ttk.Button(head, text="?", width=2,
                   command=self._show_help).pack(side=tk.LEFT, padx=(6, 0))

        # 工具栏
        bar = ttk.Frame(self.parent)
        bar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(bar, text="刷新", width=8, command=self.refresh).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(bar, text="清空", width=8,
                   command=self._confirm_clear).pack(side=tk.RIGHT)

        # 列表：关键词 / 释义 / 出处 / 原文引用 / 注释 / 时间
        cols = ("keyword", "definition", "source", "quote", "comment", "created")
        self.tree = ttk.Treeview(self.parent, columns=cols, show="headings", selectmode="extended")
        headings = {"keyword": ("关键词", 100), "definition": ("释义", 230),
                    "source": ("出处", 120), "quote": ("原文引用", 190),
                    "comment": ("注释", 130), "created": ("时间", 100)}
        for c in cols:
            self.tree.heading(c, text=headings[c][0])
            self.tree.column(c, width=headings[c][1], anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(self.tree, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 拖拽合并（实例绑定：按下/拖动/释放）
        self.tree.tag_configure("drop_target", background=self.colors['drop_hl'])
        self.tree.bind("<ButtonPress-1>", self._on_press)
        self.tree.bind("<B1-Motion>", self._on_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_release)
        self.tree.bind("<Double-1>", lambda e: self._edit_selected())

        # 右键菜单 + Delete 删除快捷键
        self._ctx_menu = tk.Menu(self.tree, tearoff=0)
        self._ctx_menu.add_command(label="编辑", command=self._edit_selected)
        self._ctx_menu.add_command(label="转成卡片", command=self._convert_to_card)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="删除", command=self._remove_selected)
        self.tree.bind("<Button-3>", self._on_context_menu)
        self.tree.bind("<Delete>", lambda e: self._remove_selected())

        # 底部操作
        bottom = ttk.Frame(self.parent)
        bottom.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(bottom, text="转成卡片", style="Accent.TButton",
                   command=self._convert_to_card).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bottom, text="编辑", command=self._edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(bottom, text="删除", command=self._remove_selected).pack(side=tk.LEFT, padx=6)
        self.status_label = ttk.Label(bottom, text="")
        self.status_label.pack(side=tk.RIGHT)

    # ---------------- 帮助 / 右键菜单 ----------------
    def _show_help(self):
        messagebox.showinfo(
            "暂存箱说明",
            "阅读时用 Ctrl+Alt+C 划词，生僻词/佳句会收进这里（仅 Windows 下生效）。\n\n"
            "· 合并字段：按住一条拖到另一条上松手即可；\n"
            "    若两个条目同一字段都已有内容，会弹窗询问 拼接/覆盖/跳过。\n"
            "· 编辑：双击条目，或右键 → 编辑。\n"
            "· 转成卡片：右键 → 转成卡片，或选中后点底部按钮。\n"
            "· 删除：右键 → 删除，或选中后按 Delete 键 / 点删除按钮。\n"
            "· 一条暂存可以只存一个字段，不必一次填全。\n\n"
            "划词收集开关：设置 → 基本设置。",
            parent=self._top)

    def _on_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            # 右键不在当前选中集合时，改为只选中被点的行
            if iid not in self.tree.selection():
                self.tree.selection_set(iid)
            self.tree.focus(iid)
        try:
            self._ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._ctx_menu.grab_release()

    # ---------------- 数据 / 展示 ----------------
    def refresh(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for it in self.store.items:
            f = it.get("fields", {})
            self.tree.insert("", tk.END, iid=it.get("id", ""), values=(
                self._cell(f.get("keyword")),
                self._cell(f.get("definition")),
                self._cell(f.get("source")),
                self._cell(f.get("quote")),
                self._cell(f.get("comment")),
                it.get("created", "")
            ))
        self._reset_status()

    @staticmethod
    def _cell(v):
        """单元格值：去换行保留单行（Treeview 按列宽自行截断显示，完整内容见双击编辑）"""
        return " ".join((v or "").split())

    def _reset_status(self):
        self.status_label.config(text=f"共 {self.store.count()} 条")

    def _flash_status(self, msg, duration_ms=2200):
        self.status_label.config(text=msg)
        if self._flash_job:
            try:
                self.parent.after_cancel(self._flash_job)
            except Exception:
                pass
        self._flash_job = self.parent.after(duration_ms, self._reset_status)

    def _selected_ids(self):
        return list(self.tree.selection())

    def _first_selected(self):
        sel = self._selected_ids()
        return sel[0] if sel else None

    # ---------------- 拖拽合并 ----------------
    def _on_press(self, event):
        iid = ""
        if self.tree.identify_region(event.x, event.y) == "cell":
            iid = self.tree.identify_row(event.y)
        self._drag_source = iid if iid else None
        self._drag_start_xy = (event.x, event.y)
        self._dragging = False
        self._drop_target = None
        # 不 return "break"，让默认单击选中继续生效

    def _on_motion(self, event):
        if self._drag_source is None:
            return
        dx = event.x - self._drag_start_xy[0]
        dy = event.y - self._drag_start_xy[1]
        if not self._dragging and (abs(dx) > 5 or abs(dy) > 5):
            self._dragging = True
            self.tree.configure(cursor="hand2")
        if not self._dragging:
            return
        target = self.tree.identify_row(event.y)
        if target != self._drop_target:
            self._drop_target = target
            self._highlight(target)
        return "break"  # 抑制默认拖拽多选

    def _highlight(self, target):
        for iid in self.tree.get_children():
            if iid == target and target != self._drag_source:
                self.tree.item(iid, tags=("drop_target",))
            else:
                self.tree.item(iid, tags=())

    def _clear_highlight(self):
        for iid in self.tree.get_children():
            self.tree.item(iid, tags=())

    def _on_release(self, event):
        was_dragging = self._dragging
        source = self._drag_source
        target = self._drop_target
        self._clear_highlight()
        self.tree.configure(cursor="")
        self._dragging = False
        self._drag_source = None
        self._drop_target = None
        self._drag_start_xy = None
        if was_dragging and source and target and target != source:
            self._merge_entries(target, source)
            return "break"

    def _merge_entries(self, target_id, source_id):
        target = self.store.get(target_id)
        source = self.store.get(source_id)
        if not target or not source:
            return
        tf = target.get("fields", {})
        sf = source.get("fields", {})
        conflicts = [k for k in FIELD_ORDER
                     if (tf.get(k) or "").strip() and (sf.get(k) or "").strip()]
        resolve = {}
        if conflicts:
            resolve = self._ask_merge_conflicts(conflicts, tf, sf)
            if resolve is None:  # 取消合并
                return
        self.store.merge(target_id, source_id, resolve=resolve)
        self.refresh()
        self._flash_status("已合并字段")

    def _style_dialog(self, dlg, title):
        """弹窗统一后处理：应用图标 + 相对主窗口置中（在内容构建完成后调用）"""
        dlg.title(title)
        # 图标：传给本视图的 app 通常是 MainWindow，其 .app 才持有 _set_window_icon
        icon_owner = getattr(self.app, 'app', None) or self.app
        if icon_owner is not None and hasattr(icon_owner, '_set_window_icon'):
            try:
                icon_owner._set_window_icon(dlg)
            except Exception:
                pass
        # 置中：按请求尺寸相对主窗口定位（窗口尚未映射，位置在显示前生效）
        try:
            dlg.update_idletasks()
            top = self._top
            dw, dh = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
            x = top.winfo_rootx() + max(0, (top.winfo_width() - dw) // 2)
            y = top.winfo_rooty() + max(0, (top.winfo_height() - dh) // 3)
            dlg.geometry(f"+{int(x)}+{int(y)}")
        except Exception:
            pass

    def _ask_merge_conflicts(self, conflicts, tf, sf):
        """冲突字段弹窗：每个字段三选一（拼接/覆盖/跳过）。返回 {field: action}，取消返回 None"""
        dlg = tk.Toplevel(self._top)
        dlg.transient(self._top)
        dlg.grab_set()
        dlg.resizable(False, False)

        body = ttk.Frame(dlg, padding="16")
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text="以下字段两条都已有内容，请选择处理方式：",
                  font=("SimHei", 11, "bold")).grid(row=0, column=0, columnspan=2,
                                                     sticky=tk.W, pady=(0, 10))

        actions = {}
        row = 1
        for k in conflicts:
            ttk.Label(body, text=f"{FIELD_LABELS[k]}：",
                      font=("SimHei", 10)).grid(row=row, column=0, sticky=tk.NW, pady=(6, 0))
            detail = f"目标：{tf.get(k, '')}\n拖入：{sf.get(k, '')}"
            ttk.Label(body, text=detail, foreground=self.colors['sub_text'], wraplength=360,
                      justify=tk.LEFT).grid(row=row, column=1, sticky=tk.W, pady=(6, 0))
            row += 1
            var = tk.StringVar(value="append")
            actions[k] = var
            fr = ttk.Frame(body)
            fr.grid(row=row, column=1, sticky=tk.W, pady=(2, 4))
            ttk.Radiobutton(fr, text="拼接", variable=var, value="append").pack(side=tk.LEFT, padx=(0, 12))
            ttk.Radiobutton(fr, text="覆盖", variable=var, value="overwrite").pack(side=tk.LEFT, padx=(0, 12))
            ttk.Radiobutton(fr, text="跳过", variable=var, value="skip").pack(side=tk.LEFT)
            row += 1

        result = {"ok": False}

        def on_ok():
            result["ok"] = True
            dlg.destroy()

        btns = ttk.Frame(body)
        btns.grid(row=row, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btns, text="确定", style="Accent.TButton", command=on_ok).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="取消", command=dlg.destroy).pack(side=tk.RIGHT)

        self._style_dialog(dlg, "合并字段冲突")
        dlg.wait_window()
        if not result["ok"]:
            return None
        return {k: v.get() for k, v in actions.items()}

    # ---------------- 编辑 ----------------
    def _edit_selected(self):
        cid = self._first_selected()
        if not cid:
            messagebox.showinfo("提示", "请先选择一条暂存条目", parent=self._top)
            return
        it = self.store.get(cid)
        if not it:
            return
        self._edit_dialog(it)

    def _edit_dialog(self, clip):
        dlg = tk.Toplevel(self._top)
        dlg.transient(self._top)
        dlg.grab_set()
        dlg.resizable(False, False)

        body = ttk.Frame(dlg, padding="14")
        body.pack(fill=tk.BOTH, expand=True)

        fields = clip.get("fields", {})
        widgets = {}
        multiline_fields = ("definition", "quote", "comment")
        row = 0
        for k in FIELD_ORDER:
            ttk.Label(body, text=f"{FIELD_LABELS[k]}:").grid(row=row, column=0, sticky=tk.NW, pady=4)
            if k in multiline_fields:
                w = tk.Text(body, width=46, height=3, wrap=tk.WORD,
                            bg=self.colors.get('field_bg', '#FFFFFF'),
                            fg=self.colors.get('text', '#000000'),
                            insertbackground=self.colors.get('text', '#000000'))
                w.insert("1.0", fields.get(k, ""))
                w.grid(row=row, column=1, sticky=tk.W, pady=4)
                widgets[k] = ("text", w)
            else:
                var = tk.StringVar(value=fields.get(k, ""))
                w = ttk.Entry(body, textvariable=var, width=46)
                w.grid(row=row, column=1, sticky=tk.W, pady=4)
                widgets[k] = ("entry", w)
            row += 1

        def on_ok():
            new_fields = {}
            for k in FIELD_ORDER:
                kind, w = widgets[k]
                val = w.get("1.0", "end").strip() if kind == "text" else w.get().strip()
                new_fields[k] = val
            self.store.replace_fields(clip.get("id"), new_fields)
            self.refresh()
            dlg.destroy()

        btns = ttk.Frame(body)
        btns.grid(row=row + 1, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btns, text="确定", style="Accent.TButton", command=on_ok).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="取消", command=dlg.destroy).pack(side=tk.RIGHT)

        self._style_dialog(dlg, "编辑暂存条目")

    # ---------------- 转卡片 ----------------
    def _convert_to_card(self):
        cids = self._selected_ids()
        if not cids:
            messagebox.showinfo("提示", "请先勾选要转成卡片的条目", parent=self._top)
            return
        made = 0
        for cid in cids:
            clip = self.store.get(cid)
            if not clip:
                continue
            ok = self._convert_dialog(clip)
            if ok:
                self.store.remove(cid)
                made += 1
        self.refresh()
        if made:
            messagebox.showinfo("完成", f"已成功创建 {made} 张卡片", parent=self._top)

    def _convert_dialog(self, clip):
        """逐条弹转卡对话框：字段映射预填（clip.comment → 卡片 notes）"""
        dlg = tk.Toplevel(self._top)
        dlg.transient(self._top)
        dlg.grab_set()
        dlg.resizable(False, False)

        body = ttk.Frame(dlg, padding="14")
        body.pack(fill=tk.BOTH, expand=True)

        fields = clip.get("fields", {})

        kw_var = tk.StringVar(value=fields.get("keyword", ""))
        def_var = tk.StringVar(value=fields.get("definition", ""))
        src_var = tk.StringVar(value=fields.get("source", ""))
        quote_var = tk.StringVar(value=fields.get("quote", ""))
        note_var = tk.StringVar(value=fields.get("comment", ""))

        ttk.Label(body, text="关键词:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=kw_var, width=44).grid(row=0, column=1, pady=4)
        ttk.Label(body, text="释义:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=def_var, width=44).grid(row=1, column=1, pady=4)
        ttk.Label(body, text="出处(可空):").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=src_var, width=44).grid(row=2, column=1, pady=4)
        ttk.Label(body, text="原文摘句(可空):").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=quote_var, width=44).grid(row=3, column=1, pady=4)
        ttk.Label(body, text="注释(可空):").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Entry(body, textvariable=note_var, width=44).grid(row=4, column=1, pady=4)

        result = {"ok": False}

        def on_ok():
            try:
                self.card_manager.add_card({
                    "keyword": kw_var.get().strip(),
                    "definition": def_var.get().strip(),
                    "source": src_var.get().strip(),
                    "quote": quote_var.get().strip(),
                    "notes": note_var.get().strip(),
                })
            except Exception as e:
                messagebox.showerror("错误", f"保存卡片失败：{e}", parent=dlg)
                return
            result["ok"] = True
            dlg.destroy()

        btns = ttk.Frame(body)
        btns.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btns, text="创建卡片", style="Accent.TButton", command=on_ok).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="取消", command=dlg.destroy).pack(side=tk.RIGHT)
        dlg.bind("<Return>", lambda e: on_ok())
        self._style_dialog(dlg, "转成卡片")
        dlg.after(50, lambda: dlg.focus_force())
        dlg.wait_window()
        return result["ok"]

    # ---------------- 删除 ----------------
    def _remove_selected(self):
        cids = self._selected_ids()
        if not cids:
            return
        if not messagebox.askyesno("确认", f"删除选中的 {len(cids)} 条暂存？", parent=self._top):
            return
        for cid in cids:
            self.store.remove(cid)
        self.refresh()

    def _confirm_clear(self):
        if not self.store.items:
            return
        if not messagebox.askyesno("确认清空", "确定清空暂存箱全部条目？", parent=self._top):
            return
        self.store.clear()
        self.refresh()
