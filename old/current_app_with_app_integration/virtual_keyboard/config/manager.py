"""
Configuration Manager - 設定管理の実装
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox

from ..core.interfaces import IConfigManager
from ..core.types import HotkeyConfig, FocusConfig, FocusRestoreMethod

# Windows API Constants
MOD_ALT = 0x0001
MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

logger = logging.getLogger(__name__)


class ConfigManager(IConfigManager):
    """設定管理の実装クラス"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        default_config = {
            "hotkeys": {
                "set1": {
                    "targetKeys": ["F13", "F14", "F15", "F16", "F17", "F18"],
                    "modifiers": {"shift": False, "ctrl": False, "alt": False, "space": False},
                    "enabled": False
                },
                "set2": {
                    "targetKeys": ["F19", "F20", "F21", "F22", "F23", "F24"],
                    "modifiers": {"shift": False, "ctrl": False, "alt": False, "space": False},
                    "enabled": False
                }
            },
            "triggerKeys": ["F1", "F2", "F3", "F4", "F5", "F6"],
            "focusRestore": {
                "enabled": True,
                "method": "enhanced",
                "delay": 50,
                "debug": False
            },
            "floatingWindow": {
                "enabled": True,
                "position": {"x": 100, "y": 100},
                "buttons": [],
                "layout": {
                    "buttonsPerRow": 3,
                    "buttonSize": {
                        "width": 70,
                        "height": 50
                    }
                }
            },
            "appearance": {
                "mode": "Light"
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    logger.info(f"Config loaded from {self.config_path}")
                    
                    # ボタンデータの検証・修正
                    if self._validate_and_fix_config(loaded_config):
                        # 修正があった場合は保存
                        self.save_config(loaded_config)
                        logger.info("Config validated and fixed")
                    
                    return loaded_config
            else:
                self.save_config(default_config)
                logger.info(f"Default config created at {self.config_path}")
                return default_config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return default_config
    
    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """設定ファイルを保存"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.config = config
            logger.info(f"Config saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def _validate_and_fix_config(self, config: Dict[str, Any]) -> bool:
        """設定データを検証・修正（修正があった場合Trueを返す）"""
        fixed = False
        
        try:
            # フローティングウィンドウのボタンを検証
            if "floatingWindow" in config and "buttons" in config["floatingWindow"]:
                buttons = config["floatingWindow"]["buttons"]
                if isinstance(buttons, list):
                    for i, button in enumerate(buttons):
                        if self._validate_and_fix_button(button, f"config.floatingWindow.buttons[{i}]"):
                            fixed = True
            
            return fixed
        except Exception as e:
            logger.error(f"Error validating config: {e}")
            return False
    
    def _validate_and_fix_button(self, button: Dict[str, Any], location: str = "unknown") -> bool:
        """ボタンデータを検証・修正（修正があった場合Trueを返す）"""
        fixed = False
        
        try:
            # 色の値を検証・修正
            if "color" in button:
                original_color = button["color"]
                button["color"] = self._validate_color(button["color"], "transparent")
                if button["color"] != original_color:
                    logger.warning(f"Fixed invalid color '{original_color}' -> '{button['color']}' at {location}")
                    fixed = True
            
            if "highlightColor" in button:
                original_color = button["highlightColor"]
                button["highlightColor"] = self._validate_color(button["highlightColor"], "")
                if button["highlightColor"] != original_color:
                    logger.warning(f"Fixed invalid highlightColor '{original_color}' -> '{button['highlightColor']}' at {location}")
                    fixed = True
            
            # 必須フィールドの補完
            required_fields = {
                "key": "F13",
                "label": "",
                "icon": "",
                "toggleHighlight": False,
                "modifiers": {
                    "ctrl": False,
                    "shift": False,
                    "alt": False,
                    "win": False
                }
            }
            
            for field, default_value in required_fields.items():
                if field not in button:
                    button[field] = default_value
                    logger.warning(f"Added missing field '{field}' at {location}")
                    fixed = True
            
            # modifiersの検証
            if isinstance(button.get("modifiers"), dict):
                modifiers = button["modifiers"]
                for key in ["ctrl", "shift", "alt", "win"]:
                    if key not in modifiers:
                        modifiers[key] = False
                        fixed = True
            
            return fixed
            
        except Exception as e:
            logger.error(f"Error fixing button at {location}: {e}")
            return False
    
    def _validate_color(self, color_value, default_value):
        """色の値を検証・修正"""
        if not color_value:
            return default_value
        
        # 透明とdefaultは有効
        if color_value in ["transparent", "default"]:
            return color_value
        
        # HEX色の検証
        if isinstance(color_value, str) and color_value.startswith("#"):
            # 正しいHEX形式かチェック
            hex_part = color_value[1:]
            if len(hex_part) == 6 and all(c in "0123456789ABCDEFabcdef" for c in hex_part):
                return color_value
            else:
                logger.warning(f"Invalid hex color '{color_value}', using default")
                return default_value
        
        # 色名の場合
        valid_color_names = ["red", "green", "blue", "yellow", "orange", "purple", "gray", "grey", "black", "white"]
        if isinstance(color_value, str) and color_value.lower() in valid_color_names:
            return color_value
        
        logger.warning(f"Invalid color value '{color_value}', using default")
        return default_value
    
    def get_hotkey_config(self, set_name: str) -> Optional[HotkeyConfig]:
        """ホットキー設定を取得"""
        try:
            hotkey_data = self.config["hotkeys"][set_name]
            return HotkeyConfig(
                target_keys=hotkey_data["targetKeys"],
                modifiers=hotkey_data["modifiers"],
                enabled=hotkey_data["enabled"]
            )
        except KeyError:
            return None
    
    def get_focus_config(self) -> FocusConfig:
        """フォーカス設定を取得"""
        try:
            focus_data = self.config.get("focusRestore", {})
            return FocusConfig(
                enabled=focus_data.get("enabled", True),
                method=FocusRestoreMethod(focus_data.get("method", "enhanced")),
                delay=focus_data.get("delay", 50),
                debug=focus_data.get("debug", False)
            )
        except (KeyError, ValueError):
            return FocusConfig()
    
    def get_modifiers_value(self, modifiers_dict: Dict[str, bool]) -> int:
        """修飾キー辞書からWindows API用の値を取得"""
        value = 0
        if modifiers_dict.get("shift", False):
            value |= MOD_SHIFT
        if modifiers_dict.get("ctrl", False):
            value |= MOD_CTRL
        if modifiers_dict.get("alt", False):
            value |= MOD_ALT
        if modifiers_dict.get("space", False):
            value |= MOD_WIN
        return value
    
    def key_name_to_vk(self, key_name: str) -> int:
        """キー名をVKコードに変換"""
        if key_name.startswith("F") and key_name[1:].isdigit():
            f_num = int(key_name[1:])
            if 1 <= f_num <= 12:
                return 0x70 + f_num - 1
            elif 13 <= f_num <= 24:
                return 0x7C + f_num - 13
        return 0x7C
    
    def export_config(self, export_path: str = None) -> bool:
        """設定をファイルにエクスポート"""
        try:
            if export_path is None:
                # ファイル選択ダイアログを表示
                export_path = filedialog.asksaveasfilename(
                    title="設定をエクスポート",
                    defaultextension=".json",
                    filetypes=[
                        ("JSON files", "*.json"),
                        ("All files", "*.*")
                    ],
                    initialname=f"VirtualKeyboard_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                
                if not export_path:
                    return False
            
            # 設定データにメタデータを追加
            export_data = {
                "metadata": {
                    "export_date": datetime.now().isoformat(),
                    "version": "1.0",
                    "source": "VirtualKeyboard"
                },
                "config": self.config.copy()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Config exported to {export_path}")
            messagebox.showinfo("エクスポート完了", f"設定をエクスポートしました:\n{export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            messagebox.showerror("エクスポートエラー", f"設定のエクスポートに失敗しました:\n{e}")
            return False
    
    def import_config(self, import_path: str = None) -> bool:
        """設定をファイルからインポート"""
        try:
            if import_path is None:
                # ファイル選択ダイアログを表示
                import_path = filedialog.askopenfilename(
                    title="設定をインポート",
                    filetypes=[
                        ("JSON files", "*.json"),
                        ("All files", "*.*")
                    ]
                )
                
                if not import_path:
                    return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # インポートデータの形式を確認
            if "config" in import_data and "metadata" in import_data:
                # メタデータ付きエクスポート形式
                config_data = import_data["config"]
                metadata = import_data["metadata"]
                logger.info(f"Importing config with metadata: {metadata}")
            else:
                # 直接設定データ形式
                config_data = import_data
            
            # 設定を保存
            if self.save_config(config_data):
                logger.info(f"Config imported from {import_path}")
                messagebox.showinfo("インポート完了", f"設定をインポートしました:\n{import_path}\n\n3秒後に自動再起動します。")
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            messagebox.showerror("インポートエラー", f"設定のインポートに失敗しました:\n{e}")
            return False
    
    def update_appearance_mode(self, mode: str) -> bool:
        """外観モードを更新"""
        try:
            if "appearance" not in self.config:
                self.config["appearance"] = {}
            
            self.config["appearance"]["mode"] = mode
            return self.save_config()
            
        except Exception as e:
            logger.error(f"Failed to update appearance mode: {e}")
            return False