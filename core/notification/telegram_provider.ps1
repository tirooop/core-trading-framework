# Telegram通知提供者模块
# 既可独立运行，也可作为导入模块使用

param(
    [Parameter(Mandatory=$false)]
    [string]$message,
    
    [Parameter(Mandatory=$false)]
    [string]$botToken = "",
    
    [Parameter(Mandatory=$false)]
    [string]$chatId = ""
)

# 获取Telegram配置
function Get-TelegramConfig {
    # 先检查是否已通过参数提供了token和chatId
    if (-not [string]::IsNullOrEmpty($script:botToken) -and -not [string]::IsNullOrEmpty($script:chatId)) {
        return @{
            botToken = $script:botToken
            chatId = $script:chatId
        }
    }
    
    # 尝试从配置文件加载
    $configFiles = @(
        "config/config.json",
        "config/telegram_config.json"
    )
    
    foreach ($configFile in $configFiles) {
        if (Test-Path $configFile) {
            try {
                $config = Get-Content $configFile -Raw | ConvertFrom-Json
                
                # 根据不同的配置文件结构获取配置
                if ($config.telegram -ne $null) {
                    # config.json中的telegram节点
                    return @{
                        botToken = $config.telegram.botToken
                        chatId = $config.telegram.chatId
                    }
                } 
                elseif ($config.botToken -ne $null -and $config.chatId -ne $null) {
                    # 直接包含botToken和chatId的配置
                    return @{
                        botToken = $config.botToken
                        chatId = $config.chatId
                    }
                }
            } catch {
                Write-Host "读取配置文件失败: $_" -ForegroundColor Yellow
            }
        }
    }
    
    # 如果所有配置文件都失败，使用默认配置
    return @{
        botToken = "7840040841:AAG5Yj8-wgOU4eICkA5ba0e17EIzyPWP088"
        chatId = "6145125455"
    }
}

# 发送Telegram消息
function Send-TelegramMessage {
    param(
        [Parameter(Mandatory=$true)]
        [string]$message,
        
        [Parameter(Mandatory=$false)]
        [string]$botToken = "",
        
        [Parameter(Mandatory=$false)]
        [string]$chatId = "",
        
        [Parameter(Mandatory=$false)]
        [string]$parseMode = "HTML"
    )
    
    # 如果未提供token或chatId，从配置获取
    if ([string]::IsNullOrEmpty($botToken) -or [string]::IsNullOrEmpty($chatId)) {
        $config = Get-TelegramConfig
        $botToken = $config.botToken
        $chatId = $config.chatId
    }
    
    $uri = "https://api.telegram.org/bot$botToken/sendMessage"
    $body = @{
        chat_id = $chatId
        text = $message
        parse_mode = $parseMode
    }
    
    try {
        $response = Invoke-RestMethod -Uri $uri -Method Post -Body $body
        return $response.ok
    }
    catch {
        Write-Host "发送Telegram消息失败: $_" -ForegroundColor Red
        return $false
    }
}

# 当作为独立脚本运行时，发送消息
if ($MyInvocation.InvocationName -ne '.') {
    # 如果提供了消息参数，则发送
    if (-not [string]::IsNullOrEmpty($message)) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $formattedMessage = "<b>🤖 交易系统通知</b>`n`n<i>[$timestamp]</i>`n`n$message"
        
        $config = Get-TelegramConfig
        if ([string]::IsNullOrEmpty($botToken)) { $botToken = $config.botToken }
        if ([string]::IsNullOrEmpty($chatId)) { $chatId = $config.chatId }
        
        $result = Send-TelegramMessage -message $formattedMessage -botToken $botToken -chatId $chatId
        
        if ($result) {
            Write-Host "消息已发送至Telegram" -ForegroundColor Green
            exit 0
        } else {
            Write-Host "消息发送失败" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "使用方法: .\telegram_provider.ps1 -message '要发送的消息'" -ForegroundColor Yellow
        exit 1
    }
} 