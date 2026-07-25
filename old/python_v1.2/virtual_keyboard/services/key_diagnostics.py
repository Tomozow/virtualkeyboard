"""
Key Diagnostics - キー送信診断ツール
システムの権限、UAC、送信能力を詳細診断
"""

import os
import sys
import time
import logging
import ctypes
import platform
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .keysender import EnhancedKeySender
from .win32_types import FunctionKeyMap, win32_api, ERROR_ACCESS_DENIED

logger = logging.getLogger(__name__)


class SystemDiagnostics:
    """システム診断クラス"""
    
    @staticmethod
    def check_admin_privileges() -> Tuple[bool, str]:
        """管理者権限の確認"""
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            status = "Administrator" if is_admin else "Standard User"
            return bool(is_admin), status
        except Exception as e:
            return False, f"Cannot determine: {str(e)}"
    
    @staticmethod
    def check_uac_status() -> Tuple[bool, str]:
        """UAC（User Account Control）の状態確認"""
        try:
            # レジストリからUAC設定を確認
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
            
            try:
                enable_lua, _ = winreg.QueryValueEx(key, "EnableLUA")
                uac_enabled = bool(enable_lua)
                
                if uac_enabled:
                    # UAC通知レベルを確認
                    try:
                        consent_level, _ = winreg.QueryValueEx(key, "ConsentPromptBehaviorAdmin")
                        level_desc = {
                            0: "Never notify",
                            1: "Prompt for credentials on the secure desktop",
                            2: "Prompt for consent on the secure desktop", 
                            3: "Prompt for credentials",
                            4: "Prompt for consent",
                            5: "Prompt for consent for non-Windows binaries"
                        }.get(consent_level, f"Unknown level: {consent_level}")
                        
                        return True, f"Enabled - {level_desc}"
                    except FileNotFoundError:
                        return True, "Enabled - Default settings"
                else:
                    return False, "Disabled"
                    
            finally:
                winreg.CloseKey(key)
                
        except Exception as e:
            return False, f"Cannot determine: {str(e)}"
    
    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """システム情報の取得"""
        return {
            "os_version": platform.platform(),
            "python_version": sys.version,
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "current_user": os.getenv("USERNAME", "Unknown"),
            "working_directory": os.getcwd()
        }


class KeySendDiagnostics:
    """キー送信診断クラス"""
    
    def __init__(self):
        self.key_sender = EnhancedKeySender(enable_stats=True, enable_retry=False)
        self.system_diag = SystemDiagnostics()
    
    def run_comprehensive_diagnosis(self) -> Dict[str, any]:
        """包括的な診断実行"""
        logger.info("Starting comprehensive key send diagnostics...")
        
        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self._diagnose_system(),
            "key_send_tests": self._test_key_sending(),
            "permission_analysis": self._analyze_permissions(),
            "recommendations": []
        }
        
        # 推奨事項を生成
        diagnosis["recommendations"] = self._generate_recommendations(diagnosis)
        
        return diagnosis
    
    def _diagnose_system(self) -> Dict[str, any]:
        """システム診断"""
        is_admin, admin_status = self.system_diag.check_admin_privileges()
        uac_enabled, uac_status = self.system_diag.check_uac_status()
        system_info = self.system_diag.get_system_info()
        
        return {
            "admin_privileges": {
                "has_admin": is_admin,
                "status": admin_status
            },
            "uac_status": {
                "enabled": uac_enabled,
                "status": uac_status
            },
            "system_info": system_info
        }
    
    def _test_key_sending(self) -> Dict[str, any]:
        """キー送信テスト"""
        test_results = {}
        
        # F1-F4キーでテスト（代表的なキー）
        test_keys = [1, 2, 3, 4]  # F1, F2, F3, F4
        
        for key_num in test_keys:
            key_name = f"F{key_num}"
            logger.debug(f"Testing {key_name} key send...")
            
            try:
                result = self.key_sender.send_function_key_detailed(key_num)
                test_results[key_name] = {
                    "success": result.success,
                    "duration_ms": result.duration_ms,
                    "error_message": result.error_message,
                    "vk_code": result.vk_code
                }
            except Exception as e:
                test_results[key_name] = {
                    "success": False,
                    "error_message": f"Exception: {str(e)}",
                    "duration_ms": 0.0
                }
        
        # 統計情報
        stats = self.key_sender.get_statistics()
        test_results["statistics"] = stats if stats else {}
        
        return test_results
    
    def _analyze_permissions(self) -> Dict[str, any]:
        """権限分析"""
        analysis = {}
        
        # 直接Win32 API テスト
        try:
            test_vk = FunctionKeyMap.get_vk_code(1)  # F1
            inputs = [(test_vk, False), (test_vk, True)]  # Key down, Key up
            
            from .win32_types import InputFactory
            input_structs = InputFactory.create_key_press_sequence(test_vk)
            success, sent_count, error_message = win32_api.send_input(input_structs)
            
            analysis["direct_api_test"] = {
                "success": success,
                "sent_count": sent_count,
                "error_message": error_message
            }
            
        except Exception as e:
            analysis["direct_api_test"] = {
                "success": False,
                "error_message": f"Exception: {str(e)}"
            }
        
        return analysis
    
    def _generate_recommendations(self, diagnosis: Dict[str, any]) -> List[str]:
        """診断結果に基づく推奨事項の生成"""
        recommendations = []
        
        # 管理者権限チェック
        if not diagnosis["system_info"]["admin_privileges"]["has_admin"]:
            recommendations.append("[WARNING] Run application as Administrator for better key send reliability")
        
        # UAC設定チェック
        if diagnosis["system_info"]["uac_status"]["enabled"]:
            recommendations.append("[INFO] UAC is enabled - may affect cross-process key sending")
        
        # キー送信失敗率チェック
        test_results = diagnosis["key_send_tests"]
        failed_keys = [k for k, v in test_results.items() 
                      if k.startswith("F") and not v.get("success", True)]
        
        if failed_keys:
            recommendations.append(f"[ERROR] Key send failures detected: {', '.join(failed_keys)}")
            
            # エラーメッセージ分析
            access_denied_errors = [k for k, v in test_results.items() 
                                  if k.startswith("F") and v.get("error_message", "").find("Access denied") >= 0]
            if access_denied_errors:
                recommendations.append("[PERMISSION] Access denied errors - Run as administrator")
        
        # パフォーマンス分析
        stats = test_results.get("statistics", {})
        success_rate = stats.get("success_rate_percent", 100)
        if success_rate < 95:
            recommendations.append(f"[PERFORMANCE] Low success rate ({success_rate}%) - Check system permissions")
        
        avg_duration = stats.get("average_duration_ms", 0)
        if avg_duration > 50:
            recommendations.append(f"[PERFORMANCE] High average duration ({avg_duration:.1f}ms) - Performance may be affected")
        
        if not recommendations:
            recommendations.append("All diagnostics passed - System is ready for key sending")
        
        return recommendations
    
    def test_specific_key_range(self, start_key: int, end_key: int) -> Dict[str, any]:
        """指定範囲のキーをテスト"""
        results = {}
        
        for key_num in range(start_key, end_key + 1):
            if key_num < 1 or key_num > 24:
                continue
                
            key_name = f"F{key_num}"
            result = self.key_sender.send_function_key_detailed(key_num)
            
            results[key_name] = {
                "success": result.success,
                "duration_ms": result.duration_ms,
                "error_message": result.error_message
            }
            
            # 連続送信による負荷を避けるため少し待機
            time.sleep(0.01)
        
        return results
    
    def benchmark_performance(self, iterations: int = 10) -> Dict[str, any]:
        """パフォーマンスベンチマーク"""
        logger.info(f"Running performance benchmark ({iterations} iterations)...")
        
        # F1キーで連続テスト
        results = []
        start_time = time.perf_counter()
        
        for i in range(iterations):
            result = self.key_sender.send_function_key_detailed(1)  # F1
            results.append(result)
            time.sleep(0.01)  # 短い間隔
        
        total_duration = (time.perf_counter() - start_time) * 1000
        
        # 統計計算
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        durations = [r.duration_ms for r in successful]
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        return {
            "iterations": iterations,
            "total_duration_ms": total_duration,
            "successful_count": len(successful),
            "failed_count": len(failed),
            "success_rate_percent": (len(successful) / iterations) * 100,
            "average_key_duration_ms": avg_duration,
            "min_duration_ms": min_duration,
            "max_duration_ms": max_duration,
            "keys_per_second": iterations / (total_duration / 1000) if total_duration > 0 else 0
        }


def run_quick_diagnosis() -> None:
    """クイック診断の実行"""
    diagnostics = KeySendDiagnostics()
    result = diagnostics.run_comprehensive_diagnosis()
    
    print("=" * 60)
    print("[DIAGNOSIS] Key Send System Diagnostic Results")
    print("=" * 60)
    
    # システム情報
    system = result["system_info"]
    print(f"[ADMIN] Admin Privileges: {system['admin_privileges']['status']}")
    print(f"[UAC] UAC Status: {system['uac_status']['status']}")
    print(f"[OS] Operating System: {system['system_info']['os_version']}")
    
    # テスト結果
    print(f"\n[TESTS] Key Send Test Results:")
    tests = result["key_send_tests"]
    for key_name, test_result in tests.items():
        if key_name.startswith("F"):
            status = "[OK]" if test_result["success"] else "[FAIL]"
            duration = test_result.get("duration_ms", 0)
            print(f"  {status} {key_name}: {duration:.2f}ms")
            if not test_result["success"] and test_result.get("error_message"):
                print(f"       Error: {test_result['error_message']}")
    
    # 統計
    stats = tests.get("statistics", {})
    if stats:
        print(f"\n[STATS] Statistics:")
        print(f"  Success Rate: {stats.get('success_rate_percent', 0)}%")
        print(f"  Average Duration: {stats.get('average_duration_ms', 0):.2f}ms")
    
    # 推奨事項
    print(f"\n[RECOMMENDATIONS] Recommendations:")
    for rec in result["recommendations"]:
        print(f"  {rec}")
    
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_quick_diagnosis()