# PyInstaller spec — сборка одного .exe (Windows), запускается в GitHub Actions.
# Команда: pyinstaller build/funpay_assistant.spec  (из папки funpay-assistant)

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        "funpay_assistant.funpay_client",
        "funpay_assistant.demo_client",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="FunPayAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,  # оконное приложение (без чёрного окна консоли)
)
