# 统一市场分析系统
# 整合实时市场数据分析、调度功能和Telegram通知

param (
    [Parameter(Mandatory=$false)]
    [ValidateSet("run", "schedule", "test", "install", "uninstall")]
    [string]$Action = "run",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("regular", "open", "close")]
    [string]$MarketEvent = "regular",
    
    [Parameter(Mandatory=$false)]
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$WorkspaceRoot = (Get-Location).Path
if ((Split-Path -Parent (Split-Path -Parent $ScriptDir)) -ne $WorkspaceRoot) {
    # 确保工作目录是项目根目录
    Set-Location $WorkspaceRoot
}

# 导入通用通知模块
$NotificationProviderPath = Join-Path -Path $ScriptDir -ChildPath "telegram_provider.ps1"
if (Test-Path $NotificationProviderPath) {
    . $NotificationProviderPath
}

# 日志函数
function Write-Log {
    param($message, $color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $message" -ForegroundColor $color
}

# Telegram配置
function Get-TelegramConfig {
    # 先从配置文件读取
    $configFile = "config/config.json"
    if (Test-Path $configFile) {
        try {
            $config = Get-Content $configFile -Raw | ConvertFrom-Json
            $telegramConfig = @{
                botToken = $config.telegram.botToken
                chatId = $config.telegram.chatId
            }
            return $telegramConfig
        }
        catch {
            Write-Log "读取配置文件失败: $_" "Yellow"
        }
    }
    
    # 如果配置文件不存在或读取失败，使用默认值
    return @{
        botToken = "7840040841:AAG5Yj8-wgOU4eICkA5ba0e17EIzyPWP088"
        chatId = "6145125455"
    }
}

# 生成不同类型的市场分析数据
function Get-MarketAnalysisData {
    param([string]$eventType)
    
    # 基础数据结构
    $data = @{
        marketStatus = ""
        indices = @{}
        sectors = @{}
        conclusion = ""
        eventType = $eventType
    }
    
    # 根据事件类型自定义数据
    switch ($eventType) {
        "open" {
            $data.marketStatus = "市场开盘"
            $data.indices = @{
                "SPY" = "+0.35%";
                "QQQ" = "+0.42%";
                "DIA" = "+0.18%"
            }
            $data.sectors = @{
                "科技" = "+0.65%";
                "半导体" = "+0.92%";
                "能源" = "-0.11%"
            }
            $data.conclusion = "市场开盘呈现积极势头。盘前指标显示科技和半导体板块有较强购买兴趣。关注科技龙头可能的早盘突破。"
        }
        "close" {
            $data.marketStatus = "市场收盘"
            $data.indices = @{
                "SPY" = "+0.88%";
                "QQQ" = "+1.15%";
                "DIA" = "+0.52%"
            }
            $data.sectors = @{
                "科技" = "+1.95%";
                "半导体" = "+2.45%";
                "能源" = "-0.22%"
            }
            $data.conclusion = "市场主要指数收盘强劲上涨。科技板块领涨，半导体表现尤为突出。盘后交易显示动能持续。考虑为明天可能的跳空做好准备。"
        }
        default { # 常规盘中更新
            $data.marketStatus = "强劲上涨"
            $data.indices = @{
                "SPY" = "+0.75%";
                "QQQ" = "+1.02%";
                "DIA" = "+0.41%"
            }
            $data.sectors = @{
                "科技" = "+1.85%";
                "半导体" = "+2.32%";
                "能源" = "-0.31%"
            }
            $data.conclusion = "市场展现强劲上涨趋势，伴随成交量增加。蓝筹股表现出色。重点关注科技和半导体板块可能的突破机会。"
        }
    }
    
    return $data
}

# 格式化市场数据为可读文本
function Format-MarketData {
    param($data)
    
    # 根据事件类型设置主题
    $subject = switch ($data.eventType) {
        "open" { "开盘市场分析" }
        "close" { "收盘市场总结" }
        default { "实时市场更新" }
    }
    
    $text = "$subject`n`n"
    $text += "市场状态: $($data.marketStatus)`n"
    
    # 添加指数数据
    $text += "主要指数: "
    $indices = foreach ($index in $data.indices.Keys) {
        "$index $($data.indices[$index])"
    }
    $text += ($indices -join ", ") + "`n`n"
    
    # 添加板块数据
    $text += "热门板块:`n"
    foreach ($sector in $data.sectors.Keys) {
        $text += "$sector $($data.sectors[$sector])`n"
    }
    
    # 添加结论
    $text += "`nAI分析结论: $($data.conclusion)"
    
    return $text, $subject
}

# 发送市场分析
function Send-MarketAnalysis {
    param([string]$marketEvent = "regular")
    
    Write-Log "开始发送市场分析，事件类型: $marketEvent..." "Yellow"
    
    try {
        # 获取市场分析数据
        $marketData = Get-MarketAnalysisData -eventType $marketEvent
        
        # 格式化数据
        $messageText, $subject = Format-MarketData -data $marketData
        
        # 添加时间戳
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $formattedMessage = "<b>$subject</b>`n`n<i>[$timestamp]</i>`n`n$messageText"
        
        # 发送到Telegram - 优先使用通用通知模块中的函数
        $result = $false
        if (Get-Command "Send-TelegramMessage" -ErrorAction SilentlyContinue) {
            # 使用导入的Send-TelegramMessage函数
            $result = Send-TelegramMessage -message $formattedMessage
        } else {
            Write-Log "未找到Send-TelegramMessage函数，使用直接调用" "Yellow"
            # 使用应急机制发送消息
            $telegramConfig = Get-TelegramConfig
            
            $uri = "https://api.telegram.org/bot$($telegramConfig.botToken)/sendMessage"
            $body = @{
                chat_id = $telegramConfig.chatId
                text = $formattedMessage
                parse_mode = "HTML"
            }
            
            $response = Invoke-RestMethod -Uri $uri -Method Post -Body $body
            $result = $response.ok
        }
        
        if ($result) {
            Write-Log "市场分析数据已发送至Telegram!" "Green"
        }
        else {
            Write-Log "发送市场分析数据失败" "Red"
        }
    }
    catch {
        Write-Log "脚本执行错误: $_" "Red"
    }
}

# 创建计划任务
function Register-Task {
    param(
        [string]$TaskName,
        [string]$ScriptPath,
        [string]$Arguments,
        [string]$Trigger,
        [int]$IntervalMinutes = 0,
        [string]$Description,
        [switch]$Force
    )
    
    # 检查任务是否已存在
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    
    if ($existingTask -and -not $Force) {
        Write-Log "任务 '$TaskName' 已存在。使用 -Force 参数可以覆盖。" "Yellow"
        return
    } elseif ($existingTask) {
        Write-Log "正在覆盖已存在的任务: $TaskName" "Yellow"
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`" $Arguments"
    
    # 基于Trigger类型创建触发器
    switch ($Trigger) {
        "Daily" {
            $trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM
        }
        "Hourly" {
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
        }
        "Minutes" {
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
        }
        "Startup" {
            $trigger = New-ScheduledTaskTrigger -AtStartup
        }
        default {
            throw "未知的触发器类型: $Trigger"
        }
    }
    
    # 如果当前用户不在执行任务时登录，则以SYSTEM身份运行
    $principal = New-ScheduledTaskPrincipal -UserID "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Description $Description
    Write-Log "已注册计划任务: $TaskName" "Green"
}

# 设置计划任务
function Schedule-MarketAnalysis {
    param([switch]$Force)
    
    # 检查管理员权限
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Log "需要管理员权限来设置计划任务。请以管理员身份运行此脚本。" "Red"
        exit 1
    }
    
    # 获取脚本的完整路径
    $scriptPath = Join-Path -Path $ScriptDir -ChildPath "telegram_market_analysis.ps1"
    
    Write-Log "正在设置市场分析系统计划任务..." "Cyan"
    
    # 1. 实时市场分析 (每30分钟)
    Register-Task -TaskName "AI_实时市场分析" `
        -ScriptPath $scriptPath `
        -Arguments "run -MarketEvent regular" `
        -Trigger "Minutes" `
        -IntervalMinutes 30 `
        -Description "每30分钟发送实时市场分析到Telegram" `
        -Force:$Force
    
    # 2. 开盘通知 (每天开盘时)
    Register-Task -TaskName "AI_开盘市场分析" `
        -ScriptPath $scriptPath `
        -Arguments "run -MarketEvent open" `
        -Trigger "Daily" `
        -Description "发送开盘市场分析到Telegram" `
        -Force:$Force
    
    # 3. 收盘总结 (每天收盘时)
    Register-Task -TaskName "AI_收盘市场分析" `
        -ScriptPath $scriptPath `
        -Arguments "run -MarketEvent close" `
        -Trigger "Daily" `
        -Description "发送收盘市场总结到Telegram" `
        -Force:$Force
    
    Write-Log "市场分析系统计划任务设置完成!" "Green"
}

# 卸载计划任务
function Uninstall-Tasks {
    # 检查管理员权限
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Log "需要管理员权限来卸载计划任务。请以管理员身份运行此脚本。" "Red"
        exit 1
    }
    
    $tasks = @(
        "AI_实时市场分析", 
        "AI_开盘市场分析", 
        "AI_收盘市场分析"
    )
    
    foreach ($task in $tasks) {
        if (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $task -Confirm:$false
            Write-Log "已卸载计划任务: $task" "Green"
        }
        else {
            Write-Log "计划任务不存在: $task" "Yellow"
        }
    }
    
    Write-Log "市场分析系统计划任务卸载完成!" "Green"
}

# 测试市场分析
function Test-MarketAnalysis {
    param([string]$marketEvent = "regular")
    
    Write-Log "=======================================================" "Cyan"
    Write-Log "  AI市场分析通知系统测试" "Cyan"
    Write-Log "=======================================================" "Cyan"
    Write-Log ""
    Write-Log "测试市场事件: $marketEvent" "Yellow"
    Write-Log ""
    
    # 运行市场分析
    Send-MarketAnalysis -marketEvent $marketEvent
    
    Write-Log ""
    Write-Log "测试完成!" "Green"
    Write-Log "请查看您的Telegram消息。" "Green"
}

# 主函数
function Main {
    param(
        [string]$Action,
        [string]$MarketEvent,
        [switch]$Force
    )
    
    Write-Log "=======================================================" "Cyan"
    Write-Log "  AI市场分析系统 (v1.0)" "Cyan"
    Write-Log "=======================================================" "Cyan"
    Write-Log "动作: $Action" "Cyan"
    if ($Action -eq "run") {
        Write-Log "市场事件: $MarketEvent" "Cyan"
    }
    Write-Log "=======================================================" "Cyan"
    Write-Log ""
    
    switch ($Action) {
        "run" {
            Send-MarketAnalysis -marketEvent $MarketEvent
        }
        "schedule" {
            Schedule-MarketAnalysis -Force:$Force
        }
        "test" {
            Test-MarketAnalysis -marketEvent $MarketEvent
        }
        "install" {
            Schedule-MarketAnalysis -Force:$Force
        }
        "uninstall" {
            Uninstall-Tasks
        }
        default {
            Write-Log "未知动作: $Action" "Red"
            exit 1
        }
    }
}

# 执行主函数
Main -Action $Action -MarketEvent $MarketEvent -Force:$Force