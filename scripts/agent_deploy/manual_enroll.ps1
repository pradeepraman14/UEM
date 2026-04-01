# ============================================================
# UEM Agent - Manual Enrollment Script
# Run on the Windows endpoint to install and enroll the agent
#
# Usage:
#   .\manual_enroll.ps1 -ServerUrl "https://your-uem-server" -EnrollmentToken "TOKEN_HERE"
# ============================================================
param(
    [Parameter(Mandatory=$true)]
    [string]$ServerUrl,

    [Parameter(Mandatory=$true)]
    [string]$EnrollmentToken,

    [string]$AgentInstallerUrl = "",
    [string]$InstallDir = "C:\Program Files\UEMAgent"
)

$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host " UEM Agent - Enrollment Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check for admin rights
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator"
    exit 1
}

# Check if agent is already installed
$agentExe = "$InstallDir\agent_main.exe"
$pythonAgent = "$InstallDir\agent_main.py"

if (Test-Path $agentExe) {
    Write-Host "✅ UEM Agent already installed at: $InstallDir" -ForegroundColor Green
} elseif (Test-Path $pythonAgent) {
    Write-Host "✅ UEM Agent (Python) found at: $InstallDir" -ForegroundColor Green
} else {
    Write-Host "⚠️  Agent not found. " -ForegroundColor Yellow

    if ($AgentInstallerUrl -ne "") {
        Write-Host "Downloading agent from: $AgentInstallerUrl" -ForegroundColor Yellow
        $installerPath = "$env:TEMP\uem-agent-setup.exe"
        Invoke-WebRequest -Uri $AgentInstallerUrl -OutFile $installerPath -UseBasicParsing

        Write-Host "Installing agent..." -ForegroundColor Yellow
        Start-Process $installerPath -ArgumentList "/S" -Wait
        Remove-Item $installerPath -Force
    } else {
        Write-Error "Agent not installed and no installer URL provided. Please install the agent first."
        exit 1
    }
}

# Run enrollment
Write-Host ""
Write-Host "Enrolling device with UEM server..." -ForegroundColor Yellow
Write-Host "  Server: $ServerUrl"
Write-Host ""

if (Test-Path $agentExe) {
    & $agentExe enroll --server $ServerUrl --token $EnrollmentToken
} elseif (Test-Path $pythonAgent) {
    python $pythonAgent enroll --server $ServerUrl --token $EnrollmentToken
} else {
    Write-Error "Could not find agent executable"
    exit 1
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Enrollment successful!" -ForegroundColor Green

    # Install and start the Windows service
    Write-Host "Installing Windows service..." -ForegroundColor Yellow
    if (Test-Path $agentExe) {
        & $agentExe install
        Start-Service -Name "UEMAgent"
    }

    Write-Host "✅ UEM Agent service started" -ForegroundColor Green
    Write-Host ""
    Write-Host "The device will now appear in the UEM console." -ForegroundColor Cyan
} else {
    Write-Error "Enrollment failed. Check the server URL and token."
    exit 1
}
