@echo off
echo Quick Claude Registry Search...
echo.

echo === Checking specific Claude locations ===
reg query "HKCU\Software\Anthropic" 2>nul
reg query "HKCU\Software\Claude" 2>nul
reg query "HKLM\Software\Anthropic" 2>nul
reg query "HKLM\Software\Claude" 2>nul

echo.
echo === Checking npm/node locations ===
reg query "HKCU\Software\Node.js" 2>nul | findstr /i "claude"
reg query "HKLM\Software\Node.js" 2>nul | findstr /i "claude"

echo.
echo === Checking PATH for Claude ===
echo User PATH entries with Claude:
reg query "HKCU\Environment" /v PATH 2>nul | findstr /i "claude"

echo.
echo System PATH entries with Claude:
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2>nul | findstr /i "claude"

echo.
echo === Checking Uninstall (non-recursive) ===
dir "C:\Program Files" 2>nul | findstr /i "claude"
dir "C:\Program Files (x86)" 2>nul | findstr /i "claude"
dir "%LOCALAPPDATA%" 2>nul | findstr /i "claude"
dir "%APPDATA%" 2>nul | findstr /i "claude"

echo.
echo === Checking where command ===
where claude 2>nul
where claude.exe 2>nul
where claude.cmd 2>nul

echo.
echo === Checking npm global packages ===
npm list -g --depth=0 2>nul | findstr /i "claude"

echo.
echo Search complete!
pause