# Telegram通知控制器
# 用于统一管理和调度所有Telegram通知相关功能

param (
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "stop", "status", "send", "analyze")]
    [string]$Action = "status",
    
    [Parameter(Mandatory=$false)]
    [string]$Message,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("info", "warning", "error", "success")]
    [string]$MessageType = "info",
    
    [Parameter(Mandatory=$false)]
    [string]$AnalysisType = "regular"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$WorkspaceRoot = (Get-Location).Path
if ((Split-Path -Parent (Split-Path -Parent $ScriptDir)) -ne $WorkspaceRoot) {
    # 确保工作目录是项目根目录
    Set-Location $WorkspaceRoot
}

# 导入必要的模块
$NotificationProviderPath = Join-Path -Path $ScriptDir -ChildPath "telegram_provider.ps1"
$MarketAnalysisPath = Join-Path -Path $ScriptDir -ChildPath "telegram_market_analysis.ps1"

if (Test-Path $NotificationProviderPath) {
    . $NotificationProviderPath
} else {
    Write-Error "找不到Telegram提供者模块: $NotificationProviderPath"
    exit 1
}

# 日志函数
function Write-Log {
    param($message, $color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $message" -ForegroundColor $color
}

# 根据消息类型格式化消息
function Format-Message {
    param($message, $type)
    
    $icon = switch ($type) {
        "info" { "ℹ️" }
        "warning" { "⚠️" }
        "error" { "❌" }
        "success" { "✅" }
        default { "📣" }
    }
    
    $formattedMessage = "$icon $message"
    return $formattedMessage
}

# 获取系统状态
function Get-NotificationStatus {
    $result = @{
        "timestamp" = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "system" = "Telegram通知系统"
        "status" = "运行中"
        "components" = @()
    }
    
    # 检查Telegram提供者
    try {
        $telegramConfig = Get-TelegramConfig
        if ($telegramConfig.botToken -and $telegramConfig.chatId) {
            $result.components += @{
                "name" = "Telegram提供者"
                "status" = "正常"
                "details" = "配置有效"
            }
        } else {
            $result.components += @{
                "name" = "Telegram提供者"
                "status" = "警告"
                "details" = "配置不完整"
            }
        }
    } catch {
        $result.components += @{
            "name" = "Telegram提供者"
            "status" = "错误"
            "details" = $_.Exception.Message
        }
    }
    
    # 检查市场分析脚本
    if (Test-Path $MarketAnalysisPath) {
        $result.components += @{
            "name" = "市场分析"
            "status" = "正常"
            "details" = "脚本可用"
        }
    } else {
        $result.components += @{
            "name" = "市场分析"
            "status" = "错误"
            "details" = "找不到市场分析脚本"
        }
    }
    
    # 检查计划任务
    try {
        $scheduledTasks = @(
            "AI_实时市场分析", 
            "AI_开盘市场分析", 
            "AI_收盘市场分析"
        )
        
        $taskStatus = @()
        foreach ($task in $scheduledTasks) {
            $taskInfo = Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
            if ($taskInfo) {
                $taskStatus += "$task (已安装)"
            } else {
                $taskStatus += "$task (未安装)"
            }
        }
        
        $result.components += @{
            "name" = "计划任务"
            "status" = "正常"
            "details" = $taskStatus -join ", "
        }
    } catch {
        $result.components += @{
            "name" = "计划任务"
            "status" = "错误"
            "details" = $_.Exception.Message
        }
    }
    
    return $result
}

# 发送消息
function Send-Message {
    param($message, $type)
    
    try {
        $formattedMessage = Format-Message -message $message -type $type
        $telegramConfig = Get-TelegramConfig
        
        $result = Send-TelegramMessage -message $formattedMessage -botToken $telegramConfig.botToken -chatId $telegramConfig.chatId
        
        if ($result) {
            Write-Log "消息发送成功!" "Green"
            return $true
        } else {
            Write-Log "消息发送失败" "Red"
            return $false
        }
    } catch {
        Write-Log "发送消息时出错: $_" "Red"
        return $false
    }
}

# 启动服务
function Start-NotificationService {
    Write-Log "启动Telegram通知服务..." "Cyan"
    
    # 检查配置
    try {
        $telegramConfig = Get-TelegramConfig
        if (-not $telegramConfig.botToken -or -not $telegramConfig.chatId) {
            Write-Log "Telegram配置不完整，请检查配置" "Yellow"
            return $false
        }
        
        # 发送测试消息
        $testResult = Send-Message -message "Telegram通知服务已启动" -type "info"
        
        if ($testResult) {
            Write-Log "Telegram通知服务启动成功!" "Green"
            return $true
        } else {
            Write-Log "Telegram通知服务启动失败" "Red"
            return $false
        }
    } catch {
        Write-Log "启动服务时出错: $_" "Red"
        return $false
    }
}

# 停止服务
function Stop-NotificationService {
    Write-Log "停止Telegram通知服务..." "Cyan"
    
    try {
        # 这里只是通知服务停止，因为没有长期运行的进程
        $stopResult = Send-Message -message "Telegram通知服务已停止" -type "warning"
        
        if ($stopResult) {
            Write-Log "Telegram通知服务停止成功!" "Green"
            return $true
        } else {
            Write-Log "Telegram通知服务停止通知失败" "Red"
            return $false
        }
    } catch {
        Write-Log "停止服务时出错: $_" "Red"
        return $false
    }
}

# 运行市场分析
function Start-MarketAnalysis {
    param($analysisType)
    
    Write-Log "启动市场分析，类型: $analysisType..." "Cyan"
    
    if (Test-Path $MarketAnalysisPath) {
        try {
            # 调用市场分析脚本
            & $MarketAnalysisPath -Action run -MarketEvent $analysisType
            return $true
        } catch {
            Write-Log "运行市场分析时出错: $_" "Red"
            return $false
        }
    } else {
        Write-Log "找不到市场分析脚本: $MarketAnalysisPath" "Red"
        return $false
    }
}

# 显示状态信息
function Show-StatusInfo {
    $status = Get-NotificationStatus
    
    Write-Log "=======================================================" "Cyan"
    Write-Log "  Telegram通知系统状态" "Cyan"
    Write-Log "=======================================================" "Cyan"
    Write-Log "时间: $($status.timestamp)" "Cyan"
    Write-Log "系统: $($status.system)" "Cyan"
    Write-Log "状态: $($status.status)" "Green"
    Write-Log ""
    
    Write-Log "组件状态:" "Yellow"
    foreach ($component in $status.components) {
        $statusColor = switch ($component.status) {
            "正常" { "Green" }
            "警告" { "Yellow" }
            "错误" { "Red" }
            default { "White" }
        }
        
        Write-Log "- $($component.name): $($component.status)" $statusColor
        Write-Log "  $($component.details)"
    }
    
    Write-Log ""
    Write-Log "=======================================================" "Cyan"
}

# 主程序
function Main {
    param(
        [string]$Action,
        [string]$Message,
        [string]$MessageType,
        [string]$AnalysisType
    )
    
    Write-Log "=======================================================" "Cyan"
    Write-Log "  Telegram通知控制器 v1.0" "Cyan"
    Write-Log "=======================================================" "Cyan"
    
    switch ($Action) {
        "start" {
            Start-NotificationService
        }
        "stop" {
            Stop-NotificationService
        }
        "status" {
            Show-StatusInfo
        }
        "send" {
            if (-not $Message) {
                Write-Log "错误: 发送消息时必须提供Message参数" "Red"
                exit 1
            }
            Send-Message -message $Message -type $MessageType
        }
        "analyze" {
            Start-MarketAnalysis -analysisType $AnalysisType
        }
        default {
            Write-Log "未知操作: $Action" "Red"
            Write-Log "支持的操作: start, stop, status, send, analyze" "Yellow"
            exit 1
        }
    }
}

# 执行主程序
Main -Action $Action -Message $Message -MessageType $MessageType -AnalysisType $AnalysisType 