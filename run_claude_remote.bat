@echo off
echo Running Claude Code CLI from nvm4w installation
echo ===============================================
echo.

REM Check if nvm4w path exists
if not exist "C:\nvm4w\nodejs\claude.cmd" (
    echo [ERROR] Claude CLI not found at C:\nvm4w\nodejs\claude.cmd
    echo Please verify nvm4w installation
    pause
    exit /b 1
)

REM Method 1: Direct execution with full path
echo Method 1: Running with full path...
"C:\nvm4w\nodejs\claude.cmd" %*
if %errorlevel% equ 0 goto :success

REM Method 2: Call with full path
echo.
echo Method 2: Trying CALL command...
call "C:\nvm4w\nodejs\claude.cmd" %*
if %errorlevel% equ 0 goto :success

REM Method 3: Set PATH and run
echo.
echo Method 3: Adding to PATH temporarily...
set "PATH=C:\nvm4w\nodejs;%PATH%"
claude %*
if %errorlevel% equ 0 goto :success

REM Method 4: Run node directly
echo.
echo Method 4: Running Node.js directly...
if exist "C:\nvm4w\nodejs\node.exe" (
    "C:\nvm4w\nodejs\node.exe" "C:\nvm4w\nodejs\node_modules\@anthropic-ai\claude-code\cli.js" %*
    if %errorlevel% equ 0 goto :success
)

echo.
echo [ERROR] All methods failed. Possible issues:
echo - nvm4w may need to be activated first
echo - Node.js version may not be selected
echo - Permission issues with the installation
echo.
echo Try running these commands on the remote computer:
echo   nvm list
echo   nvm use [version]
echo   where node
echo   where claude
pause
exit /b 1

:success
echo.
echo [OK] Claude CLI executed successfully
exit /b 0