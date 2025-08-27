# Unified Notification Module - Supporting Multiple Notification Channels
# Save as: notification.ps1

param(
    [Parameter(Mandatory=$true)]
    [string]$message,
    
    [ValidateSet("Telegram", "Email", "All")]
    [string]$channel = "All",
    
    [string]$subject = "系统通知",
    
    [string]$configPath = "config/notification_config.json"
)

# Set error handling
$ErrorActionPreference = "Stop"

# Function: Write log
function Write-Log {
    param($message, $color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $message" -ForegroundColor $color
}

# Function: Load configuration file
function Load-Config {
    param([string]$configPath)
    
    if (Test-Path $configPath) {
        try {
            $config = Get-Content $configPath | ConvertFrom-Json
            Write-Log "Configuration file loaded: $configPath" "Green"
            return $config
        }
        catch {
            Write-Log "Configuration file format error: $_" "Red"
            return $null
        }
    }
    else {
        Write-Log "Configuration file not found: $configPath, creating default config..." "Yellow"
        
        # Create default configuration
        $config = @{
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
        }
        
        # Save default configuration
        if (-not (Test-Path (Split-Path $configPath))) {
            New-Item -ItemType Directory -Path (Split-Path $configPath) -Force | Out-Null
        }
        $config | ConvertTo-Json | Out-File -FilePath $configPath
        
        Write-Log "Default configuration file created, please edit to enter your credentials" "Yellow"
        return $config
    }
}

# Function: Send Telegram message
function Send-TelegramMessage {
    param(
        [string]$message,
        [string]$token,
        [string]$chatId
    )
    
    $uri = "https://api.telegram.org/bot$token/sendMessage"
    $body = @{
        chat_id = $chatId
        text = $message
        parse_mode = "HTML"
    }
    
    try {
        $response = Invoke-RestMethod -Uri $uri -Method Post -Body $body
        return $response.ok
    }
    catch {
        Write-Log "发送Telegram消息失败: $_" "Red"
        return $false
    }
}

# Function: Send email
function Send-EmailMessage {
    param(
        [string]$from,
        [string]$to,
        [string]$subject,
        [string]$body,
        [string]$username,
        [string]$password,
        [string]$smtpServer,
        [int]$port,
        [bool]$useSsl,
        [bool]$enableHtml = $true
    )
    
    try {
        # Create credentials object
        $securePassword = ConvertTo-SecureString $password -AsPlainText -Force
        $credential = New-Object System.Management.Automation.PSCredential($username, $securePassword)
        
        # Send email
        Send-MailMessage -From $from -To $to `
            -Subject $subject -Body $body -BodyAsHtml:$enableHtml `
            -SmtpServer $smtpServer -Port $port -UseSsl:$useSsl -Credential $credential
            
        return $true
    }
    catch {
        Write-Log "Failed to send email: $_" "Red"
        return $false
    }
}

# Main code
# Load configuration
$config = Load-Config -configPath $configPath

if ($null -eq $config) {
    Write-Log "Unable to load configuration, exiting" "Red"
    exit 1
}

# Format message
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$formattedMessage = "<b>$subject</b>`n`n<i>[$timestamp]</i>`n`n$message"

# Send message based on notification channel
$results = @{}

# Telegram notification
if ($channel -eq "All" -or $channel -eq "Telegram") {
    if ($config.telegram.enabled -ne $false) {
        $token = $config.telegram.botToken
        $chatId = $config.telegram.chatId
        
        if (-not [string]::IsNullOrEmpty($token) -and -not [string]::IsNullOrEmpty($chatId)) {
            $result = Send-TelegramMessage -message $formattedMessage -token $token -chatId $chatId
            
            $results["Telegram"] = $result
            
            if ($result) {
                Write-Log "Telegram消息发送成功" "Green"
            } else {
                Write-Log "Telegram消息发送失败" "Red"
            }
        }
        else {
            Write-Log "Telegram配置不完整，已跳过" "Yellow"
            $results["Telegram"] = $false
        }
    }
    else {
        Write-Log "Telegram通知已禁用" "Yellow"
        $results["Telegram"] = $false
    }
}

# Email notification
if ($channel -eq "All" -or $channel -eq "Email") {
    if ($config.email.enabled -ne $false) {
        $emailConfig = $config.email
        
        if (-not [string]::IsNullOrEmpty($emailConfig.from) -and
            -not [string]::IsNullOrEmpty($emailConfig.to) -and
            -not [string]::IsNullOrEmpty($emailConfig.password)) {
            
            $emailBody = if ($enableHtml) {
                "<h2>Trading System Notification</h2><p><i>$timestamp</i></p><p>$message</p>"
            } else {
                "Trading System Notification`n$timestamp`n`n$message"
            }
            
            $result = Send-EmailMessage `
                -from $emailConfig.from `
                -to $emailConfig.to `
                -subject $subject `
                -body $emailBody `
                -username $emailConfig.username `
                -password $emailConfig.password `
                -smtpServer $emailConfig.smtpServer `
                -port $emailConfig.port `
                -useSsl $emailConfig.useSsl `
                -enableHtml $enableHtml
                
            $results["Email"] = $result
            
            if ($result) {
                Write-Log "Email sent successfully" "Green"
            }
            else {
                Write-Log "Email sending failed" "Red"
            }
        }
        else {
            Write-Log "Incomplete email configuration, skipped" "Yellow"
            $results["Email"] = $false
        }
    }
    else {
        Write-Log "Email notifications disabled" "Yellow"
        $results["Email"] = $false
    }
}

# Return results summary
if ($results.Values -contains $true) {
    Write-Log "Notifications sent, at least one channel succeeded" "Green"
    return $true
}
else {
    Write-Log "All notification channels failed" "Red"
    return $false
} 