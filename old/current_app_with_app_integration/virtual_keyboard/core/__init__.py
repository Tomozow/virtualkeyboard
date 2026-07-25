"""
Core module - 基本インターフェースと型定義
"""

from .interfaces import (
    IConfigManager,
    IHotkeyManager, 
    IKeySender,
    IFocusManager
)

from .types import (
    FocusRestoreMethod,
    HotkeyConfig,
    FocusConfig,
    ButtonConfig
)

__all__ = [
    'IConfigManager',
    'IHotkeyManager', 
    'IKeySender',
    'IFocusManager',
    'FocusRestoreMethod',
    'HotkeyConfig',
    'FocusConfig',
    'ButtonConfig'
]