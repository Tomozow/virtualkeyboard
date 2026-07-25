@echo off
REM Virtual Functions v1.1 Build Script
REM 実行可能ファイル作成用バッチファイル

echo ================================
echo Virtual Functions v1.1 ビルド
echo ================================

REM ビルドディレクトリをクリーンアップ
echo クリーンアップ中...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM PyInstallerでビルド実行
echo ビルド実行中...
pyinstaller --onefile --windowed --name="VirtualFunctions_v1.1" --icon=icon.ico --add-data="config.json;." main.py

REM ビルド結果確認
if exist dist\VirtualFunctions_v1.1.exe (
    echo.
    echo ================================
    echo ビルド完了！
    echo ================================
    echo 実行ファイル: dist\VirtualFunctions_v1.1.exe
    dir dist\VirtualFunctions_v1.1.exe
    echo.
    echo 配布準備:
    echo 1. dist\VirtualFunctions_v1.1.exe をコピー
    echo 2. config.json は実行ファイルと同じフォルダに配置
    echo.
) else (
    echo.
    echo ================================
    echo ビルドエラー
    echo ================================
    echo 詳細はログを確認してください。
    echo.
)

pause