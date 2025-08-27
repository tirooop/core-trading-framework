# Notification Launcher
# Unified script to launch all notification services

param (
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "test", "status", "send", "analyze")]
    [string]$Action = "status",
    
    [Parameter(Mandatory=$false)]
    [string]$Message,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("info", "warning", "error", "success")]
    [string]$MessageType = "info",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("regular", "open", "close")]
    [string]$AnalysisType = "regular"
)

# Paths to different notification components
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

$Components = @{
    TelegramProvider = Join-Path -Path $ScriptDir -ChildPath "telegram_provider.ps1"
    TelegramMarketAnalysis = Join-Path -Path $ScriptDir -ChildPath "telegram_market_analysis.ps1"
    TelegramNotifierController = Join-Path -Path $ScriptDir -ChildPath "telegram_notifier_controller.ps1"
}

# Execute command based on action
switch ($Action) {
    "start" {
        Write-Host "Starting notification services..." -ForegroundColor Cyan
        & $Components.TelegramNotifierController -Action start
    }
    "test" {
        Write-Host "Running notification tests..." -ForegroundColor Cyan
        
        # First test the basic Telegram provider
        Write-Host "`nTesting Telegram Provider..."
        & $Components.TelegramProvider -message "Test message from notification launcher"
        
        # Then test market analysis
        Write-Host "`nTesting Market Analysis for $AnalysisType event..."
        & $Components.TelegramMarketAnalysis -Action test -MarketEvent $AnalysisType
    }
    "status" {
        Write-Host "Checking notification system status..." -ForegroundColor Cyan
        & $Components.TelegramNotifierController -Action status
    }
    "send" {
        if ([string]::IsNullOrEmpty($Message)) {
            Write-Host "Error: No message specified. Use -Message parameter." -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Sending message: $Message" -ForegroundColor Cyan
        & $Components.TelegramProvider -message $Message
    }
    "analyze" {
        Write-Host "Running market analysis for $AnalysisType event..." -ForegroundColor Cyan
        & $Components.TelegramMarketAnalysis -Action run -MarketEvent $AnalysisType
    }
    default {
        Write-Host "Unknown action: $Action" -ForegroundColor Red
        Write-Host "Valid actions: start, test, status, send, analyze" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "`nNotification launcher completed action: $Action" -ForegroundColor Green 