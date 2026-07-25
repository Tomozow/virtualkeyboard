"""
Focus Manager - フォーカス管理サービス
"""

import threading
import time
import logging
from typing import Optional
import win32con
import win32gui
from ctypes import windll

from ..core.interfaces import IFocusManager
from ..core.types import FocusConfig, FocusRestoreMethod

user32 = windll.user32
kernel32 = windll.kernel32

logger = logging.getLogger(__name__)


class FocusManager(IFocusManager):
    """フォーカス管理の実装クラス"""
    
    def __init__(self, config: FocusConfig):
        self.config = config
        self.last_focus_window = None
        self.monitoring = False
        self.monitor_thread = None
        self.excluded_windows = set()  # 除外するウィンドウIDのセット
    
    def restore_focus_simple(self, target_window: int) -> bool:
        """シンプルなフォーカス復帰"""
        try:
            if not win32gui.IsWindow(target_window):
                return False
            
            win32gui.SetForegroundWindow(target_window)
            win32gui.BringWindowToTop(target_window)
            if self.config.delay > 0:
                time.sleep(min(self.config.delay / 1000.0, 0.02))  # 最大20msに制限
            
            current = win32gui.GetForegroundWindow()
            success = current == target_window
            
            if self.config.debug:
                logger.info(f"Simple focus restore: {'SUCCESS' if success else 'FAILED'}")
            
            return success
        except Exception as e:
            logger.error(f"Simple focus restore error: {e}")
            return False
    
    def restore_focus_enhanced(self, target_window: int) -> bool:
        """拡張フォーカス復帰（Alt+Tab方式）"""
        try:
            if not win32gui.IsWindow(target_window):
                return False
            
            # Alt キーを使用した強制的なフォーカス切り替え
            user32.keybd_event(0x12, 0, 0, 0)  # Alt down
            time.sleep(0.005)  # Altキー待機を最小化
            
            win32gui.SetForegroundWindow(target_window)
            win32gui.BringWindowToTop(target_window)
            
            user32.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)  # Alt up
            
            if self.config.delay > 0:
                time.sleep(min(self.config.delay / 1000.0, 0.02))  # 最大20msに制限
            
            current = win32gui.GetForegroundWindow()
            success = current == target_window
            
            if self.config.debug:
                logger.info(f"Enhanced focus restore: {'SUCCESS' if success else 'FAILED'}")
            
            return success
        except Exception as e:
            logger.error(f"Enhanced focus restore error: {e}")
            return False
    
    def restore_focus_force(self, target_window: int) -> bool:
        """強制フォーカス復帰（複数の方法を組み合わせ）"""
        try:
            if not win32gui.IsWindow(target_window):
                return False
            
            methods_tried = []
            
            # 方法1: 最小化して復元
            try:
                win32gui.ShowWindow(target_window, win32con.SW_MINIMIZE)
                time.sleep(0.01)  # 最小化化
                win32gui.ShowWindow(target_window, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target_window)
                methods_tried.append("minimize-restore")
            except:
                pass
            
            # 方法2: AttachThreadInput を使用
            try:
                current_thread = kernel32.GetCurrentThreadId()
                target_thread = user32.GetWindowThreadProcessId(target_window, None)
                if target_thread != current_thread:
                    user32.AttachThreadInput(current_thread, target_thread, True)
                    win32gui.SetForegroundWindow(target_window)
                    user32.AttachThreadInput(current_thread, target_thread, False)
                    methods_tried.append("attach-thread")
            except:
                pass
            
            # 方法3: ShowWindow + SetFocus
            try:
                win32gui.ShowWindow(target_window, win32con.SW_SHOW)
                win32gui.SetFocus(target_window)
                methods_tried.append("show-setfocus")
            except:
                pass
            
            if self.config.delay > 0:
                time.sleep(min(self.config.delay / 1000.0, 0.02))  # 最大20msに制限
            
            current = win32gui.GetForegroundWindow()
            success = current == target_window
            
            if self.config.debug:
                methods_str = ", ".join(methods_tried)
                logger.info(f"Force focus restore: {'SUCCESS' if success else 'FAILED'} - Methods: [{methods_str}]")
            
            return success
        except Exception as e:
            logger.error(f"Force focus restore error: {e}")
            return False
    
    def restore_focus(self, target_window: int) -> bool:
        """設定に基づいてフォーカスを復帰"""
        if not self.config.enabled or not target_window:
            return False
        
        success = False
        
        if self.config.method == FocusRestoreMethod.SIMPLE:
            success = self.restore_focus_simple(target_window)
        elif self.config.method == FocusRestoreMethod.ENHANCED:
            success = self.restore_focus_enhanced(target_window)
            if not success:
                success = self.restore_focus_simple(target_window)
        elif self.config.method == FocusRestoreMethod.FORCE:
            success = self.restore_focus_force(target_window)
            if not success:
                success = self.restore_focus_enhanced(target_window)
            if not success:
                success = self.restore_focus_simple(target_window)
        
        return success
    
    def add_excluded_window(self, window_id: int) -> None:
        """除外するウィンドウIDを追加"""
        if window_id:
            self.excluded_windows.add(window_id)
            if self.config.debug:
                logger.info(f"Added window {window_id} to exclusion list")
    
    def remove_excluded_window(self, window_id: int) -> None:
        """除外するウィンドウIDを削除"""
        self.excluded_windows.discard(window_id)
        if self.config.debug:
            logger.info(f"Removed window {window_id} from exclusion list")
    
    def start_monitoring(self) -> None:
        """フォーカス監視を開始"""
        if self.monitoring:
            logger.info("Focus monitoring already running")
            return
        
        try:
            # 現在のフォーカスウィンドウを初期値として設定
            current_window = win32gui.GetForegroundWindow()
            if current_window and win32gui.IsWindow(current_window):
                try:
                    window_title = win32gui.GetWindowText(current_window)
                    # バーチャルキーボード関連ウィンドウでなければ初期値として設定
                    is_excluded = (current_window in self.excluded_windows or 
                                 "Virtual Key" in window_title or 
                                 "[VKEYPAD]" in window_title)
                    if not is_excluded:
                        self.last_focus_window = current_window
                        logger.info(f"Initial focus window set: {current_window} - '{window_title}'")
                except Exception as e:
                    logger.warning(f"Could not get initial window title: {e}")
                    if current_window not in self.excluded_windows:
                        self.last_focus_window = current_window
            
            self.monitoring = True
            
            def monitor():
                last_window = None
                logger.info("Focus monitor thread started")
                while self.monitoring:
                    try:
                        current = win32gui.GetForegroundWindow()
                        if current and current != last_window:
                            # ウィンドウが変わったときのみ処理
                            if win32gui.IsWindow(current):
                                try:
                                    window_title = win32gui.GetWindowText(current)
                                    
                                    # 除外リストまたはバーチャルキーボード関連のウィンドウをチェック
                                    is_excluded = (current in self.excluded_windows or 
                                                 "Virtual Key" in window_title or 
                                                 "Virtual Keyboard" in window_title or
                                                 "[VKEYPAD]" in window_title or
                                                 "🎹" in window_title)
                                    
                                    if not is_excluded:
                                        self.last_focus_window = current
                                        if self.config.debug:
                                            logger.info(f"Focus monitor: Window {current} - '{window_title}'")
                                    elif self.config.debug:
                                        logger.info(f"Focus monitor: Ignoring virtual keyboard window {current} - '{window_title}'")
                                except Exception as e:
                                    logger.warning(f"Error getting window title for {current}: {e}")
                                    if current not in self.excluded_windows:
                                        self.last_focus_window = current
                            
                            last_window = current
                    except Exception as e:
                        logger.error(f"Focus monitor error: {e}")
                        if self.config.debug:
                            import traceback
                            logger.debug(traceback.format_exc())
                    
                    time.sleep(0.1)  # 監視間隔を短縮
                
                logger.info("Focus monitor thread stopped")
            
            self.monitor_thread = threading.Thread(target=monitor, daemon=True)
            self.monitor_thread.start()
            logger.info("Focus monitoring started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start focus monitoring: {e}")
            self.monitoring = False
            import traceback
            logger.error(traceback.format_exc())
    
    def stop_monitoring(self) -> None:
        """フォーカス監視を停止"""
        self.monitoring = False
        logger.info("Focus monitoring stopped")
    
    def get_last_focus_window(self) -> Optional[int]:
        """最後のフォーカスウィンドウを取得（Virtual Keyboard関連を除外）"""
        # まず現在のlast_focus_windowが有効かチェック
        if self.last_focus_window and win32gui.IsWindow(self.last_focus_window):
            try:
                window_title = win32gui.GetWindowText(self.last_focus_window)
                # Virtual Keyboard関連ウィンドウでないかチェック
                is_excluded = (self.last_focus_window in self.excluded_windows or 
                             "Virtual Key" in window_title or 
                             "Virtual Keyboard" in window_title or
                             "[VKEYPAD]" in window_title or
                             "🎹" in window_title)
                
                if not is_excluded:
                    logger.info(f"Returning valid last_focus_window: {self.last_focus_window} - '{window_title}'")
                    return self.last_focus_window
                else:
                    logger.warning(f"Clearing invalid last_focus_window: {self.last_focus_window} - '{window_title}'")
                    self.last_focus_window = None
                    
            except Exception as e:
                logger.warning(f"Error validating last_focus_window {self.last_focus_window}: {e}")
                self.last_focus_window = None
        
        logger.info("No valid last_focus_window available")
        return None
    
    def get_current_window_as_fallback(self) -> Optional[int]:
        """現在のフォーカスウィンドウをフォールバックとして取得（ドラッグ時のみ使用）"""
        try:
            current = win32gui.GetForegroundWindow()
            if current and win32gui.IsWindow(current):
                window_title = win32gui.GetWindowText(current)
                is_excluded = (current in self.excluded_windows or 
                             "Virtual Key" in window_title or 
                             "Virtual Keyboard" in window_title or
                             "[VKEYPAD]" in window_title or
                             "🎹" in window_title)
                
                if not is_excluded:
                    logger.info(f"Using current window as fallback: {current} - '{window_title}'")
                    return current
        except Exception as e:
            logger.warning(f"Error getting current window as fallback: {e}")
        
        return None