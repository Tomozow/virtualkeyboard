# -*- mode: python ; coding: utf-8 -*-
"""
Virtual Functions v1.1 PyInstaller Spec File
実行可能ファイル生成用の設定
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files

# 現在のディレクトリを取得
current_dir = os.path.dirname(os.path.abspath(SPEC))

# バージョン情報を読み込み
sys.path.insert(0, current_dir)
from version_info import VERSION_INFO

# データファイルの収集
datas = []

# 設定ファイル
config_file = os.path.join(current_dir, 'config.json')
if os.path.exists(config_file):
    datas.append((config_file, '.'))

# アイコンファイル
icon_file = os.path.join(current_dir, 'icon.ico')
if os.path.exists(icon_file):
    datas.append((icon_file, '.'))

# CustomTkinterのテーマファイル
try:
    ctk_data = collect_data_files('customtkinter')
    datas.extend(ctk_data)
except:
    pass

# PIL/Pillowのファイル
try:
    pil_data = collect_data_files('PIL')
    datas.extend(pil_data)
except:
    pass

# 必要な隠されたインポート
hiddenimports = [
    'virtual_keyboard',
    'virtual_keyboard.config',
    'virtual_keyboard.config.manager',
    'virtual_keyboard.services',
    'virtual_keyboard.services.keysender',
    'virtual_keyboard.services.focus',
    'virtual_keyboard.services.hotkey',
    'virtual_keyboard.ui',
    'virtual_keyboard.ui.floating',
    'virtual_keyboard.ui.main_window',
    'virtual_keyboard.ui.button_manager',
    'virtual_keyboard.ui.dialogs',
    'virtual_keyboard.ui.button_edit_dialog',
    'virtual_keyboard.ui.window_selector',
    'virtual_keyboard.core',
    'virtual_keyboard.core.types',
    'virtual_keyboard.core.interfaces',
    'virtual_keyboard.utils',
    'virtual_keyboard.utils.window_utils',
    'customtkinter',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'win32api',
    'win32gui',
    'win32con',
    'win32process',
    'win32console',
    'pywintypes',
    'emoji',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'tkinterdnd2'
]

# 除外するモジュール
excludes = [
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'jupyter',
    'notebook',
    'IPython',
    'test',
    'tests',
    'unittest',
    'pytest'
]

# 分析設定
a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 不要なファイルを除去
def remove_unwanted_files(a):
    """不要なファイルを除去してサイズを削減"""
    # 除去するファイルパターン
    unwanted_patterns = [
        '_test',
        'test_',
        '.pyc',
        '__pycache__',
        '.git',
        '.vscode',
        'docs',
        'examples',
    ]
    
    a.binaries = [
        (name, path, type_) for name, path, type_ in a.binaries
        if not any(pattern in name.lower() or pattern in path.lower() 
                  for pattern in unwanted_patterns)
    ]
    
    a.datas = [
        (name, path, type_) for name, path, type_ in a.datas
        if not any(pattern in name.lower() or pattern in path.lower() 
                  for pattern in unwanted_patterns)
    ]
    
    return a

a = remove_unwanted_files(a)

# バイナリ生成
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 実行可能ファイル生成
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VirtualFunctions_v1.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # UPX圧縮を有効化（サイズ削減）
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # コンソールウィンドウを非表示
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file if os.path.exists(icon_file) else None,
    version_file=None,  # version_fileは後で追加
    uac_admin=False,  # 管理者権限は不要
    uac_uiaccess=False,
    manifest=None,
)

# バージョン情報を含むWindowsバイナリリソース（後で手動追加可能）
version_info_template = f"""
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({VERSION_INFO['FileVersion'].replace('.', ', ')}),
    prodvers=({VERSION_INFO['ProductVersion'].replace('.', ', ')}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'{VERSION_INFO['CompanyName']}'),
            StringStruct(u'FileDescription', u'{VERSION_INFO['FileDescription']}'),
            StringStruct(u'FileVersion', u'{VERSION_INFO['FileVersion']}'),
            StringStruct(u'InternalName', u'{VERSION_INFO['InternalName']}'),
            StringStruct(u'LegalCopyright', u'{VERSION_INFO['LegalCopyright']}'),
            StringStruct(u'OriginalFilename', u'{VERSION_INFO['OriginalFilename']}'),
            StringStruct(u'ProductName', u'{VERSION_INFO['ProductName']}'),
            StringStruct(u'ProductVersion', u'{VERSION_INFO['ProductVersion']}'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

print("PyInstaller spec file created successfully!")
print(f"Output executable: VirtualFunctions_v1.1.exe")
print(f"Icon file: {'Found' if os.path.exists(icon_file) else 'Not found'}")
print(f"Config file: {'Found' if os.path.exists(config_file) else 'Not found'}")