@echo off
echo Setting up NVM4W and Claude CLI in PATH
echo ========================================
echo.

echo Current PATH environment setup:
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Not running as Administrator
    echo Some changes may require admin privileges
    echo.
)

echo [1/5] Adding NVM4W to PATH for current session...
set "PATH=C:\nvm4w;C:\nvm4w\nodejs;%PATH%"
echo    [OK] Added to current session PATH

echo.
echo [2/5] Testing commands in current session...
echo    Testing nvm...
nvm version 2>nul
if %errorlevel% equ 0 (
    echo    [OK] nvm command now works
) else (
    echo    [ERROR] nvm still not working
)

echo    Testing node...
node --version 2>nul
if %errorlevel% equ 0 (
    echo    [OK] node command now works
) else (
    echo    [ERROR] node still not working
)

echo    Testing claude...
claude --version 2>nul
if %errorlevel% equ 0 (
    echo    [OK] claude command now works
) else (
    echo    [ERROR] claude still not working
)

echo.
echo [3/5] To make changes PERMANENT, run these commands as Administrator:
echo.
echo    For User PATH:
echo    setx PATH "C:\nvm4w;C:\nvm4w\nodejs;%%PATH%%"
echo.
echo    For System PATH (requires admin):
echo    setx /M PATH "C:\nvm4w;C:\nvm4w\nodejs;%%PATH%%"
echo.
echo    Set NVM environment variables:
echo    setx NVM_HOME "C:\nvm4w"
echo    setx NVM_SYMLINK "C:\nvm4w\nodejs"
echo.

echo [4/5] Creating command shortcuts in current directory...

REM Create nvm.bat shortcut
echo @echo off > nvm.bat
echo "C:\nvm4w\nvm.exe" %%* >> nvm.bat
echo    [OK] Created nvm.bat shortcut

REM Create claude.bat shortcut
echo @echo off > claude.bat
echo "C:\nvm4w\nodejs\claude.cmd" %%* >> claude.bat
echo    [OK] Created claude.bat shortcut

REM Create node.bat shortcut
echo @echo off > node.bat
echo "C:\nvm4w\nodejs\node.exe" %%* >> node.bat
echo    [OK] Created node.bat shortcut

echo.
echo [5/5] Alternative: Add to Windows Registry (requires admin)
echo.
echo    Would you like to see the registry commands? (y/n)
set /p answer=
if /i "%answer%"=="y" (
    echo.
    echo    Registry commands to add to PATH permanently:
    echo    reg add "HKCU\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\nvm4w;C:\nvm4w\nodejs;%%PATH%%" /f
    echo    reg add "HKCU\Environment" /v NVM_HOME /t REG_SZ /d "C:\nvm4w" /f
    echo    reg add "HKCU\Environment" /v NVM_SYMLINK /t REG_SZ /d "C:\nvm4w\nodejs" /f
)

echo.
echo ========================================
echo Setup complete!
echo.
echo For this session, you can now use:
echo    nvm list
echo    nvm use [version]
echo    claude
echo    node
echo.
echo For permanent changes:
echo    1. Run this script as Administrator
echo    2. Or manually add C:\nvm4w and C:\nvm4w\nodejs to system PATH
echo    3. Or use the .bat shortcuts created in current directory
echo.
pause