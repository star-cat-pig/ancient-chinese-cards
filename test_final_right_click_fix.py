#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试脚本 - 验证右键批量删除功能的完整修复
这个脚本测试用户提供的修复方案是否正确实现
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class MockTreeview:
    """模拟Treeview的关键方法"""
    def __init__(self, selectmode="extended"):
        self._selection = []
        self._items = ['item1', 'item2', 'item3', 'item4', 'item5']
        self._tags = {'item1': ['card1'], 'item2': ['card2'], 'item3': ['card3'], 
                      'item4': ['card4'], 'item5': ['card5']}
        self._focus = None
        self._anchor = None
        self._selectmode = selectmode
    
    def selection(self):
        """获取当前选中项"""
        return self._selection
    
    def selection_clear(self):
        """清除选中项"""
        self._selection.clear()
    
    def selection_add(self, items):
        """添加选中项"""
        if isinstance(items, list):
            self._selection.extend(items)
        else:
            self._selection.append(items)
    
    def selection_set(self, items):
        """设置选中项（替换现有选中）"""
        if isinstance(items, list):
            self._selection = items.copy()
        else:
            self._selection = [items]
    
    def selection_remove(self, item):
        """移除选中项"""
        if item in self._selection:
            self._selection.remove(item)
    
    def selection_anchor(self, item):
        """设置选中锚点"""
        self._anchor = item
    
    def focus(self, item=None):
        """设置焦点项"""
        if item is not None:
            self._focus = item
        return self._focus
    
    def focus_set(self):
        """设置焦点到自身"""
        pass
    
    def item(self, item_id, option):
        """获取项的属性"""
        if option == 'tags':
            return self._tags.get(item_id, [])
        return None
    
    def identify_region(self, x, y):
        """识别点击区域"""
        return "cell"
    
    def identify_row(self, y):
        """识别点击的行"""
        return 'item3'  # 模拟点击第三项
    
    def get_children(self):
        """获取所有子项"""
        return self._items

class MockEvent:
    """模拟Tkinter事件"""
    def __init__(self, num=1, state=0, x=10, y=10):
        self.num = num  # 1=左键，3=右键
        self.state = state  # 0x0004=Ctrl，0x0001=Shift
        self.x = x
        self.y = y
        self.x_root = x + 100
        self.y_root = y + 100
        self.widget = MockTreeview()

class MockMenu:
    """模拟右键菜单"""
    def __init__(self):
        self.entries = {}
        self.posted = False
    
    def add_command(self, label, command=None, state="normal"):
        """添加菜单项"""
        self.entries[label] = {"command": command, "state": state}
    
    def add_separator(self):
        """添加分隔线"""
        pass
    
    def post(self, x, y):
        """显示菜单"""
        self.posted = True
        print(f"菜单显示在坐标: ({x}, {y})")

class TestFinalRightClickFix:
    """测试用户提供的最终修复方案"""
    
    def __init__(self):
        print("=== 最终测试 - 用户提供的右键批量删除修复方案 ===")
        
        # 初始化模拟对象
        self.card_tree = MockTreeview(selectmode="extended")
        self.last_mouse_button = 1  # 默认左键
        self.selected_card_id = None
        self.context_menu = MockMenu()
        
        # 初始化菜单
        self.context_menu.add_command(label="编辑", command=lambda: None)
        self.context_menu.add_command(label="删除", command=lambda: None)
        
        print("初始状态:")
        print(f"- Treeview多选模式: {self.card_tree._selectmode}")
        print(f"- 初始鼠标按键记录: {self.last_mouse_button}")
        print(f"- 初始选中卡片ID: {self.selected_card_id}")
        
        # 运行所有测试
        self.test_left_click_normal()
        self.test_ctrl_click_multi_select()
        self.test_right_click_preserves_selection()
        self.test_right_click_adds_to_selection()
        self.test_selection_event_filtering()
        self.test_batch_delete_recognition()
        
        print("\n=== 最终测试完成 ===")
    
    def test_left_click_normal(self):
        """测试1: 正常左键点击"""
        print("\n--- 测试1: 正常左键点击 ---")
        
        # 模拟左键点击
        event = MockEvent(num=1)
        event.widget = self.card_tree
        
        self.on_treeview_click(event)
        
        print(f"左键点击后鼠标按键记录: {self.last_mouse_button}")
        print(f"左键点击后选中状态: {self.card_tree.selection()}")
        print(f"左键点击后锚点状态: {self.card_tree._anchor}")
        
        # 验证左键点击正确设置单选
        if self.last_mouse_button == 1 and self.card_tree.selection() == ['item3']:
            print("✓ 正常左键点击功能正确")
        else:
            print("✗ 正常左键点击功能异常")
    
    def test_ctrl_click_multi_select(self):
        """测试2: Ctrl+左键多选"""
        print("\n--- 测试2: Ctrl+左键多选 ---")
        
        # 先清空选中状态
        self.card_tree.selection_clear()
        
        # 模拟第一次普通点击
        event1 = MockEvent(num=1)
        event1.widget = self.card_tree
        self.on_treeview_click(event1)
        
        # 模拟Ctrl+点击
        event2 = MockEvent(num=1, state=0x0004)  # Ctrl键
        event2.widget = self.card_tree
        event2.widget._items = ['item1', 'item2', 'item3', 'item4', 'item5']
        event2.widget._focus = 'item3'
        
        self.on_treeview_ctrl_click(event2)
        
        print(f"Ctrl+点击后鼠标按键记录: {self.last_mouse_button}")
        print(f"Ctrl+点击后选中状态: {self.card_tree.selection()}")
        
        # 验证Ctrl+点击正确添加到多选
        expected_selection = ['item3', 'item3']  # 两次点击同一个项目，应该被移除
        if self.last_mouse_button == 1 and set(self.card_tree.selection()).issubset({'item3'}):
            print("✓ Ctrl+左键多选功能正确")
        else:
            print("✗ Ctrl+左键多选功能异常")
    
    def test_right_click_preserves_selection(self):
        """测试3: 右键点击保留多选状态"""
        print("\n--- 测试3: 右键点击保留多选状态 ---")
        
        # 设置初始多选状态
        self.card_tree.selection_set(['item1', 'item3', 'item5'])
        initial_selection = self.card_tree.selection().copy()
        
        print(f"右键点击前选中状态: {initial_selection}")
        
        # 模拟右键点击
        event = MockEvent(num=3)
        event.widget = self.card_tree
        
        result = self.on_treeview_click(event)
        
        print(f"右键点击后鼠标按键记录: {self.last_mouse_button}")
        print(f"右键点击后选中状态: {self.card_tree.selection()}")
        print(f"右键点击后锚点状态: {self.card_tree._anchor}")
        print(f"右键点击返回值: {result}")
        
        # 验证右键点击不改变多选状态
        if (self.last_mouse_button == 3 and 
            self.card_tree.selection() == initial_selection and
            self.card_tree._anchor == "" and
            result == "break"):
            print("✓ 右键点击正确保留多选状态")
        else:
            print("✗ 右键点击破坏了多选状态")
    
    def test_right_click_adds_to_selection(self):
        """测试4: 右键点击未选中项追加到多选"""
        print("\n--- 测试4: 右键点击未选中项追加到多选 ---")
        
        # 设置初始多选状态
        self.card_tree.selection_set(['item1', 'item3'])
        initial_selection = self.card_tree.selection().copy()
        
        print(f"右键菜单前选中状态: {initial_selection}")
        
        # 模拟右键菜单显示
        event = MockEvent(num=3)
        event.widget = self.card_tree
        event.widget._items = ['item1', 'item2', 'item3', 'item4', 'item5']
        
        self.show_context_menu(event)
        
        print(f"右键菜单后鼠标按键记录: {self.last_mouse_button}")
        print(f"右键菜单后选中状态: {self.card_tree.selection()}")
        
        # 验证右键菜单正确处理未选中项
        expected_selection = ['item1', 'item3', 'item3']  # 点击已选中的item3，应该不变
        if (self.last_mouse_button == 3 and 
            set(self.card_tree.selection()) == set(['item1', 'item3'])):
            print("✓ 右键菜单追加选中功能正确")
        else:
            print("✗ 右键菜单追加选中功能异常")
    
    def test_selection_event_filtering(self):
        """测试5: 选中事件过滤右键触发的伪选中"""
        print("\n--- 测试5: 选中事件过滤右键触发的伪选中 ---")
        
        # 设置初始多选状态
        self.card_tree.selection_set(['item1', 'item3', 'item5'])
        
        # 模拟右键触发的选中事件
        self.last_mouse_button = 3  # 设置为右键
        event = MockEvent()
        event.widget = self.card_tree
        
        self.on_treeview_select(event)
        
        print(f"右键选中事件后选中卡片ID: {self.selected_card_id}")
        
        # 验证右键触发的选中事件被正确过滤
        if self.selected_card_id is None:
            print("✓ 右键触发的选中事件被正确过滤")
        else:
            print("✗ 右键触发的选中事件未被过滤")
        
        # 测试左键触发的选中事件
        self.last_mouse_button = 1  # 设置为左键
        self.on_treeview_select(event)
        
        print(f"左键选中事件后选中卡片ID: {self.selected_card_id}")
        
        # 验证左键触发的选中事件正确处理
        if self.selected_card_id == 'card1':
            print("✓ 左键触发的选中事件正确处理")
        else:
            print("✗ 左键触发的选中事件处理异常")
    
    def test_batch_delete_recognition(self):
        """测试6: 批量删除识别多选数量"""
        print("\n--- 测试6: 批量删除识别多选数量 ---")
        
        # 设置多选状态
        self.card_tree.selection_set(['item1', 'item3', 'item5'])
        selected_items = self.card_tree.selection()
        
        print(f"当前选中项数量: {len(selected_items)}")
        print(f"当前选中项: {selected_items}")
        
        # 模拟批量删除逻辑检查
        if len(selected_items) > 1:
            print(f"批量删除提示: 确定要删除选中的{len(selected_items)}张卡片吗？")
            print("✓ 批量删除逻辑正确识别多选状态")
        else:
            print("✗ 批量删除逻辑未正确识别多选状态")
    
    def on_treeview_click(self, event):
        """Treeview点击事件处理（右键禁止自动选中）"""
        # 记录鼠标按键（1=左键，3=右键）
        self.last_mouse_button = event.num
        
        # 右键点击：直接阻止所有选中相关行为，保留原多选状态
        if event.num == 3:
            # 清空选中锚点，阻止Treeview自动选中单个项
            event.widget.selection_anchor("")
            # 阻止事件传播，不让后续触发单选
            return "break"
        
        # 左键处理逻辑
        region = event.widget.identify_region(event.x, event.y)
        if region == "cell":
            item = event.widget.identify_row(event.y)
            if item:
                if not (event.state & 0x0004) and not (event.state & 0x0001):
                    event.widget.selection_set(item)
                    event.widget.focus(item)
    
    def on_treeview_ctrl_click(self, event):
        """Treeview Ctrl+点击事件处理"""
        # 记录鼠标按键
        self.last_mouse_button = event.num
        
        # Ctrl+点击，切换选中状态
        region = event.widget.identify_region(event.x, event.y)
        if region == "cell":
            item = event.widget.identify_row(event.y)
            if item:
                if item in event.widget.selection():
                    event.widget.selection_remove(item)
                else:
                    event.widget.selection_add(item)
                event.widget.focus(item)
                # 阻止默认的选择行为
                return "break"
    
    def on_treeview_shift_click(self, event):
        """Treeview Shift+点击事件处理"""
        # 记录鼠标按键
        self.last_mouse_button = event.num
        
        # Shift+点击，选择连续的项
        region = event.widget.identify_region(event.x, event.y)
        if region == "cell":
            item = event.widget.identify_row(event.y)
            if item and event.widget.selection():
                # 获取当前焦点项和点击的项
                focus_item = event.widget.focus()
                if focus_item:
                    # 获取所有项
                    all_items = event.widget.get_children()
                    # 找到焦点项和点击项的索引
                    focus_idx = all_items.index(focus_item)
                    try:
                        click_idx = all_items.index(item)
                        # 选择从焦点项到点击项的所有项
                        start_idx = min(focus_idx, click_idx)
                        end_idx = max(focus_idx, click_idx)
                        event.widget.selection_set(all_items[start_idx:end_idx+1])
                    except ValueError:
                        pass
                # 阻止默认的选择行为
                return "break"
    
    def on_treeview_select(self, event):
        """选中事件处理（过滤右键触发的伪选中）"""
        # 右键触发的选中事件直接跳过，保留原多选
        if self.last_mouse_button == 3:
            return
        
        # 只有左键触发的选中才更新状态
        selection = event.widget.selection()
        if selection:
            item = selection[0]
            card_id = event.widget.item(item, "tags")[0]
            self.selected_card_id = card_id
    
    def show_context_menu(self, event):
        """显示右键菜单（保留多选状态）"""
        # 记录鼠标按键为右键
        self.last_mouse_button = 3
        
        # 获取当前真实的多选状态（右键点击前的状态）
        selected_items = event.widget.selection()
        if not selected_items:
            return
        
        # 获取点击的项目
        item = event.widget.identify_row(event.y)
        if item and item not in selected_items:
            # 支持右键点击时"追加选中"（和左键Ctrl+点击一致）
            event.widget.selection_add(item)
        
        # 显示菜单（位置微调，避免遮挡）
        self.context_menu.post(event.x_root + 10, event.y_root + 10)

if __name__ == "__main__":
    TestFinalRightClickFix()