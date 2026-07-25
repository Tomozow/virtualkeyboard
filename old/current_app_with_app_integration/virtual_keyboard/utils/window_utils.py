"""
Window utilities for enumerating and managing system windows
"""

import win32gui
import win32process
import psutil
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    """ウィンドウ情報を格納するデータクラス"""
    hwnd: int
    title: str
    class_name: str
    process_name: str
    process_id: int
    exe_path: str
    is_visible: bool
    is_enabled: bool
    
    def __str__(self):
        return f"{self.process_name} - {self.title}"
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'hwnd': self.hwnd,
            'title': self.title,
            'class_name': self.class_name,
            'process_name': self.process_name,
            'process_id': self.process_id,
            'exe_path': self.exe_path,
            'is_visible': self.is_visible,
            'is_enabled': self.is_enabled
        }


class WindowEnumerator:
    """システムウィンドウの列挙と情報取得"""
    
    # 除外するウィンドウの条件
    EXCLUDED_TITLES = [
        "Virtual Key", "Virtual Keyboard", "[VKEYPAD]", "🎹",
        "Program Manager", "Desktop", ""
    ]
    
    EXCLUDED_CLASSES = [
        "Shell_TrayWnd", "DV2ControlHost", "MsgrIMEWindowClass", 
        "SysShadow", "Button", "Windows.UI.Core.CoreWindow"
    ]
    
    @staticmethod
    def _should_exclude_window(hwnd: int, title: str, class_name: str) -> bool:
        """ウィンドウを除外すべきかどうかを判定"""
        # タイトルによる除外
        for excluded_title in WindowEnumerator.EXCLUDED_TITLES:
            if excluded_title in title:
                return True
        
        # クラス名による除外
        if class_name in WindowEnumerator.EXCLUDED_CLASSES:
            return True
        
        # 非表示ウィンドウを除外
        if not win32gui.IsWindowVisible(hwnd):
            return True
        
        # 無効化されたウィンドウを除外
        if not win32gui.IsWindowEnabled(hwnd):
            return True
        
        return False
    
    @staticmethod
    def _get_window_info(hwnd: int) -> Optional[WindowInfo]:
        """ウィンドウハンドルから詳細情報を取得"""
        try:
            # 基本情報取得
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            
            # プロセス情報取得
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                exe_path = process.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                process_name = f"PID_{pid}"
                exe_path = "アクセス不可"
            
            # ウィンドウ状態
            is_visible = win32gui.IsWindowVisible(hwnd)
            is_enabled = win32gui.IsWindowEnabled(hwnd)
            
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=class_name,
                process_name=process_name,
                process_id=pid,
                exe_path=exe_path,
                is_visible=is_visible,
                is_enabled=is_enabled
            )
            
        except Exception as e:
            logger.debug(f"Error getting window info for {hwnd}: {e}")
            return None
    
    @staticmethod
    def get_all_windows(include_hidden: bool = False) -> List[WindowInfo]:
        """全ウィンドウを取得"""
        windows = []
        
        def enum_callback(hwnd, lparam):
            try:
                window_info = WindowEnumerator._get_window_info(hwnd)
                if window_info:
                    # 除外条件をチェック
                    if not include_hidden and WindowEnumerator._should_exclude_window(
                        hwnd, window_info.title, window_info.class_name
                    ):
                        return True
                    
                    windows.append(window_info)
            except Exception as e:
                logger.debug(f"Error in enum_callback for {hwnd}: {e}")
            
            return True
        
        try:
            win32gui.EnumWindows(enum_callback, 0)
        except Exception as e:
            logger.error(f"Error enumerating windows: {e}")
        
        # タイトルとプロセス名でソート
        windows.sort(key=lambda w: (w.process_name.lower(), w.title.lower()))
        return windows
    
    @staticmethod
    def get_visible_windows() -> List[WindowInfo]:
        """表示されているウィンドウのみ取得"""
        return WindowEnumerator.get_all_windows(include_hidden=False)
    
    @staticmethod
    def find_windows_by_process(process_name: str) -> List[WindowInfo]:
        """プロセス名でウィンドウを検索"""
        all_windows = WindowEnumerator.get_all_windows(include_hidden=True)
        return [w for w in all_windows if process_name.lower() in w.process_name.lower()]
    
    @staticmethod
    def find_windows_by_title(title_pattern: str) -> List[WindowInfo]:
        """タイトル（部分一致）でウィンドウを検索"""
        all_windows = WindowEnumerator.get_all_windows(include_hidden=True)
        return [w for w in all_windows if title_pattern.lower() in w.title.lower()]
    
    @staticmethod
    def find_windows_by_class(class_name: str) -> List[WindowInfo]:
        """クラス名でウィンドウを検索"""
        all_windows = WindowEnumerator.get_all_windows(include_hidden=True)
        return [w for w in all_windows if class_name.lower() in w.class_name.lower()]
    
    @staticmethod
    def get_window_by_hwnd(hwnd: int) -> Optional[WindowInfo]:
        """ウィンドウハンドルから情報を取得"""
        try:
            if win32gui.IsWindow(hwnd):
                return WindowEnumerator._get_window_info(hwnd)
        except Exception as e:
            logger.debug(f"Error getting window by hwnd {hwnd}: {e}")
        return None


class WindowMatcher:
    """ウィンドウマッチング用のユーティリティ"""
    
    @staticmethod
    def match_window(window_info: WindowInfo, criteria: Dict[str, Any]) -> bool:
        """指定された条件でウィンドウがマッチするかチェック"""
        if not window_info or not criteria:
            return False
        
        match_type = criteria.get('matchType', 'any')  # any, all, windowTitle, processName, className
        
        matches = []
        
        # ウィンドウタイトルマッチング
        if 'windowTitle' in criteria and criteria['windowTitle']:
            title_match = WindowMatcher._string_match(
                window_info.title, criteria['windowTitle'], criteria.get('caseSensitive', False)
            )
            matches.append(('windowTitle', title_match))
        
        # プロセス名マッチング  
        if 'processName' in criteria and criteria['processName']:
            process_match = WindowMatcher._string_match(
                window_info.process_name, criteria['processName'], criteria.get('caseSensitive', False)
            )
            matches.append(('processName', process_match))
        
        # クラス名マッチング
        if 'className' in criteria and criteria['className']:
            class_match = WindowMatcher._string_match(
                window_info.class_name, criteria['className'], criteria.get('caseSensitive', False)
            )
            matches.append(('className', class_match))
        
        # 実行ファイルパスマッチング
        if 'exePath' in criteria and criteria['exePath']:
            exe_match = WindowMatcher._string_match(
                window_info.exe_path, criteria['exePath'], criteria.get('caseSensitive', False)
            )
            matches.append(('exePath', exe_match))
        
        # マッチング結果の評価
        if not matches:
            return False
        
        if match_type == 'any':
            return any(match[1] for match in matches)
        elif match_type == 'all':
            return all(match[1] for match in matches)
        else:
            # 特定の条件のみでマッチング
            specific_matches = [match[1] for match in matches if match[0] == match_type]
            return any(specific_matches) if specific_matches else False
    
    @staticmethod
    def _string_match(target: str, pattern: str, case_sensitive: bool = False) -> bool:
        """文字列マッチング（部分一致）"""
        if not target or not pattern:
            return False
        
        if not case_sensitive:
            target = target.lower()
            pattern = pattern.lower()
        
        return pattern in target


# 使用例とテスト用の関数
def print_all_windows():
    """全ウィンドウ一覧を出力（デバッグ用）"""
    windows = WindowEnumerator.get_visible_windows()
    print(f"Found {len(windows)} visible windows:")
    for i, window in enumerate(windows):
        print(f"{i+1:2d}. {window.process_name:20s} | {window.title[:50]:50s} | {window.class_name}")


if __name__ == "__main__":
    # テスト実行
    print_all_windows()