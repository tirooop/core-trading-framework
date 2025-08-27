# 路径: core/notification/ai_conditional_notifier.ps1

param(
    [Parameter(Mandatory=$true)]
    [string]$condition,  # signal, threshold, volatility, event
    
    [Parameter(Mandatory=$false)]
    [string]$symbol = "",
    
    [Parameter(Mandatory=$false)]
    [string]$value = "",
    
    [Parameter(Mandatory=$false)]
    [string]$configPath = "config/notification_config.json",
    
    [Parameter(Mandatory=$false)]
    [switch]$onlyOutsideMarketHours = $false
)

# 引入通知中心
$notificationCenterPath = Join-Path $PSScriptRoot "notification_center.ps1"
if (-not (Test-Path $notificationCenterPath)) {
    Write-Error "无法找到通知中心: $notificationCenterPath"
    exit 1
}

# 检查是否在交易时段
function Is-TradingHours {
    $now = Get-Date
    $dayOfWeek = $now.DayOfWeek
    
    # 周末不是交易日
    if ($dayOfWeek -eq "Saturday" -or $dayOfWeek -eq "Sunday") {
        return $false
    }
    
    # 美国东部时间转换
    $estOffset = -5  # 可能需要调整夏令时
    $estNow = $now.AddHours($estOffset - (Get-Date).Hour)
    $estTime = $estNow.TimeOfDay
    
    # 交易时段：9:30 AM - 4:00 PM EST
    $marketOpen = New-TimeSpan -Hours 9 -Minutes 30
    $marketClose = New-TimeSpan -Hours 16 -Minutes 0
    
    return ($estTime -ge $marketOpen -and $estTime -le $marketClose)
}

# 加载分析数据以验证条件
function Validate-Condition {
    param(
        [string]$condition,
        [string]$symbol,
        [string]$value
    )
    
    # 根据不同条件类型处理
    switch ($condition) {
        "signal" {
            # 验证是否有新的交易信号
            $signalsDir = "data/signals"
            if (-not (Test-Path $signalsDir)) {
                $signalsDir = "ai/signals"
            }
            
            # 检查最近30分钟内的信号
            $recentTime = (Get-Date).AddMinutes(-30)
            $files = Get-ChildItem -Path $signalsDir -Filter "*$symbol*.json" | Where-Object { $_.LastWriteTime -gt $recentTime }
            
            if ($files.Count -gt 0) {
                # 读取信号内容以获取方向
                $signalData = Get-Content $files[0].FullName | ConvertFrom-Json
                $direction = if ($signalData.action -eq "BUY") { "看涨" } else { "看跌" }
                $confidence = [math]::Round($signalData.confidence * 100)
                
                return @{
                    valid = $true
                    message = "检测到$($symbol)的$direction信号，置信度：$confidence%"
                    priority = "High"
                }
            } else {
                return @{ valid = $false }
            }
        }
        "threshold" {
            # 验证指定值是否超过阈值
            if ($symbol -and $value) {
                # 分割值和阈值
                $parts = $value -split ":"
                if ($parts.Count -ge 2) {
                    $actualValue = [double]$parts[0]
                    $threshold = [double]$parts[1]
                    
                    if ($actualValue -gt $threshold) {
                        return @{
                            valid = $true
                            message = "$symbol 超过预设阈值：$actualValue > $threshold"
                            priority = "Medium"
                        }
                    }
                }
            }
            return @{ valid = $false }
        }
        "volatility" {
            # 验证波动率是否异常
            if ($symbol -and $value -match "^[\d\.]+$") {
                $volatility = [double]$value
                if ($volatility -gt 3.0) {  # 波动率大于3%视为高波动
                    return @{
                        valid = $true
                        message = "⚠️ $symbol 市场波动率异常：$([math]::Round($volatility, 2))%"
                        priority = "High"
                    }
                }
            }
            return @{ valid = $false }
        }
        "event" {
            # 处理特定事件
            if (-not [string]::IsNullOrEmpty($value)) {
                return @{
                    valid = $true
                    message = $value
                    priority = "Medium"
                }
            }
            return @{ valid = $false }
        }
        default {
            return @{ valid = $false }
        }
    }
}

# 主执行逻辑
# 检查是否应该发送通知
if ($onlyOutsideMarketHours -and (Is-TradingHours)) {
    Write-Host "仅在非交易时段发送通知" -ForegroundColor Yellow
    exit 0
}

# 验证条件
$conditionResult = Validate-Condition -condition $condition -symbol $symbol -value $value

if ($conditionResult.valid) {
    # 确定频道
    $priority = $conditionResult.priority
    
    # 发送通知
    & $notificationCenterPath -message $conditionResult.message -subject "AI交易系统通知 - $condition" -channel "All" -enableHtml
    
    Write-Host "条件触发通知已发送" -ForegroundColor Green
} else {
    Write-Host "条件未满足，不发送通知" -ForegroundColor Yellow
} 