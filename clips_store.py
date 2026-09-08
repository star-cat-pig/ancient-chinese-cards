#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暂存箱存储层 - 划词收集的条目暂存管理（字段拆分版）
数据文件: <用户数据目录>/clips.json
条目结构（新版，字段拆分）:
    {id, fields: {keyword, definition, source, quote, comment}, todo, created}
- 每条可只含单个字段（如只有 keyword，或只有 source）
- 通过拖拽合并把多条拼成一条完整条目
兼容旧版: {id, text, note, source, todo, created}
    text→keyword, note→definition, source→source（load 时自动迁移）
"""
import json
import os
import time
import uuid

# 字段定义（顺序即显示/合并顺序）
FIELD_ORDER = ["keyword", "definition", "source", "quote", "comment"]

FIELD_LABELS = {
    "keyword": "关键词",
    "definition": "释义",
    "source": "出处",
    "quote": "原文引用",
    "comment": "注释",
}

# 列表里用的短徽章
FIELD_BADGES = {
    "keyword": "词",
    "definition": "义",
    "source": "源",
    "quote": "句",
    "comment": "注",
}


class ClipsStore:
    """暂存箱数据管理（clips.json 读写，字段拆分版）"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.file_path = os.path.join(data_dir, "clips.json")
        self.items = []  # list[dict]，每条已字段化
        self.load()

    # ---------------- 加载 / 保存 ----------------
    def load(self):
        """从磁盘加载（损坏时自动重建），并做旧版→新版字段化迁移"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw = data if isinstance(data, list) else data.get("items", [])
                self.items = [n for n in (self._normalize(it) for it in raw) if n is not None]
            else:
                self.items = []
        except Exception as e:
            print(f"加载暂存箱失败，已重建: {e}", file=__import__("sys").stderr)
            self.items = []

    def save(self):
        """写回磁盘"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({"items": self.items}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存暂存箱失败: {e}", file=__import__("sys").stderr)

    @staticmethod
    def _normalize(it):
        """把旧版/新版条目统一成字段化结构，坏数据返回 None"""
        if not isinstance(it, dict):
            return None
        if "fields" in it and isinstance(it.get("fields"), dict):
            fields = {}
            for k in FIELD_ORDER:
                v = (it["fields"].get(k) or "").strip()
                if v:
                    fields[k] = v
            return {
                "id": it.get("id") or uuid.uuid4().hex[:12],
                "fields": fields,
                "todo": bool(it.get("todo", False)),
                "created": it.get("created", ""),
            }
        # 旧版 {text, note, source, todo, created}
        fields = {}
        if (it.get("text") or "").strip():
            fields["keyword"] = it.get("text", "").strip()
        if (it.get("note") or "").strip():
            fields["definition"] = it.get("note", "").strip()
        if (it.get("source") or "").strip():
            fields["source"] = it.get("source", "").strip()
        return {
            "id": it.get("id") or uuid.uuid4().hex[:12],
            "fields": fields,
            "todo": bool(it.get("todo", False)),
            "created": it.get("created", ""),
        }

    # ---------------- 写入 ----------------
    def add_field(self, field_type: str, text: str, todo: bool = False):
        """新增一条单字段条目，返回 clip_id；字段非法或内容为空返回 None"""
        if field_type not in FIELD_ORDER:
            raise ValueError(f"未知字段类型: {field_type}")
        value = (text or "").strip()
        if not value:
            return None
        clip_id = uuid.uuid4().hex[:12]
        self.items.insert(0, {
            "id": clip_id,
            "fields": {field_type: value},
            "todo": bool(todo),
            "created": time.strftime("%Y-%m-%d %H:%M"),
        })
        self.save()
        return clip_id

    def set_field(self, clip_id: str, field_type: str, value: str) -> bool:
        """设置/覆盖条目某个字段；空值则删除该字段"""
        if field_type not in FIELD_ORDER:
            return False
        for it in self.items:
            if it.get("id") == clip_id:
                value = (value or "").strip()
                if value:
                    it.setdefault("fields", {})[field_type] = value
                else:
                    it.setdefault("fields", {}).pop(field_type, None)
                self.save()
                return True
        return False

    def replace_fields(self, clip_id: str, fields: dict) -> bool:
        """整条替换字段（编辑对话框用）；空值字段被丢弃"""
        for it in self.items:
            if it.get("id") == clip_id:
                cleaned = {}
                for k in FIELD_ORDER:
                    v = (fields.get(k) or "").strip()
                    if v:
                        cleaned[k] = v
                it["fields"] = cleaned
                self.save()
                return True
        return False

    def set_todo(self, clip_id: str, todo: bool) -> bool:
        for it in self.items:
            if it.get("id") == clip_id:
                it["todo"] = bool(todo)
                self.save()
                return True
        return False

    # ---------------- 合并 ----------------
    def merge(self, target_id: str, source_id: str, resolve: dict = None) -> bool:
        """把 source 的字段并入 target。

        resolve: 冲突字段的处理 {field: 'overwrite'|'append'|'skip'}，缺省 append。
        冲突 = 两条都有该字段且都非空。
        """
        target = self.get(target_id)
        source = self.get(source_id)
        if not target or not source or target_id == source_id:
            return False
        tf = target.setdefault("fields", {})
        sf = source.get("fields", {})
        resolve = resolve or {}
        for k in FIELD_ORDER:
            sv = (sf.get(k) or "").strip()
            if not sv:
                continue
            if tf.get(k):
                action = resolve.get(k, "append")
                if action == "overwrite":
                    tf[k] = sv
                elif action == "append":
                    tf[k] = tf[k] + "；" + sv
                # skip：保持原值不动
            else:
                tf[k] = sv
        self.items = [it for it in self.items if it.get("id") != source_id]
        self.save()
        return True

    # ---------------- 读取 ----------------
    def get(self, clip_id: str):
        for it in self.items:
            if it.get("id") == clip_id:
                return it
        return None

    def remove(self, clip_id: str) -> bool:
        before = len(self.items)
        self.items = [it for it in self.items if it.get("id") != clip_id]
        changed = len(self.items) != before
        if changed:
            self.save()
        return changed

    def clear(self):
        self.items = []
        self.save()

    def count(self, todo_only: bool = False) -> int:
        if todo_only:
            return sum(1 for it in self.items if it.get("todo"))
        return len(self.items)

    # ---------------- 展示辅助 ----------------
    @staticmethod
    def filled_fields(item: dict):
        """返回条目已填的字段名列表（按 FIELD_ORDER）"""
        fields = item.get("fields", {}) if item else {}
        return [k for k in FIELD_ORDER if (fields.get(k) or "").strip()]

    @staticmethod
    def summary_text(text: str, limit: int = 60) -> str:
        """列表用摘要（去换行、截断）"""
        one_line = " ".join((text or "").split())
        return one_line if len(one_line) <= limit else one_line[:limit] + "…"
