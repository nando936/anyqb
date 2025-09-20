# PowerShell script to run Claude CLI on remote computer
Write-Host "Running Claude Code CLI from nvm4w installation" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$claudePath = "C:\nvm4w\nodejs\claude.cmd"
$nodePath = "C:\nvm4w\nodejs\node.exe"
$cliPath = "C:\nvm4w\nodejs\node_modules\@anthropic-ai\claude-code\cli.js"

# Check if claude.cmd exists
if (-not (Test-Path $claudePath)) {
    Write-Host "[ERROR] Claude CLI not found at $claudePath" -ForegroundColor Red
    Write-Host "Please verify nvm4w installation" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found Claude at: $claudePath" -ForegroundColor Green
Write-Host ""

# Try different methods
Write-Host "Method 1: Direct execution..." -ForegroundColor Yellow
try {
    & $claudePath $args
    Write-Host "[OK] Claude CLI executed successfully" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "Method 1 failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Method 2: Start-Process..." -ForegroundColor Yellow
try {
    Start-Process -FilePath $claudePath -ArgumentList $args -NoNewWindow -Wait
    Write-Host "[OK] Claude CLI executed successfully" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "Method 2 failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Method 3: Node.exe directly..." -ForegroundColor Yellow
if (Test-Path $nodePath) {
    try {
        & $nodePath $cliPath $args
        Write-Host "[OK] Claude CLI executed successfully" -ForegroundColor Green
        exit 0
    } catch {
        Write-Host "Method 3 failed: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "[ERROR] All methods failed" -ForegroundColor Red
Write-Host ""
Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
Write-Host "1. Open Command Prompt as Administrator on remote computer"
Write-Host "2. Run: nvm list"
Write-Host "3. Run: nvm use [version-number]"
Write-Host "4. Run: where node"
Write-Host "5. Run: where claude"
Write-Host "6. Try: C:\nvm4w\nodejs\claude.cmd"
Write-Host ""
Write-Host "If nvm is not recognized, you may need to:"
Write-Host "- Restart Command Prompt"
Write-Host "- Check if C:\nvm4w is in system PATH"
Write-Host "- Reinstall nvm4w"

Read-Host "Press Enter to exit"