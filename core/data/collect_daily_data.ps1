# Automatic daily data collection for monitored stocks (Google Finance version)
param (
    [string[]]$symbols = @("SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA"),
    [switch]$includeOptions = $false,
    [switch]$sendNotification = $false
)

$ErrorActionPreference = "Stop"
$logFile = "logs/data_collection_$(Get-Date -Format 'yyyyMMdd').log"

function Write-Log {
    param($message, $color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $message" -ForegroundColor $color
    "[$timestamp] $message" | Out-File -Append -FilePath $logFile
}

# Ensure log directory exists
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }
Write-Log "Starting historical data collection (Google Finance)..." "Cyan"

# Check if it's a trading day
$today = Get-Date
if ($today.DayOfWeek -eq "Saturday" -or $today.DayOfWeek -eq "Sunday") {
    Write-Log "Today is a weekend, skipping data collection" "Yellow"
    exit
}

# Collection result tracking
$successCount = 0
$failureCount = 0
$processedSymbols = @()

# Collect data for each stock
foreach ($symbol in $symbols) {
    Write-Log "Processing $symbol daily data..." "Green"
    $symbolSuccess = $true
    
    # Collect daily data
    try {
        # Use the new standalone Google Finance version
        $cmd = "python standalone_google_finance.py --symbol $symbol --historical --timeframe 1d --days 5 --plot --save"
        Invoke-Expression $cmd
        Write-Log "  $symbol daily data collection complete" "Green"
    }
    catch {
        Write-Log "  $symbol daily data collection failed: $_" "Red"
        $symbolSuccess = $false
    }
    
    # Collect hourly data
    try {
        $cmd = "python standalone_google_finance.py --symbol $symbol --historical --timeframe 1h --days 3 --save"
        Invoke-Expression $cmd
        Write-Log "  $symbol hourly data collection complete" "Green"
    }
    catch {
        Write-Log "  $symbol hourly data collection failed: $_" "Red"
        $symbolSuccess = $false
    }
    
    # Get options chain data if needed
    if ($includeOptions) {
        Write-Log "  Processing $symbol options chain data..." "Blue"
        try {
            $cmd = "python standalone_google_finance.py --symbol $symbol --options"
            Invoke-Expression $cmd
            Write-Log "  $symbol options chain data collection complete" "Blue"
        }
        catch {
            Write-Log "  $symbol options chain data collection failed: $_" "Red"
            $symbolSuccess = $false
        }
    }
    
    # Update counters
    if ($symbolSuccess) {
        $successCount++
    } else {
        $failureCount++
    }
    
    $processedSymbols += $symbol
    
    # Small pause to avoid too frequent requests
    Start-Sleep -Seconds 3
}

Write-Log "All data collection tasks completed" "Cyan"

# Generate summary information
$dataFiles = Get-ChildItem -Path "data/historical" -Filter "*$(Get-Date -Format 'yyyyMMdd')*"
$summaryFile = "data/historical/_Summary_Report_$(Get-Date -Format 'yyyyMMdd').txt"

"Data Collection Summary - $(Get-Date)" | Out-File -FilePath $summaryFile
"Collection Time: $(Get-Date)" | Out-File -FilePath $summaryFile -Append
"Collected Symbols: $($symbols -join ', ')" | Out-File -FilePath $summaryFile -Append
"Total Files: $($dataFiles.Count)" | Out-File -FilePath $summaryFile -Append
"Success: $successCount, Failed: $failureCount" | Out-File -FilePath $summaryFile -Append
"" | Out-File -FilePath $summaryFile -Append
"File List:" | Out-File -FilePath $summaryFile -Append
$dataFiles | ForEach-Object { "- $($_.Name)" } | Out-File -FilePath $summaryFile -Append

Write-Log "Summary report saved to: $summaryFile" "Green"

# Send notification
if ($sendNotification) {
    try {
        if (Test-Path ".\new_notification.ps1") {
            # Prepare notification message
            $notificationMessage = "📊 <b>Daily Data Collection Complete (Google Finance)</b>
            
Collection Time: $(Get-Date)
Collected Symbols: $($symbols -join ', ')
Collection Results: Success $successCount, Failed $failureCount
Data Files: $($dataFiles.Count) files

$( if ($failureCount -gt 0) { "⚠️ <b>Warning</b>: Some data collection failed, please check the logs." } else { "✅ <b>All data collection successful</b>" } )"

            # Send notification
            & .\new_notification.ps1 -message $notificationMessage -subject "Google Finance Data Collection Complete" -channel "Telegram"
            Write-Log "Collection results notification sent" "Green"
        }
        else {
            Write-Log "Notification module not found, cannot send result notification" "Yellow"
        }
    }
    catch {
        Write-Log "Failed to send notification: $_" "Red"
    }
} 