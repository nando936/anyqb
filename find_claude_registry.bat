@echo off
echo Searching Windows Registry for Claude installations...
echo.

echo === Checking HKEY_CURRENT_USER Software ===
reg query "HKCU\Software" /s /f "claude" 2>nul | findstr /i "claude"

echo.
echo === Checking HKEY_LOCAL_MACHINE Software ===
reg query "HKLM\Software" /s /f "claude" 2>nul | findstr /i "claude"

echo.
echo === Checking Uninstall Registry (Current User) ===
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "claude" 2>nul

echo.
echo === Checking Uninstall Registry (Local Machine) ===
reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "claude" 2>nul
reg query "HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "claude" 2>nul

echo.
echo === Checking App Paths ===
reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths" /s /f "claude" 2>nul

echo.
echo === Checking Environment Variables ===
reg query "HKCU\Environment" /v PATH 2>nul | findstr /i "claude"
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2>nul | findstr /i "claude"

echo.
echo === Checking Run Keys ===
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" 2>nul | findstr /i "claude"
reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" 2>nul | findstr /i "claude"

echo.
echo === Checking File Associations ===
reg query "HKCR" /f "claude" 2>nul | findstr /i "claude"

echo.
echo Search complete!
pause