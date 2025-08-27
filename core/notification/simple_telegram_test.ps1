# Simple Telegram Test Script

# Telegram configuration
$botToken = "7840040841:AAG5Yj8-wgOU4eICkA5ba0e17EIzyPWP088"
$chatId = "6145125455"

Write-Host "Starting to send Telegram test message..." -ForegroundColor Cyan

# Prepare message
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$message = "This is a test message, sent at: $timestamp"

# Send message
$uri = "https://api.telegram.org/bot$botToken/sendMessage"
$body = @{
    chat_id = $chatId
    text = $message
}

try {
    $response = Invoke-RestMethod -Uri $uri -Method Post -Body $body
    
    if ($response.ok) {
        Write-Host "Message sent successfully!" -ForegroundColor Green
    } else {
        Write-Host "Message sending failed: $($response.description)" -ForegroundColor Red
    }
} catch {
    Write-Host "Sending failed: $_" -ForegroundColor Red
} 