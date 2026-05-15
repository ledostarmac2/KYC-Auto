@echo off
cd /d "%~dp0"

REM Find Python in common locations
for %%i in (python.exe) do set "PYTHON_PATH=%%~$PATH:i"

if not defined PYTHON_PATH (
    echo Searching for Python...
    for /f "delims=" %%i in ('where python 2^>nul') do set "PYTHON_PATH=%%i"
)

if not defined PYTHON_PATH (
    echo ERROR: Python not found!
    echo Please install Python from https://www.python.org
    echo Make sure to check "Add Python to PATH" during installation.
    if not defined CI pause
    exit /b 1
)

echo Found Python: %PYTHON_PATH%
echo.
echo Installing dependencies...
"%PYTHON_PATH%" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo WARNING: Failed to install some dependencies
)

if not exist "msedgedriver.exe" (
    echo.
    echo Downloading Microsoft Edge WebDriver...
    "%PYTHON_PATH%" download_edgedriver.py
    if errorlevel 1 (
        echo ERROR: Failed to download Microsoft Edge WebDriver
        if not defined CI pause
        exit /b 1
    )
)

echo.
echo Installing PyInstaller...
"%PYTHON_PATH%" -m pip install pyinstaller -q
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    if not defined CI pause
    exit /b 1
)

echo.
echo Building executable...
"%PYTHON_PATH%" -m PyInstaller --clean --noconfirm --distpath release kyc_reminder.spec
if errorlevel 1 (
    echo ERROR: Failed to build executable
    if not defined CI pause
    exit /b 1
)

copy /Y "release\KYCReminder.exe" "..\KYCReminder.exe" >nul
if errorlevel 1 (
    echo WARNING: Built the executable, but could not copy it to the parent KYC folder.
)

echo.
echo Cleaning temporary build files...
if exist "build" rmdir /S /Q "build"
if exist "release" rmdir /S /Q "release"
if exist "__pycache__" rmdir /S /Q "__pycache__"

echo.
echo Done! Your executable is in the parent KYC folder.
echo KYCReminder.exe is ready to use!
if not defined CI pause
