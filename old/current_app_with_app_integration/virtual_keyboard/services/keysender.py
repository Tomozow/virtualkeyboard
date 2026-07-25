"""
Key Sender Enhanced - キー送信サービス（SendInput API版）
tech.mdの仕様に基づく高性能・高信頼性実装
"""

import time
import logging
import asyncio
from typing import Optional, Dict, List, Tuple
from datetime import datetime

from ..core.interfaces import IKeySender
from .win32_types import (
    win32_api, FunctionKeyMap, InputFactory,
    INPUT, KEYBDINPUT, ERROR_ACCESS_DENIED, ERROR_INVALID_PARAMETER
)

logger = logging.getLogger(__name__)


class KeySendResult:
    """キー送信結果の詳細情報"""
    
    def __init__(self, success: bool, vk_code: int, duration_ms: float,
                 error_message: Optional[str] = None, retry_count: int = 0):
        self.success = success
        self.vk_code = vk_code
        self.key_name = FunctionKeyMap.get_key_name(vk_code)
        self.duration_ms = duration_ms
        self.error_message = error_message
        self.retry_count = retry_count
        self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"[{status}] {self.key_name} ({self.duration_ms:.2f}ms)"


class KeySenderStats:
    """キー送信統計情報"""
    
    def __init__(self):
        self.total_attempts = 0
        self.successful_sends = 0
        self.failed_sends = 0
        self.total_duration_ms = 0.0
        self.retry_count = 0
        self.error_history: List[str] = []
        self.recent_results: List[KeySendResult] = []
        self.max_recent_results = 100
    
    def add_result(self, result: KeySendResult) -> None:
        """結果を統計に追加"""
        self.total_attempts += 1
        self.total_duration_ms += result.duration_ms
        self.retry_count += result.retry_count
        
        if result.success:
            self.successful_sends += 1
        else:
            self.failed_sends += 1
            if result.error_message:
                self.error_history.append(f"{result.timestamp}: {result.error_message}")
        
        # 最近の結果を保存（最大数を超えたら古いものを削除）
        self.recent_results.append(result)
        if len(self.recent_results) > self.max_recent_results:
            self.recent_results.pop(0)
    
    @property
    def success_rate(self) -> float:
        """成功率を計算"""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_sends / self.total_attempts) * 100
    
    @property
    def average_duration_ms(self) -> float:
        """平均送信時間を計算"""
        if self.total_attempts == 0:
            return 0.0
        return self.total_duration_ms / self.total_attempts
    
    def get_summary(self) -> Dict[str, any]:
        """統計サマリーを取得"""
        return {
            "total_attempts": self.total_attempts,
            "success_rate_percent": round(self.success_rate, 2),
            "average_duration_ms": round(self.average_duration_ms, 2),
            "failed_sends": self.failed_sends,
            "retry_count": self.retry_count,
            "recent_errors": self.error_history[-5:] if self.error_history else []
        }


class EnhancedKeySender(IKeySender):
    """キー送信の実装クラス（SendInput API版）"""
    
    def __init__(self, enable_stats: bool = True, enable_retry: bool = True, max_retries: int = 2):
        self.enable_stats = enable_stats
        self.enable_retry = enable_retry
        self.max_retries = max_retries
        self.stats = KeySenderStats() if enable_stats else None
        self._input_cache = {}  # INPUT構造体のキャッシュ
    
    def send_key(self, vk_code: int) -> bool:
        """仮想キーコードを送信（メインインターフェース）"""
        result = self.send_key_detailed(vk_code)
        return result.success
    
    def send_key_detailed(self, vk_code: int) -> KeySendResult:
        """仮想キーコードを送信（詳細結果付き）"""
        start_time = time.perf_counter()
        key_name = FunctionKeyMap.get_key_name(vk_code)
        retry_count = 0
        
        logger.debug(f"Sending key: {key_name} (VK_{vk_code:02X})")
        
        for attempt in range(self.max_retries + 1 if self.enable_retry else 1):
            try:
                # INPUT構造体を取得（キャッシュあり）
                inputs = self._get_cached_inputs(vk_code)
                
                # SendInput呼び出し
                success, sent_count, error_message = win32_api.send_input(inputs)
                
                if success:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    result = KeySendResult(True, vk_code, duration_ms, retry_count=retry_count)
                    
                    logger.info(f"Key sent successfully: {key_name} ({duration_ms:.2f}ms)")
                    
                    if self.stats:
                        self.stats.add_result(result)
                    
                    return result
                
                # 失敗した場合
                if not self.enable_retry or attempt >= self.max_retries:
                    # 最終的な失敗
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    result = KeySendResult(False, vk_code, duration_ms, error_message, retry_count)
                    
                    logger.error(f"Failed to send key {key_name}: {error_message}")
                    
                    if self.stats:
                        self.stats.add_result(result)
                    
                    return result
                
                # リトライの場合
                retry_count += 1
                logger.warning(f"Key send failed, retrying ({retry_count}/{self.max_retries}): {error_message}")
                time.sleep(0.01 * attempt)  # 指数的バックオフ
                
            except Exception as e:
                error_message = f"Exception in send_key: {str(e)}"
                
                if not self.enable_retry or attempt >= self.max_retries:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    result = KeySendResult(False, vk_code, duration_ms, error_message, retry_count)
                    
                    logger.error(f"Exception sending key {key_name}: {e}")
                    
                    if self.stats:
                        self.stats.add_result(result)
                    
                    return result
                
                retry_count += 1
                logger.warning(f"Exception in key send, retrying ({retry_count}/{self.max_retries}): {e}")
                time.sleep(0.01 * attempt)
    
    def send_function_key(self, function_key_number: int) -> bool:
        """ファンクションキー番号で送信"""
        vk_code = FunctionKeyMap.get_vk_code(function_key_number)
        if vk_code is None:
            logger.error(f"Invalid function key number: F{function_key_number}")
            return False
        
        return self.send_key(vk_code)
    
    def send_function_key_detailed(self, function_key_number: int) -> KeySendResult:
        """ファンクションキー番号で送信（詳細結果付き）"""
        vk_code = FunctionKeyMap.get_vk_code(function_key_number)
        if vk_code is None:
            error_msg = f"Invalid function key number: F{function_key_number}"
            logger.error(error_msg)
            return KeySendResult(False, 0, 0.0, error_msg)
        
        return self.send_key_detailed(vk_code)
    
    async def send_key_with_delay(self, vk_code: int, delay_seconds: float) -> KeySendResult:
        """遅延送信（非同期）"""
        key_name = FunctionKeyMap.get_key_name(vk_code)
        logger.info(f"Delayed key send scheduled: {key_name} in {delay_seconds}s")
        
        await asyncio.sleep(delay_seconds)
        
        return self.send_key_detailed(vk_code)
    
    def _get_cached_inputs(self, vk_code: int) -> List[INPUT]:
        """INPUT構造体をキャッシュから取得（パフォーマンス最適化）"""
        if vk_code not in self._input_cache:
            self._input_cache[vk_code] = InputFactory.create_key_press_sequence(vk_code)
        return self._input_cache[vk_code]
    
    def diagnose_send_capability(self) -> Dict[str, any]:
        """送信機能の診断実行"""
        logger.info("Running key send capability diagnosis...")
        
        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "test_results": {},
            "system_info": {},
            "recommendations": []
        }
        
        # F1キーでテスト送信
        test_vk = FunctionKeyMap.get_vk_code(1)  # F1
        if test_vk:
            try:
                inputs = InputFactory.create_key_press_sequence(test_vk)
                success, sent_count, error_message = win32_api.send_input(inputs)
                
                diagnosis["test_results"]["f1_test"] = {
                    "success": success,
                    "sent_count": sent_count,
                    "error_message": error_message
                }
                
                if not success and error_message:
                    if "Access denied" in error_message:
                        diagnosis["recommendations"].append("Run application as administrator")
                    elif "Invalid parameter" in error_message:
                        diagnosis["recommendations"].append("Check INPUT structure compatibility")
                
            except Exception as e:
                diagnosis["test_results"]["f1_test"] = {
                    "success": False,
                    "error_message": f"Exception: {str(e)}"
                }
        
        # 統計情報を追加
        if self.stats:
            diagnosis["statistics"] = self.stats.get_summary()
        
        return diagnosis
    
    def get_statistics(self) -> Optional[Dict[str, any]]:
        """統計情報を取得"""
        return self.stats.get_summary() if self.stats else None
    
    def reset_statistics(self) -> None:
        """統計情報をリセット"""
        if self.stats:
            self.stats = KeySenderStats()
            logger.info("Key sender statistics reset")
    
    def clear_cache(self) -> None:
        """INPUT構造体キャッシュをクリア"""
        self._input_cache.clear()
        logger.debug("INPUT cache cleared")
    
    @staticmethod
    def vk_code_to_name(vk_code: int) -> str:
        """VKコードをキー名に変換（後方互換性用）"""
        return FunctionKeyMap.get_key_name(vk_code)


# 後方互換性のために既存のKeySenderクラスを維持しつつ、新機能を追加
class KeySender(EnhancedKeySender):
    """既存のKeySenderインターフェースを保持した拡張版"""
    
    def __init__(self):
        # デフォルトで統計とリトライを有効化
        super().__init__(enable_stats=True, enable_retry=True, max_retries=2)
        
        # 修飾キーのVKコードマッピング
        self.modifier_map = {
            'Ctrl': 0x11,    # VK_CONTROL
            'Alt': 0x12,     # VK_MENU
            'Shift': 0x10,   # VK_SHIFT
            'Win': 0x5B,     # VK_LWIN
        }
    
    def send_key_combination(self, key_combination: str) -> bool:
        """修飾キーの組み合わせを送信（例: "Ctrl+C", "Alt+Tab"）"""
        try:
            if '+' not in key_combination:
                # 単一キーの場合
                vk_code = self.key_name_to_vk(key_combination)
                return self.send_key(vk_code)
            
            # 修飾キーの組み合わせを解析
            parts = [part.strip() for part in key_combination.split('+')]
            if len(parts) < 2:
                logger.error(f"Invalid key combination: {key_combination}")
                return False
            
            # 修飾キーとメインキーを分離
            modifiers = parts[:-1]
            main_key = parts[-1]
            
            # 修飾キーのVKコードを取得
            modifier_vks = []
            for mod in modifiers:
                if mod in self.modifier_map:
                    modifier_vks.append(self.modifier_map[mod])
                else:
                    logger.error(f"Unknown modifier: {mod}")
                    return False
            
            # メインキーのVKコードを取得
            main_vk = self.key_name_to_vk(main_key)
            if main_vk == 0:
                logger.error(f"Unknown key: {main_key}")
                return False
            
            logger.info(f"Sending key combination: {key_combination}")
            
            # 修飾キーを押下
            for mod_vk in modifier_vks:
                self._send_key_down(mod_vk)
            
            # メインキーを送信
            self._send_key_down(main_vk)
            time.sleep(0.01)  # 短い遅延
            self._send_key_up(main_vk)
            
            # 修飾キーを解放（逆順）
            for mod_vk in reversed(modifier_vks):
                self._send_key_up(mod_vk)
            
            logger.info(f"Key combination sent successfully: {key_combination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send key combination {key_combination}: {e}")
            return False
    
    def _send_key_down(self, vk_code: int):
        """キーの押下を送信"""
        try:
            if vk_code is None:
                logger.error("vk_code is None in _send_key_down")
                return
            inputs = InputFactory.create_keyboard_input(vk_code, key_up=False)
            success, result, error_msg = win32_api.send_input([inputs])
            if not success:
                logger.warning(f"Failed to send key down for VK_0x{vk_code:02X}: {error_msg}")
        except Exception as e:
            logger.error(f"Error sending key down VK_0x{vk_code:02X if vk_code else 0}: {e}")
    
    def _send_key_up(self, vk_code: int):
        """キーの解放を送信"""
        try:
            if vk_code is None:
                logger.error("vk_code is None in _send_key_up")
                return
            inputs = InputFactory.create_keyboard_input(vk_code, key_up=True)
            success, result, error_msg = win32_api.send_input([inputs])
            if not success:
                logger.warning(f"Failed to send key up for VK_0x{vk_code:02X}: {error_msg}")
        except Exception as e:
            logger.error(f"Error sending key up VK_0x{vk_code:02X if vk_code else 0}: {e}")
    
    def key_name_to_vk(self, key_name: str) -> int:
        """キー名をVKコードに変換（拡張版）"""
        try:
            # ファンクションキーの処理 (F1-F24)
            if key_name.startswith('F') and key_name[1:].isdigit():
                f_num = int(key_name[1:])
                vk_code = FunctionKeyMap.get_vk_code(f_num)
                if vk_code is not None:
                    return vk_code
            
            # 追加のキーマッピング
            extended_key_map = {
                # 数字キー
                '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
                '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
                
                # アルファベット
                'A': 0x41, 'B': 0x42, 'C': 0x43, 'D': 0x44, 'E': 0x45,
                'F': 0x46, 'G': 0x47, 'H': 0x48, 'I': 0x49, 'J': 0x4A,
                'K': 0x4B, 'L': 0x4C, 'M': 0x4D, 'N': 0x4E, 'O': 0x4F,
                'P': 0x50, 'Q': 0x51, 'R': 0x52, 'S': 0x53, 'T': 0x54,
                'U': 0x55, 'V': 0x56, 'W': 0x57, 'X': 0x58, 'Y': 0x59, 'Z': 0x5A,
                
                # 特殊キー
                'Space': 0x20, 'Enter': 0x0D, 'Backspace': 0x08, 'Delete': 0x2E,
                'Tab': 0x09, 'Escape': 0x1B, 'Insert': 0x2D, 'Home': 0x24,
                'End': 0x23, 'PageUp': 0x21, 'PageDown': 0x22,
                'Up': 0x26, 'Down': 0x28, 'Left': 0x25, 'Right': 0x27,
                'Shift': 0x10, 'Ctrl': 0x11, 'Alt': 0x12, 'Win': 0x5B,
                'CapsLock': 0x14, 'NumLock': 0x90, 'ScrollLock': 0x91,
                'PrintScreen': 0x2C, 'Pause': 0x13,
                
                # 記号キー
                'Semicolon': 0xBA, 'Equal': 0xBB, 'Comma': 0xBC, 'Minus': 0xBD,
                'Period': 0xBE, 'Slash': 0xBF, 'Grave': 0xC0, 'LeftBracket': 0xDB,
                'Backslash': 0xDC, 'RightBracket': 0xDD, 'Quote': 0xDE,
            }
            
            return extended_key_map.get(key_name, 0)
            
        except Exception as e:
            logger.error(f"Error converting key name {key_name}: {e}")
            return 0