#!/usr/bin/env python3
"""
Virtual Functions - プロセス終了・クリーンアップスクリプト
バックグラウンドプロセスが残った場合の緊急対処用ツール
"""

import os
import sys
import time
import psutil
import subprocess
from typing import List, Dict, Any

def find_virtual_keyboard_processes() -> List[Dict[str, Any]]:
    """Virtual Keyboardに関連するプロセスを検索"""
    processes = []
    
    # 検索キーワード
    search_keywords = [
        'main.py',
        'virtual_keyboard',
        'Virtual Functions',
        'FloatingKeyboardApp',
        'python.exe'
    ]
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
        try:
            # コマンドライン引数をチェック
            cmdline = proc.info.get('cmdline', [])
            if cmdline:
                cmdline_str = ' '.join(cmdline).lower()
                
                # main.pyを実行しているpythonプロセス
                if ('main.py' in cmdline_str and 
                    'virtualkeyboard' in cmdline_str):
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline_str,
                        'type': 'main_process'
                    })
                    continue
                
                # virtual_keyboardモジュール関連
                if any(keyword in cmdline_str for keyword in ['virtual_keyboard', 'floating']):
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline_str,
                        'type': 'related_process'
                    })
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    return processes

def kill_process_tree(pid: int) -> bool:
    """プロセスツリー全体を終了"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # 子プロセスを先に終了
        for child in children:
            try:
                print(f"Terminating child process: {child.pid} - {child.name()}")
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 親プロセスを終了
        print(f"Terminating parent process: {parent.pid} - {parent.name()}")
        parent.terminate()
        
        # 正常終了を待機（最大5秒）
        _, alive = psutil.wait_procs(children + [parent], timeout=5)
        
        # まだ生きているプロセスを強制終了
        for proc in alive:
            try:
                print(f"Force killing process: {proc.pid} - {proc.name()}")
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return True
        
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"Error killing process tree {pid}: {e}")
        return False

def cleanup_temp_files():
    """一時ファイルのクリーンアップ"""
    temp_patterns = [
        'debug_log.txt*',
        'virtual_keyboard*.tmp',
        'floating_keyboard*.tmp'
    ]
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Cleaning up temporary files in: {current_dir}")
    
    for pattern in temp_patterns:
        try:
            import glob
            files = glob.glob(os.path.join(current_dir, pattern))
            for file in files:
                try:
                    if os.path.exists(file):
                        os.remove(file)
                        print(f"Removed temp file: {file}")
                except Exception as e:
                    print(f"Failed to remove {file}: {e}")
        except Exception as e:
            print(f"Error cleaning pattern {pattern}: {e}")

def show_running_processes():
    """現在実行中のVirtual Keyboard関連プロセスを表示"""
    processes = find_virtual_keyboard_processes()
    
    if not processes:
        print("✅ Virtual Keyboard関連のプロセスは見つかりませんでした。")
        return False
    
    print(f"🔍 {len(processes)}個のVirtual Keyboard関連プロセスが見つかりました:\n")
    
    for i, proc in enumerate(processes, 1):
        print(f"{i}. PID: {proc['pid']}")
        print(f"   Name: {proc['name']}")
        print(f"   Type: {proc['type']}")
        print(f"   Command: {proc['cmdline'][:100]}...")
        print()
    
    return True

def interactive_cleanup():
    """対話式クリーンアップ"""
    print("=== Virtual Functions プロセス クリーンアップツール ===\n")
    
    # 実行中プロセスをチェック
    has_processes = show_running_processes()
    
    if not has_processes:
        cleanup_temp_files()
        return
    
    print("対処方法を選択してください:")
    print("1. すべてのプロセスを終了")
    print("2. 個別にプロセスを選択して終了")
    print("3. プロセス情報のみ表示（終了しない）")
    print("4. 一時ファイルのクリーンアップのみ")
    print("0. 終了")
    
    while True:
        try:
            choice = input("\n選択 (0-4): ").strip()
            
            if choice == "0":
                print("クリーンアップを終了します。")
                return
            
            elif choice == "1":
                # 全プロセス終了
                processes = find_virtual_keyboard_processes()
                print(f"\n{len(processes)}個のプロセスを終了します...")
                
                success_count = 0
                for proc in processes:
                    if kill_process_tree(proc['pid']):
                        success_count += 1
                
                print(f"\n✅ {success_count}/{len(processes)}個のプロセスを正常に終了しました。")
                time.sleep(1)
                cleanup_temp_files()
                break
            
            elif choice == "2":
                # 個別選択
                processes = find_virtual_keyboard_processes()
                print("\n終了するプロセスの番号を入力してください（カンマ区切りで複数指定可能）:")
                
                try:
                    indices_str = input("番号: ").strip()
                    indices = [int(x.strip()) - 1 for x in indices_str.split(",")]
                    
                    for idx in indices:
                        if 0 <= idx < len(processes):
                            proc = processes[idx]
                            print(f"終了中: PID {proc['pid']} - {proc['name']}")
                            kill_process_tree(proc['pid'])
                        else:
                            print(f"無効な番号: {idx + 1}")
                    
                    cleanup_temp_files()
                    print("選択されたプロセスの終了が完了しました。")
                    break
                    
                except ValueError:
                    print("無効な入力です。数字を入力してください。")
            
            elif choice == "3":
                # 表示のみ
                show_running_processes()
                continue
            
            elif choice == "4":
                # 一時ファイルクリーンアップのみ
                cleanup_temp_files()
                print("一時ファイルのクリーンアップが完了しました。")
                break
            
            else:
                print("無効な選択です。0-4の範囲で選択してください。")
                
        except KeyboardInterrupt:
            print("\n\nクリーンアップが中断されました。")
            return
        except Exception as e:
            print(f"エラーが発生しました: {e}")

def emergency_cleanup():
    """緊急時の自動クリーンアップ（引数指定時）"""
    print("🚨 緊急クリーンアップモード")
    
    processes = find_virtual_keyboard_processes()
    if not processes:
        print("✅ 終了すべきプロセスはありません。")
        cleanup_temp_files()
        return
    
    print(f"⚠️  {len(processes)}個のプロセスを強制終了します...")
    
    success_count = 0
    for proc in processes:
        print(f"Killing: PID {proc['pid']} - {proc['name']}")
        if kill_process_tree(proc['pid']):
            success_count += 1
    
    print(f"✅ {success_count}/{len(processes)}個のプロセスを終了しました。")
    
    # 一時ファイルもクリーンアップ
    cleanup_temp_files()
    print("🧹 緊急クリーンアップが完了しました。")

def main():
    """メイン処理"""
    if len(sys.argv) > 1 and sys.argv[1] in ['--force', '-f', 'emergency']:
        # 緊急モード（自動）
        emergency_cleanup()
    else:
        # 対話モード
        interactive_cleanup()

if __name__ == "__main__":
    # 必要な依存関係をチェック
    try:
        import psutil
    except ImportError:
        print("❌ psutil が必要です。以下のコマンドでインストールしてください:")
        print("pip install psutil")
        sys.exit(1)
    
    main()