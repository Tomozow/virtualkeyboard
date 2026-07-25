"""
Core interfaces - 基本インターフェースの定義
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from .types import HotkeyConfig, FocusConfig


class IConfigManager(ABC):
    """設定管理インターフェース"""
    
    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def save_config(self, config: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def get_hotkey_config(self, set_name: str) -> Optional[HotkeyConfig]:
        pass
    
    @abstractmethod
    def get_focus_config(self) -> FocusConfig:
        pass


class IHotkeyManager(ABC):
    """ホットキー管理インターフェース"""
    
    @abstractmethod
    def register_hotkey(self, hotkey_id: int, modifiers: int, vk_code: int, description: str) -> bool:
        pass
    
    @abstractmethod
    def unregister_hotkey(self, hotkey_id: int) -> bool:
        pass
    
    @abstractmethod
    def unregister_all(self) -> None:
        pass


class IKeySender(ABC):
    """キー送信インターフェース"""
    
    @abstractmethod
    def send_key(self, vk_code: int) -> bool:
        pass
    
    @staticmethod
    @abstractmethod
    def vk_code_to_name(vk_code: int) -> str:
        pass


class IFocusManager(ABC):
    """フォーカス管理インターフェース"""
    
    @abstractmethod
    def restore_focus(self, target_window: int) -> bool:
        pass
    
    @abstractmethod
    def start_monitoring(self) -> None:
        pass
    
    @abstractmethod
    def stop_monitoring(self) -> None:
        pass
    
    @abstractmethod
    def get_last_focus_window(self) -> Optional[int]:
        pass