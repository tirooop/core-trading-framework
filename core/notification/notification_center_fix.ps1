# 简化版通知中心 - 专注于Telegram通知

param(
    [Parameter(Mandatory=$true)]
    [string]$message,
    
    [Parameter(Mandatory=$false)]
    [string]$subject = "AI交易系统通知",
    
    [Parameter(Mandatory=$false)]
    [string]$configPath = "config/notification_config.json"
)

# 设置错误处理
$ErrorActionPreference = "Stop"

# 日志函数
function Write-Log {
    param($message, $color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $message" -ForegroundColor $color
}

# 读取配置文件
function Get-Config {
    param($configPath)
    
    if (Test-Path $configPath) {
        try {
            $config = Get-Content $configPath | ConvertFrom-Json
            Write-Log "已加载配置文件: $configPath" "Green"
            return $config
        }
        catch {
            Write-Log "配置文件格式错误: $_" "Red"
            return $null
        }
    }
    else {
        Write-Log "找不到配置文件: $configPath" "Red"
        return $null
    }
}

# 发送Telegram消息
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
        Write-Log "开始发送Telegram消息..." "Cyan"
        $response = Invoke-RestMethod -Uri $uri -Method Post -Body $body
        if ($response.ok) {
            Write-Log "Telegram消息发送成功!" "Green"
            return $true
        }
        else {
            Write-Log "Telegram返回错误: $($response | ConvertTo-Json)" "Red"
            return $false
        }
    }
    catch {
        Write-Log "发送Telegram消息失败: $_" "Red"
        return $false
    }
}

# 主执行逻辑
try {
    # 加载配置
    $config = Get-Config -configPath $configPath
    if ($null -eq $config) {
        Write-Log "无法加载配置，退出" "Red"
        exit 1
    }
    
    # 检查Telegram配置
    if (-not $config.telegram.enabled) {
        Write-Log "Telegram通知已禁用，退出" "Yellow"
        exit 0
    }
    
    $token = $config.telegram.botToken
    $chatId = $config.telegram.chatId
    
    if ([string]::IsNullOrEmpty($token) -or [string]::IsNullOrEmpty($chatId)) {
        Write-Log "Telegram配置不完整，无法发送通知" "Red"
        exit 1
    }
    
    # 格式化消息
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $formattedMessage = "<b>$subject</b>`n`n<i>[$timestamp]</i>`n`n$message"
    
    # 发送消息
    $result = Send-TelegramMessage -message $formattedMessage -token $token -chatId $chatId
    
    if ($result) {
        Write-Log "通知发送成功!" "Green"
        exit 0
    }
    else {
        Write-Log "通知发送失败" "Red"
        exit 1
    }
}
catch {
    Write-Log "发送通知时出错: $_" "Red"
    exit 1
} 