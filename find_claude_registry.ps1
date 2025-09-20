# PowerShell script to find Claude in Windows Registry

Write-Host "Searching for Claude in Windows Registry..." -ForegroundColor Cyan
Write-Host ""

# Function to search registry
function Search-RegistryForClaude {
    param($Path, $Description)

    Write-Host "=== $Description ===" -ForegroundColor Yellow
    try {
        Get-ChildItem -Path $Path -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*claude*" -or $_.PSChildName -like "*claude*" } |
        ForEach-Object {
            Write-Host $_.PSPath -ForegroundColor Green
            if ($_.Property) {
                $_.Property | Where-Object { $_ -like "*claude*" } | ForEach-Object {
                    $value = (Get-ItemProperty -Path $_.PSPath -Name $_).$_
                    Write-Host "  Property: $_ = $value" -ForegroundColor Gray
                }
            }
        }

        Get-ItemProperty -Path "$Path\*" -ErrorAction SilentlyContinue |
        ForEach-Object {
            $item = $_
            $_.PSObject.Properties | Where-Object { $_.Value -like "*claude*" } |
            ForEach-Object {
                Write-Host "$($item.PSPath)" -ForegroundColor Green
                Write-Host "  $($_.Name) = $($_.Value)" -ForegroundColor Gray
            }
        }
    }
    catch {
        Write-Host "  Error accessing $Path" -ForegroundColor Red
    }
    Write-Host ""
}

# Search main registry locations
Search-RegistryForClaude "HKCU:\Software" "Current User Software"
Search-RegistryForClaude "HKLM:\Software" "Local Machine Software"
Search-RegistryForClaude "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall" "User Uninstall Info"
Search-RegistryForClaude "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall" "System Uninstall Info"
Search-RegistryForClaude "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" "32-bit Apps on 64-bit System"

# Check environment variables
Write-Host "=== Environment Variables ===" -ForegroundColor Yellow
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$machinePath = [Environment]::GetEnvironmentVariable("PATH", "Machine")

if ($userPath -like "*claude*") {
    Write-Host "User PATH contains Claude:" -ForegroundColor Green
    $userPath.Split(';') | Where-Object { $_ -like "*claude*" } | ForEach-Object { Write-Host "  $_" }
}

if ($machinePath -like "*claude*") {
    Write-Host "System PATH contains Claude:" -ForegroundColor Green
    $machinePath.Split(';') | Where-Object { $_ -like "*claude*" } | ForEach-Object { Write-Host "  $_" }
}

Write-Host ""
Write-Host "Search complete!" -ForegroundColor Cyan