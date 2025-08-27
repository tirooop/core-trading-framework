# Trading System Controller - Unified Workflow Management
param(
    [switch]$RunDataCollection = $false,
    [switch]$RunAnalysis = $false,
    [switch]$GenerateSignals = $true,
    [switch]$Backtest = $false,
    [string[]]$symbols = @("SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA"),
    [switch]$SendNotification = $true,
    [string]$LogFile = "logs/trading_system_$(Get-Date -Format 'yyyyMMdd').log"
)

$ErrorActionPreference = "Stop"

# Ensure log directory exists
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }

# Function: Write to log file
function Write-Log {
    param($message, $color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $message" -ForegroundColor $color
    "[$timestamp] $message" | Out-File -Append -FilePath $LogFile
}

# Function: Check if script exists
function Verify-Script {
    param([string]$scriptPath)
    
    if (Test-Path $scriptPath) {
        return $true
    }
    else {
        Write-Log "Missing required script: $scriptPath" "Red"
        return $false
    }
}

# Welcome message
Write-Log "=========================================" "Cyan"
Write-Log "  Trading System Controller Started" "Cyan"
Write-Log "=========================================" "Cyan"

# Step 1: Verify all required script files
Write-Log "Verifying required components..." "White"
$requiredScripts = @(
    "new_collect_daily_data.ps1",
    "new_analyze_logs.ps1",
    "new_notification.ps1",
    "standalone_google_finance.py"
)

$allScriptsExist = $true
foreach ($script in $requiredScripts) {
    if (-not (Verify-Script $script)) {
        $allScriptsExist = $false
    }
}

if (-not $allScriptsExist) {
    Write-Log "One or more required scripts are missing. Please run new_deploy_google_finance.ps1 first." "Red"
    if ($SendNotification) {
        & .\new_notification.ps1 -message "⚠️ CRITICAL: Trading system controller failed to start due to missing components" -subject "Trading System Error" -channel "Telegram"
    }
    exit 1
}

Write-Log "All required components verified" "Green"

# Step 2: Data Collection (if requested)
if ($RunDataCollection) {
    Write-Log "Starting data collection process..." "Cyan"
    try {
        & .\new_collect_daily_data.ps1 -symbols $symbols -includeOptions -sendNotification:$SendNotification
        Write-Log "Data collection completed successfully" "Green"
    }
    catch {
        Write-Log "Data collection failed: $_" "Red"
        if ($SendNotification) {
            & .\new_notification.ps1 -message "⚠️ ERROR: Data collection process failed`n$_" -subject "Trading System Error" -channel "Telegram"
        }
    }
}

# Step 3: Log Analysis (if requested)
if ($RunAnalysis) {
    Write-Log "Starting log analysis process..." "Cyan"
    try {
        & .\new_analyze_logs.ps1 -sendNotification:$SendNotification
        Write-Log "Log analysis completed successfully" "Green"
    }
    catch {
        Write-Log "Log analysis failed: $_" "Red"
        if ($SendNotification) {
            & .\new_notification.ps1 -message "⚠️ ERROR: Log analysis process failed`n$_" -subject "Trading System Error" -channel "Telegram"
        }
    }
}

# Step 4: Generate Trading Signals (if requested)
if ($GenerateSignals) {
    Write-Log "Generating trading signals..." "Cyan"
    
    # Define the output directory for signals
    $signalDir = "data/signals"
    if (-not (Test-Path $signalDir)) { New-Item -ItemType Directory -Path $signalDir | Out-Null }
    
    $signalFile = "$signalDir/trading_signals_$(Get-Date -Format 'yyyyMMdd').json"
    $signalCount = 0
    $signalResults = @()
    
    try {
        # Process each symbol to generate signals
        foreach ($symbol in $symbols) {
            Write-Log "Processing signals for $symbol..." "White"
            
            # Run the Python analysis script (we'll create this next)
            $pythonCmd = "python analyze_market_data.py --symbol $symbol --generate-signals"
            $signalOutput = Invoke-Expression $pythonCmd
            
            if ($signalOutput -match "SIGNAL:") {
                # If signal detected, process it
                $signal = $signalOutput | Select-String "SIGNAL:" | ForEach-Object { $_.Line.Replace("SIGNAL:", "").Trim() }
                
                foreach ($s in $signal) {
                    $signalData = ConvertFrom-Json $s
                    $signalResults += $signalData
                    $signalCount++
                    
                    Write-Log "  Signal for $($signalData.symbol): $($signalData.action) at $($signalData.price)" "Green"
                }
            }
        }
        
        # Save all signals to a JSON file
        if ($signalCount -gt 0) {
            $signalResults | ConvertTo-Json | Out-File -FilePath $signalFile
            Write-Log "Generated $signalCount trading signals, saved to $signalFile" "Green"
            
            # Send notification about signals
            if ($SendNotification) {
                $signalMessage = "🔔 <b>Trading Signals Generated</b>`n`n"
                $signalMessage += "<b>Date:</b> $(Get-Date -Format 'yyyy-MM-dd')`n"
                $signalMessage += "<b>Total Signals:</b> $signalCount`n`n"
                
                foreach ($result in $signalResults | Select-Object -First 5) {
                    $signalMessage += "• <b>$($result.symbol):</b> $($result.action) at $($result.price) - $($result.reason)`n"
                }
                
                if ($signalCount -gt 5) {
                    $signalMessage += "`n<i>... and $($signalCount - 5) more signals</i>"
                }
                
                & .\new_notification.ps1 -message $signalMessage -subject "Trading Signals Generated" -channel "All"
            }
        }
        else {
            Write-Log "No trading signals generated for the current market conditions" "Yellow"
        }
    }
    catch {
        Write-Log "Signal generation failed: $_" "Red"
        if ($SendNotification) {
            & .\new_notification.ps1 -message "⚠️ ERROR: Signal generation process failed`n$_" -subject "Trading System Error" -channel "Telegram"
        }
    }
}

# Step 5: Run Backtesting (if requested)
if ($Backtest) {
    Write-Log "Running backtesting simulation..." "Cyan"
    
    try {
        # Execute backtesting script
        $backtestOutput = Invoke-Expression "python backtest_strategy.py --days 30 --verbose"
        Write-Log "Backtesting completed" "Green"
        
        # Extract performance metrics
        if ($backtestOutput -match "PERFORMANCE:") {
            $perfData = $backtestOutput | Select-String "PERFORMANCE:" | ForEach-Object { $_.Line.Replace("PERFORMANCE:", "").Trim() }
            $performance = ConvertFrom-Json $perfData
            
            Write-Log "Backtest Results:" "Cyan"
            Write-Log "  Time Period: $($performance.period)" "White"
            Write-Log "  Total Return: $($performance.total_return)%" "White"
            Write-Log "  Max Drawdown: $($performance.max_drawdown)%" "White"
            Write-Log "  Sharpe Ratio: $($performance.sharpe)" "White"
            
            # Send notification with performance results
            if ($SendNotification) {
                $backtestMessage = "📊 <b>Backtest Results</b>`n`n"
                $backtestMessage += "<b>Period:</b> $($performance.period)`n"
                $backtestMessage += "<b>Total Return:</b> $($performance.total_return)%`n"
                $backtestMessage += "<b>Max Drawdown:</b> $($performance.max_drawdown)%`n"
                $backtestMessage += "<b>Win Rate:</b> $($performance.win_rate)%`n"
                $backtestMessage += "<b>Sharpe Ratio:</b> $($performance.sharpe)`n"
                
                & .\new_notification.ps1 -message $backtestMessage -subject "Backtest Results" -channel "All"
            }
        }
    }
    catch {
        Write-Log "Backtesting failed: $_" "Red"
        if ($SendNotification) {
            & .\new_notification.ps1 -message "⚠️ ERROR: Backtesting process failed`n$_" -subject "Trading System Error" -channel "Telegram"
        }
    }
}

Write-Log "Trading System Controller execution completed" "Cyan" 