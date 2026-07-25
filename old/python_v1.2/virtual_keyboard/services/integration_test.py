"""
Integration Test - キー送信とフォーカス管理の統合テスト
"""

import time
import logging
from typing import Dict, List, Optional

from .keysender import EnhancedKeySender
from .focus import FocusManager
from ..core.types import FocusConfig, FocusRestoreMethod

logger = logging.getLogger(__name__)


class IntegrationTester:
    """統合テストクラス"""
    
    def __init__(self):
        # フォーカス設定
        self.focus_config = FocusConfig(
            enabled=True,
            method=FocusRestoreMethod.ENHANCED,
            delay=10,  # 10ms
            debug=True
        )
        
        # サービス初期化
        self.key_sender = EnhancedKeySender(enable_stats=True, enable_retry=True)
        self.focus_manager = FocusManager(self.focus_config)
    
    def test_focus_and_key_send_integration(self) -> Dict[str, any]:
        """フォーカス復元とキー送信の統合テスト"""
        logger.info("Starting focus + key send integration test...")
        
        results = {
            "timestamp": time.time(),
            "focus_tests": {},
            "key_send_tests": {},
            "integration_tests": {},
            "recommendations": []
        }
        
        try:
            # フォーカス監視開始
            self.focus_manager.start_monitoring()
            time.sleep(0.5)  # 監視開始待機
            
            # 現在のフォーカスウィンドウを取得
            current_window = self.focus_manager.get_last_focus_window()
            results["focus_tests"]["current_window"] = current_window
            
            if current_window:
                logger.info(f"Current focus window: {current_window}")
                
                # フォーカス復元テスト
                for method in [FocusRestoreMethod.SIMPLE, FocusRestoreMethod.ENHANCED, FocusRestoreMethod.FORCE]:
                    method_name = method.name.lower()
                    logger.info(f"Testing focus restore method: {method_name}")
                    
                    # 設定を一時変更
                    original_method = self.focus_config.method
                    self.focus_config.method = method
                    
                    success = self.focus_manager.restore_focus(current_window)
                    results["focus_tests"][f"restore_{method_name}"] = {
                        "success": success,
                        "target_window": current_window
                    }
                    
                    # 設定を戻す
                    self.focus_config.method = original_method
                    
                    time.sleep(0.1)  # 短い待機
                
                # キー送信テスト（F1-F4）
                for key_num in range(1, 5):
                    logger.info(f"Testing F{key_num} key send...")
                    
                    # フォーカス復元してからキー送信
                    focus_success = self.focus_manager.restore_focus(current_window)
                    time.sleep(0.01)  # フォーカス安定化待機
                    
                    key_result = self.key_sender.send_function_key_detailed(key_num)
                    
                    results["integration_tests"][f"F{key_num}"] = {
                        "focus_restore_success": focus_success,
                        "key_send_success": key_result.success,
                        "key_send_duration_ms": key_result.duration_ms,
                        "error_message": key_result.error_message
                    }
                    
                    time.sleep(0.05)  # キー間隔
                
            else:
                results["focus_tests"]["error"] = "No valid focus window found"
                logger.warning("No valid focus window found for testing")
            
        except Exception as e:
            results["integration_tests"]["error"] = str(e)
            logger.error(f"Integration test error: {e}")
        
        finally:
            # フォーカス監視停止
            self.focus_manager.stop_monitoring()
        
        # 統計を取得
        stats = self.key_sender.get_statistics()
        if stats:
            results["key_send_tests"]["statistics"] = stats
        
        # 推奨事項を生成
        results["recommendations"] = self._generate_integration_recommendations(results)
        
        return results
    
    def _generate_integration_recommendations(self, results: Dict[str, any]) -> List[str]:
        """統合テスト結果に基づく推奨事項"""
        recommendations = []
        
        # フォーカステスト結果チェック
        focus_tests = results.get("focus_tests", {})
        if "error" in focus_tests:
            recommendations.append("[FOCUS] No valid focus window - May need to interact with other applications first")
        
        # 統合テスト結果チェック
        integration_tests = results.get("integration_tests", {})
        failed_integrations = []
        
        for test_name, test_result in integration_tests.items():
            if test_name.startswith("F") and isinstance(test_result, dict):
                focus_ok = test_result.get("focus_restore_success", False)
                key_ok = test_result.get("key_send_success", False)
                
                if not focus_ok:
                    recommendations.append(f"[FOCUS] {test_name} focus restore failed")
                
                if not key_ok:
                    failed_integrations.append(test_name)
        
        if failed_integrations:
            recommendations.append(f"[INTEGRATION] Key send failures: {', '.join(failed_integrations)}")
        
        # パフォーマンス分析
        stats = results.get("key_send_tests", {}).get("statistics", {})
        if stats:
            success_rate = stats.get("success_rate_percent", 100)
            avg_duration = stats.get("average_duration_ms", 0)
            
            if success_rate < 100:
                recommendations.append(f"[PERFORMANCE] Success rate: {success_rate}%")
            
            if avg_duration > 10:
                recommendations.append(f"[PERFORMANCE] Average duration: {avg_duration:.2f}ms")
        
        if not recommendations:
            recommendations.append("[SUCCESS] All integration tests passed")
        
        return recommendations
    
    def test_performance_under_load(self, iterations: int = 20) -> Dict[str, any]:
        """負荷テスト"""
        logger.info(f"Starting performance test with {iterations} iterations...")
        
        results = {
            "iterations": iterations,
            "results": [],
            "statistics": {}
        }
        
        try:
            self.focus_manager.start_monitoring()
            time.sleep(0.2)
            
            current_window = self.focus_manager.get_last_focus_window()
            
            if current_window:
                start_time = time.perf_counter()
                
                for i in range(iterations):
                    # フォーカス復元
                    focus_success = self.focus_manager.restore_focus(current_window)
                    
                    # F1キー送信
                    key_result = self.key_sender.send_function_key_detailed(1)
                    
                    results["results"].append({
                        "iteration": i + 1,
                        "focus_success": focus_success,
                        "key_success": key_result.success,
                        "duration_ms": key_result.duration_ms
                    })
                    
                    # 短い待機（システム負荷軽減）
                    time.sleep(0.02)
                
                total_time = (time.perf_counter() - start_time) * 1000
                
                # 統計計算
                successful_focuses = sum(1 for r in results["results"] if r["focus_success"])
                successful_keys = sum(1 for r in results["results"] if r["key_success"])
                durations = [r["duration_ms"] for r in results["results"] if r["key_success"]]
                
                results["statistics"] = {
                    "total_duration_ms": total_time,
                    "focus_success_rate": (successful_focuses / iterations) * 100,
                    "key_success_rate": (successful_keys / iterations) * 100,
                    "average_key_duration_ms": sum(durations) / len(durations) if durations else 0,
                    "operations_per_second": iterations / (total_time / 1000) if total_time > 0 else 0
                }
                
            else:
                results["error"] = "No valid focus window for load testing"
        
        except Exception as e:
            results["error"] = str(e)
            logger.error(f"Load test error: {e}")
        
        finally:
            self.focus_manager.stop_monitoring()
        
        return results


def run_integration_tests() -> None:
    """統合テストの実行"""
    print("=" * 60)
    print("[INTEGRATION] Focus + Key Send Integration Tests")
    print("=" * 60)
    
    tester = IntegrationTester()
    
    # 基本統合テスト
    print("[TEST] Running basic integration test...")
    basic_results = tester.test_focus_and_key_send_integration()
    
    # 結果表示
    focus_tests = basic_results.get("focus_tests", {})
    if "current_window" in focus_tests and focus_tests["current_window"]:
        print(f"[FOCUS] Current window ID: {focus_tests['current_window']}")
    
    integration_tests = basic_results.get("integration_tests", {})
    for test_name, result in integration_tests.items():
        if test_name.startswith("F") and isinstance(result, dict):
            focus_status = "[OK]" if result.get("focus_restore_success", False) else "[FAIL]"
            key_status = "[OK]" if result.get("key_send_success", False) else "[FAIL]"
            duration = result.get("key_send_duration_ms", 0)
            print(f"[TEST] {test_name}: Focus{focus_status} Key{key_status} {duration:.2f}ms")
    
    # 統計表示
    stats = basic_results.get("key_send_tests", {}).get("statistics", {})
    if stats:
        print(f"[STATS] Success Rate: {stats.get('success_rate_percent', 0)}%")
        print(f"[STATS] Average Duration: {stats.get('average_duration_ms', 0):.2f}ms")
    
    # 推奨事項
    print(f"\n[RECOMMENDATIONS]")
    for rec in basic_results.get("recommendations", []):
        print(f"  {rec}")
    
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_integration_tests()