"""
Core types - データクラスとEnum定義
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict


class FocusRestoreMethod(Enum):
    """フォーカス復帰方法の列挙"""
    SIMPLE = "simple"
    ENHANCED = "enhanced" 
    FORCE = "force"


@dataclass
class HotkeyConfig:
    """ホットキー設定データクラス"""
    target_keys: List[str]
    modifiers: Dict[str, bool]
    enabled: bool


@dataclass
class FocusConfig:
    """フォーカス復帰設定データクラス"""
    enabled: bool = True
    method: FocusRestoreMethod = FocusRestoreMethod.ENHANCED
    delay: int = 50
    debug: bool = False


@dataclass
class ButtonConfig:
    """ボタン設定データクラス"""
    key: str
    label: str
    icon: str