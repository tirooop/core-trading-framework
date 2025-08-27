# Automatically analyze logs and generate reports
param (
    [string]$logDir = "logs",
    [string]$outputDir = "reports",
    [switch]$sendNotification = $false
)

# Ensure output directory exists
if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }

$today = Get-Date -Format "yyyyMMdd"
$reportFile = "$outputDir/Log_Analysis_$today.html"

# Get recent log files
$logFiles = Get-ChildItem -Path $logDir -Filter "google_finance_*.log" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 10

# Analyze connection status
$totalChecks = 0
$failedChecks = 0
$errors = @()

foreach ($file in $logFiles) {
    $content = Get-Content $file.FullName
    
    # Count connection checks
    $checkCount = ($content | Select-String "connection" -SimpleMatch).Count
    $totalChecks += $checkCount
    
    # Identify failures
    $failCount = ($content | Select-String "fail|error|Error" -SimpleMatch).Count
    $failedChecks += $failCount
    
    # Collect error messages
    $errorLines = $content | Select-String "fail|error|Error" -SimpleMatch
    foreach ($line in $errorLines) {
        $errors += $line.Line
    }
}

# Calculate connection stability
$stability = if ($totalChecks -gt 0) { 
    [math]::Round(100 - ($failedChecks / $totalChecks * 100), 2)
} else { 
    100 
}

# Get CSS class name
$stabilityClass = if ($stability -ge 95) { 'success' } else { 'error' }

# Generate HTML report
$htmlReport = @"
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Google Finance Monitoring Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #4CAF50; color: white; padding: 10px; }
        .section { margin-top: 20px; }
        .error { color: red; }
        .success { color: green; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; }
        th { background-color: #f2f2f2; }
        .meter { height: 20px; background-color: #f3f3f3; border-radius: 3px; margin-top: 5px; }
        .progress { height: 100%; background-color: #4CAF50; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Google Finance Monitoring Report</h1>
        <p>Generated: $(Get-Date)</p>
    </div>
    
    <div class="section">
        <h2>Connection Stability Analysis</h2>
        <p>Total Checks: $totalChecks, Failures: $failedChecks</p>
        <p>System Stability: <span class="$stabilityClass">$stability%</span></p>
        <div class="meter">
            <div class="progress" style="width: $stability%;"></div>
        </div>
    </div>
    
    <div class="section">
        <h2>Recent Error Records</h2>
        <table>
            <tr><th>Error Message</th></tr>
            $(if ($errors.Count -eq 0) { "<tr><td>No errors recorded</td></tr>" } else {
                $errors | Select-Object -First 10 | ForEach-Object { "<tr><td>$_</td></tr>" } | Out-String
            })
        </table>
    </div>
    
    <div class="section">
        <h2>Recommended Actions</h2>
        $(if ($stability -lt 90) {
            "<p class='error'>System stability is below 90%, please check the following:</p>
            <ul>
                <li>Check your network connection</li>
                <li>Verify Google Finance API status</li>
                <li>Ensure API configuration parameters are valid</li>
                <li>Check if backup data sources are working properly</li>
            </ul>"
        } else {
            "<p class='success'>System is running normally.</p>"
        })
    </div>
</body>
</html>
"@

$htmlReport | Out-File -FilePath $reportFile

# Send notifications if requested
if ($sendNotification) {
    try {
        # Use the unified notification module to send email notification
        if (Test-Path ".\new_notification.ps1") {
            # Prepare summary information
            $summaryText = if ($stability -lt 90) {
                "⚠️ <b>Warning</b>: System stability is below 90% ($stability%), please check the system."
            } else {
                "✅ <b>System Normal</b>: Stability $stability%, everything is running fine."
            }
            
            # Use Email channel to send the full HTML report
            & .\new_notification.ps1 -message $htmlReport -channel "Email" -subject "Google Finance System Daily Report - $today"
            
            # Use Telegram to send a brief summary
            & .\new_notification.ps1 -message $summaryText -channel "Telegram" -subject "Google Finance System Status"
            
            Write-Host "Analysis report sent via unified notification module" -ForegroundColor Green
        } else {
            Write-Host "Unified notification module not found, cannot send notification" -ForegroundColor Yellow
            Write-Host "Please confirm new_notification.ps1 script exists" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "Notification sending failed: $_" -ForegroundColor Red
    }
}

Write-Host "Analysis report generated: $reportFile" -ForegroundColor Cyan 