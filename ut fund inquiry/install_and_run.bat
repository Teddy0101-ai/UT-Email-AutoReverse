@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

echo ============================================================
echo Gmail Fund AutoReply Checker Setup
echo ============================================================
echo.

set "VENV_DIR=venv"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe"
set "PY_CMD="

rem ============================================================
rem Step 1: Detect working Python
rem ============================================================
py -3.12 --version >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=py -3.12"
)

if not defined PY_CMD (
    python --version >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    py --version >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=py"
    )
)

if not defined PY_CMD (
    echo [INFO] No working Python found. Downloading installer...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing } catch { exit 1 }"
    if errorlevel 1 (
        echo [ERROR] Failed to download Python installer.
        echo Please install Python manually:
        echo https://www.python.org/downloads/
        pause
        exit /b 1
    )

    echo [INFO] Installing Python 3.12.9...
    "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1
    if errorlevel 1 (
        echo [ERROR] Python installation failed.
        del "%PYTHON_INSTALLER%" >nul 2>&1
        pause
        exit /b 1
    )

    del "%PYTHON_INSTALLER%" >nul 2>&1

    echo [INFO] Python installed.
    echo [INFO] Please close this window and run install_and_run.bat again.
    pause
    exit /b 0
)

echo [INFO] Using Python command: %PY_CMD%
%PY_CMD% --version
if errorlevel 1 (
    echo [ERROR] Selected Python command could not run properly.
    echo [INFO] Try disabling Windows App execution aliases for python.exe / python3.exe,
    echo        or reopen terminal and run again.
    pause
    exit /b 1
)

rem ============================================================
rem Step 2: Create virtual environment
rem ============================================================
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo.
    echo [INFO] Creating virtual environment...
    %PY_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

rem ============================================================
rem Step 3: Activate virtual environment
rem ============================================================
echo.
echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

rem ============================================================
rem Step 4: Upgrade pip
rem ============================================================
echo.
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

rem ============================================================
rem Step 5: Install dependencies if needed
rem ============================================================
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found.
    pause
    exit /b 1
)

set "REQUIRES_INSTALL=1"
if exist "%VENV_DIR%\requirements_installed.txt" (
    fc /b requirements.txt "%VENV_DIR%\requirements_installed.txt" >nul 2>&1
    if not errorlevel 1 set "REQUIRES_INSTALL=0"
)

if "!REQUIRES_INSTALL!"=="1" (
    echo.
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    copy /y requirements.txt "%VENV_DIR%\requirements_installed.txt" >nul
) else (
    echo.
    echo [INFO] Dependencies are up to date.
)

rem ============================================================
rem Step 6: Check required files
rem ============================================================
if not exist "credentials.json" (
    echo.
    echo [ERROR] credentials.json not found.
    echo Put your real Google OAuth desktop credentials JSON in this folder.
    pause
    exit /b 1
)

if not exist "masterlist.xlsx" (
    echo.
    echo [ERROR] masterlist.xlsx not found.
    echo Put your real masterlist.xlsx in this folder.
    pause
    exit /b 1
)

if not exist "launcher.py" (
    echo.
    echo [ERROR] launcher.py not found.
    pause
    exit /b 1
)

rem ============================================================
rem Step 7: Start app
rem ============================================================
echo.
echo [INFO] Starting application...
python launcher.py

echo.
echo [INFO] Application exited.
pause
endlocal