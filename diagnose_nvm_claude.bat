@echo off
echo NVM4W and Claude CLI Diagnostic Tool
echo =====================================
echo.

echo [1/10] Checking nvm4w installation...
if exist "C:\nvm4w\nvm.exe" (
    echo    [OK] nvm4w found at C:\nvm4w
) else (
    echo    [ERROR] nvm4w not found at C:\nvm4w
)

echo.
echo [2/10] Checking current PATH...
echo %PATH% | findstr /i "nvm4w" >nul
if %errorlevel% equ 0 (
    echo    [OK] nvm4w is in PATH
) else (
    echo    [WARNING] nvm4w not in PATH
)

echo.
echo [3/10] Checking Node.js in nvm4w...
if exist "C:\nvm4w\nodejs\node.exe" (
    echo    [OK] Node.js found at C:\nvm4w\nodejs
    "C:\nvm4w\nodejs\node.exe" --version 2>nul
) else (
    echo    [ERROR] Node.js not found at C:\nvm4w\nodejs
)

echo.
echo [4/10] Checking claude.cmd...
if exist "C:\nvm4w\nodejs\claude.cmd" (
    echo    [OK] claude.cmd found
) else (
    echo    [ERROR] claude.cmd not found
)

echo.
echo [5/10] Checking Claude CLI package...
if exist "C:\nvm4w\nodejs\node_modules\@anthropic-ai\claude-code\cli.js" (
    echo    [OK] Claude CLI package found
) else (
    echo    [ERROR] Claude CLI package not found
)

echo.
echo [6/10] Testing nvm command...
nvm version 2>nul
if %errorlevel% equ 0 (
    echo    [OK] nvm command works
    echo.
    echo    Active Node versions:
    nvm list
) else (
    echo    [ERROR] nvm command not recognized
    echo    Try opening a new Command Prompt
)

echo.
echo [7/10] Testing node command...
node --version 2>nul
if %errorlevel% equ 0 (
    echo    [OK] node command works
) else (
    echo    [WARNING] node command not recognized
)

echo.
echo [8/10] Testing claude command...
claude --version 2>nul
if %errorlevel% equ 0 (
    echo    [OK] claude command works
) else (
    echo    [WARNING] claude command not recognized
)

echo.
echo [9/10] Checking Windows environment variables...
reg query "HKCU\Environment" /v NVM_HOME 2>nul
if %errorlevel% equ 0 (
    echo    [OK] NVM_HOME is set in user environment
) else (
    echo    [WARNING] NVM_HOME not set
)

reg query "HKCU\Environment" /v NVM_SYMLINK 2>nul
if %errorlevel% equ 0 (
    echo    [OK] NVM_SYMLINK is set in user environment
) else (
    echo    [WARNING] NVM_SYMLINK not set
)

echo.
echo [10/10] Recommended fixes:
echo.
echo If claude command doesn't work:
echo 1. Open new Command Prompt (close current one first)
echo 2. Run: nvm list
echo 3. Run: nvm use [version-number]
echo 4. Try: C:\nvm4w\nodejs\claude.cmd
echo.
echo Alternative: Run claude directly:
echo    "C:\nvm4w\nodejs\node.exe" "C:\nvm4w\nodejs\node_modules\@anthropic-ai\claude-code\cli.js"
echo.
pause