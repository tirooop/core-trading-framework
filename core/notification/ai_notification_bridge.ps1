# 路径: core/notification/ai_notification_bridge.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$analysisType = "market",  # market, strategy, performance
    
    [Parameter(Mandatory=$false)]
    [string]$dataPath = $null,         # 指定分析数据路径
    
    [Parameter(Mandatory=$false)]
    [string]$configPath = "config/notification_config.json",
    
    [Parameter(Mandatory=$false)]
    [string]$priority = "Medium"       # Low, Medium, High, Critical
)

# 引入通知中心
$notificationCenterPath = Join-Path $PSScriptRoot "notification_center.ps1"
if (-not (Test-Path $notificationCenterPath)) {
    Write-Error "无法找到通知中心: $notificationCenterPath"
    exit 1
}

# 加载最新AI分析数据
function Load-LatestAnalysisData {
    param(
        [string]$analysisType,
        [string]$customPath = $null
    )
    
    if ($customPath -and (Test-Path $customPath)) {
        return Get-Content $customPath -Raw
    }
    
    # 默认路径
    $insightsDir = "data/insights"
    if (-not (Test-Path $insightsDir)) {
        $insightsDir = "ai/insights"
    }
    
    # 查找最新文件
    $searchPattern = switch ($analysisType) {
        "market" { "ai_market_analysis_*.txt" }
        "strategy" { "ai_recommendations_*.json" }
        "performance" { "ai_analysis_*.txt" }
        default { "ai_*_*.txt" }
    }
    
    $files = Get-ChildItem -Path $insightsDir -Filter $searchPattern | Sort-Object LastWriteTime -Descending
    if ($files.Count -eq 0) {
        return $null
    }
    
    return Get-Content $files[0].FullName -Raw
}

# 格式化通知内容
function Format-AnalysisNotification {
    param(
        [string]$content,
        [string]$analysisType
    )
    
    if (-not $content) {
        return "没有找到AI分析数据"
    }
    
    $title = switch ($analysisType) {
        "market" { "AI市场分析报告" }
        "strategy" { "AI策略优化建议" }
        "performance" { "AI交易绩效分析" }
        default { "AI分析报告" }
    }
    
    # 提取关键信息（限制大小）
    $maxLength = 1000
    if ($content.Length -gt $maxLength) {
        $content = $content.Substring(0, $maxLength) + "...(更多内容请查看完整报告)"
    }
    
    # 添加时间戳
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    return "$title`n时间: $timestamp`n`n$content"
}

# 确定通知渠道
function Get-NotificationChannels {
    param(
        [string]$priority,
        [string]$configPath
    )
    
    # 加载配置
    $config = Get-Content $configPath | ConvertFrom-Json
    
    # 默认渠道
    $defaultChannels = @("Telegram", "Email")
    
    if ($config.notification_preferences) {
        # 按优先级选择通知渠道
        $channelsByPriority = switch ($priority.ToLower()) {
            "low" { $config.notification_preferences.daily_reports }
            "medium" { $config.notification_preferences.trading_signals }
            "high" { $config.notification_preferences.system_alerts }
            "critical" { $config.notification_preferences.error_alerts }
            default { $defaultChannels }
        }
        
        if ($channelsByPriority) {
            return $channelsByPriority -join ","
        }
    }
    
    # 默认返回
    return "All"
}

# 主执行逻辑
try {
    # 加载分析数据
    $analysisData = Load-LatestAnalysisData -analysisType $analysisType -customPath $dataPath
    
    if ($analysisData) {
        # 格式化内容
        $notificationContent = Format-AnalysisNotification -content $analysisData -analysisType $analysisType
        
        # 确定通知渠道
        $channels = Get-NotificationChannels -priority $priority -configPath $configPath
        
        # 发送通知
        $subject = "AI分析报告 - $analysisType"
        & $notificationCenterPath -message $notificationContent -subject $subject -channel $channels -enableHtml
        
        Write-Host "AI分析通知已发送" -ForegroundColor Green
    } else {
        Write-Host "未找到分析数据，跳过通知" -ForegroundColor Yellow
    }
} catch {
    Write-Error "发送AI分析通知失败: $_"
    exit 1
} 