# One-click deployment for Google Finance data tools
param (
    [switch]$InstallDependencies = $true,
    [switch]$SetupTasks = $true,
    [switch]$Force = $false,
    [switch]$InstallWebDashboard = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

function Write-Step {
    param($message)
    Write-Host "`n===== $message =====" -ForegroundColor Cyan
}

# Check Python environment
Write-Step "Checking Python Environment"
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Installed: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "Python not detected, preparing to install..." -ForegroundColor Yellow
    if ($InstallDependencies) {
        Write-Host "Starting Python 3.10 installation..." -ForegroundColor Cyan
        try {
            Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.10.8/python-3.10.8-amd64.exe" -OutFile "python_installer.exe"
            Start-Process -FilePath "python_installer.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
            Remove-Item "python_installer.exe"
            Write-Host "Python 3.10 installation complete" -ForegroundColor Green
            # Refresh environment variables
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        }
        catch {
            Write-Host "Python installation failed: $_" -ForegroundColor Red
            Write-Host "Please install Python 3.8+ manually" -ForegroundColor Yellow
            exit 1
        }
    }
    else {
        Write-Host "Please install Python 3.8+ manually" -ForegroundColor Red
        exit 1
    }
}

# Install dependencies
if ($InstallDependencies) {
    Write-Step "Installing Required Python Dependencies"
    
    # Check pip
    try {
        $pipVersion = pip --version
        Write-Host "Installed: $pipVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "pip not detected, trying to install..." -ForegroundColor Yellow
        python -m ensurepip --upgrade
    }
    
    # Install googlefinance and other dependencies
    Write-Host "Installing Google Finance API and dependencies..." -ForegroundColor Green
    
    # If local googlefinance-master directory exists, install local version
    if (Test-Path "googlefinance-master") {
        Write-Host "Installing googlefinance from local directory..." -ForegroundColor Green
        pip install -e googlefinance-master
    } else {
        # Otherwise install from PyPI
        Write-Host "Installing googlefinance-api from PyPI..." -ForegroundColor Green
        pip install googlefinance-api
    }
    
    # Install other dependencies
    pip install pandas matplotlib yfinance requests scipy numpy

    # Install web dashboard dependencies if needed
    if ($InstallWebDashboard) {
        Write-Host "Installing web dashboard dependencies..." -ForegroundColor Green
        pip install flask waitress
    }
    
    Write-Host "All Python dependencies installed" -ForegroundColor Green
}

# Check and create necessary directories
Write-Step "Creating Necessary Directories"
$directories = @("logs", "data", "data/historical", "data/cache", "data/signals", "data/analysis", "data/backtests", "reports", "config")
foreach ($dir in directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "Created: $dir" -ForegroundColor Green
    }
    else {
        Write-Host "Already exists: $dir" -ForegroundColor Gray
    }
}

# Create unified notification config (if it doesn't exist)
if (-not (Test-Path "config/notification_config.json")) {
    Write-Step "Creating Unified Notification Config Template"
    $notificationConfig = @{
        telegram = @{
            enabled = $false
            botToken = "YOUR_BOT_TOKEN_HERE"
            chatId = "YOUR_CHAT_ID_HERE"
        }
        email = @{
            enabled = $false
            from = "sender@example.com"
            to = "recipient@example.com"
            username = "username@example.com"
            password = "your_password_here"
            smtpServer = "smtp.example.com"
            port = 587
            useSsl = $true
        }
        notification_preferences = @{
            system_alerts = @("Telegram", "Email")
            trading_signals = @("Telegram")
            daily_reports = @("Email")
            error_alerts = @("Telegram", "Email")
        }
    }
    $notificationConfig | ConvertTo-Json -Depth 3 | Out-File -FilePath "config/notification_config.json"
    Write-Host "Notification config template created. Please edit to fill in your credentials." -ForegroundColor Yellow
    
    # If old configs exist, try to migrate
    $migratedConfig = $false
    
    if (Test-Path "config/telegram_config.json") {
        try {
            $telegramConfig = Get-Content "config/telegram_config.json" | ConvertFrom-Json
            if ($telegramConfig.botToken -and $telegramConfig.botToken -ne "YOUR_BOT_TOKEN_HERE") {
                Write-Host "Migrating Telegram settings from old config..." -ForegroundColor Green
                $notificationConfig.telegram.botToken = $telegramConfig.botToken
                $notificationConfig.telegram.chatId = $telegramConfig.chatId
                $notificationConfig.telegram.enabled = $true
                $migratedConfig = $true
            }
        } catch {
            Write-Host "Failed to migrate Telegram config: $_" -ForegroundColor Yellow
        }
    }
    
    if (Test-Path "config/email_config.json") {
        try {
            $emailConfig = Get-Content "config/email_config.json" | ConvertFrom-Json
            if ($emailConfig.from -and $emailConfig.from -ne "sender@example.com") {
                Write-Host "Migrating Email settings from old config..." -ForegroundColor Green
                $notificationConfig.email.from = $emailConfig.from
                $notificationConfig.email.to = $emailConfig.to
                $notificationConfig.email.username = $emailConfig.username
                $notificationConfig.email.password = $emailConfig.password
                $notificationConfig.email.smtpServer = $emailConfig.smtpServer
                $notificationConfig.email.port = $emailConfig.port
                $notificationConfig.email.useSsl = $emailConfig.useSsl
                $notificationConfig.email.enabled = $true
                $migratedConfig = $true
            }
        } catch {
            Write-Host "Failed to migrate Email config: $_" -ForegroundColor Yellow
        }
    }
    
    if ($migratedConfig) {
        $notificationConfig | ConvertTo-Json -Depth 3 | Out-File -FilePath "config/notification_config.json"
        Write-Host "Successfully migrated old configs to unified notification config" -ForegroundColor Green
    }
}

# Check required script files
Write-Step "Checking Required Script Files"
$requiredScripts = @(
    "new_monitor_google_finance.ps1",
    "new_analyze_logs.ps1",
    "new_collect_daily_data.ps1",
    "new_notification.ps1",
    "new_setup_scheduled_tasks.ps1",
    "new_trading_system_controller.ps1",
    "standalone_google_finance.py",
    "analyze_market_data.py",
    "backtest_strategy.py"
)

$missingFiles = @()
foreach ($script in $requiredScripts) {
    if (-not (Test-Path $script)) {
        $missingFiles += $script
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "Warning: The following required script files are missing:" -ForegroundColor Yellow
    foreach ($file in $missingFiles) {
        Write-Host "  - $file" -ForegroundColor Yellow
    }
    Write-Host "Please ensure all required script files are downloaded to the current directory" -ForegroundColor Yellow
    
    $continue = Read-Host "Continue? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

# Setup web dashboard if requested
if ($InstallWebDashboard) {
    Write-Step "Setting Up Web Dashboard"
    
    if (Test-Path "simple_dashboard.py") {
        Write-Host "Initializing web dashboard..." -ForegroundColor Green
        
        # Create a Windows service or task for the dashboard
        if ($SetupTasks -and ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
            $taskName = "GoogleFinance_WebDashboard"
            $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            
            if ($existingTask -and -not $Force) {
                Write-Host "Task '$taskName' already exists. Use the -Force parameter to override." -ForegroundColor Yellow
            } elseif ($existingTask) {
                Write-Host "Overriding existing dashboard task" -ForegroundColor Yellow
                Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
                
                $action = New-ScheduledTaskAction -Execute "python" -Argument "simple_dashboard.py"
                $trigger = New-ScheduledTaskTrigger -AtStartup
                $principal = New-ScheduledTaskPrincipal -UserID "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
                
                Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Description "Web dashboard for Google Finance trading system"
                Write-Host "Web dashboard scheduled task registered" -ForegroundColor Green
            } else {
                $action = New-ScheduledTaskAction -Execute "python" -Argument "simple_dashboard.py"
                $trigger = New-ScheduledTaskTrigger -AtStartup
                $principal = New-ScheduledTaskPrincipal -UserID "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
                
                Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Description "Web dashboard for Google Finance trading system"
                Write-Host "Web dashboard scheduled task registered" -ForegroundColor Green
            }
        } else {
            Write-Host "To register the dashboard as a startup service, please run this script as administrator" -ForegroundColor Yellow
            Write-Host "You can manually start the dashboard with 'python simple_dashboard.py'" -ForegroundColor White
        }
    } else {
        Write-Host "Web dashboard script (simple_dashboard.py) not found." -ForegroundColor Yellow
    }
}

# Setup scheduled tasks
if ($SetupTasks -and ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Step "Setting Up Scheduled Tasks"
    if (Test-Path "new_setup_scheduled_tasks.ps1") {
        & .\new_setup_scheduled_tasks.ps1 -Force:$Force
    }
    else {
        Write-Host "Cannot set up scheduled tasks: new_setup_scheduled_tasks.ps1 file doesn't exist" -ForegroundColor Yellow
    }
}
elseif ($SetupTasks) {
    Write-Host "To set up scheduled tasks, please run this script as administrator" -ForegroundColor Yellow
}

# Deployment complete
Write-Step "Deployment Complete"
Write-Host "Google Finance data tools successfully deployed" -ForegroundColor Green
Write-Host "`nAvailable Scripts:" -ForegroundColor Cyan
Write-Host "- new_trading_system_controller.ps1 - Main system controller (integrates all components)" -ForegroundColor White
Write-Host "- new_monitor_google_finance.ps1 - Monitor Google Finance data connection status" -ForegroundColor White
Write-Host "- new_analyze_logs.ps1 - Analyze logs and generate reports" -ForegroundColor White
Write-Host "- new_collect_daily_data.ps1 - Automatically collect stock historical data" -ForegroundColor White
Write-Host "- new_notification.ps1 - Unified notification system (Telegram/Email)" -ForegroundColor White
Write-Host "- new_setup_scheduled_tasks.ps1 - Set up scheduled tasks" -ForegroundColor White
Write-Host "- analyze_market_data.py - Generate trading signals" -ForegroundColor White
Write-Host "- backtest_strategy.py - Backtest trading strategies" -ForegroundColor White
Write-Host "- simple_dashboard.py - Web-based system dashboard" -ForegroundColor White

if ($InstallWebDashboard) {
    Write-Host "`nWeb Dashboard URL: http://localhost:5000/" -ForegroundColor Green
}

Write-Host "`nStart using now?" -ForegroundColor Cyan
$choice = Read-Host "Run Trading System Controller? (y/n)"
if ($choice -eq "y") {
    Write-Host "Starting Trading System Controller..." -ForegroundColor Green
    if (Test-Path "new_trading_system_controller.ps1") {
        & .\new_trading_system_controller.ps1 -RunDataCollection -RunAnalysis -GenerateSignals -SendNotification
    }
    else {
        Write-Host "Cannot start controller: new_trading_system_controller.ps1 file doesn't exist" -ForegroundColor Red
    }
} 