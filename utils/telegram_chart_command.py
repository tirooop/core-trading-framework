"""
Telegram chart command handler.
Processes /chart commands and generates technical chart images.
Uses PIL (Pillow) instead of imghdr for image processing.
"""

from telegram.ext import CommandHandler
from utils.chart_renderer import ChartRenderer
from utils.ai_chart_analyzer import AIChartAnalyzer
import os
from PIL import Image  # Using Pillow instead of imghdr

class TelegramChartCommands:
    def __init__(self, dispatcher=None):
        self.chart_renderer = ChartRenderer()
        self.chart_analyzer = AIChartAnalyzer()
        
        if dispatcher:
            self.register_handlers(dispatcher)
    
    def chart_command(self, update, context):
        """Handle /chart command - Generate charts for given symbols"""
        symbols = context.args
        
        if not symbols:
            update.message.reply_text("请提供股票代码，例如 /chart TSLA AAPL NVDA")
            return
            
        # Send "processing" message
        processing_msg = update.message.reply_text("正在生成图表，请稍候...")
        
        try:
            for symbol in symbols:
                # Generate chart
                chart_path = self.chart_renderer.render(symbol.upper())
                
                # Verify image with PIL
                try:
                    with Image.open(chart_path) as img:
                        width, height = img.size  # Basic validation that image is valid
                except Exception as e:
                    update.message.reply_text(f"生成图表时出错 {symbol}: {str(e)}")
                    continue
                
                # Get AI analysis
                analysis = self.chart_analyzer.analyze(symbol.upper())
                
                # Send chart with analysis caption
                with open(chart_path, 'rb') as photo:
                    update.message.reply_photo(
                        photo=photo, 
                        caption=f"📊 {symbol.upper()} 技术分析\n\n{analysis}"
                    )
                
                # Clean up file after sending
                os.remove(chart_path)
            
            # Delete processing message after completion
            context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id
            )
        
        except Exception as e:
            update.message.reply_text(f"生成图表时出错: {str(e)}")
            
    def portfolio_command(self, update, context):
        """Handle /portfolio command - Generate charts for user portfolio"""
        # Get portfolio from user settings or use default
        try:
            # Replace with actual portfolio retrieval
            portfolio = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
            
            processing_msg = update.message.reply_text("正在生成投资组合概览...")
            
            # Generate summary of portfolio
            summary = "📈 投资组合概览\n\n"
            
            # Send individual charts with analysis
            for symbol in portfolio:
                # Generate chart
                chart_path = self.chart_renderer.render(symbol)
                
                # Verify image with PIL
                try:
                    with Image.open(chart_path) as img:
                        width, height = img.size  # Basic validation
                except Exception as e:
                    update.message.reply_text(f"生成图表时出错 {symbol}: {str(e)}")
                    continue
                
                # Get AI analysis
                analysis = self.chart_analyzer.analyze(symbol, brief=True)
                summary += f"• {symbol}: {analysis}\n\n"
                
                # Send chart
                with open(chart_path, 'rb') as photo:
                    update.message.reply_photo(
                        photo=photo, 
                        caption=f"{symbol} 走势图"
                    )
                
                # Clean up
                os.remove(chart_path)
            
            # Send portfolio summary
            update.message.reply_text(summary)
            
            # Delete processing message
            context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id
            )
                
        except Exception as e:
            update.message.reply_text(f"生成投资组合图表时出错: {str(e)}")
    
    def register_handlers(self, dispatcher):
        """Register command handlers with the dispatcher"""
        dispatcher.add_handler(CommandHandler("chart", self.chart_command))
        dispatcher.add_handler(CommandHandler("portfolio", self.portfolio_command)) 