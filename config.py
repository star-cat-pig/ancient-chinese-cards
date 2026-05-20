#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局唯一配置文件 - 全程序所有配置唯一来源
修改版本、名称、仓库地址，只改这里！
"""
import os
import json
import sys
from typing import Optional

# ===================== 核心全局配置（唯一修改处）=====================
APP_NAME = "古文卡片学习软件"
MAIN_EXE_NAME = "cards.exe"          # 统一主程序exe名称
UPDATE_EXE_NAME = "update.exe"       # 统一更新程序exe名称
CURRENT_VERSION = "2.0"               # 全局唯一版本号，更新只改这里
GITHUB_OWNER = "star-cat-pig"         # 仓库所有者
GITHUB_REPO = "ancient-chinese-cards" # 仓库名称
# ======================================================================

# 路径相关常量（无需修改）
ASSETS_DIR = "assets"
ICON_FILE = "icon.ico"
DATA_FILE_NAME = "cards.json"  # 卡片数据文件统一名称
ENCRYPT_KEY = b"ancient_chinese_cards_2024"  # 加密密钥统一管理
TEMP_UPDATE_INFO_FILE = "card_update_info.json"
TEMP_UPDATE_CONFIG_FILE = "card_update_config.json"

# -------------------------- 平台兼容路径函数 --------------------------
def get_main_exe_dir() -> str:
    """统一获取主程序所在目录（兼容开发/打包环境）"""
    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_update_exe_path() -> str:
    """统一获取update.exe路径"""
    main_dir = get_main_exe_dir()
    update_exe = os.path.join(main_dir, UPDATE_EXE_NAME)
    
    # 开发环境降级：如果exe不存在，返回py脚本
    if not os.path.exists(update_exe):
        dev_update_script = os.path.join(get_main_exe_dir(), "update.py")
        if os.path.exists(dev_update_script):
            return dev_update_script
    return update_exe

def get_icon_path() -> str:
    """统一获取图标路径"""
    return os.path.join(get_main_exe_dir(), ASSETS_DIR, ICON_FILE)

def get_user_data_dir() -> str:
    """
    统一获取跨平台用户数据目录（彻底解决card_manager/settings_manager重复代码问题）
    """
    home_dir = os.path.expanduser("~")
    if os.name == "nt":  # Windows
        app_data_dir = os.getenv("LOCALAPPDATA", os.path.join(home_dir, "AppData", "Local"))
        return os.path.join(app_data_dir, "ancient_chinese_cards")
    elif os.name == "posix":  # Mac/Linux
        if sys.platform == "darwin":
            return os.path.join(home_dir, "Library", "Application Support", "ancient_chinese_cards")
        else:
            return os.path.join(home_dir, ".config", "ancient_chinese_cards")
    else:
        # 其他系统兜底
        return os.path.join(home_dir, ".ancient_chinese_cards")

def generate_temp_update_config(save_path: Optional[str] = None) -> str:
    """
    【核心解决update同步问题】生成临时配置文件，供独立update.exe读取
    主程序调用update.exe前，先调用这个方法生成配置文件，通过--config参数传给update
    """
    if not save_path:
        save_path = os.path.join(get_main_exe_dir(), TEMP_UPDATE_CONFIG_FILE)
    
    # 把所有需要传给update的配置打包
    config_data = {
        "github_owner": GITHUB_OWNER,
        "github_repo": GITHUB_REPO,
        "current_version": CURRENT_VERSION,
        "app_name": APP_NAME,
        "main_exe_name": MAIN_EXE_NAME,
        "main_exe_dir": get_main_exe_dir(),
        "icon_relative_path": os.path.join(ASSETS_DIR, ICON_FILE)
    }
    
    # 写入临时文件
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    return save_path