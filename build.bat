@echo off
REM ==========================================================================
REM FunPay AutoResponder - build script (Windows)
REM Creates dist\FunPayAutoResponder\ and (optionally) the Inno Setup installer
REM ==========================================================================
setlocal
cd /d "%~dp0"

echo ==^> Creating virtual environment (.venv)
if not exist ".venv" (
    py -3 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate.bat

echo ==^> Installing dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

echo ==^> Generating assets (icons + sounds)
python scripts\generate_assets.py

echo ==^> Installing Playwright browser (chromium)
python -m playwright install chromium

echo ==^> Building with PyInstaller
pyinstaller --noconfirm FunPayAutoResponder.spec

echo.
echo Build complete: dist\FunPayAutoResponder\
echo.
echo To build the installer, open installer\setup.iss in Inno Setup Compiler,
echo or run:  iscc installer\setup.iss
echo (Requires Inno Setup 6+: https://jrsoftware.org/isdl.php)

endlocal
