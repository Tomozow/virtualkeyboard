"""
Win32 API Types - SendInput用の構造体定義
tech.mdの仕様に基づいた正確な実装
"""

import ctypes
from ctypes import wintypes, Structure, Union, POINTER, byref
from typing import Optional


# 定数定義
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# GetLastError用のエラーコード
ERROR_SUCCESS = 0
ERROR_ACCESS_DENIED = 5
ERROR_INVALID_PARAMETER = 87
ERROR_INVALID_HANDLE = 6


class MOUSEINPUT(Structure):
    """マウス入力構造体（構造体サイズ計算用）"""
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', POINTER(ctypes.c_ulong))
    ]


class KEYBDINPUT(Structure):
    """キーボード入力構造体 - tech.mdの仕様通り"""
    _fields_ = [
        ('wVk', wintypes.WORD),         # 仮想キーコード
        ('wScan', wintypes.WORD),       # スキャンコード（通常0）
        ('dwFlags', wintypes.DWORD),    # フラグ（0=押下、KEYEVENTF_KEYUP=離上）
        ('time', wintypes.DWORD),       # タイムスタンプ（通常0で自動）
        ('dwExtraInfo', POINTER(ctypes.c_ulong))  # 追加情報（通常None）
    ]


class HARDWAREINPUT(Structure):
    """ハードウェア入力構造体（構造体サイズ計算用）"""
    _fields_ = [
        ('uMsg', wintypes.DWORD),
        ('wParamL', wintypes.WORD),
        ('wParamH', wintypes.WORD)
    ]


class InputUnion(Union):
    """INPUT構造体の共用体部分 - Size=24で明示的に制御"""
    _fields_ = [
        ('ki', KEYBDINPUT),     # キーボード入力
        ('mi', MOUSEINPUT),     # マウス入力（必須：サイズ計算用）
        ('hi', HARDWAREINPUT)   # ハードウェア入力（必須：サイズ計算用）
    ]


class INPUT(Structure):
    """INPUT構造体 - Win32 SendInput API用"""
    _fields_ = [
        ('type', wintypes.DWORD),  # INPUT_KEYBOARD (1)
        ('u', InputUnion)          # 共用体
    ]


class FunctionKeyMap:
    """F1-F24の仮想キーコードマッピング"""
    
    # tech.mdの完全マッピング
    FUNCTION_KEYS = {
        1: 0x70,   # F1   (VK_F1)
        2: 0x71,   # F2   (VK_F2)
        3: 0x72,   # F3   (VK_F3)
        4: 0x73,   # F4   (VK_F4)
        5: 0x74,   # F5   (VK_F5)
        6: 0x75,   # F6   (VK_F6)
        7: 0x76,   # F7   (VK_F7)
        8: 0x77,   # F8   (VK_F8)
        9: 0x78,   # F9   (VK_F9)
        10: 0x79,  # F10  (VK_F10)
        11: 0x7A,  # F11  (VK_F11)
        12: 0x7B,  # F12  (VK_F12)
        13: 0x7C,  # F13  (VK_F13)
        14: 0x7D,  # F14  (VK_F14)
        15: 0x7E,  # F15  (VK_F15)
        16: 0x7F,  # F16  (VK_F16)
        17: 0x80,  # F17  (VK_F17)
        18: 0x81,  # F18  (VK_F18)
        19: 0x82,  # F19  (VK_F19)
        20: 0x83,  # F20  (VK_F20)
        21: 0x84,  # F21  (VK_F21)
        22: 0x85,  # F22  (VK_F22)
        23: 0x86,  # F23  (VK_F23)
        24: 0x87   # F24  (VK_F24)
    }
    
    @classmethod
    def get_vk_code(cls, function_key_number: int) -> Optional[int]:
        """ファンクションキー番号から仮想キーコードを取得"""
        return cls.FUNCTION_KEYS.get(function_key_number)
    
    @classmethod
    def get_key_name(cls, vk_code: int) -> str:
        """仮想キーコードからキー名を取得"""
        if vk_code is None:
            return "VK_UNKNOWN"
        for key_num, code in cls.FUNCTION_KEYS.items():
            if code == vk_code:
                return f"F{key_num}"
        return f"VK_{vk_code:02X}"
    
    @classmethod
    def is_function_key(cls, vk_code: int) -> bool:
        """ファンクションキーかどうかをチェック"""
        return vk_code in cls.FUNCTION_KEYS.values()


class Win32API:
    """Win32 API関数の定義"""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # SendInput関数の定義 - tech.mdの仕様通り
        self.user32.SendInput.argtypes = [
            wintypes.UINT,      # nInputs
            POINTER(INPUT),     # pInputs
            ctypes.c_int        # cbSize
        ]
        self.user32.SendInput.restype = wintypes.UINT
        
        # GetLastError関数の定義
        self.kernel32.GetLastError.argtypes = []
        self.kernel32.GetLastError.restype = wintypes.DWORD
    
    def send_input(self, inputs: list[INPUT]) -> tuple[bool, int, Optional[str]]:
        """
        SendInput API呼び出し
        
        Returns:
            tuple[bool, int, Optional[str]]: (成功フラグ, 送信数, エラーメッセージ)
        """
        num_inputs = len(inputs)
        input_array = (INPUT * num_inputs)(*inputs)
        
        # SendInput呼び出し
        result = self.user32.SendInput(
            num_inputs,
            input_array,
            ctypes.sizeof(INPUT)
        )
        
        # 結果検証
        success = (result == num_inputs)
        
        error_message = None
        if not success:
            error_code = self.kernel32.GetLastError()
            error_message = self._get_error_message(error_code)
        
        return success, result, error_message
    
    def _get_error_message(self, error_code: int) -> str:
        """エラーコードからメッセージを生成"""
        error_messages = {
            ERROR_ACCESS_DENIED: "Access denied - run as administrator",
            ERROR_INVALID_PARAMETER: "Invalid parameter - check INPUT structure",
            ERROR_INVALID_HANDLE: "Invalid handle",
            0: "Success"
        }
        
        message = error_messages.get(error_code, f"Unknown error code: {error_code}")
        return f"Error {error_code}: {message}"


class InputFactory:
    """INPUT構造体の生成ファクトリ"""
    
    @staticmethod
    def create_keyboard_input(vk_code: int, key_up: bool = False) -> INPUT:
        """キーボード入力のINPUT構造体を作成"""
        input_obj = INPUT()
        input_obj.type = INPUT_KEYBOARD
        input_obj.u.ki = KEYBDINPUT(
            wVk=vk_code,
            wScan=0,
            dwFlags=KEYEVENTF_KEYUP if key_up else 0,
            time=0,
            dwExtraInfo=None
        )
        return input_obj
    
    @staticmethod
    def create_key_press_sequence(vk_code: int) -> list[INPUT]:
        """キー押下・離上のシーケンスを作成"""
        key_down = InputFactory.create_keyboard_input(vk_code, key_up=False)
        key_up = InputFactory.create_keyboard_input(vk_code, key_up=True)
        return [key_down, key_up]


# グローバルインスタンス
win32_api = Win32API()