@echo off
REM Запуск InvoiceForge на Windows (двойной клик или из cmd).
cd /d "%~dp0"

if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate

echo Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if "%INVOICEFORGE_PORT%"=="" set INVOICEFORGE_PORT=8000
echo Starting InvoiceForge on http://127.0.0.1:%INVOICEFORGE_PORT%
python -m uvicorn app.main:app --host 0.0.0.0 --port %INVOICEFORGE_PORT%
pause
