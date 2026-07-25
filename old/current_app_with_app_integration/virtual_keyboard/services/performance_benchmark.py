"""
Performance Benchmark - パフォーマンス測定とベンチマーク
新旧実装の比較とパフォーマンス最適化
"""

import time
import statistics
import logging
from typing import Dict, List, Tuple
import sys
import os

# 元の実装をインポートするための準備
sys.path.append(os.path.dirname(__file__))

# 新しい実装
from .keysender import EnhancedKeySender
from .win32_types import FunctionKeyMap

logger = logging.getLogger(__name__)


class LegacyKeySender:
    """元のKeyboard Event実装（比較用）"""
    
    def __init__(self):
        try:
            import win32con
            from ctypes import windll
            self.user32 = windll.user32
            self.win32con = win32con
        except ImportError:
            logger.warning("Legacy implementation requires win32con")
            self.user32 = None
            self.win32con = None
    
    def send_key(self, vk_code: int) -> bool:
        """元のkeybd_event実装"""
        if not self.user32:
            return False
        
        try:
            # Key down
            self.user32.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.005)  # 元の実装の遅延
            # Key up
            self.user32.keybd_event(vk_code, 0, self.win32con.KEYEVENTF_KEYUP, 0)
            return True
        except Exception as e:
            logger.error(f"Legacy key send failed: {e}")
            return False


class PerformanceBenchmark:
    """パフォーマンスベンチマーククラス"""
    
    def __init__(self):
        self.enhanced_sender = EnhancedKeySender(enable_stats=True, enable_retry=False)
        self.legacy_sender = LegacyKeySender()
    
    def benchmark_single_key_send(self, iterations: int = 50) -> Dict[str, any]:
        """単発キー送信のベンチマーク"""
        logger.info(f"Benchmarking single key send ({iterations} iterations)...")
        
        results = {
            "iterations": iterations,
            "enhanced_results": [],
            "legacy_results": [],
            "comparison": {}
        }
        
        test_vk = FunctionKeyMap.get_vk_code(1)  # F1キー
        
        # Enhanced版テスト
        logger.info("Testing enhanced version...")
        for i in range(iterations):
            start_time = time.perf_counter()
            success = self.enhanced_sender.send_key(test_vk)
            duration = (time.perf_counter() - start_time) * 1000
            
            results["enhanced_results"].append({
                "success": success,
                "duration_ms": duration
            })
            
            time.sleep(0.02)  # システム負荷軽減
        
        # Legacy版テスト
        logger.info("Testing legacy version...")
        for i in range(iterations):
            start_time = time.perf_counter()
            success = self.legacy_sender.send_key(test_vk)
            duration = (time.perf_counter() - start_time) * 1000
            
            results["legacy_results"].append({
                "success": success,
                "duration_ms": duration
            })
            
            time.sleep(0.02)  # システム負荷軽減
        
        # 統計計算
        results["comparison"] = self._calculate_comparison_stats(
            results["enhanced_results"], 
            results["legacy_results"]
        )
        
        return results
    
    def benchmark_burst_send(self, burst_count: int = 10, iterations: int = 5) -> Dict[str, any]:
        """連続キー送信のベンチマーク"""
        logger.info(f"Benchmarking burst send ({burst_count} keys x {iterations} iterations)...")
        
        results = {
            "burst_count": burst_count,
            "iterations": iterations,
            "enhanced_results": [],
            "legacy_results": [],
            "comparison": {}
        }
        
        test_keys = [FunctionKeyMap.get_vk_code(i) for i in range(1, burst_count + 1)]
        
        # Enhanced版テスト
        for iteration in range(iterations):
            start_time = time.perf_counter()
            successful_sends = 0
            
            for vk_code in test_keys:
                if self.enhanced_sender.send_key(vk_code):
                    successful_sends += 1
                time.sleep(0.001)  # 最小待機
            
            total_duration = (time.perf_counter() - start_time) * 1000
            
            results["enhanced_results"].append({
                "successful_sends": successful_sends,
                "total_duration_ms": total_duration,
                "keys_per_second": burst_count / (total_duration / 1000) if total_duration > 0 else 0
            })
            
            time.sleep(0.1)  # イテレーション間の待機
        
        # Legacy版テスト
        for iteration in range(iterations):
            start_time = time.perf_counter()
            successful_sends = 0
            
            for vk_code in test_keys:
                if self.legacy_sender.send_key(vk_code):
                    successful_sends += 1
                time.sleep(0.001)  # 最小待機
            
            total_duration = (time.perf_counter() - start_time) * 1000
            
            results["legacy_results"].append({
                "successful_sends": successful_sends,
                "total_duration_ms": total_duration,
                "keys_per_second": burst_count / (total_duration / 1000) if total_duration > 0 else 0
            })
            
            time.sleep(0.1)  # イテレーション間の待機
        
        # 統計計算
        results["comparison"] = self._calculate_burst_comparison_stats(
            results["enhanced_results"],
            results["legacy_results"]
        )
        
        return results
    
    def benchmark_memory_usage(self, iterations: int = 100) -> Dict[str, any]:
        """メモリ使用量ベンチマーク"""
        logger.info(f"Benchmarking memory usage ({iterations} iterations)...")
        
        try:
            import psutil
            process = psutil.Process()
            
            # 初期メモリ使用量
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Enhanced版テスト
            enhanced_memory_start = process.memory_info().rss / 1024 / 1024
            
            for i in range(iterations):
                self.enhanced_sender.send_key(FunctionKeyMap.get_vk_code(1))
                if i % 10 == 0:  # ガベージコレクション促進
                    time.sleep(0.001)
            
            enhanced_memory_end = process.memory_info().rss / 1024 / 1024
            
            # キャッシュクリア
            self.enhanced_sender.clear_cache()
            
            # Legacy版テスト
            legacy_memory_start = process.memory_info().rss / 1024 / 1024
            
            for i in range(iterations):
                self.legacy_sender.send_key(FunctionKeyMap.get_vk_code(1))
                if i % 10 == 0:
                    time.sleep(0.001)
            
            legacy_memory_end = process.memory_info().rss / 1024 / 1024
            
            return {
                "iterations": iterations,
                "initial_memory_mb": initial_memory,
                "enhanced_memory_usage_mb": enhanced_memory_end - enhanced_memory_start,
                "legacy_memory_usage_mb": legacy_memory_end - legacy_memory_start,
                "memory_difference_mb": (enhanced_memory_end - enhanced_memory_start) - (legacy_memory_end - legacy_memory_start)
            }
            
        except ImportError:
            logger.warning("psutil not available for memory benchmarking")
            return {"error": "psutil not available"}
    
    def _calculate_comparison_stats(self, enhanced_results: List[Dict], 
                                  legacy_results: List[Dict]) -> Dict[str, any]:
        """単発キー送信の比較統計"""
        enhanced_durations = [r["duration_ms"] for r in enhanced_results if r["success"]]
        legacy_durations = [r["duration_ms"] for r in legacy_results if r["success"]]
        
        enhanced_success_count = sum(1 for r in enhanced_results if r["success"])
        legacy_success_count = sum(1 for r in legacy_results if r["success"])
        
        comparison = {
            "enhanced_success_rate": (enhanced_success_count / len(enhanced_results)) * 100,
            "legacy_success_rate": (legacy_success_count / len(legacy_results)) * 100,
        }
        
        if enhanced_durations and legacy_durations:
            enhanced_avg = statistics.mean(enhanced_durations)
            legacy_avg = statistics.mean(legacy_durations)
            
            comparison.update({
                "enhanced_avg_duration_ms": enhanced_avg,
                "legacy_avg_duration_ms": legacy_avg,
                "enhanced_median_duration_ms": statistics.median(enhanced_durations),
                "legacy_median_duration_ms": statistics.median(legacy_durations),
                "enhanced_std_duration_ms": statistics.stdev(enhanced_durations) if len(enhanced_durations) > 1 else 0,
                "legacy_std_duration_ms": statistics.stdev(legacy_durations) if len(legacy_durations) > 1 else 0,
                "performance_improvement_percent": ((legacy_avg - enhanced_avg) / legacy_avg) * 100 if legacy_avg > 0 else 0
            })
        
        return comparison
    
    def _calculate_burst_comparison_stats(self, enhanced_results: List[Dict], 
                                        legacy_results: List[Dict]) -> Dict[str, any]:
        """連続キー送信の比較統計"""
        enhanced_kps = [r["keys_per_second"] for r in enhanced_results]
        legacy_kps = [r["keys_per_second"] for r in legacy_results]
        
        enhanced_durations = [r["total_duration_ms"] for r in enhanced_results]
        legacy_durations = [r["total_duration_ms"] for r in legacy_results]
        
        comparison = {
            "enhanced_avg_keys_per_second": statistics.mean(enhanced_kps) if enhanced_kps else 0,
            "legacy_avg_keys_per_second": statistics.mean(legacy_kps) if legacy_kps else 0,
            "enhanced_avg_total_duration_ms": statistics.mean(enhanced_durations) if enhanced_durations else 0,
            "legacy_avg_total_duration_ms": statistics.mean(legacy_durations) if legacy_durations else 0
        }
        
        if enhanced_kps and legacy_kps:
            enhanced_avg_kps = statistics.mean(enhanced_kps)
            legacy_avg_kps = statistics.mean(legacy_kps)
            
            if legacy_avg_kps > 0:
                comparison["throughput_improvement_percent"] = ((enhanced_avg_kps - legacy_avg_kps) / legacy_avg_kps) * 100
        
        return comparison
    
    def run_comprehensive_benchmark(self) -> Dict[str, any]:
        """包括的なベンチマーク実行"""
        logger.info("Running comprehensive performance benchmark...")
        
        return {
            "timestamp": time.time(),
            "single_key_benchmark": self.benchmark_single_key_send(50),
            "burst_benchmark": self.benchmark_burst_send(10, 5),
            "memory_benchmark": self.benchmark_memory_usage(100)
        }


def print_benchmark_results(results: Dict[str, any]) -> None:
    """ベンチマーク結果の表示"""
    print("=" * 60)
    print("[BENCHMARK] Performance Comparison Results")
    print("=" * 60)
    
    # 単発キー送信結果
    single_key = results.get("single_key_benchmark", {})
    comparison = single_key.get("comparison", {})
    
    if comparison:
        print(f"[SINGLE KEY] Results ({single_key.get('iterations', 0)} iterations):")
        print(f"  Enhanced Success Rate: {comparison.get('enhanced_success_rate', 0):.1f}%")
        print(f"  Legacy Success Rate: {comparison.get('legacy_success_rate', 0):.1f}%")
        
        if 'enhanced_avg_duration_ms' in comparison:
            print(f"  Enhanced Avg Duration: {comparison['enhanced_avg_duration_ms']:.2f}ms")
            print(f"  Legacy Avg Duration: {comparison['legacy_avg_duration_ms']:.2f}ms")
            print(f"  Performance Improvement: {comparison.get('performance_improvement_percent', 0):.1f}%")
    
    # 連続キー送信結果
    burst = results.get("burst_benchmark", {})
    burst_comparison = burst.get("comparison", {})
    
    if burst_comparison:
        print(f"\n[BURST SEND] Results ({burst.get('burst_count', 0)} keys x {burst.get('iterations', 0)} iterations):")
        print(f"  Enhanced Keys/sec: {burst_comparison.get('enhanced_avg_keys_per_second', 0):.1f}")
        print(f"  Legacy Keys/sec: {burst_comparison.get('legacy_avg_keys_per_second', 0):.1f}")
        
        if 'throughput_improvement_percent' in burst_comparison:
            print(f"  Throughput Improvement: {burst_comparison['throughput_improvement_percent']:.1f}%")
    
    # メモリ使用量結果
    memory = results.get("memory_benchmark", {})
    if memory and "error" not in memory:
        print(f"\n[MEMORY] Usage ({memory.get('iterations', 0)} iterations):")
        print(f"  Enhanced Memory Usage: {memory.get('enhanced_memory_usage_mb', 0):.2f}MB")
        print(f"  Legacy Memory Usage: {memory.get('legacy_memory_usage_mb', 0):.2f}MB")
        print(f"  Memory Difference: {memory.get('memory_difference_mb', 0):.2f}MB")
    
    print("=" * 60)


def run_performance_benchmark() -> None:
    """パフォーマンスベンチマークの実行"""
    benchmark = PerformanceBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    print_benchmark_results(results)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_performance_benchmark()