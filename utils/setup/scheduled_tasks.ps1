# Set up scheduled tasks for Google Finance data tools
param (
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# Check for administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Administrator privileges required to set up scheduled tasks. Please run this script as administrator." -ForegroundColor Red
    exit 1
}

# Get script paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$CurrentDir = (Get-Location).Path
if ($ScriptDir -ne $CurrentDir) {
    Set-Location $ScriptDir
}

# Create scheduled task
function Register-Task {
    param(
        [string]$TaskName,
        [string]$ScriptPath,
        [string]$Arguments,
        [string]$Trigger,
        [string]$Description,
        [switch]$Force
    )
    
    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    
    if ($existingTask -and -not $Force) {
        Write-Host "Task '$TaskName' already exists. Use the -Force parameter to override." -ForegroundColor Yellow
        return
    } elseif ($existingTask) {
        Write-Host "Overriding existing task: $TaskName" -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`" $Arguments"
    
    # Create trigger based on the trigger string
    switch ($Trigger) {
        "Daily" {
            $trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM
        }
        "Hourly" {
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
        }
        "Startup" {
            $trigger = New-ScheduledTaskTrigger -AtStartup
        }
        default {
            throw "Unknown trigger type: $Trigger"
        }
    }
    
    # Run as SYSTEM if the current user is not logged in at task execution time
    $principal = New-ScheduledTaskPrincipal -UserID "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Description $Description
    Write-Host "Scheduled task registered: $TaskName" -ForegroundColor Green
}

# Create necessary scheduled tasks
Write-Host "Setting up Google Finance data tools scheduled tasks..." -ForegroundColor Cyan

# 1. Connection monitor (hourly)
Register-Task -TaskName "GoogleFinance_ConnectionMonitor" `
    -ScriptPath "$CurrentDir\new_monitor_google_finance.ps1" `
    -Arguments "" `
    -Trigger "Hourly" `
    -Description "Monitor Google Finance data connection status" `
    -Force:$Force

# 2. Daily data collection (9:30 AM daily)
Register-Task -TaskName "GoogleFinance_DataCollection" `
    -ScriptPath "$CurrentDir\new_collect_daily_data.ps1" `
    -Arguments "-sendNotification" `
    -Trigger "Daily" `
    -Description "Daily automatic collection of Google Finance market data" `
    -Force:$Force

# 3. Log analysis (5:00 PM daily)
Register-Task -TaskName "GoogleFinance_LogAnalysis" `
    -ScriptPath "$CurrentDir\new_analyze_logs.ps1" `
    -Arguments "-sendNotification" `
    -Trigger "Daily" `
    -Description "Analyze Google Finance data collection logs and generate reports" `
    -Force:$Force

# 4. Startup connection monitor
Register-Task -TaskName "GoogleFinance_StartupMonitor" `
    -ScriptPath "$CurrentDir\new_monitor_google_finance.ps1" `
    -Arguments "" `
    -Trigger "Startup" `
    -Description "Start monitoring Google Finance data connection at system startup" `
    -Force:$Force

Write-Host "Google Finance scheduled tasks setup complete!" -ForegroundColor Green
Write-Host "You can view and manage these tasks in Task Scheduler." -ForegroundColor Cyan 