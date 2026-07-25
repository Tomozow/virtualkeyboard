"""
Hotkey Manager - ホットキー管理サービス
"""

import threading
import time
import logging
from typing import Optional, Callable
import win32con
import win32gui
from ctypes import windll

from ..core.interfaces import IHotkeyManager

user32 = windll.user32
kernel32 = windll.kernel32

logger = logging.getLogger(__name__)


class HotkeyManager(IHotkeyManager):
    """ホットキー管理の実装クラス"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.hotkeys = {}
        self.callback = callback
        self.hwnd = None
        self.running = False
        self.thread = None
    
    def create_message_window(self) -> bool:
        """メッセージ受信用の隠しウィンドウを作成"""
        try:
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = self.wnd_proc_wrapper
            wc.lpszClassName = "VirtualKeyboardHotkey"
            wc.hInstance = win32gui.GetModuleHandle(None)
            
            try:
                class_atom = win32gui.RegisterClass(wc)
            except:
                pass  # 既に登録済みの場合
            
            self.hwnd = win32gui.CreateWindow(
                "VirtualKeyboardHotkey", "Hotkey Window", 0,
                0, 0, 0, 0, 0, 0, wc.hInstance, None
            )
            
            return self.hwnd is not None
        except Exception as e:
            logger.error(f"Failed to create message window: {e}")
            return False
    
    def wnd_proc_wrapper(self, hwnd, msg, wparam, lparam):
        """Windowsプロシージャラッパー"""
        if msg == win32con.WM_HOTKEY:
            hotkey_id = wparam
            if hotkey_id in self.hotkeys and self.callback:
                threading.Thread(
                    target=self.callback,
                    args=(hotkey_id, self.hotkeys[hotkey_id]),
                    daemon=True
                ).start()
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        else:
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
    
    def register_hotkey(self, hotkey_id: int, modifiers: int, vk_code: int, description: str = "") -> bool:
        """ホットキーを登録"""
        try:
            if self.hwnd is None:
                if not self.create_message_window():
                    return False
            
            if hotkey_id in self.hotkeys:
                self.unregister_hotkey(hotkey_id)
            
            result = user32.RegisterHotKey(self.hwnd, hotkey_id, modifiers, vk_code)
            
            if result:
                self.hotkeys[hotkey_id] = {
                    'modifiers': modifiers,
                    'vk_code': vk_code,
                    'description': description,
                    'target_key': None
                }
                logger.info(f"Registered hotkey {hotkey_id}: {description}")
                return True
            else:
                error = kernel32.GetLastError()
                logger.error(f"Failed to register hotkey {hotkey_id}: Error {error}")
                return False
        except Exception as e:
            logger.error(f"Exception in register_hotkey: {e}")
            return False
    
    def unregister_hotkey(self, hotkey_id: int) -> bool:
        """ホットキーの登録解除"""
        try:
            if self.hwnd and hotkey_id in self.hotkeys:
                success = user32.UnregisterHotKey(self.hwnd, hotkey_id)
                if success:
                    del self.hotkeys[hotkey_id]
                    logger.info(f"Unregistered hotkey {hotkey_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Exception in unregister_hotkey: {e}")
            return False
    
    def unregister_all(self) -> None:
        """全ホットキーの登録解除"""
        for hotkey_id in list(self.hotkeys.keys()):
            self.unregister_hotkey(hotkey_id)
    
    def set_target_key(self, hotkey_id: int, target_vk: int) -> None:
        """ターゲットキーを設定"""
        if hotkey_id in self.hotkeys:
            self.hotkeys[hotkey_id]['target_key'] = target_vk
    
    def start_message_loop(self) -> None:
        """メッセージループ開始"""
        if self.running:
            return
        
        self.running = True
        
        def message_loop():
            while self.running:
                try:
                    win32gui.PumpWaitingMessages()
                    time.sleep(0.01)
                except KeyboardInterrupt:
                    break
                except:
                    pass
        
        self.thread = threading.Thread(target=message_loop, daemon=True)
        self.thread.start()
        logger.info("Hotkey message loop started")
    
    def stop_message_loop(self) -> None:
        """メッセージループ停止"""
        self.running = False
        
        # ウィンドウを破棄してメッセージループを停止
        if self.hwnd:
            try:
                win32gui.DestroyWindow(self.hwnd)
            except:
                pass
            self.hwnd = None
        
        # スレッドが存在し、現在のスレッドと異なる場合は停止を待機
        if self.thread and self.thread.is_alive():
            try:
                # メッセージループを強制停止するために PostQuitMessage を送信
                if self.hwnd:
                    try:
                        win32gui.PostMessage(self.hwnd, win32con.WM_QUIT, 0, 0)
                    except:
                        pass
                
                # スレッドの停止を待機（最大2秒）
                self.thread.join(timeout=2.0)
                if self.thread.is_alive():
                    logger.warning("Hotkey message loop thread did not stop within timeout")
                else:
                    logger.info("Hotkey message loop thread stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping hotkey message loop thread: {e}")
        
        self.thread = None
        logger.info("Hotkey message loop stopped")