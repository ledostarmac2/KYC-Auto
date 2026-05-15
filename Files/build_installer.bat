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

if not exist "..\KYCReminder.exe" (
    echo KYCReminder.exe was not found in the parent folder.
    echo Building KYCReminder.exe first...
    call "%~dp0build.bat"
    if errorlevel 1 (
        echo ERROR: Could not build KYCReminder.exe
        if not defined CI pause
        exit /b 1
    )
)

if not exist "msedgedriver.exe" (
    echo.
    echo Downloading Microsoft Edge WebDriver...
    "%PYTHON_PATH%" download_edgedriver.py
    if errorlevel 1 (
        echo ERROR: Could not download Microsoft Edge WebDriver
        if not defined CI pause
        exit /b 1
    )
)

echo Found Python: %PYTHON_PATH%
echo.
echo Installing PyInstaller...
"%PYTHON_PATH%" -m pip install pyinstaller -q
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    if not defined CI pause
    exit /b 1
)

echo.
echo Building setup wizard...
"%PYTHON_PATH%" -m PyInstaller --clean --noconfirm --distpath installer_release setup_wizard.spec
if errorlevel 1 (
    echo ERROR: Failed to build setup wizard
    if not defined CI pause
    exit /b 1
)

copy /Y "installer_release\KYCReminderSetup.exe" "..\KYCReminderSetup.exe" >nul
if errorlevel 1 (
    echo WARNING: Built the setup wizard, but could not copy it to the parent KYC folder.
)

echo.
echo Cleaning temporary installer build files...
if exist "build" rmdir /S /Q "build"
if exist "installer_release" rmdir /S /Q "installer_release"
if exist "__pycache__" rmdir /S /Q "__pycache__"

echo.
echo Done! KYCReminderSetup.exe is in the parent KYC folder.
if not defined CI pause
