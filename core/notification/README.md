# AI市场分析通知系统

本系统提供实时市场分析和Telegram通知功能，旨在帮助交易者及时获取市场动态和AI分析结果。

## 功能特点

- **实时市场分析**: 定期提供市场状态更新和重要指数变动
- **开盘/收盘分析**: 在市场开盘和收盘时提供专门的分析报告
- **自动调度**: 通过Windows计划任务自动执行分析和通知
- **Telegram集成**: 将分析结果直接发送到您的Telegram
- **简单配置**: 易于设置和自定义

## 文件结构

- `telegram_market_analysis.ps1` - 主要脚本文件，整合了所有功能
- `telegram_provider.ps1` - Telegram通知提供者，负责发送消息

## 快速开始

1. 确保已设置Telegram Bot并获取token和chat_id
2. 运行测试命令验证配置是否正确:

```powershell
.\telegram_market_analysis.ps1 -Action test
```

3. 设置自动计划任务:

```powershell
# 以管理员身份运行
.\telegram_market_analysis.ps1 -Action install
```

## 使用方法

### 手动运行市场分析

```powershell
# 发送常规市场分析
.\telegram_market_analysis.ps1 -Action run -MarketEvent regular

# 发送开盘分析
.\telegram_market_analysis.ps1 -Action run -MarketEvent open

# 发送收盘总结
.\telegram_market_analysis.ps1 -Action run -MarketEvent close
```

### 管理计划任务

```powershell
# 安装计划任务
.\telegram_market_analysis.ps1 -Action install

# 卸载计划任务
.\telegram_market_analysis.ps1 -Action uninstall
```

## 配置说明

系统会按以下顺序查找Telegram配置:

1. 从项目根目录的`config/config.json`读取
2. 如果找不到配置文件，使用脚本中的默认值

配置文件示例:

```json
{
  "telegram": {
    "botToken": "YOUR_BOT_TOKEN",
    "chatId": "YOUR_CHAT_ID"
  }
}
```

## 计划任务

安装后会创建以下计划任务:

- **AI_实时市场分析** - 每30分钟运行一次常规市场分析
- **AI_开盘市场分析** - 每天早上9:00发送开盘分析
- **AI_收盘市场分析** - 每天发送收盘总结

## 故障排除

如果遇到问题:

1. 检查Telegram配置是否正确
2. 验证网络连接是否正常
3. 确认PowerShell执行策略允许运行脚本
4. 查看脚本输出的错误消息 