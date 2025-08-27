# Automatically monitor Google Finance data connection
$ErrorActionPreference = "Stop"
$logFile = "logs/google_finance_monitor_$(Get-Date -Format 'yyyyMMdd').log"

function Write-Log {
    param($message, $color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $message" -ForegroundColor $color
    "[$timestamp] $message" | Out-File -Append -FilePath $logFile
}

function Test-GoogleFinanceConnection {
    try {
        $result = python -c "from googlefinance import getQuotes; quotes = getQuotes('SPY'); print('OK' if quotes else 'FAIL')"
        if ($result.Trim() -eq "OK") {
            return $true
        }

        # If Google Finance API fails, try using a backup data source
        $result = python -c "import yfinance as yf; data = yf.download('SPY', period='1d', progress=False); print('OK' if not data.empty else 'FAIL')"
        return $result.Trim() -eq "OK"
    }
    catch {
        # Check if this is an import error
        if ($_.Exception.Message -like "*ImportError*" -or $_.Exception.Message -like "*ModuleNotFoundError*") {
            Write-Log "Missing necessary Python packages, trying to install..." "Yellow"
            try {
                pip install yfinance pandas requests
                Start-Sleep -Seconds 2
                # Try again
                $result = python -c "import yfinance as yf; data = yf.download('SPY', period='1d', progress=False); print('OK' if not data.empty else 'FAIL')"
                return $result.Trim() -eq "OK"
            }
            catch {
                return $false
            }
        }
        return $false
    }
}

function Send-Notification {
    param($message)
    try {
        if (Test-Path ".\new_notification.ps1") {
            # Use unified notification module
            & .\new_notification.ps1 -message $message -channel "All" -subject "Google Finance Connection Alert"
        } else {
            Write-Log "Cannot send notification: new_notification.ps1 script does not exist" "Yellow"
        }
    } catch {
        Write-Log "Failed to send notification: $_" "Red"
    }
}

if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }
Write-Log "Google Finance data connection monitoring started..." "Cyan"

$failCount = 0
$maxFailBeforeNotify = 3
$notificationSent = $false

while ($true) {
    $isConnected = Test-GoogleFinanceConnection
    
    if ($isConnected) {
        Write-Log "Google Finance data connection is normal" "Green"
        $failCount = 0
        $notificationSent = $false
    }
    else {
        $failCount++
        Write-Log "Google Finance data connection failed (failure count: $failCount)" "Yellow"
        
        if ($failCount -ge $maxFailBeforeNotify -and -not $notificationSent) {
            $message = "WARNING: Google Finance data connection has failed $failCount times consecutively. This might be due to network issues or API limitations. The system will try to use backup data sources."
            Send-Notification $message
            $notificationSent = $true
            
            # Check Internet connection
            $hasInternet = Test-Connection -ComputerName 8.8.8.8 -Count 2 -Quiet
            if (-not $hasInternet) {
                Write-Log "Network connection issue detected" "Red"
                $message = "CRITICAL WARNING: Cannot connect to the internet. This may affect all data sources. Please check your network connection."
                Send-Notification $message
            }
        }
    }
    
    # Check every 5 minutes
    Start-Sleep -Seconds 300
} 