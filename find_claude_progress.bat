@echo off
echo Claude Registry Search with Progress Indicators
echo ================================================
echo.

echo [1/15] Checking HKCU\Software\Anthropic...
reg query "HKCU\Software\Anthropic" 2>nul
if %errorlevel% equ 0 (echo    FOUND!) else (echo    Not found)

echo [2/15] Checking HKCU\Software\Claude...
reg query "HKCU\Software\Claude" 2>nul
if %errorlevel% equ 0 (echo    FOUND!) else (echo    Not found)

echo [3/15] Checking HKLM\Software\Anthropic...
reg query "HKLM\Software\Anthropic" 2>nul
if %errorlevel% equ 0 (echo    FOUND!) else (echo    Not found)

echo [4/15] Checking HKLM\Software\Claude...
reg query "HKLM\Software\Claude" 2>nul
if %errorlevel% equ 0 (echo    FOUND!) else (echo    Not found)

echo [5/15] Checking User PATH environment variable...
reg query "HKCU\Environment" /v PATH 2>nul | findstr /i "claude" >nul
if %errorlevel% equ 0 (
    echo    FOUND Claude in User PATH:
    reg query "HKCU\Environment" /v PATH 2>nul | findstr /i "claude"
) else (echo    No Claude in User PATH)

echo [6/15] Checking System PATH environment variable...
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2>nul | findstr /i "claude" >nul
if %errorlevel% equ 0 (
    echo    FOUND Claude in System PATH:
    reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2>nul | findstr /i "claude"
) else (echo    No Claude in System PATH)

echo [7/15] Checking C:\Program Files...
dir "C:\Program Files" 2>nul | findstr /i "claude" >nul
if %errorlevel% equ 0 (
    echo    FOUND:
    dir "C:\Program Files" 2>nul | findstr /i "claude"
) else (echo    No Claude found)

echo [8/15] Checking C:\Program Files (x86)...
dir "C:\Program Files (x86)" 2>nul | findstr /i "claude" >nul
if %errorlevel% equ 0 (
    echo    FOUND:
    dir "C:\Program Files (x86)" 2>nul | findstr /i "claude"
) else (echo    No Claude found)

echo [9/15] Checking %LOCALAPPDATA% (User AppData\Local)...
dir "%LOCALAPPDATA%" 2>nul | findstr /i "claude" >nul
if %errorlevel% equ 0 (
    echo    FOUND:
    dir "%LOCALAPPDATA%" 2>nul | findstr /i "claude"
) else (echo    No Claude found)

echo [10/15] Checking %APPDATA% (User AppData\Roaming)...
dir "%APPDATA%" 2>nul | findstr /i "claude" >nul
if %errorlevel% equ 0 (
    echo    FOUND:
    dir "%APPDATA%" 2>nul | findstr /i "claude"
) else (echo    No Claude found)

echo [11/15] Checking npm folder in %APPDATA%...
if exist "%APPDATA%\npm" (
    dir "%APPDATA%\npm" 2>nul | findstr /i "claude" >nul
    if %errorlevel% equ 0 (
        echo    FOUND:
        dir "%APPDATA%\npm" 2>nul | findstr /i "claude"
    ) else (echo    No Claude in npm folder)
) else (echo    npm folder not found)

echo [12/15] Running WHERE command for claude...
where claude 2>nul
if %errorlevel% equ 0 (echo    FOUND with WHERE command!) else (echo    Not in PATH)

echo [13/15] Running WHERE command for claude.exe...
where claude.exe 2>nul
if %errorlevel% equ 0 (echo    FOUND claude.exe!) else (echo    claude.exe not in PATH)

echo [14/15] Running WHERE command for claude.cmd...
where claude.cmd 2>nul
if %errorlevel% equ 0 (echo    FOUND claude.cmd!) else (echo    claude.cmd not in PATH)

echo [15/15] Checking npm global packages (this may take a moment)...
echo    Please wait, running npm list...
npm list -g --depth=0 2>nul | findstr /i "claude" >nul
if %errorlevel% equ 0 (
    echo    FOUND in npm:
    npm list -g --depth=0 2>nul | findstr /i "claude"
) else (echo    Not found in npm global packages)

echo.
echo ================================================
echo Search complete!
echo.
echo Summary of findings:
echo - Check above for any "FOUND" messages
echo - Claude Desktop is at: %LOCALAPPDATA%\AnthropicClaude\claude.exe
echo - Claude CLI (if via nvm4w) is at: C:\nvm4w\nodejs\claude.cmd
echo - Claude config is at: %USERPROFILE%\.claude
echo.
echo To run Claude CLI directly use:
echo    "C:\nvm4w\nodejs\claude.cmd"
echo.
echo.
echo Script will close in 30 seconds or press Ctrl+C to keep open...
timeout /t 30